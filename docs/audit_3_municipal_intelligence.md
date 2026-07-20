# Audit 3 — Municipal Intelligence & Rules Analysis

**Author / Persona**: Senior Environmental Data Scientist, Municipal Policy Architect, Technical Reviewer  
**Target Project**: `AtmosEdgeAI`  
**Date**: July 20, 2026  

---

## 1. System Overview & Architecture

The Intelligence Engine (`backend/app/services/intelligence/`) is a **stateless, rule-based expert system with heuristic scoring**. It does NOT use a machine learning model.

```
                    IntelligenceContext (DB + Weather + Satellite Fire)
                                           |
                                           v
                          [reasoning_engine.py]
                                           |
       +-------------------+---------------+-------------------+
       |                   |               |                   |
       v                   v               v                   v
[source_attribution.py] [confidence.py] [risk_assessment.py] [decision_engine.py]
(Rules: NO2 > 35,       (Heuristics:    (Composite Score:    (Maps Risk Score
 Wind > 270°, Fire > 15) Completeness,  0.4*AQI + 0.3*Wind  to CPCB GRAP Stage
                         Data Age)       + 0.2*Fire)          Directives)
       |                   |               |                   |
       +-------------------+---------------+-------------------+
                                           v
                                [report_generator.py]
                                (Formats Markdown Text)
```

---

## 2. Rule Execution, Evidence, and Confidence

### 2.1 Rule 1: Crop Burning Hypothesis
* **Trigger Condition**: `fire_intensity > 15.0` AND (`wind_deg > 270` OR `wind_deg < 90`).
* **Confidence Weight**: $0.5 + \min(0.4, (\text{fire\_intensity} - 15) / 100)$.
* **Evidence String**: `"NASA FIRMS satellite detected {fire_count} upwind hotspots in regional corridors."`

### 2.2 Rule 2: Vehicular Emissions Hypothesis
* **Trigger Condition**: `no2 > 35.0` OR `is_rush_hour` (Hour in $[8,9,10,11,17,18,19,20]$) OR `has_heavy_traffic_congestion`.
* **Confidence Weight**: Base $0.45$ + $0.20$ (if rush hour) + $0.15$ (if wind speed $< 5.0$ km/h).
* **Evidence String**: `"High NO2 sub-index indicating fuel combustion."`

### 2.3 Rule 3: Industrial Emissions Hypothesis
* **Trigger Condition**: Station name contains `"peenya"` or `"okhla"`.
* **Confidence Weight**: Base $0.40$ + $0.25$ (if NO2 $> 40.0$).
* **Evidence String**: `"Station sits inside active industrial monitoring quadrant."`

### 2.4 Rule 4: Construction & Mechanical Dust Hypothesis
* **Trigger Condition**: `humidity < 40.0` AND `temp > 28.0`.
* **Confidence Weight**: Base $0.40$ + $0.20$ (if wind speed $> 15.0$ km/h).
* **Evidence String**: `"Low relative humidity and elevated temperatures favor mechanical dust suspension."`

---

## 3. Heuristic Scoring Mechanics

### 3.1 Data Confidence Score (`confidence.py`)
$$\text{Confidence} = \min\left(1.0, \frac{\text{History Length}}{48.0}\right) \times \frac{\text{Quality Score}}{100.0}$$

### 3.2 Composite Risk Score (`risk_assessment.py`)
$$\text{Risk Score} = 0.4 \cdot \text{AQI}_{\text{norm}} + 0.3 \cdot \text{Stagnation} + 0.2 \cdot \text{Fire}_{\text{norm}} + 0.1 \cdot \text{Trend}$$

| Composite Risk Score Band | Risk Level | CPCB GRAP Stage Directive |
| :---: | :---: | :--- |
| $< 0.30$ | Low | Normal environmental monitoring. |
| $0.30 - 0.50$ | Medium | Enforce mechanical road sweeping, water sprinkling. |
| $0.50 - 0.75$ | High | Deploy anti-smog guns, restrict diesel generator usage. |
| $> 0.75$ | Critical | Ban non-essential construction, enforce GRAP Stage IV truck entry restriction. |

---

## 4. Root Cause: Why Bengaluru and Delhi Receive Similar Directives

* **Why it Happens**: `decision_engine.py` maps the numerical `Risk Score` directly to standard national CPCB GRAP (Graded Response Action Plan) intervention strings (e.g., `"Deploy anti-smog guns"`).
* **Where It Originated**: If Peenya (Bengaluru) reaches AQI 220 ("Poor"), it enters the "High" risk bracket and receives the **exact same GRAP directive string** as Anand Vihar (Delhi) at AQI 220 because `decision_engine.py` lacks state-level policy rules or regional regulatory context (e.g., KSPCB rules for Karnataka vs DPCC rules for Delhi NCR).

---

## 5. Scientific Evaluation of Rules

* **Evaluation**: The current rules are heuristic proxies (e.g., station name string matching `"peenya"` is hardcoded). They lack chemical mass closure or true Chemical Mass Balance (CMB) / Positive Matrix Factorization (PMF) receptor modeling.

---

## 6. Recommended Redesign for Region-Specific Interventions

1. **State-Level Regulatory Policy Mapping**: Partition policy directives by jurisdiction (DPCC for Delhi NCR, KSPCB for Karnataka).
2. **Chemical Species Ratios**: Incorporate $PM10/PM2.5$ ratios, $SO2$, and $CO$ to differentiate industrial coal burning from vehicular diesel vs biomass.
3. **GIS Spatial Zoning**: Replace station name string checks with explicit shapefile/GeoJSON GIS polygon intersections for industrial parks, heavy traffic corridors, and agricultural upwind buffers.
