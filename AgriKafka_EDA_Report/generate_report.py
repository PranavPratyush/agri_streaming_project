#!/usr/bin/env python
"""Reproducibly build the AgriKafka-Agent dataset and EDA report.

Reads the original baseline CSV and selected audited EDA exports. Writes only
to this output directory. Run with: py -3.13 generate_report.py
"""
from pathlib import Path
import json
import math
import re

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, Image, KeepTogether, PageBreak, HRFlowable)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data" / "open_meteo_karnataka_2024-10-05_to_2026-10-04.csv"
EDA = ROOT / "eda_output"
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)
PDF = HERE / "AgriKafka-Agent_Dataset_Description_and_EDA.pdf"
NAVY = colors.HexColor("#17365D")
BLUE = colors.HexColor("#DCEAF5")
PALE = colors.HexColor("#F2F6FA")
INK = colors.HexColor("#202934")
MUTED = colors.HexColor("#586776")
sns.set_theme(style="whitegrid", palette="deep", font="DejaVu Sans", font_scale=0.88)
plt.rcParams.update({"figure.dpi": 180, "savefig.dpi": 240, "axes.titlesize": 11,
                     "axes.labelsize": 9, "legend.fontsize": 8, "xtick.labelsize": 8,
                     "ytick.labelsize": 8})

df = pd.read_csv(DATA, parse_dates=["timestamp"])
meta = json.loads((ROOT / "data" / "open_meteo_metadata.json").read_text(encoding="utf-8"))
numeric = ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation",
           "vapour_pressure_deficit", "soil_moisture_0_to_7cm", "wind_speed_10m"]
units = {"temperature_2m":"°C", "relative_humidity_2m":"%", "dew_point_2m":"°C",
         "precipitation":"mm per hour", "vapour_pressure_deficit":"kPa",
         "soil_moisture_0_to_7cm":"m³/m³", "wind_speed_10m":"km/h"}
labels = {"temperature_2m":"Air temperature", "relative_humidity_2m":"Relative humidity",
          "dew_point_2m":"Dew point", "precipitation":"Precipitation",
          "vapour_pressure_deficit":"Vapour pressure deficit", "soil_moisture_0_to_7cm":"Modelled soil moisture (0–7 cm)",
          "wind_speed_10m":"Wind speed"}
stats = pd.read_csv(EDA / "summary_statistics.csv", index_col=0)
corr = pd.read_csv(EDA / "correlation_matrix.csv", index_col=0)
diurnal = pd.read_csv(EDA / "diurnal_means.csv")
lags = pd.read_csv(EDA / "rainfall_soil_moisture_lags.csv")
plaus = pd.read_csv(EDA / "physical_plausibility.csv")
anoms = pd.read_csv(EDA / "natural_anomaly_rates.csv")
dups = int(df.duplicated(["field_id", "timestamp"]).sum())
miss = int(df.isna().sum().sum())
per_field = df.groupby("field_id", sort=True).agg(n=("timestamp", "size"), start=("timestamp", "min"), end=("timestamp", "max"))
gaps = df.sort_values(["field_id", "timestamp"]).groupby("field_id")["timestamp"].diff().dropna()
gap_n = int((gaps > pd.Timedelta(hours=1)).sum())
row_count, col_count = df.shape
field_count = df.field_id.nunique()
start, end = df.timestamp.min(), df.timestamp.max()

def save_fig(name):
    plt.tight_layout()
    plt.savefig(FIG / name, bbox_inches="tight", facecolor="white")
    plt.close()

# Report-specific compact, high-resolution visuals derived from the CSV.
daily = df.groupby(["field_id", pd.Grouper(key="timestamp", freq="D")], as_index=False).agg(
    temperature_2m=("temperature_2m", "mean"), precipitation=("precipitation", "sum"),
    soil_moisture_0_to_7cm=("soil_moisture_0_to_7cm", "mean"))
daily["month"] = daily.timestamp.dt.month
daily["year"] = daily.timestamp.dt.year
state_daily = daily.groupby("timestamp").agg({"temperature_2m":"mean", "precipitation":"mean", "soil_moisture_0_to_7cm":"mean"})
fig, ax = plt.subplots(2, 1, figsize=(8.0, 4.2), sharex=True)
ax[0].plot(state_daily.index, state_daily.temperature_2m, color="#D2691E", lw=.8)
ax[0].set_ylabel("Mean temperature (°C)"); ax[0].set_title("Hourly source aggregated to daily location means")
ax[1].bar(state_daily.index, state_daily.precipitation, width=1.0, color="#5B9BD5", alpha=.75, label="Mean daily precipitation (mm/location)")
ax[1].set_ylabel("Precipitation (mm)"); ax[1].legend(loc="upper right", frameon=False)
for a in ax: a.set_xlabel("Date")
save_fig("fig01_temperature_precipitation.png")

fig, ax = plt.subplots(figsize=(8.0, 2.7))
ax.plot(state_daily.index, state_daily.soil_moisture_0_to_7cm, color="#2E7D5B", lw=.8)
ax.set_ylabel("Volumetric water content (m³/m³)"); ax.set_xlabel("Date")
ax.set_title("Daily mean modelled soil moisture across the ten virtual locations")
save_fig("fig02_soil_moisture.png")

fig, ax = plt.subplots(figsize=(8.0, 3.0))
ax.hist(df.relative_humidity_2m, bins=30, density=True, histtype="step", lw=1.8, color="#3274A1", label="Relative humidity (%)")
ax.set_xlabel("Relative humidity (%)"); ax.set_ylabel("Density", color="#3274A1")
ax.set_title("Pooled hourly distributions (separate native-unit axes)")
ax2=ax.twinx()
ax2.hist(df.vapour_pressure_deficit, bins=30, density=True, histtype="step", lw=1.8, color="#C44E52", label="VPD (kPa)")
ax2.set_xlabel("Value in native units"); ax2.set_ylabel("Density", color="#C44E52")
lines=ax.get_lines()+ax2.get_lines()
from matplotlib.lines import Line2D
ax.legend([Line2D([0],[0],color="#3274A1",lw=1.8),Line2D([0],[0],color="#C44E52",lw=1.8)],
          ["Relative humidity (%)","VPD (kPa)"],frameon=False)
save_fig("fig03_humidity_vpd_distribution.png")

fig, ax = plt.subplots(figsize=(7.3, 5.0))
short = ["Temp", "RH", "Dew point", "Rain", "VPD", "Soil moisture", "Wind"]
cm = corr.loc[numeric, numeric].copy(); cm.index = short; cm.columns = short
sns.heatmap(cm, annot=True, fmt=".2f", cmap="RdBu_r", center=0, vmin=-1, vmax=1,
            square=True, linewidths=.4, cbar_kws={"shrink":.78, "label":"Pearson r"}, ax=ax,
            annot_kws={"size":8})
ax.set_title("Pearson correlations (pooled hourly observations)")
save_fig("fig04_correlation_heatmap.png")

fig, ax = plt.subplots(figsize=(8.0, 3.2))
hourly = df.assign(hour=df.timestamp.dt.hour).groupby("hour").agg(
    temperature=("temperature_2m", "mean"), humidity=("relative_humidity_2m", "mean"),
    soil=("soil_moisture_0_to_7cm", "mean"))
ax.plot(hourly.index, hourly.temperature, marker="o", ms=3, color="#D2691E", label="Temperature (°C)")
ax.set_xlabel("Hour of day (local time)"); ax.set_ylabel("Temperature (°C)")
ax2 = ax.twinx(); ax2.plot(hourly.index, hourly.humidity, marker="s", ms=2.5, color="#3274A1", label="Relative humidity (%)")
ax2.set_ylabel("Relative humidity (%)")
ax.set_xticks(range(0,24,2)); ax.set_title("Pooled diurnal cycle; air variables use distinct axes")
lines = ax.get_lines()+ax2.get_lines(); ax.legend(lines, [l.get_label() for l in lines], loc="center right", frameon=False)
save_fig("fig05_diurnal_cycle.png")

fig, ax = plt.subplots(figsize=(8.0, 3.4))
field_stats = df.groupby("field_id").agg(
    soil=("soil_moisture_0_to_7cm", "mean"), temp=("temperature_2m", "mean"),
    vpd=("vapour_pressure_deficit", "mean"), rh=("relative_humidity_2m", "mean")).sort_values("soil")
field_stats.soil.plot(kind="bar", ax=ax, color="#5B9BD5", edgecolor="white")
ax.set_ylabel("Mean modelled soil moisture (m³/m³)"); ax.set_xlabel("Virtual location ID")
ax.set_title("Location-wise mean soil moisture over the full period"); ax.tick_params(axis="x", labelrotation=35)
save_fig("fig06_location_comparison.png")

def fnum(x, n=2):
    return f"{x:,.{n}f}"

styles = getSampleStyleSheet()
font_regular = Path("C:/Windows/Fonts/georgia.ttf")
font_bold = Path("C:/Windows/Fonts/georgiab.ttf")
if font_regular.exists() and font_bold.exists():
    pdfmetrics.registerFont(TTFont("Georgia", str(font_regular)))
    pdfmetrics.registerFont(TTFont("Georgia-Bold", str(font_bold)))
    F, FB = "Georgia", "Georgia-Bold"
else:
    F, FB = "Times-Roman", "Times-Bold"
styles.add(ParagraphStyle(name="BodyA", fontName=F, fontSize=8.25, leading=11.1, textColor=INK, spaceAfter=4.1, alignment=TA_LEFT))
styles.add(ParagraphStyle(name="SmallA", fontName=F, fontSize=7.0, leading=9.1, textColor=INK, spaceAfter=2))
styles.add(ParagraphStyle(name="TitleA", fontName=FB, fontSize=15.5, leading=19, alignment=TA_CENTER, textColor=NAVY, spaceBefore=3, spaceAfter=6))
styles.add(ParagraphStyle(name="H1A", fontName=FB, fontSize=10.7, leading=13, textColor=NAVY, spaceBefore=7, spaceAfter=4, keepWithNext=True))
styles.add(ParagraphStyle(name="H2A", fontName=FB, fontSize=8.7, leading=10.5, textColor=INK, spaceBefore=4, spaceAfter=2, keepWithNext=True))
styles.add(ParagraphStyle(name="CaptionA", fontName=F, fontSize=7.2, leading=9, textColor=MUTED, alignment=TA_CENTER, spaceBefore=2, spaceAfter=6))
styles.add(ParagraphStyle(name="HeaderA", fontName=FB, fontSize=9, leading=11, textColor=NAVY, alignment=TA_LEFT))
styles.add(ParagraphStyle(name="RightA", fontName=F, fontSize=7, leading=9, textColor=MUTED, alignment=2))
styles.add(ParagraphStyle(name="CellA", fontName=F, fontSize=6.8, leading=8.3, textColor=INK))
styles.add(ParagraphStyle(name="CellHeadA", fontName=FB, fontSize=6.8, leading=8, textColor=colors.white))

def P(text, style="BodyA"):
    return Paragraph(text, styles[style])

def section(n, title):
    return [P(f"{n}. {title}", "H1A"), HRFlowable(width="100%", thickness=.65, color=NAVY, spaceAfter=4)]

def make_table(headers, rows, widths, font=6.8, repeat=1):
    data = [[P(str(x), "CellHeadA") for x in headers]]
    for row in rows:
        data.append([x if isinstance(x, Paragraph) else P(str(x), "CellA") for x in row])
    t = Table(data, colWidths=widths, repeatRows=repeat, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,0),NAVY), ("GRID",(0,0),(-1,-1),.35,colors.HexColor("#8EA6BA")),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,BLUE]),
        ("VALIGN",(0,0),(-1,-1),"TOP"), ("LEFTPADDING",(0,0),(-1,-1),4),
        ("RIGHTPADDING",(0,0),(-1,-1),4), ("TOPPADDING",(0,0),(-1,-1),3.2),
        ("BOTTOMPADDING",(0,0),(-1,-1),3.2)]))
    return t

def figure(name, width=164*mm, caption=""):
    im = Image(str(FIG/name), width=width, height=width*0.42)
    im.hAlign="CENTER"
    return [im, P(caption,"CaptionA")]

story=[]
# Reference-like header band: no logo/motto asset exists in supplied project.
hdr = Table([[P("RV COLLEGE OF ENGINEERING®<br/><font size='7'>Department of Artificial Intelligence and Machine Learning</font>","HeaderA"),
              P("Go, change the world<br/><font size='6'>AI372IA · Stream Processing and Analytics</font>","RightA")]], colWidths=[111*mm,73*mm])
hdr.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LINEBELOW",(0,0),(-1,-1),1,NAVY),
                         ("LEFTPADDING",(0,0),(-1,-1),2),("RIGHTPADDING",(0,0),(-1,-1),2),
                         ("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
story += [hdr, Spacer(1,5), P("Data Set Description and Exploratory Data Analysis (EDA)","TitleA"),
          P("AgriKafka-Agent: Fault-Tolerant, Real-Time Agricultural Risk Monitoring and Decision Support","BodyA")]
details=[
 ["Project title", "AgriKafka-Agent: Fault-Tolerant, Real-Time Agricultural Risk Monitoring and Decision Support"],
 ["Students / USNs", "Aanish Khan — 1RV23AI002<br/>Daksh Chauhan — 1RV23AI028<br/>Pranav Pratyush — 1RV23AI133"],
 ["Faculty guides", "Dr. Vijayalakshmi M N (Associate Professor)<br/>Dr. S. Anupama Kumar (Associate Professor)"],
 ["Course", "AI372IA · Stream Processing and Analytics"],
 ["Department", "Department of Artificial Intelligence and Machine Learning"],
]
story += [make_table(["Project detail","Information"],details,[34*mm,150*mm]), Spacer(1,6),
          P(f"Dataset examined: {row_count:,} observations × {col_count} attributes from {field_count} virtual Karnataka locations; {start:%d %b %Y %H:%M}–{end:%d %b %Y %H:%M} (Asia/Kolkata), at hourly cadence. Source CSV and EDA exports are preserved; report figures are regenerated from the CSV.")]
story += section(1,"Overview of Data Sources")
story += [P("The analysis uses the project’s archived Open-Meteo Historical Weather API extract. Its metadata records hourly requests for seven environmental variables at ten coordinate-defined virtual study locations in Karnataka, from 5 October 2024 through 4 October 2026. The API supplies gridded historical/modelled environmental values, not direct observations from physical farm sensors. The metadata does not establish a specific underlying reanalysis product, so none is attributed here."),
          P("This dataset provides environmental context for replay and risk-monitoring pipeline design. It contains no verified crop-disease diagnoses, crop-health outcomes, or physical soil-sensor ground truth. The location identifiers denote representative virtual points, not instrumented farms.")]
story += [make_table(["Dataset / source","Type","Coverage","Rate / volume","Role"],[["Open-Meteo Historical Weather API", "Historical gridded environmental time series", "10 virtual Karnataka points; 5 Oct 2024–4 Oct 2026", "Hourly; 175,200 rows", "Baseline replay, environmental context and EDA"]],[38*mm,37*mm,43*mm,31*mm,35*mm]), Spacer(1,5)]
schema_rows=[]
for c in ["field_id","timestamp","latitude_requested","longitude_requested","latitude_grid","longitude_grid","elevation_m"]+numeric:
    schema_rows.append([c, str(df[c].dtype), units.get(c,"identifier / local timestamp / degrees / m"), "Metadata" if c not in numeric else "Environmental variable"])
story += [make_table(["Column","CSV dtype","Unit / representation","Role"],schema_rows,[55*mm,31*mm,56*mm,42*mm]),
          P("All numeric variables are stored in numeric CSV types; timestamp is parsed from a local-time string for analysis. The archived file contains seven analytical variables and seven structural/location fields.","SmallA"), PageBreak()]

story += section(2,"Dataset Characteristics and Data Quality")
story += [P(f"The source file has {row_count:,} rows and {col_count} columns, distributed evenly at {int(per_field.n.min()):,} records per location. Coverage is {start:%Y-%m-%d %H:%M} to {end:%Y-%m-%d %H:%M} local time. Across all locations, consecutive timestamp differences are exactly one hour; gaps longer than one hour: {gap_n}. Missing cells: {miss}; duplicate (field_id, timestamp) keys: {dups}. These checks describe this CSV snapshot and do not prove source-service completeness beyond the requested period."),
          P("Physical-bound checks in the existing EDA audit found values within the tested broad bounds: RH 0–100%, precipitation ≥0 mm, VPD ≥0 kPa and modelled volumetric soil moisture 0–1 m³/m³. The observed maxima and minima below include plausible extremes; a statistical outlier flag alone is not evidence of invalidity. Long zero-rain periods and repeated soil-moisture values can be natural dry-season patterns.")]
stat_rows=[]
for c in numeric:
    s=stats.loc[c]
    stat_rows.append([labels[c],units[c],f"{s['mean']:.3f}",f"{s['std']:.3f}",f"{s['min']:.3f}",f"{s['50%']:.3f}",f"{s['max']:.3f}"])
story += [make_table(["Variable","Unit","Mean","SD","Min","Median","Max"],stat_rows,[48*mm,29*mm,23*mm,23*mm,22*mm,24*mm,24*mm]),
          Spacer(1,4), P("Coverage by virtual location is balanced (17,520 hourly records each). The EDA audit reports no per-location gaps over one hour; each field spans the full two-year window.")]
field_rows=[]
for fid,r in per_field.iterrows():
    field_rows.append([fid, f"{r.n:,}",r.start.strftime("%Y-%m-%d"),r.end.strftime("%Y-%m-%d")])
story += [make_table(["Virtual location","Rows","Start","End"],field_rows,[52*mm,28*mm,47*mm,47*mm]), PageBreak()]

story += section(3,"Exploratory Data Analysis")
story += [P("The figures below are generated by this script from the verified dataset. Daily summaries pool the ten points with equal weight; distribution and Pearson-correlation analyses use pooled hourly rows. Pooled associations combine time and location effects and should not be read as causal effects or independent-sample inference.")]
story += figure("fig01_temperature_precipitation.png",160*mm,"Fig. 1. Daily mean air temperature and mean daily precipitation per virtual location, pooled over the ten locations. Precipitation bars show the mean daily sum, not statewide area totals.")
story += [P("Pooled temperature has a mean of 24.56 °C (range 11.2–41.2 °C). The hourly diurnal profile reaches its pooled minimum near 05:00 and maximum near 14:00 local time. Rainfall is sparse in the pooled hourly distribution (median 0 mm per hour), with episodic nonzero observations.")]
story += figure("fig02_soil_moisture.png",160*mm,"Fig. 2. Daily mean of the modelled 0–7 cm soil-moisture variable across virtual locations (m³/m³). This is a gridded estimate, not sensor ground truth.")
story += [P("The series varies over both seasonal and shorter time scales. The complete window contains two annual cycles; two years are not sufficient to establish stable long-run climate or agronomic baselines."),
          P("Relative humidity spans 6–100% (mean 67.84%); VPD spans 0–6.81 kPa (mean 1.18 kPa). Both are bounded/strongly skewed environmental measures, so the distribution view uses native-unit axes.")]
story += figure("fig03_humidity_vpd_distribution.png",155*mm,"Fig. 3. Pooled hourly distributions of relative humidity and VPD, shown with separate native-unit axes.")

story += section(3,"Exploratory Data Analysis (continued)")
story += figure("fig04_correlation_heatmap.png",132*mm,"Fig. 4. Pearson correlation matrix for seven pooled hourly environmental variables. Strong contemporaneous association does not imply causal direction.")
story += [P(f"The strongest absolute associations include VPD with relative humidity (r = {corr.loc['vapour_pressure_deficit','relative_humidity_2m']:.2f}) and temperature (r = {corr.loc['vapour_pressure_deficit','temperature_2m']:.2f}). Modelled soil moisture has moderate pooled association with dew point (r = {corr.loc['soil_moisture_0_to_7cm','dew_point_2m']:.2f}) and weaker association with hourly precipitation (r = {corr.loc['soil_moisture_0_to_7cm','precipitation']:.2f}). Shared seasonality, location differences, variable construction and temporal autocorrelation can influence these pooled coefficients.")]
story += figure("fig05_diurnal_cycle.png",157*mm,"Fig. 5. Pooled mean diurnal cycle for temperature and relative humidity. Separate axes preserve native units.")
story += [P("The existing lag analysis reports maximum rainfall–soil-moisture cross-correlation at a lag of 0–2 h across locations (1 h for seven of ten), with the largest reported coefficient about 0.297. This is an exploratory correlation, not proof of infiltration timing or causation.")]
story += [PageBreak()]

story += section(3,"Exploratory Data Analysis (continued)")
story += figure("fig06_location_comparison.png",157*mm,"Fig. 6. Mean modelled 0–7 cm soil moisture by virtual location over the full study period; use for contextual comparison rather than farm ranking.")
story += [P("Location means differ, which motivates location-aware summaries. Such differences may reflect model-grid, climate and elevation characteristics; they are not evidence of actual field condition differences.")]

story += section(4,"Findings and Design Implications for AgriKafka-Agent")
implications=[
 ["Verified finding","Engineering implication"],
 ["Uniform 1 h records; no observed >1 h gaps in this extract.","Use event timestamps and field_id as the event key; validate cadence and apply watermarks/late-event policy. Test injected gaps and reordering separately."],
 ["No nulls or duplicate field-time keys in this baseline.","Retain runtime checks for required fields and key uniqueness. Define explicit missing-value, replay deduplication and idempotency behavior for future/live sources."],
 ["Strong VPD–RH and VPD–temperature associations; observable diurnal cycles.","Compare fixed thresholds with rolling, time-of-day and location-aware baselines. Treat thresholds as candidate rules requiring evaluation, not established risk cutoffs."],
 ["Rain–modelled-moisture peak lag is 0–2 h in exploratory cross-correlation.","A 1 h update window and a longer antecedent context window are reasonable candidates for replay tests. Do not hard-code the observed lag as a physical response law."],
 ["Some extreme values and long plateaus occur within broad physical bounds.","Flag boundary violations and robust statistical deviations for review; preserve valid extremes. Use multi-variable context before classifying a value as sensor fault."],
 ["Location-wise pooled means differ.","Partition by field_id; compare normalized or field-specific baselines alongside statewide summaries to reduce location confounding."],
 ["Dataset contains no labels and no physical sensor observations.","Assess ingestion integrity and rule behavior with explicit synthetic fault-injection cases; assess crop-health performance only after obtaining independent expert labels or field outcomes."],
]
story += [make_table(implications[0],implications[1:],[70*mm,114*mm]), Spacer(1,5),
          P("The native cadence supports hourly tumbling aggregation for validation and candidate daily windows for cumulative summaries. Window size, lateness allowance and alert thresholds remain engineering choices to test under replay and injected delay, duplication, dropout, stuck-value, drift and out-of-range scenarios. Fault injections must be labelled synthetic and kept distinct from the untouched baseline.")]

story += section(5,"Limitations and Evaluation Considerations")
story += [P("The ten coordinates are virtual study locations. Open-Meteo historical values and the modelled 0–7 cm soil-moisture variable are not direct physical farm sensor measurements. The dataset includes meteorological context only: it has no crop species, growth stage, irrigation records, disease diagnoses, yield outcomes or expert-labelled crop-stress events. Consequently, the present data can support schema, continuity, replay, descriptive EDA and exploratory rule prototyping; it cannot establish crop-disease prediction accuracy, verified crop stress, or operational agricultural benefit."),
          P("The observed two-year span, ten points and selected variables limit geographic and temporal generalization. Correlation, lag and anomaly summaries are descriptive and affected by seasonality, serial dependence and spatial pooling. The fact-check audit corrected prior unsupported model attribution and overly strong causal/diurnal claims; the report uses verified quantities and qualified interpretations. Synthetic fault-injection evaluation can measure pipeline response under specified scenarios, but those outcomes are not natural failures or agricultural labels."),
          P("Independent field validation would require timestamp-aligned physical weather/soil observations and crop-specific, expert-reviewed health labels or outcomes. Useful future inputs include live weather observations, farm sensor telemetry, crop and management metadata, and satellite-derived vegetation indicators, each with provenance and quality checks.")]
story += section(6,"Reproducibility and References")
story += [P("The accompanying <i>generate_report.py</i> reads the source CSV, metadata and audited EDA exports; it writes report-only charts to <i>figures/</i>. Original data and EDA artifacts were preserved. The dataset source is the Open-Meteo Historical Weather API; its underlying model product is unspecified. RVCE logo and motto images were absent, so institutional artwork is not recreated.")]

def decorate(canvas, doc):
    canvas.saveState()
    w,h=A4
    canvas.setStrokeColor(NAVY); canvas.setLineWidth(.55)
    canvas.line(15*mm, 13*mm, w-15*mm, 13*mm)
    canvas.setFont(F,7); canvas.setFillColor(MUTED)
    canvas.drawString(16*mm,8.5*mm,"Go, change the world")
    canvas.drawRightString(w-16*mm,8.5*mm,f"AgriKafka-Agent · {doc.page}")
    canvas.restoreState()

doc=SimpleDocTemplate(str(PDF),pagesize=A4,rightMargin=15*mm,leftMargin=15*mm,topMargin=13*mm,bottomMargin=18*mm,
                      title="Data Set Description and Exploratory Data Analysis (EDA) — AgriKafka-Agent",
                      author="Aanish Khan; Daksh Chauhan; Pranav Pratyush",subject="Dataset description and exploratory data analysis")
doc.build(story,onFirstPage=decorate,onLaterPages=decorate)
print(json.dumps({"pdf":str(PDF),"pages":"created","rows":row_count,"columns":col_count,"locations":field_count,
                  "coverage_start":str(start),"coverage_end":str(end),"missing":miss,"duplicate_keys":dups,"gaps_gt_1h":gap_n,
                  "figures":[p.name for p in FIG.glob("*.png")]},indent=2))
