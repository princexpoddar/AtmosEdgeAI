import os
import math
import random
import logging
import pickle
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
import torch

from backend.app.core.database import City, Ward, Reading, Forecast, Station, StationReading
from backend.app.services.ml.config import config, MODELS_DIR, BASE_DIR
from backend.app.services.ml.features import engineer_features, get_temporal_feature_names
from backend.app.services.ml.preprocessing import (
    split_chronologically, 
    create_sequences_for_ward, 
    MLDataPipeline, 
    SpatiotemporalDataset,
    SCALER_PATH
)
from backend.app.services.ml.model import GlobalCNNLSTMForecaster
from backend.app.services.ml.engine import train_model, set_seed, CHECKPOINT_PATH
from backend.app.services.ml.evaluation import evaluate_predictions, save_metrics
from backend.app.services.ml.plotting import plot_learning_curves, plot_prediction_vs_actual, plot_residuals
from backend.app.services.data_pipeline.station_manager import StationManager
from backend.app.services.data_pipeline.preprocessor import FEATURE_CACHE_PATH

logger = logging.getLogger(__name__)

# Legacy class name maintained for compatibility
class CNNLSTMForecaster(torch.nn.Module):
    def __init__(self, input_dim, seq_len=24, hidden_dim=64, num_layers=1, output_dim=2):
        super(CNNLSTMForecaster, self).__init__()
        self.seq_len = seq_len
        self.hidden_dim = hidden_dim
        self.conv1d = torch.nn.Conv1d(
            in_channels=input_dim, 
            out_channels=hidden_dim, 
            kernel_size=3, 
            padding=1
        )
        self.relu = torch.nn.ReLU()
        self.lstm = torch.nn.LSTM(
            input_size=hidden_dim, 
            hidden_size=hidden_dim, 
            num_layers=num_layers, 
            batch_first=True
        )
        self.fc = torch.nn.Linear(hidden_dim, output_dim)
        
    def forward(self, x):
        x = x.permute(0, 2, 1)
        conv_out = self.relu(self.conv1d(x))
        conv_out = conv_out.permute(0, 2, 1)
        lstm_out, _ = self.lstm(conv_out)
        out = self.fc(lstm_out[:, -1, :])
        return out

def calculate_pm25_aqi(pm25: float) -> float:
    """
    Calculates sub-index for PM2.5 according to CPCB Indian AQI standards
    """
    if pm25 <= 30:
        return pm25 * (50.0 / 30.0)
    elif pm25 <= 60:
        return 50.0 + (pm25 - 30.0) * (50.0 / 30.0)
    elif pm25 <= 90:
        return 100.0 + (pm25 - 60.0) * (100.0 / 30.0)
    elif pm25 <= 120:
        return 200.0 + (pm25 - 90.0) * (100.0 / 30.0)
    elif pm25 <= 250:
        return 300.0 + (pm25 - 120.0) * (100.0 / 130.0)
    else:
        return 400.0 + (pm25 - 250.0) * (100.0 / 150.0)

def create_dataset_sequences(df, features, target_cols, seq_len=24, lead=24):
    """
    Legacy sliding window sequence generator. Maintained for compatibility.
    """
    X, y = [], []
    num_rows = len(df)
    for i in range(num_rows - seq_len - lead):
        seq_x = df.iloc[i : i + seq_len][features].values
        target_idx = i + seq_len - 1 + lead
        seq_y = df.iloc[target_idx][target_cols].values
        X.append(seq_x)
        y.append(seq_y)
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

def _save_forecast(
    db: Session, 
    ward_id: int, 
    timestamp: datetime, 
    forecast_time: datetime, 
    predicted_pm25: float, 
    predicted_no2: float, 
    predicted_aqi: float
) -> None:
    """
    Helper function to insert or update forecast entries in the database.
    """
    exists = db.query(Forecast).filter(
        Forecast.ward_id == ward_id,
        Forecast.timestamp == timestamp,
        Forecast.forecast_time == forecast_time
    ).first()
    
    if exists:
        exists.predicted_pm25 = predicted_pm25
        exists.predicted_no2 = predicted_no2
        exists.predicted_aqi = predicted_aqi
    else:
        fc = Forecast(
            ward_id=ward_id,
            timestamp=timestamp,
            forecast_time=forecast_time,
            predicted_pm25=predicted_pm25,
            predicted_no2=predicted_no2,
            predicted_aqi=predicted_aqi
        )
        db.add(fc)

def generate_forecasts_for_all(db: Session, retrain: bool = False) -> None:
    """
    Unified Forecasting Engine.
    - retrain=True: Loads station features from cache, trains the global spatiotemporal model, and saves weights.
    - retrain=False: Loads the model once, executes fast prediction on active stations, and maps them to Wards via Inverse Distance Weighting (IDW).
    """
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    
    # 1. Retrain Phase: Model updates entirely on station readings
    if retrain:
        print("   [ML Engine] Starting global model retraining using Station Feature Cache...")
        if not os.path.exists(FEATURE_CACHE_PATH):
            logger.error(f"Feature Cache not found at {FEATURE_CACHE_PATH}. Retraining aborted.")
            print(f"   [ML Engine] ERROR: Feature Cache file not found. Ingest historical data first.")
            return
            
        with open(FEATURE_CACHE_PATH, "rb") as f:
            station_dfs = pickle.load(f)
            
        if not station_dfs:
            logger.error("Feature Cache is empty. Retraining aborted.")
            return
            
        stations = db.query(Station).filter(Station.id.in_(list(station_dfs.keys()))).all()
        station_id_to_idx = {st.id: i for i, st in enumerate(stations)}
        
        # Load unique cities from DB
        cities = list(set([st.city for st in stations]))
        city_name_to_idx = {c: i for i, c in enumerate(cities)}
        
        train_dfs = {}
        val_dfs = {}
        test_dfs = {}
        static_features_dict = {}
        
        for st in stations:
            df = station_dfs[st.id]
            # Split chronologically
            train_df, val_df, test_df = split_chronologically(df)
            
            train_dfs[st.id] = train_df
            val_dfs[st.id] = val_df
            test_dfs[st.id] = test_df
            
            city_encoded = city_name_to_idx.get(st.city, 0)
            static_features_dict[st.id] = {
                "latitude": st.latitude,
                "longitude": st.longitude,
                "city_encoded": city_encoded
            }
            
        # Fit data pipeline scalers
        data_pipeline = MLDataPipeline()
        data_pipeline.fit(train_dfs, static_features_dict)
        data_pipeline.save(SCALER_PATH)
        
        train_seqs = []
        val_seqs = []
        test_seqs = []
        
        temporal_cols = get_temporal_feature_names()
        
        for st in stations:
            city_encoded = city_name_to_idx.get(st.city, 0)
            st_idx = station_id_to_idx[st.id]
            
            # Scale
            t_scaled = data_pipeline.transform_df(train_dfs[st.id])
            v_scaled = data_pipeline.transform_df(val_dfs[st.id])
            te_scaled = data_pipeline.transform_df(test_dfs[st.id])
            
            scaled_static = data_pipeline.transform_static(st.latitude, st.longitude, city_encoded)
            
            # Generate target sequences
            t_x, t_w, t_s, t_y = create_sequences_for_ward(t_scaled, st_idx, scaled_static[0], scaled_static[1], scaled_static[2], seq_len=config.seq_len)
            v_x, v_w, v_s, v_y = create_sequences_for_ward(v_scaled, st_idx, scaled_static[0], scaled_static[1], scaled_static[2], seq_len=config.seq_len)
            te_x, te_w, te_s, te_y = create_sequences_for_ward(te_scaled, st_idx, scaled_static[0], scaled_static[1], scaled_static[2], seq_len=config.seq_len)
            
            if len(t_x) > 0:
                train_seqs.append((t_x, t_w, t_s, t_y))
            if len(v_x) > 0:
                val_seqs.append((v_x, v_w, v_s, v_y))
            if len(te_x) > 0:
                test_seqs.append((te_x, te_w, te_s, te_y))
                
        # Merge datasets
        X_train_temp = np.concatenate([s[0] for s in train_seqs], axis=0)
        X_train_ward = np.concatenate([s[1] for s in train_seqs], axis=0)
        X_train_static = np.concatenate([s[2] for s in train_seqs], axis=0)
        y_train = np.concatenate([s[3] for s in train_seqs], axis=0)
        
        X_val_temp = np.concatenate([s[0] for s in val_seqs], axis=0)
        X_val_ward = np.concatenate([s[1] for s in val_seqs], axis=0)
        X_val_static = np.concatenate([s[2] for s in val_seqs], axis=0)
        y_val = np.concatenate([s[3] for s in val_seqs], axis=0)
        
        X_test_temp = np.concatenate([s[0] for s in test_seqs], axis=0)
        X_test_ward = np.concatenate([s[1] for s in test_seqs], axis=0)
        X_test_static = np.concatenate([s[2] for s in test_seqs], axis=0)
        y_test = np.concatenate([s[3] for s in test_seqs], axis=0)
        
        # Build dataloaders
        train_dataset = SpatiotemporalDataset(X_train_temp, X_train_ward, X_train_static, y_train)
        val_dataset = SpatiotemporalDataset(X_val_temp, X_val_ward, X_val_static, y_val)
        test_dataset = SpatiotemporalDataset(X_test_temp, X_test_ward, X_test_static, y_test)
        
        from torch.utils.data import DataLoader
        train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=config.batch_size, shuffle=False)
        test_loader = DataLoader(test_dataset, batch_size=config.batch_size, shuffle=False)
        
        # Train
        model, train_losses, val_losses = train_model(
            train_loader=train_loader,
            val_loader=val_loader,
            temporal_dim=len(temporal_cols),
            static_dim=3,
            num_wards=len(stations) + 1
        )
        
        # Save plots & metrics
        plot_learning_curves(train_losses, val_losses)
        
        model.eval()
        device = next(model.parameters()).device
        test_preds = []
        with torch.no_grad():
            for batch_x_temp, batch_x_ward, batch_x_static, _ in test_loader:
                batch_x_temp = batch_x_temp.to(device)
                batch_x_ward = batch_x_ward.to(device)
                batch_x_static = batch_x_static.to(device)
                preds = model(batch_x_temp, batch_x_ward, batch_x_static)
                test_preds.append(preds.cpu().numpy())
                
        y_pred = np.concatenate(test_preds, axis=0)
        y_pred_raw = data_pipeline.inverse_transform_targets(y_pred)
        y_test_raw = data_pipeline.inverse_transform_targets(y_test)
        
        metrics_dict, metrics_df = evaluate_predictions(y_test_raw, y_pred_raw)
        save_metrics(metrics_dict, metrics_df)
        
        plot_prediction_vs_actual(y_test_raw, y_pred_raw)
        plot_residuals(y_test_raw, y_pred_raw)
        
        print("   [ML Engine] Global model retraining on stations successfully finished.")
        
    # 2. Prediction / Fast Inference Phase
    # Performs forecast predictions for stations and maps to Wards via IDW
    stations = db.query(Station).all()
    station_id_to_idx = {st.id: i for i, st in enumerate(stations)}
    
    cities = list(set([st.city for st in stations]))
    city_name_to_idx = {c: i for i, c in enumerate(cities)}
    
    model_loaded = False
    if not os.path.exists(SCALER_PATH) or not os.path.exists(CHECKPOINT_PATH):
        print("   [ML Engine] Checkpoints not found. Using physics fallbacks.")
    else:
        try:
            data_pipeline = MLDataPipeline()
            data_pipeline.load(SCALER_PATH)
            
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            checkpoint = torch.load(CHECKPOINT_PATH, map_location=device)
            chk_cfg = checkpoint["config"]
            
            model = GlobalCNNLSTMForecaster(
                temporal_dim=chk_cfg["temporal_dim"],
                static_dim=chk_cfg["static_dim"],
                num_wards=chk_cfg["num_wards"],
                seq_len=chk_cfg["seq_len"],
                hidden_dim=chk_cfg["hidden_dim"],
                num_layers=chk_cfg["num_lstm_layers"],
                dropout=chk_cfg["dropout"],
                output_dim=6
            ).to(device)
            model.load_state_dict(checkpoint["model_state_dict"])
            model.eval()
            model_loaded = True
        except Exception as e:
            print(f"   [ML Engine] Error loading model: {e}. Fallbacks active.")
            model_loaded = False
            
    temporal_cols = get_temporal_feature_names()
    
    station_predictions = {}
    
    # Generate predictions per station
    for st in stations:
        # Fetch last 100 readings
        readings_query = db.query(StationReading).filter(
            StationReading.station_id == st.id,
            StationReading.timestamp <= now
        ).order_by(StationReading.timestamp.desc()).limit(100)
        readings_list = list(readings_query)
        readings_list.reverse()
        
        use_fallback = not model_loaded or len(readings_list) < 48
        
        if use_fallback:
            # Fallback estimation values for this station
            preds = {}
            for lead in [24, 48, 72]:
                latest_reading = readings_list[-1] if readings_list else None
                if latest_reading:
                    diurnal_t = 1.0 + 0.15 * math.sin((lead - 8) * math.pi / 12.0)
                    pred_pm = latest_reading.pm25 * diurnal_t * (1.0 + random.uniform(-0.1, 0.1))
                    pred_no2 = latest_reading.no2 * diurnal_t * (1.0 + random.uniform(-0.1, 0.1))
                else:
                    pred_pm = 100.0 if "Delhi" in st.city else 40.0
                    pred_no2 = 40.0 if "Delhi" in st.city else 16.0
                preds[lead] = (pred_pm, pred_no2)
            station_predictions[st.id] = preds
            continue
            
        try:
            data = []
            for r in readings_list:
                data.append({
                    "timestamp": r.timestamp,
                    "pm25": r.pm25,
                    "no2": r.no2,
                    "temp": r.temp,
                    "humidity": r.humidity,
                    "wind_speed": r.wind_speed,
                    "wind_deg": r.wind_deg,
                    "stagnation": r.stagnation,
                    "upwind_fire_intensity": r.upwind_fire_intensity,
                    "upwind_fire_count": r.upwind_fire_count
                })
            df = pd.DataFrame(data)
            df.set_index("timestamp", inplace=True)
            
            df_engineered = engineer_features(df, drop_na=True)
            if len(df_engineered) < config.seq_len:
                raise ValueError("Insufficient station history")
                
            df_scaled = data_pipeline.transform_df(df_engineered)
            last_seq = df_scaled.iloc[-config.seq_len:][temporal_cols].values
            
            city_encoded = city_name_to_idx.get(st.city, 0)
            scaled_static = data_pipeline.transform_static(st.latitude, st.longitude, city_encoded)
            
            x_temp_t = torch.tensor(last_seq, dtype=torch.float32).unsqueeze(0).to(device)
            x_ward_t = torch.tensor([station_id_to_idx[st.id]], dtype=torch.long).to(device)
            x_static_t = torch.tensor([scaled_static], dtype=torch.float32).to(device)
            
            with torch.no_grad():
                preds_scaled = model(x_temp_t, x_ward_t, x_static_t).cpu().numpy()
                
            preds_raw = data_pipeline.inverse_transform_targets(preds_scaled)[0]
            
            station_predictions[st.id] = {
                24: (preds_raw[0], preds_raw[3]),
                48: (preds_raw[1], preds_raw[4]),
                72: (preds_raw[2], preds_raw[5])
            }
        except Exception as e:
            logger.error(f"Inference fail for station {st.name}: {e}")
            preds = {}
            for lead in [24, 48, 72]:
                latest_reading = readings_list[-1] if readings_list else None
                if latest_reading:
                    pred_pm = latest_reading.pm25 * (1.0 + random.uniform(-0.1, 0.1))
                    pred_no2 = latest_reading.no2 * (1.0 + random.uniform(-0.1, 0.1))
                else:
                    pred_pm = 50.0
                    pred_no2 = 20.0
                preds[lead] = (pred_pm, pred_no2)
            station_predictions[st.id] = preds
            
    # Run Ward Aggregation Layer via IDW mapping
    station_mgr = StationManager()
    station_mgr.aggregate_station_predictions(db, station_predictions, now)
    
    print("Forecasting runs completed for all wards.")
