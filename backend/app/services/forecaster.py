import os
import pickle
import numpy as np
import pandas as pd
import math
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.app.core.database import Ward, Reading, Forecast
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import StandardScaler

# PyTorch CNN-LSTM model implementation matching the spatiotemporal architecture in the project PDF
class CNNLSTMForecaster(nn.Module):
    def __init__(self, input_dim, seq_len=24, hidden_dim=64, num_layers=1, output_dim=2):
        super(CNNLSTMForecaster, self).__init__()
        self.seq_len = seq_len
        self.hidden_dim = hidden_dim
        
        # 1D Convolution over temporal dimension
        self.conv1d = nn.Conv1d(
            in_channels=input_dim, 
            out_channels=hidden_dim, 
            kernel_size=3, 
            padding=1
        )
        self.relu = nn.ReLU()
        
        # LSTM layer
        self.lstm = nn.LSTM(
            input_size=hidden_dim, 
            hidden_size=hidden_dim, 
            num_layers=num_layers, 
            batch_first=True
        )
        
        # Fully connected layer to predict PM2.5 and NO2 simultaneously
        self.fc = nn.Linear(hidden_dim, output_dim)
        
    def forward(self, x):
        # Input shape: (batch_size, seq_len, input_dim)
        # Permute for Conv1d: (batch_size, input_dim, seq_len)
        x = x.permute(0, 2, 1)
        conv_out = self.relu(self.conv1d(x))
        
        # Permute back for LSTM: (batch_size, seq_len, hidden_dim)
        conv_out = conv_out.permute(0, 2, 1)
        
        lstm_out, _ = self.lstm(conv_out)
        # Output of the last sequence step
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
    Constructs sliding window sequences for temporal training
    """
    X, y = [], []
    num_rows = len(df)
    
    for i in range(num_rows - seq_len - lead):
        # Input sequence from i to i + seq_len - 1
        seq_x = df.iloc[i : i + seq_len][features].values
        # Target at i + seq_len - 1 + lead
        target_idx = i + seq_len - 1 + lead
        seq_y = df.iloc[target_idx][target_cols].values
        
        X.append(seq_x)
        y.append(seq_y)
        
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

def generate_forecasts_for_all(db: Session, retrain: bool = False):
    """
    Core spatiotemporal Deep Learning Forecasting Engine.
    For each ward, extracts historical readings, precomputes upwind fire indicators,
    fits a CNN-LSTM model in PyTorch, and outputs 24h, 48h, and 72h future predictions for PM2.5 & NO2.
    """
    wards = db.query(Ward).all()
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    
    # Instantiate the singleton FIRMS processor
    from backend.app.services.firms_processor import get_firms_processor
    firms_proc = get_firms_processor()
    
    for ward in wards:
        # 1. Fetch historical readings for training or fast inference
        if not retrain:
            # Query only the last 100 readings for fast inference
            readings_query = db.query(Reading).filter(
                Reading.ward_id == ward.id,
                Reading.timestamp <= now
            ).order_by(Reading.timestamp.desc()).limit(100)
            readings_list = list(readings_query)
            readings_list.reverse()
        else:
            # Query all historical readings for full retraining
            readings_query = db.query(Reading).filter(
                Reading.ward_id == ward.id,
                Reading.timestamp <= now
            ).order_by(Reading.timestamp.asc())
            readings_list = list(readings_query)
            
        # Fallback if insufficient data
        if len(readings_list) < 48:
            print(f"   [ML Engine] Insufficient data for ward {ward.name} (<48 rows). Using physics fallback.")
            for lead in [24, 48, 72]:
                f_time = now + timedelta(hours=lead)
                diurnal_t = 1.0 + 0.15 * math.sin((f_time.hour - 8) * math.pi / 12.0)
                
                latest_reading = db.query(Reading).filter(
                    Reading.ward_id == ward.id
                ).order_by(Reading.timestamp.desc()).first()
                
                if latest_reading:
                    base_pm = latest_reading.pm25
                    base_no2 = latest_reading.no2
                    rand_shift = 1.0 + random.uniform(-0.15, 0.15)
                    pred_pm = base_pm * diurnal_t * rand_shift
                    pred_no2 = base_no2 * diurnal_t * rand_shift
                else:
                    pred_pm = 100.0 if "Delhi" in ward.city.name else 40.0
                    pred_no2 = 40.0 if "Delhi" in ward.city.name else 16.0
                
                pred_pm = float(round(max(5.0, pred_pm), 2))
                pred_no2 = float(round(max(2.0, pred_no2), 2))
                pred_aqi = float(round(calculate_pm25_aqi(pred_pm), 1))
                
                exists = db.query(Forecast).filter(
                    Forecast.ward_id == ward.id,
                    Forecast.timestamp == now,
                    Forecast.forecast_time == f_time
                ).first()
                
                if not exists:
                    fc = Forecast(
                        ward_id=ward.id,
                        timestamp=now,
                        forecast_time=f_time,
                        predicted_pm25=pred_pm,
                        predicted_no2=pred_no2,
                        predicted_aqi=pred_aqi
                    )
                    db.add(fc)
            db.commit()
            continue
            
        # 2. Convert database readings to DataFrame
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
                "hour": r.timestamp.hour,
                "dayofweek": r.timestamp.weekday()
            })
        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        
        # 3. Add dynamic upwind fire features
        print(f"   [ML Engine] Computing dynamic upwind fire features for ward {ward.name}...")
        fire_intensities = []
        fire_counts = []
        for idx, row in df.iterrows():
            metrics = firms_proc.get_upwind_fire_metrics(
                ward.latitude,
                ward.longitude,
                idx,
                row["wind_speed"],
                row["wind_deg"],
                ward.city.name
            )
            fire_intensities.append(metrics["upwind_fire_intensity"])
            fire_counts.append(metrics["upwind_fire_count"])
            
        df["upwind_fire_intensity"] = fire_intensities
        df["upwind_fire_count"] = fire_counts
        
        features = ["pm25", "no2", "temp", "humidity", "wind_speed", "stagnation", "upwind_fire_intensity", "upwind_fire_count", "hour", "dayofweek"]
        target_cols = ["pm25", "no2"]
        seq_len = 24
        
        # Setup paths for models and scalers caching
        models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "models"))
        os.makedirs(models_dir, exist_ok=True)
        scaler_path = os.path.join(models_dir, f"scaler_ward_{ward.id}.pkl")
        
        # Determine whether to load cached scaler or fit a new one
        scaler_X = StandardScaler()
        scaler_y = StandardScaler()
        scaler_loaded = False
        
        if not retrain and os.path.exists(scaler_path):
            try:
                with open(scaler_path, "rb") as f:
                    scaler_data = pickle.load(f)
                    scaler_X = scaler_data["scaler_X"]
                    scaler_y = scaler_data["scaler_y"]
                    scaler_loaded = True
            except Exception as e:
                print(f"   [ML Engine] Failed to load scaler from {scaler_path}: {e}. Fitting a new one.")
                
        try:
            if scaler_loaded:
                X_scaled = scaler_X.transform(df[features].values)
                df_scaled = pd.DataFrame(X_scaled, columns=features, index=df.index)
            else:
                X_scaled = scaler_X.fit_transform(df[features].values)
                y_scaled = scaler_y.fit_transform(df[target_cols].values)
                df_scaled = pd.DataFrame(X_scaled, columns=features, index=df.index)
                with open(scaler_path, "wb") as f:
                    pickle.dump({"scaler_X": scaler_X, "scaler_y": scaler_y}, f)
        except Exception as e:
            print(f"   [ML Engine] Scaling failed: {e}. Falling back to unscaled data.")
            df_scaled = df.copy()
            scaler_X = None
            scaler_y = None
        
        # 4. Process predictions for the forecasting horizons
        for lead in [24, 48, 72]:
            latest_row = df.iloc[-1]
            f_time = now + timedelta(hours=lead)
            
            # Construct training dataset from scaled dataframe
            X_train, y_train = create_dataset_sequences(df_scaled, features, target_cols, seq_len=seq_len, lead=lead)
            
            if len(X_train) < 5:
                # Fallback to diurnal physics prediction if history is too short for sequences
                pred_pm = latest_row["pm25"] * (1.0 + 0.15 * math.sin((f_time.hour - latest_row["hour"]) * math.pi / 12.0))
                pred_no2 = latest_row["no2"] * (1.0 + 0.1 * math.sin((f_time.hour - latest_row["hour"]) * math.pi / 12.0))
            else:
                model = CNNLSTMForecaster(input_dim=len(features), seq_len=seq_len)
                model_path = os.path.join(models_dir, f"model_ward_{ward.id}_lead_{lead}.pth")
                model_loaded = False
                
                # Try to load pre-trained weights to skip training
                if not retrain and os.path.exists(model_path):
                    try:
                        model.load_state_dict(torch.load(model_path))
                        model_loaded = True
                    except Exception as e:
                        print(f"   [ML Engine] Failed to load model from {model_path}: {e}. Retraining...")
                
                if not model_loaded:
                    if not retrain:
                        # Fallback to fast diurnal physics prediction to avoid blocking the sync thread
                        pred_pm = latest_row["pm25"] * (1.0 + 0.15 * math.sin((f_time.hour - latest_row["hour"]) * math.pi / 12.0))
                        pred_no2 = latest_row["no2"] * (1.0 + 0.1 * math.sin((f_time.hour - latest_row["hour"]) * math.pi / 12.0))
                    else:
                        print(f"   [ML Engine] Retraining CNN-LSTM forecaster model for ward {ward.name} (lead +{lead}h)...")
                        # Convert sequences to PyTorch float tensors
                        X_tensor = torch.tensor(X_train, dtype=torch.float32)
                        y_tensor = torch.tensor(y_train, dtype=torch.float32)
                        
                        criterion = nn.MSELoss()
                        optimizer = optim.Adam(model.parameters(), lr=0.005)
                        
                        model.train()
                        epochs = 30
                        batch_size = min(256, len(X_train))
                        dataset_size = len(X_train)
                        
                        for epoch in range(epochs):
                            permutation = torch.randperm(dataset_size)
                            for i in range(0, dataset_size, batch_size):
                                indices = permutation[i:i+batch_size]
                                batch_x, batch_y = X_tensor[indices], y_tensor[indices]
                                
                                optimizer.zero_grad()
                                outputs = model(batch_x)
                                loss = criterion(outputs, batch_y)
                                loss.backward()
                                optimizer.step()
                        
                        # Cache the trained model weights
                        try:
                            torch.save(model.state_dict(), model_path)
                        except Exception as e:
                            print(f"   [ML Engine] Failed to save model state: {e}")
                            
                        # Perform rolling inference using the last seq_len steps (instantaneous)
                        last_seq = df_scaled.iloc[-seq_len:][features].values
                        model.eval()
                        with torch.no_grad():
                            input_seq = torch.tensor(last_seq, dtype=torch.float32).unsqueeze(0)
                            pred = model(input_seq).numpy()[0]
                            
                            if scaler_y:
                                pred_raw = scaler_y.inverse_transform(pred.reshape(1, -1))[0]
                                pred_pm = float(pred_raw[0])
                                pred_no2 = float(pred_raw[1])
                            else:
                                pred_pm = float(pred[0])
                                pred_no2 = float(pred[1])
                else:
                    # Perform rolling inference using the last seq_len steps (instantaneous)
                    last_seq = df_scaled.iloc[-seq_len:][features].values
                    model.eval()
                    with torch.no_grad():
                        input_seq = torch.tensor(last_seq, dtype=torch.float32).unsqueeze(0)
                        pred = model(input_seq).numpy()[0]
                        
                        if scaler_y:
                            pred_raw = scaler_y.inverse_transform(pred.reshape(1, -1))[0]
                            pred_pm = float(pred_raw[0])
                            pred_no2 = float(pred_raw[1])
                        else:
                            pred_pm = float(pred[0])
                            pred_no2 = float(pred[1])
            
            pred_pm = round(max(5.0, pred_pm), 2)
            pred_no2 = round(max(2.0, pred_no2), 2)
            pred_aqi = round(calculate_pm25_aqi(pred_pm), 1)
            
            # Save predictions to SQLite database
            exists = db.query(Forecast).filter(
                Forecast.ward_id == ward.id,
                Forecast.timestamp == now,
                Forecast.forecast_time == f_time
            ).first()
            
            if not exists:
                fc = Forecast(
                    ward_id=ward.id,
                    timestamp=now,
                    forecast_time=f_time,
                    predicted_pm25=pred_pm,
                    predicted_no2=pred_no2,
                    predicted_aqi=pred_aqi
                )
                db.add(fc)
                
        db.commit()
    print("Forecasting runs completed for all wards.")
