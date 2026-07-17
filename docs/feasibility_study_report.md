# 📊 OpenAQ Nationwide Data Feasibility Report (India)

This report presents a nationwide analysis of ground air quality data availability across India, queried directly from the **OpenAQ V3 API**. 

---

## 🔍 1. Discovery Report

A search across the entire country code **IN** (India) discovered **745 active monitoring stations**.

### Pollutant & Historical Coverage Breakdown:
* **Total Stations Discovered**: `745`
* **Stations containing PM2.5**: `402` (54.0%)
* **Stations containing NO2**: `369` (49.5%)
* **Stations containing BOTH PM2.5 and NO2**: `362` (48.6%)
* **Temporal Sufficiency**:
  * Stations having **> 2 years** of history: `353`
  * Stations having **> 3 years** of history: `338`
  * Stations having **> 5 years** of history: `252`
  * Stations having **> 7 years** of history: `158`

---

## 🏆 2. Station Ranking (Top 20 Stations)

Stations are ranked by their **Quality Score**, which is calculated as follows:
* **35% History Length**: `min(100, (Years / 5.0) * 100)`
* **35% Completeness**: Percentage of observed hourly records relative to expected hourly records over the history.
* **30% Pollutant Coverage**: `100` if both PM2.5 and NO2 are monitored, `50` if only one, `0` if neither.

| Rank | ID | Station Name | City | State / Region | History (Years) | Completeness (%) | Quality Score | Available Pollutants |
|:---:|:---:|:---|:---|:---|:---:|:---:|:---:|:---|
| **1** | 407 | Zoo Park, Hyderabad - TSPCB | Hyderabad | Kolkata | 10.32 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **2** | 301 | Vikas Sadan, Gurugram - HSPCB | Gurugram | Kolkata | 10.31 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **3** | 235 | Anand Vihar, New Delhi - DPCC | Delhi | Kolkata | 10.44 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **4** | 2456 | Talkatora District Industries Center, Lucknow | Lucknow | Kolkata | 10.32 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **5** | 227384 | Jhunsi, Prayagraj - UPPCB | Agra | Kolkata | 5.12 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **6** | 223146 | Naharlagun, Naharlagun - APSPCB | Other | Kolkata | 5.30 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **7** | 2586 | Manali, Chennai - CPCB | Chennai | Kolkata | 10.32 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **8** | 2583 | Sector-6, Panchkula - HSPCB | Other | Kolkata | 10.32 | 100.0 | 100.0 | co, no, no2, nox, o3, pm25, rh, so2, temp, wind_direction, wind_speed |
| **9** | 44513 | Kadri, Mangalore - KSPCB | Other | Kolkata | 5.53 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, so2 |
| **10** | 42240 | Pan Bazaar, Guwahati - APCB | Guwahati | Kolkata | 5.55 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, so2, wind_direction, wind_speed |
| **11** | 228297 | SVPI Airport Hansol, Ahmedabad - IITM | Ahmedabad | Kolkata | 5.08 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **12** | 227931 | Sector-3B Avas Vikas Colony, Agra - UPPCB | Agra | Kolkata | 5.09 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **13** | 227536 | Chandkheda, Ahmedabad - IITM | Ahmedabad | Kolkata | 5.11 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **14** | 227535 | Manoharpur, Agra - UPPCB | Agra | Kolkata | 5.11 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **15** | 227534 | Gyaspur, Ahmedabad - IITM | Ahmedabad | Kolkata | 5.11 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **16** | 227533 | Rakhial, Ahmedabad - IITM | Ahmedabad | Kolkata | 5.11 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **17** | 227387 | Motilal Nehru NIT, Prayagraj - UPPCB | Agra | Kolkata | 5.12 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **18** | 227386 | B R Ambedkar University, Lucknow - UPPCB | Lucknow | Kolkata | 5.12 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **19** | 11607 | Lodhi Road, Delhi - IITM | Delhi | Kolkata | 5.12 | 100.0 | 100.0 | co, no2, o3, pm10, pm25, rh, so2, temp, wind_direction, wind_speed |
| **20** | 11606 | Borivali East, Mumbai - IITM | Mumbai | Kolkata | 5.67 | 100.0 | 100.0 | co, no, no2, nox, o3, pm10, pm25, rh, temp, wind_direction, wind_speed |

---

## 🏙️ 3. City Availability Summary (Target Cities)

This table summarizes data quality across the project's primary target cities in India:

| City | Number of Stations | Average Years Available | Average Completeness (%) | Average Quality Score |
|:---|:---:|:---:|:---:|:---:|
| **Delhi** | 78 | 4.37 | 40.5% | 48.26 |
| **Bengaluru** | 18 | 4.97 | 83.3% | 77.24 |
| **Mumbai** | 40 | 3.70 | 57.3% | 57.71 |
| **Hyderabad** | 20 | 4.97 | 79.8% | 76.83 |
| **Chennai** | 12 | 4.51 | 66.4% | 66.17 |
| **Lucknow** | 8 | 5.40 | 87.5% | 85.31 |
| **Kolkata** | 11 | 4.70 | 52.7% | 57.10 |
| **Pune** | 15 | 2.69 | 93.3% | 76.65 |
| **Ahmedabad** | 9 | 5.27 | 55.6% | 69.95 |

---

## 📈 4. Estimated Dataset Size & Download Times

Based on a **5-year history window** (2021–2026) for the target pollutants (PM2.5 and NO2), we estimate the following download volumes, API requests, and database storage sizes:

| Selection | Stations | Total Available Observations (Rows) | Sum of History Years | Unique Cities | Expected API Requests | Est. Download Time (Optimal) | Est. Storage Size (SQLite) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Top 10 Stations** | 10 | 5,039,126 | 83.5 yrs | 8 | ~880 | ~3 minutes | 576 MB |
| **Top 20 Stations** | 20 | 9,144,995 | 135.2 yrs | 10 | ~1,760 | ~6 minutes | 1.05 GB |
| **Top 50 Stations** | 50 | 19,297,208 | 318.2 yrs | 14 | ~4,400 | ~15 minutes | 2.21 GB |
| **Top 100 Stations** | 100 | 46,271,359 | 708.9 yrs | 23 | ~8,800 | ~30 minutes | 5.30 GB |

* **Optimal Download Speed**: Assumes thread pool fetches at 5 requests/sec with key.
* **Storage estimate**: Assumes SQLite database records require ~120 bytes per row (including indexing, forecasts, and attributions).

---

## 💡 5. Recommendations

### Are Delhi and Bengaluru Sufficient?
> [!IMPORTANT]
> **Yes, they are highly sufficient for the core project goals.** 
> * **Delhi (78 stations)** provides dense coverage of the Indo-Gangetic Plains, which experiences intense stubble burning and crop fire plumes (crucial for evaluating the Upwind Fire Transport Index).
> * **Bengaluru (18 stations)** provides the high-quality baseline representing Southern Indian meteorological conditions.
>
> Together, they give the model a stark contrast between a high-pollution, winter-inversion meteorology (Delhi) and a clean-background, tropical coastal-inland meteorology (Bengaluru).

### Recommended Action: Option B (Expand to Top 20 Stations)
We recommend **Option B (Expand to Top 20 Stations)** instead of only Delhi + Bengaluru:
1. **Climatic Diversity**: The Top 20 stations cover **10 distinct Indian cities** (Delhi, Gurugram, Lucknow, Prayagraj, Chennai, Mangalore, Guwahati, Ahmedabad, Agra, Mumbai). This adds coastal, dry Deccan plateau, and eastern plains data to the deep learning model.
2. **Model Generalization**: Spatiotemporal deep learning models (like our CNN-LSTM architecture) generalize much better when exposed to different meteorological baselines.
3. **Extremely Low Overhead**: Spanning 20 stations only requires **~6 minutes of optimal download time** and **1.05 GB** of SQLite database space, which is trivial for current local storage boundaries.

---

### 🛑 6. Do Not Download Yet
All background historical observation downloads have been successfully stopped. No observations have been downloaded. 

**Please review this report and provide your approval on the expansion option to proceed.**
