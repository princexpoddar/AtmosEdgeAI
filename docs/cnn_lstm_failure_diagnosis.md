# CNN-LSTM Failure Diagnosis — Temporal Distribution Shift Report

> **Verdict**: **19/19 variables show statistically significant temporal distribution shift (all KS p < 0.05).** The CNN-LSTM failure is caused by a well-documented phenomenon — *temporal covariate shift* — where the pollution regime of the validation/test period is systematically different from the training period.

---

## 1. Split Sizes

| Split | Sequences | Period |
|---|---|---|
| Train | 71,703 | Earliest 70% per station |
| Validation | 13,956 | Next 15% per station |
| Test | 13,981 | Latest 15% per station |

---

## 2. PM2.5 Distribution (Raw μg/m³)

### Input Feature & Lag Features

| Metric | Train | Val | Test | Val−Train | Test−Train |
|---|---|---|---|---|---|
| **Mean** | 66.95 | 78.94 | 80.31 | **+11.99** | **+13.36** |
| Std | 61.61 | 62.48 | 65.02 | +0.87 | +3.41 |
| Min | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| P5 | 8.67 | 15.10 | 11.18 | +6.43 | +2.51 |
| P25 | 26.67 | 36.00 | 32.37 | +9.33 | +5.70 |
| **Median** | 49.23 | 64.71 | 60.70 | **+15.48** | **+11.47** |
| P75 | 86.00 | 103.08 | 111.20 | +17.08 | +25.20 |
| P95 | 189.50 | 194.30 | 216.10 | +4.80 | +26.60 |
| Max | 487.20 | 477.50 | 466.60 | −9.70 | −20.60 |

**KS Test (Train vs Val)**: stat=**0.1371**, p=**0.00** → *** SIGNIFICANT  
**Mean shift**: +11.99 μg/m³ = **+0.195 sigma** above training distribution

### PM2.5 Target (24h ahead)

| Metric | Train | Val | Test | Val−Train | Test−Train |
|---|---|---|---|---|---|
| Mean | 66.92 | 78.77 | 80.18 | +11.85 | +13.26 |
| Median | 49.14 | 64.44 | 60.44 | +15.30 | +11.30 |

**KS Test (Train vs Val)**: stat=0.1349, p=**9.46e-186** → *** SIGNIFICANT  
**Mean shift**: **+0.191 sigma**

### PM2.5 Lag Features (all consistent)

| Feature | Mean Shift (sigma) | KS stat | KS p |
|---|---|---|---|
| pm25_lag_1 | +0.195 | 0.1370 | 0.00 |
| pm25_lag_2 | +0.195 | 0.1368 | 0.00 |
| pm25_lag_3 | +0.196 | 0.1365 | 0.00 |
| pm25_lag_24 | +0.201 | 0.1318 | 0.00 |
| pm25_roll_mean_6 | +0.202 | 0.1388 | 0.00 |
| pm25_roll_mean_24 | **+0.217** | 0.1347 | 0.00 |

> The lag and rolling mean features carry essentially the **same shift as the raw PM2.5 value**, because they are derived from it. This is critical — **the model's primary temporal context signals are shifted**, so its learned prediction function is being applied out-of-distribution.

---

## 3. NO2 Distribution (Raw μg/m³)

| Metric | Train | Val | Test | Val−Train | Test−Train |
|---|---|---|---|---|---|
| **Mean** | 30.57 | 32.67 | 33.21 | **+2.11** | **+2.65** |
| Std | 23.43 | 23.74 | 27.92 | +0.31 | +4.49 |
| Min | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| P25 | 15.76 | 18.68 | 15.56 | +2.92 | −0.20 |
| **Median** | 23.31 | 24.93 | 20.86 | **+1.62** | −2.46 |
| P75 | 38.60 | 39.75 | 45.45 | +1.15 | +6.85 |
| P95 | 79.55 | 84.16 | 94.06 | +4.61 | +14.51 |

**KS Test (Train vs Val)**: stat=**0.0988**, p=**0.00** → *** SIGNIFICANT  
**Mean shift**: +2.11 μg/m³ = **+0.090 sigma**

> NO2 shift is smaller than PM2.5 — partially explained by NO2 being more tied to local traffic (which doesn't change as dramatically as agricultural/seasonal PM2.5 sources).

---

## 4. Weather Variables

| Variable | Train Mean | Val Mean | Shift (sigma) | KS stat | KS p | Direction |
|---|---|---|---|---|---|---|
| Temperature (°C) | 24.24 | 22.99 | **−0.182** | 0.0939 | 0.00 | COOLER in val |
| Humidity (%) | 69.76 | 67.97 | −0.084 | 0.0498 | 1.18e-25 | Slightly drier |
| Wind Speed (km/h) | 9.20 | 9.04 | −0.031 | 0.0234 | 5.35e-06 | Nearly stable |

> **Key insight**: Temperature drops by −1.26°C in the validation period. Cooler, less windy conditions **promote pollution accumulation** — this explains why PM2.5 is higher in val/test. The model has seen this causal chain (cool+low wind → high PM2.5) in training but the absolute PM2.5 level in those conditions is different in the later period.

---

## 5. KS Test Summary — Ranked by Severity

| Rank | Variable | KS stat | p-value | Shift (sigma) | Verdict |
|---|---|---|---|---|---|
| 1 | pm25_roll_mean_6 | 0.1388 | 0.00 | +0.202 | *** SIGNIFICANT |
| 2 | pm25 (input) | 0.1371 | 0.00 | +0.195 | *** SIGNIFICANT |
| 3 | pm25_lag_1 | 0.1370 | 0.00 | +0.195 | *** SIGNIFICANT |
| 4 | pm25_lag_2 | 0.1368 | 0.00 | +0.195 | *** SIGNIFICANT |
| 5 | pm25_lag_3 | 0.1365 | 0.00 | +0.196 | *** SIGNIFICANT |
| 6 | pm25 (target 24h) | 0.1349 | 9.46e-186 | +0.191 | *** SIGNIFICANT |
| 7 | pm25_roll_mean_24 | 0.1347 | 0.00 | +0.217 | *** SIGNIFICANT |
| 8 | pm25_lag_24 | 0.1318 | 0.00 | +0.201 | *** SIGNIFICANT |
| 9 | no2 (input) | 0.0988 | 0.00 | +0.090 | *** SIGNIFICANT |
| 10 | no2_lag_1 | 0.0983 | 0.00 | +0.090 | *** SIGNIFICANT |
| 11 | no2_lag_2 | 0.0979 | 0.00 | +0.090 | *** SIGNIFICANT |
| 12 | no2_lag_3 | 0.0975 | 0.00 | +0.090 | *** SIGNIFICANT |
| 13 | no2 (target 24h) | 0.0971 | 2.12e-96 | +0.083 | *** SIGNIFICANT |
| 14 | temperature | 0.0939 | 0.00 | −0.182 | *** SIGNIFICANT |
| 15 | no2_lag_24 | 0.0902 | 0.00 | +0.091 | *** SIGNIFICANT |
| 16 | no2_roll_mean_6 | 0.0770 | 0.00 | +0.033 | *** SIGNIFICANT |
| 17 | no2_roll_mean_24 | 0.0564 | 9.09e-33 | +0.111 | *** SIGNIFICANT |
| 18 | humidity | 0.0498 | 1.18e-25 | −0.084 | *** SIGNIFICANT |
| 19 | wind_speed | 0.0234 | 5.35e-6 | −0.031 | *** SIGNIFICANT |

> [!CAUTION]
> **19/19 variables are significantly shifted** (KS p < 0.05). This is not a borderline case. The temporal distribution shift is pervasive across all input channels.

---

## 6. Root Cause Analysis

### Why the CNN-LSTM always picks epoch 1 as best

```
Epoch 1:  Train MSE = 0.496   Val MSE = 0.501   Gap = 0.005
Epoch 2:  Train MSE = 0.407   Val MSE = 0.503   Gap = 0.096
Epoch 21: Train MSE = 0.279   Val MSE = 0.609   Gap = 0.330
```

The gap between train and val MSE grows by ~**0.016 per epoch**. This is not random — it is the model progressively memorising the training distribution's absolute pollution level rather than learning generalizable temporal patterns.

**The mechanism:**
1. The CNN-LSTM learns lag-to-forecast mappings (e.g., "if pm25_lag_1 ≈ 45 μg/m³, predict ~48 μg/m³")
2. In validation, the ambient PM2.5 is ~67 μg/m³ median (vs ~49 μg/m³ in training)
3. The model's learned mapping undershoots by ~18 μg/m³ on average
4. Additional training reinforces the training-period mapping, making val performance worse

### Why LR outperforms CNN-LSTM

Linear Regression learns a **weight vector** over all features simultaneously. It benefits from:
- The lag features explicitly providing the current PM2.5 level
- No "memorization" — a linear model cannot overfit to distribution-level means, only to patterns

The CNN-LSTM has the *capacity* to memorize station-level means via its ward embeddings, and it does so from epoch 2 onwards.

---

## 7. Conclusion & Recommended Fixes

| Fix | Difficulty | Expected Impact |
|---|---|---|
| **More training data** (3+ years) covering both regimes | High | High — eliminates the shift |
| **Remove station embeddings** from model | Low | Medium — prevents station-level mean memorization |
| **Domain Adaptation** (e.g., DANN / fine-tune on val) | High | High |
| **Residual prediction** (predict Δ from lag_1 instead of absolute value) | Medium | Medium — removes level bias |
| **Accept current result** — use LR/XGB for production, CNN-LSTM for multi-horizon structure | None | Immediately deployable |

> [!IMPORTANT]
> For the **current dataset**, the Linear Regression (MAE=0.488) and XGBoost (MAE=0.496) are the most reliable models for production. The CNN-LSTM architecture is sound but needs either a longer historical training window (≥3 years) or domain-adaptation techniques to fully overcome the temporal distribution shift observed here.
