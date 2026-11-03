"""
Baseline EDA for the Smart Agriculture Crop Health Monitoring backbone.

Run after acquisition:
    python eda_open_meteo.py

Outputs are written to:
    eda_output/
"""
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import adfuller
from scipy.stats import zscore

warnings.filterwarnings("ignore")

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
OUT = BASE / "eda_output"
OUT.mkdir(exist_ok=True)

csvs = list(DATA_DIR.glob("open_meteo_karnataka_*.csv"))
if not csvs:
    raise FileNotFoundError("Run acquire_open_meteo.py first.")
df = pd.read_csv(csvs[0], parse_dates=["timestamp"])

print("\n=== 1. STRUCTURE ===")
print("Shape:", df.shape)
print("\nDtypes:")
print(df.dtypes)
print("\nTimestamp range:", df["timestamp"].min(), "->", df["timestamp"].max())
print("\nMissingness (%):")
print((df.isna().mean() * 100).sort_values(ascending=False).round(3))

# ------------------------------------------------------------------
# 2. Duplicate timestamps and regularity
# ------------------------------------------------------------------
print("\n=== 2. REGULARITY ===")
dup = df.duplicated(["field_id", "timestamp"]).sum()
print("Duplicate field/timestamp rows:", dup)

gap_rows = []
for field, g in df.groupby("field_id"):
    g = g.sort_values("timestamp")
    delta = g["timestamp"].diff()
    counts = delta.dropna().value_counts()
    interval_str = str(counts.index[0]) if len(counts) else "N/A"
    print(f"{field}: most common interval = {interval_str}")
    mask = delta > pd.Timedelta(hours=1)
    if mask.any():
        gaps = g.loc[mask, ["timestamp"]].copy()
        gaps["field_id"] = field
        gaps["gap_duration"] = delta.loc[mask]
        gap_rows.append(gaps)

if gap_rows:
    gaps_df = pd.concat(gap_rows, ignore_index=True)
else:
    gaps_df = pd.DataFrame(columns=["field_id", "timestamp", "gap_duration"])
gaps_df.to_csv(OUT / "gaps_over_1h.csv", index=False)
print(f"Total gaps > 1h found: {len(gaps_df)}")

# ------------------------------------------------------------------
# 3. Physical plausibility
# ------------------------------------------------------------------
print("\n=== 3. PHYSICAL PLAUSIBILITY ===")
checks = {
    "relative_humidity_2m": ((df["relative_humidity_2m"] < 0) | (df["relative_humidity_2m"] > 100)),
    "soil_moisture_0_to_7cm": ((df["soil_moisture_0_to_7cm"] < 0) | (df["soil_moisture_0_to_7cm"] > 1)),
    "precipitation": (df["precipitation"] < 0),
    "vapour_pressure_deficit": (df["vapour_pressure_deficit"] < 0),
}
plausibility = pd.DataFrame({
    "variable": list(checks),
    "invalid_count": [int(x.sum()) for x in checks.values()],
})
plausibility["invalid_pct"] = 100 * plausibility["invalid_count"] / len(df)
print(plausibility)
plausibility.to_csv(OUT / "physical_plausibility.csv", index=False)

# ------------------------------------------------------------------
# 4. Summary distributions
# ------------------------------------------------------------------
vars_ = [
    "temperature_2m", "relative_humidity_2m", "dew_point_2m",
    "precipitation", "vapour_pressure_deficit",
    "soil_moisture_0_to_7cm", "wind_speed_10m"
]
summary = df[vars_].describe().T
summary.to_csv(OUT / "summary_statistics.csv")
print("\nSummary Statistics:")
print(summary)

sns.set_theme(style="whitegrid", font="sans-serif")
for v in vars_:
    plt.figure(figsize=(8, 4.5))
    sns.histplot(data=df, x=v, bins=60, kde=True, color="#2b5c8f")
    plt.title(f"Distribution: {v}", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel(v, fontsize=11)
    plt.ylabel("Frequency", fontsize=11)
    plt.tight_layout()
    plt.savefig(OUT / f"hist_{v}.png", dpi=180)
    plt.close()

# ------------------------------------------------------------------
# 5. Missingness heatmap by time
# ------------------------------------------------------------------
miss = df.set_index("timestamp")[vars_].isna().astype(float)
daily_miss = miss.resample("D").mean()
plt.figure(figsize=(12, 5))
date_ticks = np.linspace(0, len(daily_miss) - 1, 9, dtype=int)
date_labels = [daily_miss.index[i].strftime("%b %Y") for i in date_ticks]

ax = sns.heatmap(
    daily_miss.T,
    cmap="YlGnBu",
    vmin=0,
    vmax=1,
    cbar_kws={"label": "Missing Fraction (0 = Complete, 1 = Missing)"}
)
ax.set_xticks(date_ticks)
ax.set_xticklabels(date_labels, rotation=0, fontsize=10)
plt.title("Temporal Missingness Heatmap (Daily Aggregation across 10 Fields)", fontsize=13, fontweight="bold", pad=12)
plt.xlabel("Timeline (Oct 2024 - Oct 2026)", fontsize=11)
plt.ylabel("Core Agricultural Variable", fontsize=11)
plt.tight_layout()
plt.savefig(OUT / "missingness_heatmap.png", dpi=180)
plt.close()

# ------------------------------------------------------------------
# 6. Diurnal cycle
# ------------------------------------------------------------------
df["hour"] = df["timestamp"].dt.hour
diurnal = df.groupby(["field_id", "hour"])[
    ["temperature_2m", "relative_humidity_2m", "soil_moisture_0_to_7cm"]
].mean().reset_index()
diurnal.to_csv(OUT / "diurnal_means.csv", index=False)

unit_map = {
    "temperature_2m": "Temperature (°C)",
    "relative_humidity_2m": "Relative Humidity (%)",
    "soil_moisture_0_to_7cm": "Soil Moisture (m³/m³)"
}

for v in ["temperature_2m", "relative_humidity_2m", "soil_moisture_0_to_7cm"]:
    plt.figure(figsize=(9, 4.8))
    sns.lineplot(data=diurnal, x="hour", y=v, hue="field_id", palette="tab10", linewidth=1.8)
    plt.title(f"Diurnal Cycle (00:00 - 23:00 IST): {unit_map[v]}", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Hour of Day (IST)", fontsize=11)
    plt.ylabel(unit_map[v], fontsize=11)
    plt.xticks(range(0, 24, 2))
    plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, title="Field ID", fontsize=9)
    plt.tight_layout()
    plt.savefig(OUT / f"daily_cycle_{v}.png", dpi=180)
    plt.close()

# Combined 3-panel diurnal plot for presentation
fig, axes = plt.subplots(3, 1, figsize=(11, 11), sharex=True)
for i, v in enumerate(["temperature_2m", "relative_humidity_2m", "soil_moisture_0_to_7cm"]):
    sns.lineplot(data=diurnal, x="hour", y=v, hue="field_id", palette="tab10", ax=axes[i], legend=(i == 0))
    axes[i].set_ylabel(unit_map[v], fontsize=10, fontweight="bold")
    axes[i].set_title(f"Mean Hourly Profile: {unit_map[v]}", fontsize=11, fontweight="bold")
    if i == 0:
        axes[i].legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, title="Virtual Field", fontsize=8)
axes[2].set_xlabel("Hour of Day (IST)", fontsize=11, fontweight="bold")
axes[2].set_xticks(range(0, 24, 2))
fig.suptitle("Diurnal Micro-Climate Profiles Across 10 Karnataka Fields", fontsize=14, fontweight="bold", y=0.99)
fig.tight_layout()
fig.savefig(OUT / "daily_cycle_combined.png", dpi=180)
plt.close(fig)

# ------------------------------------------------------------------
# 7. Correlation heatmap
# ------------------------------------------------------------------
corr = df[vars_].corr()
corr.to_csv(OUT / "correlation_matrix.csv")
plt.figure(figsize=(9, 7.5))
mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", vmin=-1, vmax=1, square=True,
            cbar_kws={"label": "Pearson Correlation Coefficient", "shrink": 0.8})
plt.title("Correlation Matrix of Core Agrometeorological Variables", fontsize=13, fontweight="bold", pad=12)
plt.tight_layout()
plt.savefig(OUT / "correlation_heatmap.png", dpi=180)
plt.close()

# ------------------------------------------------------------------
# 8. Rainfall -> soil-moisture lag
# ------------------------------------------------------------------
lag_results = []
for field, g in df.groupby("field_id"):
    g = g.sort_values("timestamp").set_index("timestamp")
    for lag in range(0, 73):  # 0 to 72 hours
        rain = g["precipitation"].shift(lag)
        sm = g["soil_moisture_0_to_7cm"]
        c = rain.corr(sm)
        lag_results.append({"field_id": field, "lag_hours": lag, "correlation": c})
lag_df = pd.DataFrame(lag_results)
lag_df.to_csv(OUT / "rainfall_soil_moisture_lags.csv", index=False)

best = lag_df.loc[lag_df.groupby("field_id")["correlation"].idxmax()]
print("\nBest rainfall->soil moisture lag by field:")
print(best.sort_values("field_id"))

plt.figure(figsize=(10, 5.2))
sns.lineplot(data=lag_df, x="lag_hours", y="correlation", hue="field_id", palette="tab10", linewidth=1.6)
mean_lag = lag_df.groupby("lag_hours")["correlation"].mean().reset_index()
sns.lineplot(data=mean_lag, x="lag_hours", y="correlation", color="black", linewidth=2.5, linestyle="--", label="All-Fields Mean")
plt.title("Rainfall-to-Soil-Moisture Cross-Correlation vs Lag (0–72 Hours)", fontsize=13, fontweight="bold", pad=12)
plt.xlabel("Rainfall Lag (Hours Shifted)", fontsize=11)
plt.ylabel("Pearson Correlation with Soil Moisture", fontsize=11)
plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, title="Virtual Field", fontsize=8)
plt.tight_layout()
plt.savefig(OUT / "rainfall_to_moisture_lag.png", dpi=180)
plt.close()

# ------------------------------------------------------------------
# 9. VPD relationships
# ------------------------------------------------------------------
sample = df.sample(min(30000, len(df)), random_state=42)
plt.figure(figsize=(7.5, 5))
sns.scatterplot(data=sample, x="vapour_pressure_deficit",
                y="soil_moisture_0_to_7cm", hue="field_id", palette="tab10", alpha=0.25, s=16)
plt.title("Vapour Pressure Deficit (VPD) vs Soil Moisture", fontsize=13, fontweight="bold", pad=12)
plt.xlabel("Vapour Pressure Deficit (kPa)", fontsize=11)
plt.ylabel("Soil Moisture (0 to 7 cm, m³/m³)", fontsize=11)
plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, title="Virtual Field", fontsize=8)
plt.tight_layout()
plt.savefig(OUT / "vpd_vs_soil_moisture.png", dpi=180)
plt.close()

plt.figure(figsize=(7.5, 5))
sns.scatterplot(data=sample, x="temperature_2m",
                y="vapour_pressure_deficit", hue="field_id", palette="tab10", alpha=0.25, s=16)
plt.title("Ambient Temperature vs Vapour Pressure Deficit (VPD)", fontsize=13, fontweight="bold", pad=12)
plt.xlabel("Temperature at 2m (°C)", fontsize=11)
plt.ylabel("Vapour Pressure Deficit (kPa)", fontsize=11)
plt.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0, title="Virtual Field", fontsize=8)
plt.tight_layout()
plt.savefig(OUT / "temperature_vs_vpd.png", dpi=180)
plt.close()

# ------------------------------------------------------------------
# 10. Sensor-health patterns: repeated values / flatlines / sudden jumps
# ------------------------------------------------------------------
health_rows = []
for field, g in df.groupby("field_id"):
    g = g.sort_values("timestamp")
    for v in vars_:
        s = g[v]
        is_diff = s.ne(s.shift())
        group_ids = is_diff.cumsum()
        run_lengths = group_ids.value_counts(sort=False)
        repeated_runs = run_lengths[run_lengths > 1]
        
        diffs = s.diff().abs().dropna()
        max_jump = float(diffs.max()) if len(diffs) else 0.0
        p99_9_jump = float(diffs.quantile(0.999)) if len(diffs) else 0.0
        flatline_ge_6h = int((run_lengths >= 6).sum())
        
        health_rows.append({
            "field_id": field,
            "variable": v,
            "longest_identical_run_hours": int(run_lengths.max()),
            "total_repeated_runs_count": int(len(repeated_runs)),
            "median_repeated_run_length": float(repeated_runs.median()) if len(repeated_runs) else 1.0,
            "max_1h_jump": round(max_jump, 4),
            "p99_9_1h_jump": round(p99_9_jump, 4),
            "flatline_runs_ge_6h": flatline_ge_6h,
        })
health = pd.DataFrame(health_rows)
health.to_csv(OUT / "repeated_value_health.csv", index=False)
print("\nLongest repeated-value runs summary (Top 10):")
print(health.sort_values("longest_identical_run_hours", ascending=False).head(10))

# ------------------------------------------------------------------
# 11. Natural anomalies: z-score and EWMA (All 7 Core Variables)
# ------------------------------------------------------------------
anom = []
for field, g in df.groupby("field_id"):
    g = g.sort_values("timestamp").copy()
    for v in vars_:
        s = g[v]
        z = (s - s.mean()) / s.std(ddof=0)
        natural_z = z.abs() > 3

        # EWMA residual: observation minus exponentially weighted moving average (span=24h)
        ewma = s.ewm(span=24, adjust=False).mean()
        resid = s - ewma
        threshold = resid.std(ddof=0) * 3
        natural_ewma = resid.abs() > threshold

        anom.append({
            "field_id": field,
            "variable": v,
            "n": int(s.notna().sum()),
            "zscore_gt_3": int(natural_z.sum()),
            "zscore_gt_3_pct": round(float(100 * natural_z.mean()), 3),
            "ewma_gt_3sigma": int(natural_ewma.sum()),
            "ewma_gt_3sigma_pct": round(float(100 * natural_ewma.mean()), 3),
        })

anom_df = pd.DataFrame(anom)
anom_df.to_csv(OUT / "natural_anomaly_rates.csv", index=False)
print("\nNatural anomaly rate summary by variable (Mean across fields):")
print(anom_df.groupby("variable")[["zscore_gt_3_pct", "ewma_gt_3sigma_pct"]].mean().round(3))

# Target Chart 5: Natural Anomaly Example Visualization (Representative Field Window)
rep_field = "KA_BENGALURU"
rep_data = df[df["field_id"] == rep_field].sort_values("timestamp").set_index("timestamp")
sample_window = rep_data.loc["2025-04-01":"2025-05-15"]  # 45-day pre-monsoon dry/hot season

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7.5), sharex=True)

# Temperature Panel
t_obs = sample_window["temperature_2m"]
t_ewma = t_obs.ewm(span=24, adjust=False).mean()
t_std = (t_obs - t_ewma).std(ddof=0)
t_anom_mask = (t_obs - t_ewma).abs() > 3 * t_std

ax1.plot(sample_window.index, t_obs, label="Observed Temperature", color="#1f77b4", alpha=0.7, linewidth=1.2)
ax1.plot(sample_window.index, t_ewma, label="24h EWMA Baseline", color="#ff7f0e", linewidth=1.6)
ax1.fill_between(sample_window.index, t_ewma - 3 * t_std, t_ewma + 3 * t_std, color="#ff7f0e", alpha=0.15, label="±3σ EWMA Control Band")
if t_anom_mask.any():
    ax1.scatter(sample_window.index[t_anom_mask], t_obs[t_anom_mask], color="red", s=32, zorder=5, label="Natural Anomaly (|residual| > 3σ)")
ax1.set_ylabel("Temperature (°C)", fontsize=11, fontweight="bold")
ax1.set_title(f"Baseline Natural Anomaly Detection: Temperature ({rep_field})", fontsize=12, fontweight="bold")
ax1.legend(loc="upper right", fontsize=8.5)

# Precipitation / Soil Moisture Panel
sm_obs = sample_window["soil_moisture_0_to_7cm"]
sm_ewma = sm_obs.ewm(span=24, adjust=False).mean()
sm_std = (sm_obs - sm_ewma).std(ddof=0)
sm_anom_mask = (sm_obs - sm_ewma).abs() > 3 * sm_std

ax2.plot(sample_window.index, sm_obs, label="Observed Soil Moisture", color="#2ca02c", alpha=0.8, linewidth=1.2)
ax2.plot(sample_window.index, sm_ewma, label="24h EWMA Baseline", color="#d62728", linewidth=1.6)
ax2.fill_between(sample_window.index, sm_ewma - 3 * sm_std, sm_ewma + 3 * sm_std, color="#d62728", alpha=0.15, label="±3σ EWMA Control Band")
if sm_anom_mask.any():
    ax2.scatter(sample_window.index[sm_anom_mask], sm_obs[sm_anom_mask], color="darkred", s=32, zorder=5, label="Natural Anomaly (|residual| > 3σ)")
ax2.set_ylabel("Soil Moisture (m³/m³)", fontsize=11, fontweight="bold")
ax2.set_title(f"Baseline Natural Anomaly Detection: Soil Moisture ({rep_field})", fontsize=12, fontweight="bold")
ax2.set_xlabel("Observation Date (April - May 2025)", fontsize=11, fontweight="bold")
ax2.legend(loc="upper right", fontsize=8.5)

fig.suptitle("Natural Anomaly Baseline Identification (Before Fault Injection)", fontsize=14, fontweight="bold", y=0.99)
fig.tight_layout()
fig.savefig(OUT / "natural_anomaly_example.png", dpi=180)
plt.close(fig)

# ------------------------------------------------------------------
# 12. ADF + STL + Autocorrelation on representative field
# ------------------------------------------------------------------
field = df["field_id"].iloc[0]
g = df[df["field_id"] == field].sort_values("timestamp").set_index("timestamp")
series_daily = g["soil_moisture_0_to_7cm"].resample("D").mean().dropna()
series_hourly_sm = g["soil_moisture_0_to_7cm"].dropna()
series_hourly_temp = g["temperature_2m"].dropna()

# Autocorrelation across key operational streaming lags
lags_to_eval = [1, 2, 6, 12, 24, 48, 72, 168]
acf_sm = {f"lag_{k}h": round(float(series_hourly_sm.autocorr(lag=k)), 4) for k in lags_to_eval}
acf_temp = {f"lag_{k}h": round(float(series_hourly_temp.autocorr(lag=k)), 4) for k in lags_to_eval}

if len(series_daily) >= 30:
    adf_stat, adf_p, _, _, adf_crit, _ = adfuller(series_daily)
    with open(OUT / "stationarity.txt", "w") as f:
        f.write(f"Representative field: {field}\n")
        f.write(f"Daily soil moisture observations: {len(series_daily)}\n")
        f.write(f"ADF statistic: {adf_stat:.6f}\n")
        f.write(f"ADF p-value: {adf_p:.6g}\n")
        f.write(f"ADF critical values: {adf_crit}\n")
        f.write(f"Stationarity: {'Stationary (Reject H0)' if adf_p < 0.05 else 'Non-stationary (Fail to reject H0)'}\n\n")
        f.write("Hourly Autocorrelation - Soil Moisture:\n")
        for k, v in acf_sm.items():
            f.write(f"  {k}: {v}\n")
        f.write("\nHourly Autocorrelation - Temperature:\n")
        for k, v in acf_temp.items():
            f.write(f"  {k}: {v}\n")

    stl = STL(series_daily, period=7, robust=True).fit()
    fig = stl.plot()
    fig.set_size_inches(10.5, 7.5)
    fig.suptitle(f"STL Decomposition: Daily Mean Soil Moisture ({field})", fontsize=13, fontweight="bold", y=0.99)
    fig.tight_layout()
    fig.savefig(OUT / "stl_soil_moisture_representative_field.png", dpi=180)
    plt.close(fig)

# ------------------------------------------------------------------
# 13. Streaming-readiness metrics
# ------------------------------------------------------------------
rows = len(df)
fields_count = df["field_id"].nunique()
t_min = df["timestamp"].min()
t_max = df["timestamp"].max()
hours = (t_max - t_min).total_seconds() / 3600 + 1

with open(OUT / "streaming_readiness.txt", "w") as f:
    f.write("=" * 60 + "\n")
    f.write("SMART AGRICULTURE STREAMING READINESS SPECIFICATION\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"Virtual Fields Count: {fields_count}\n")
    f.write(f"Total Observation Records: {rows:,}\n")
    f.write(f"Start Timestamp: {t_min}\n")
    f.write(f"End Timestamp: {t_max}\n")
    f.write(f"Total Dataset Duration (Source Hours): {hours:,.0f} hours ({hours/24:.1f} days / {hours/24/365.25:.2f} years)\n\n")
    f.write("STREAMING REPLAY CHARACTERISTICS:\n")
    f.write(f"  - Real-world production rate: 10 events/hour (1 event/field/hour)\n")
    f.write(f"  - Nominal replay assumption: 1 source hour = 1 real second\n")
    f.write(f"  - Nominal streaming ingestion throughput: {fields_count} events/second\n")
    f.write(f"  - Accelerated replay (10x, 1 source hour = 100ms): {fields_count * 10} events/second\n")
    f.write(f"  - Accelerated replay (60x, 1 source min = 1 sec): {fields_count * 60} events/second\n")
    f.write(f"  - Total run duration at nominal 1x replay: {rows / fields_count:.0f} seconds (~{rows / fields_count / 3600:.2f} hours)\n\n")
    f.write("RECOMMENDED STREAMING WINDOW CONFIGURATIONS:\n")
    f.write("  1. Tumbling 1-Hour Window:\n")
    f.write("     - Purpose: Freshness validation, physical limit checks, multi-parameter packet assembly.\n")
    f.write("     - Latency budget: Immediate upon hourly arrival.\n")
    f.write("  2. Sliding 6-Hour Window (Slide = 1 Hour):\n")
    f.write("     - Purpose: Rapid rate-of-change detection (e.g. abrupt soil drying, temperature spike).\n")
    f.write("  3. Hopping / Tumbling 24-Hour Window:\n")
    f.write("     - Purpose: Diurnal cycle baseline calculation, daily precipitation accumulation, min/max temperatures, EWMA reference.\n")
    f.write("  4. Hopping / Tumbling 72-Hour Window:\n")
    f.write("     - Purpose: Cumulative rainfall-to-soil-moisture response tracking, multi-day drought stress detection.\n\n")
    f.write("STREAMING PAYLOAD SCHEMA (JSON):\n")
    f.write("{\n")
    f.write('  "field_id": "KA_BENGALURU",\n')
    f.write('  "timestamp": "2024-10-05T00:00:00",\n')
    f.write('  "temperature_2m": 22.4,\n')
    f.write('  "relative_humidity_2m": 88,\n')
    f.write('  "dew_point_2m": 20.3,\n')
    f.write('  "precipitation": 0.0,\n')
    f.write('  "vapour_pressure_deficit": 0.33,\n')
    f.write('  "soil_moisture_0_to_7cm": 0.342,\n')
    f.write('  "wind_speed_10m": 8.5,\n')
    f.write('  "latitude_grid": 12.9701,\n')
    f.write('  "longitude_grid": 77.5636,\n')
    f.write('  "elevation_m": 910.0\n')
    f.write("}\n")

print(f"\nEDA complete. All charts, tables, and readiness reports written to: {OUT}")

