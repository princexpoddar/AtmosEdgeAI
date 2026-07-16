import os
import json
import base64
import logging
from io import BytesIO
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sklearn.feature_selection import mutual_info_regression

from backend.app.core.database import Station, StationReading
from backend.app.services.ml.config import config, BASE_DIR, MODELS_DIR
from backend.app.services.ml.features import get_temporal_feature_names

logger = logging.getLogger(__name__)

EDA_DIR = os.path.join(MODELS_DIR, "EDA")

class PipelineReporter:
    def __init__(self, eda_dir: str = EDA_DIR):
        self.eda_dir = eda_dir
        os.makedirs(self.eda_dir, exist_ok=True)

    def calculate_eda_metrics(self, df_combined: pd.DataFrame) -> None:
        """
        Computes Pearson, Spearman, Mutual Information (MI), and feature variances.
        Saves CSV and JSON files inside backend/models/EDA/.
        """
        logger.info("Computing EDA statistical tables (MI, Pearson, Spearman)...")
        if df_combined.empty:
            logger.warning("Empty dataframe provided for EDA calculation.")
            return
            
        numeric_df = df_combined.select_dtypes(include=[np.number]).dropna()
        if numeric_df.empty:
            logger.warning("No numeric columns available after dropping NaNs for EDA.")
            return
            
        # 1. Pearson and Spearman correlations
        pearson_corr = numeric_df.corr(method="pearson")
        spearman_corr = numeric_df.corr(method="spearman")
        
        pearson_corr.to_csv(os.path.join(self.eda_dir, "correlation_matrix_pearson.csv"))
        spearman_corr.to_csv(os.path.join(self.eda_dir, "correlation_matrix_spearman.csv"))
        
        # 2. Feature statistics (mean, std, min, max, variance, missingness)
        stats_df = pd.DataFrame()
        stats_df["mean"] = df_combined.mean(numeric_only=True)
        stats_df["std"] = df_combined.std(numeric_only=True)
        stats_df["min"] = df_combined.min(numeric_only=True)
        stats_df["max"] = df_combined.max(numeric_only=True)
        stats_df["variance"] = df_combined.var(numeric_only=True)
        stats_df["missing_pct"] = (df_combined.isnull().sum() / len(df_combined)) * 100.0
        
        stats_df.to_csv(os.path.join(self.eda_dir, "feature_statistics.csv"))
        
        # 3. Missingness report
        missing_df = pd.DataFrame(df_combined.isnull().sum(), columns=["missing_count"])
        missing_df["missing_pct"] = (df_combined.isnull().sum() / len(df_combined)) * 100.0
        missing_df.to_csv(os.path.join(self.eda_dir, "missingness.csv"))
        
        # 4. Mutual Information for target pollutants (PM2.5 and NO2)
        mi_scores = {}
        for target in ["pm25", "no2"]:
            if target in numeric_df.columns:
                X = numeric_df.drop(columns=[target])
                y = numeric_df[target]
                
                # Filter out ID columns
                X_cols = [c for c in X.columns if c not in ["id", "station_id", "ward_id"]]
                if X_cols:
                    mi = mutual_info_regression(X[X_cols], y, random_state=42)
                    mi_scores[target] = {X_cols[j]: float(mi[j]) for j in range(len(X_cols))}
                    
        with open(os.path.join(self.eda_dir, "feature_importance.json"), "w") as f:
            json.dump(mi_scores, f, indent=2)
            
        logger.info(f"EDA metrics saved to {self.eda_dir}")

    def generate_plots_base64(self, db: Session) -> Dict[str, str]:
        """
        Generates plots using Matplotlib and converts them to base64 images.
        """
        plots_b64 = {}
        
        # Plot 1: Discovered Station Map (Latitude vs Longitude scatter)
        stations = db.query(Station).all()
        if stations:
            lats = [s.latitude for s in stations]
            lngs = [s.longitude for s in stations]
            scores = [s.quality_score for s in stations]
            names = [s.name for s in stations]
            
            plt.figure(figsize=(8, 6))
            sc = plt.scatter(lngs, lats, c=scores, cmap="viridis", s=60, edgecolors="black", alpha=0.8)
            plt.colorbar(sc, label="Quality Score (0-100)")
            plt.xlabel("Longitude", fontsize=10)
            plt.ylabel("Latitude", fontsize=10)
            plt.title("Discovered Stations Spatial Distribution", fontsize=12, fontweight="bold")
            plt.grid(True, linestyle="--", alpha=0.5)
            
            buf = BytesIO()
            plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close()
            plots_b64["station_map"] = base64.b64encode(buf.getvalue()).decode("utf-8")
            
        # Plot 2: Quality Score distribution histogram
        if stations:
            plt.figure(figsize=(8, 4))
            plt.hist(scores, bins=15, color="teal", edgecolor="black", alpha=0.7)
            plt.axvline(np.mean(scores), color="red", linestyle="--", lw=2, label=f"Mean: {np.mean(scores):.1f}")
            plt.xlabel("Quality Score", fontsize=10)
            plt.ylabel("Frequency", fontsize=10)
            plt.title("Discovered Stations Quality Score Distribution", fontsize=12, fontweight="bold")
            plt.legend()
            plt.grid(True, linestyle="--", alpha=0.5)
            
            buf = BytesIO()
            plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close()
            plots_b64["quality_dist"] = base64.b64encode(buf.getvalue()).decode("utf-8")
            
        return plots_b64

    def compile_reports(self, db: Session, total_samples: int, discarded_stations: List[Dict[str, Any]]) -> None:
        """
        Creates the ML Readiness Report and the self-contained visual Dataset Audit HTML report.
        """
        stations = db.query(Station).all()
        
        # 1. Compile ML Readiness Report JSON
        train_count = int(0.70 * total_samples)
        val_count = int(0.15 * total_samples)
        test_count = int(0.15 * total_samples)
        
        readiness_report = {
            "total_usable_samples": total_samples,
            "training_samples": train_count,
            "validation_samples": val_count,
            "testing_samples": test_count,
            "stations_retained": len(stations),
            "stations_discarded": len(discarded_stations),
            "discarded_reasons": discarded_stations
        }
        
        with open(os.path.join(MODELS_DIR, "ml_readiness_report.json"), "w") as f:
            json.dump(readiness_report, f, indent=2)
            
        # Save quality scores to CSV
        q_scores = [{"station_id": s.id, "name": s.name, "city": s.city, "quality_score": s.quality_score} for s in stations]
        pd.DataFrame(q_scores).to_csv(os.path.join(self.eda_dir, "quality_scores.csv"), index=False)
        
        # 2. Compile Dataset Audit HTML Report
        plots = self.generate_plots_base64(db)
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>AtmosEdgeAI Dataset Ingestion Audit</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f7f9fa; color: #333; margin: 0; padding: 30px; }}
        .container {{ max-width: 1100px; margin: 0 auto; background: #fff; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); padding: 40px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #ecf0f1; padding-bottom: 15px; margin-top: 0; }}
        h2 {{ color: #34495e; margin-top: 30px; border-left: 5px solid #3498db; padding-left: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 25px; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        th {{ background-color: #edf2f7; color: #4a5568; font-weight: 600; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: #ebf8ff; border: 1px solid #bee3f8; border-radius: 8px; padding: 20px; text-align: center; }}
        .card h3 {{ margin: 0; color: #2b6cb0; font-size: 14px; text-transform: uppercase; }}
        .card p {{ margin: 10px 0 0 0; font-size: 28px; font-weight: bold; color: #2c5282; }}
        .plots {{ display: grid; grid-template-columns: 1fr 1fr; gap: 30px; margin-top: 25px; }}
        .plot-box {{ text-align: center; background: #fafafa; border: 1px solid #eaeaea; border-radius: 8px; padding: 15px; }}
        .plot-box img {{ max-width: 100%; height: auto; border-radius: 4px; }}
        .reason-tag {{ background: #fed7d7; color: #9b2c2c; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>AtmosEdgeAI Dataset Audit Report</h1>
        <p style="color: #718096; font-style: italic;">Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        
        <h2>Execution KPIs</h2>
        <div class="metrics-grid">
            <div class="card">
                <h3>Discovered Stations</h3>
                <p>{len(stations) + len(discarded_stations)}</p>
            </div>
            <div class="card">
                <h3>Stations Retained</h3>
                <p>{len(stations)}</p>
            </div>
            <div class="card">
                <h3>Usable Observations</h3>
                <p>{total_samples:,}</p>
            </div>
            <div class="card">
                <h3>Avg Quality Score</h3>
                <p>{np.mean([s.quality_score for s in stations]):.1f}</p>
            </div>
        </div>
        
        <h2>Spatial & Quality Analysis</h2>
        <div class="plots">
            <div class="plot-box">
                <h4>Spatial Distribution</h4>
                <img src="data:image/png;base64,{plots.get('station_map', '')}" alt="Station Distribution Map">
            </div>
            <div class="plot-box">
                <h4>Quality Scores Histogram</h4>
                <img src="data:image/png;base64,{plots.get('quality_dist', '')}" alt="Quality Distribution Plot">
            </div>
        </div>
        
        <h2>Stations Discarded (Quality Threshold Fails)</h2>
        <table>
            <thead>
                <tr>
                    <th>Station ID</th>
                    <th>Name</th>
                    <th>City</th>
                    <th>Reason</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for ds in discarded_stations:
            html_content += f"""
                <tr>
                    <td><code>{ds.get('station_id')}</code></td>
                    <td>{ds.get('name')}</td>
                    <td>{ds.get('city')}</td>
                    <td><span class="reason-tag">{ds.get('reason')}</span></td>
                </tr>
            """
            
        if not discarded_stations:
            html_content += "<tr><td colspan='4' style='text-align: center; color: #718096;'>No stations were discarded.</td></tr>"
            
        html_content += """
            </tbody>
        </table>
        
        <h2>Retained Stations Quality Scores</h2>
        <table>
            <thead>
                <tr>
                    <th>Station ID</th>
                    <th>Name</th>
                    <th>City</th>
                    <th>State</th>
                    <th>Coordinates</th>
                    <th>Quality Score</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for s in stations:
            html_content += f"""
                <tr>
                    <td><code>{s.id}</code></td>
                    <td>{s.name}</td>
                    <td>{s.city}</td>
                    <td>{s.state}</td>
                    <td>{s.latitude:.4f}, {s.longitude:.4f}</td>
                    <td><strong>{s.quality_score:.2f}</strong></td>
                </tr>
            """
            
        html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
        """
        
        # Save HTML audit file
        audit_path = os.path.join(MODELS_DIR, "dataset_audit.html")
        try:
            with open(audit_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"Dataset audit report generated successfully at {audit_path}")
        except Exception as e:
            logger.error(f"Failed saving HTML dataset audit: {e}")
