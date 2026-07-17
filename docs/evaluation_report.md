# AtmosEdge AI Model Evaluation & Explainability Report

This document presents the overall evaluation metrics, baseline model comparisons, inference benchmarks, and explainability audits for the atmospheric forecast pipelines.

---

## 1. Executive Summary & Model Leaderboard

A clean chronological split (70/15/15) was executed across all 36 active stations. Evaluation is conducted on the untouched **Test Set** containing **13,981 sequences**.

| Rank | Model | Overall MAE | Overall RMSE | Model Size (MB) | Inference Latency (ms/sample) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| 🥇 1 | **Linear Regression (Best Baseline)** | **0.4880** | **0.7267** | 0.027 MB | 0.00184 ms |
| 🥈 2 | **XGBoost Regressor** | **0.4965** | **0.7664** | 0.843 MB | 0.01405 ms |
| 🥉 3 | **Persistence Baseline** | **0.5104** | **0.8226** | 0.000 MB | 0.00002 ms |
| 4 | **Random Forest Regressor** | **0.5171** | **0.7729** | 2.716 MB | 0.00517 ms |
| 5 | **CNN-LSTM Forecaster (Best Weights)** | **0.5570** | **0.8392** | 0.948 MB | 0.04080 ms |

### Key Diagnostic Takeaways:
1. **Temporal Covariate Shift**: The test set mean shifts upward by **+0.195 sigma** for PM2.5 compared to the training set. Tabular models like Linear Regression and XGBoost generalize well because they map lag relationships directly. The CNN-LSTM struggles with capacity memorization and peaks at epoch 1.
2. **Model Efficiency**: Linear Regression and XGBoost are fast, lightweight, and deployable. Random Forest is bulky (2.72 MB) with higher latency. CNN-LSTM requires 0.95 MB but has higher CPU latency (0.041 ms).

---

## 2. Detailed Performance by Target Horizon

The models forecast PM2.5 and NO2 levels for $t+24$h, $t+48$h, and $t+72$h.

### PM2.5 Metrics (Standardized scale)

| Model | Avg MAE | Avg RMSE | 24h MAE | 48h MAE | 72h MAE |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Linear Regression** | **0.4827** | **0.7039** | 0.4269 | 0.4917 | 0.5294 |
| **XGBoost** | 0.4866 | 0.7317 | 0.4136 | 0.4957 | 0.5503 |
| **Persistence** | 0.5271 | 0.8097 | 0.4538 | 0.5365 | 0.5910 |
| **Random Forest** | 0.5051 | 0.7419 | 0.4540 | 0.5110 | 0.5503 |
| **CNN-LSTM** | 0.5453 | 0.7948 | 0.5238 | 0.5479 | 0.5642 |

### NO2 Metrics (Standardized scale)

| Model | Avg MAE | Avg RMSE | 24h MAE | 48h MAE | 72h MAE |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Linear Regression** | **0.4934** | **0.7495** | 0.4352 | 0.5043 | 0.5407 |
| **XGBoost** | 0.5064 | 0.8011 | 0.4304 | 0.5028 | 0.5860 |
| **Persistence** | 0.4938 | 0.8355 | 0.4309 | 0.5029 | 0.5475 |
| **Random Forest** | 0.5292 | 0.8038 | 0.4795 | 0.5385 | 0.5694 |
| **CNN-LSTM** | 0.5686 | 0.8835 | 0.5356 | 0.5729 | 0.5974 |

---

## 3. Visualizations

Here are the key diagnostic plots.

### Model Comparison
![Model Comparison Bar Chart](model_comparison_benchmark.png)

### Actual vs Predicted Time-Series
![Actual vs Predicted Time-Series](pm25_actual_vs_predicted.png)

### PM2.5 Error Histogram (Residuals)
![PM2.5 Error Histogram](pm25_error_histogram.png)

### Station Performance Map
![Station Performance Map](station_performance_map.png)

### XGBoost Feature Importance
![XGBoost Feature Importance](xgboost_feature_importance.png)

### SHAP Explainability Beeswarm Plot
![SHAP Beeswarm Plot](shap_xgboost_summary.png)

---

## 4. SHAP & Feature Importance Interpretation

The SHAP beeswarm plot reveals:
1. **Strong Autoregressive Signal**: The immediate lag values (`pm25_t` and `pm25_t-1`) dominate the predictions. A high current PM2.5 level strongly shifts predictions higher.
2. **Upwind Fire Transport**: The fire transport features (NASA FIRMS upwind fires multiplied by wind vectors) show an active positive SHAP contribution, indicating that the model successfully captures regional agricultural burning and transport.
3. **Weather Drivers**: Cooler temperature and high relative humidity contribute to higher predicted PM2.5, matching physical atmospheric inversion models.
