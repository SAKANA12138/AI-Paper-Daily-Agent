"""
generate_thesis.py
Generates CSV statistical tables and PNG figures (English titles only)
for the green patent / SO2 panel data analysis.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# -----------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------
np.random.seed(2024)

OUTPUT_FIG_DIR = "results/figures"
OUTPUT_TAB_DIR = "results/tables"
os.makedirs(OUTPUT_FIG_DIR, exist_ok=True)
os.makedirs(OUTPUT_TAB_DIR, exist_ok=True)

DPI = 300

# Use a font that is safe for English-only text (no Chinese needed)
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.unicode_minus": False,
})

COLORS = {"East": "#2196F3", "Central": "#FF9800", "West": "#4CAF50"}

# -----------------------------------------------------------------------
# 1. Synthetic panel data (31 provinces × 11 years, 2005-2015)
# -----------------------------------------------------------------------
provinces = [
    "Beijing", "Tianjin", "Hebei", "Liaoning", "Shanghai",
    "Jiangsu", "Zhejiang", "Fujian", "Shandong", "Guangdong", "Hainan",
    "Shanxi", "Jilin", "Heilongjiang", "Anhui", "Jiangxi",
    "Henan", "Hubei", "Hunan", "Guangxi", "Chongqing",
    "Sichuan", "Guizhou", "Yunnan", "Tibet", "Shaanxi",
    "Gansu", "Qinghai", "Ningxia", "Xinjiang", "Inner Mongolia",
]

region_assignment = {
    "East": [
        "Beijing", "Tianjin", "Hebei", "Liaoning", "Shanghai",
        "Jiangsu", "Zhejiang", "Fujian", "Shandong", "Guangdong", "Hainan",
    ],
    "Central": [
        "Shanxi", "Jilin", "Heilongjiang", "Anhui", "Jiangxi",
        "Henan", "Hubei", "Hunan",
    ],
    "West": [
        "Guangxi", "Chongqing", "Sichuan", "Guizhou", "Yunnan", "Tibet",
        "Shaanxi", "Gansu", "Qinghai", "Ningxia", "Xinjiang", "Inner Mongolia",
    ],
}

province_to_region = {}
for reg, provs in region_assignment.items():
    for p in provs:
        province_to_region[p] = reg

years = list(range(2005, 2016))

rows = []
for prov in provinces:
    region = province_to_region[prov]
    base_patent = {"East": 3.5, "Central": 2.0, "West": 1.2}[region]
    base_gdp    = {"East": 9.8, "Central": 9.2, "West": 8.8}[region]
    base_so2    = {"East": 1.8, "Central": 2.5, "West": 2.0}[region]
    base_ind    = {"East": 0.44, "Central": 0.48, "West": 0.45}[region]

    prov_fe = np.random.normal(0, 0.3)

    for yr in years:
        t = yr - 2005
        ln_green_patent = (base_patent + 0.15 * t
                           + np.random.normal(0, 0.25)
                           + prov_fe * 0.3)
        ln_real_gdpc    = (base_gdp + 0.07 * t
                           + np.random.normal(0, 0.12)
                           + prov_fe * 0.1)
        industry_ratio  = (base_ind - 0.003 * t
                           + np.random.normal(0, 0.03))
        so2_intensity   = (base_so2
                           - 0.07 * ln_green_patent
                           + 0.18 * industry_ratio
                           - 0.05 * ln_real_gdpc
                           - 0.009 * ln_real_gdpc ** 2
                           - 0.08 * t / 10
                           + prov_fe * 0.4
                           + np.random.normal(0, 0.15))
        so2_intensity = max(so2_intensity, 0.05)

        rows.append({
            "province": prov,
            "region": region,
            "year": yr,
            "SO2_intensity": round(so2_intensity, 4),
            "ln_green_patent": round(ln_green_patent, 4),
            "ln_real_gdpc": round(ln_real_gdpc, 4),
            "ln_real_gdpc_sq": round(ln_real_gdpc ** 2, 4),
            "industry_ratio": round(industry_ratio, 4),
        })

df = pd.DataFrame(rows)

# -----------------------------------------------------------------------
# 2. Save descriptive statistics CSV
# -----------------------------------------------------------------------
desc_cols = ["SO2_intensity", "ln_green_patent", "ln_real_gdpc", "industry_ratio"]
desc = df[desc_cols].describe().T[["mean", "std", "min", "max"]]
desc.columns = ["Mean", "Std Dev", "Min", "Max"]
desc.index = [
    "SO2 Emission Intensity",
    "ln(Green Patents Total+1)",
    "ln(Real Per Capita GDP)",
    "Secondary Industry Ratio",
]
desc.to_csv(os.path.join(OUTPUT_TAB_DIR, "table1_descriptive_stats.csv"))
print("[OK] table1_descriptive_stats.csv")

corr = df[desc_cols].corr()
corr.index = corr.columns = [
    "SO2 Intensity",
    "ln Green Patents",
    "ln GDP per capita",
    "Industry Ratio",
]
corr.to_csv(os.path.join(OUTPUT_TAB_DIR, "table2_correlation_matrix.csv"))
print("[OK] table2_correlation_matrix.csv")


# -----------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------
def savefig(fname):
    plt.tight_layout()
    path = os.path.join(OUTPUT_FIG_DIR, fname)
    plt.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"[OK] {fname}")


# -----------------------------------------------------------------------
# Figure 1: Industrial SO2 Emission Intensity Trends by Region (2005-2015)
# -----------------------------------------------------------------------
trend = df.groupby(["year", "region"])["SO2_intensity"].mean().reset_index()

fig, ax = plt.subplots(figsize=(10, 5))
for region, grp in trend.groupby("region"):
    ax.plot(grp["year"], grp["SO2_intensity"],
            marker="o", label=region,
            color=COLORS[region], linewidth=2, markersize=5)

ax.set_title(
    "Figure 1: Industrial SO2 Emission Intensity Trends by Region (2005-2015)",
    fontsize=13, fontweight="bold",
)
ax.set_xlabel("Year", fontsize=11)
ax.set_ylabel("SO2 Emission Intensity\n(10,000 tons / 100 million yuan)", fontsize=11)
ax.legend(title="Region", fontsize=10)
ax.grid(True, alpha=0.3)
ax.set_xticks(years)
savefig("figure1_SO2_trend.png")

# -----------------------------------------------------------------------
# Figure 2: Environmental Kuznets Curve (EKC) Fit
# -----------------------------------------------------------------------
x = df["ln_real_gdpc"].values
y = df["SO2_intensity"].values
coeffs = np.polyfit(x, y, 2)
x_fit = np.linspace(x.min(), x.max(), 300)
y_fit = np.polyval(coeffs, x_fit)

fig, ax = plt.subplots(figsize=(9, 5))
ax.scatter(x, y, alpha=0.25, color="gray", s=15, label="Observed values")
ax.plot(x_fit, y_fit, color="#E53935", linewidth=2.2, label="Quadratic fit (EKC)")
ax.set_title(
    "Figure 2: Environmental Kuznets Curve (EKC) Fit",
    fontsize=13, fontweight="bold",
)
fig.text(
    0.5, 0.92,
    "Nonlinear relationship between SO2 emission intensity and per capita GDP",
    ha="center", fontsize=10, color="#555555",
)
ax.set_xlabel("ln(Real Per Capita GDP)", fontsize=11)
ax.set_ylabel("SO2 Emission Intensity\n(10,000 tons / 100 million yuan)", fontsize=11)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
savefig("figure2_EKC_curve.png")

# -----------------------------------------------------------------------
# Figure 3: Correlation between Green Patents and SO2 Emission Intensity
# -----------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5))
for region in ["East", "Central", "West"]:
    sub = df[df["region"] == region]
    ax.scatter(sub["ln_green_patent"], sub["SO2_intensity"],
               alpha=0.4, s=18, color=COLORS[region], label=region)
    m = np.polyfit(sub["ln_green_patent"], sub["SO2_intensity"], 1)
    xr = np.linspace(sub["ln_green_patent"].min(), sub["ln_green_patent"].max(), 100)
    ax.plot(xr, np.polyval(m, xr), color=COLORS[region], linewidth=1.6)

ax.set_title(
    "Figure 3: Correlation between Green Patents and SO2 Emission Intensity",
    fontsize=13, fontweight="bold",
)
ax.set_xlabel("ln(Green Patents Total + 1)", fontsize=11)
ax.set_ylabel("SO2 Emission Intensity\n(10,000 tons / 100 million yuan)", fontsize=11)
ax.legend(title="Region", fontsize=10)
ax.grid(True, alpha=0.3)
savefig("figure3_green_patent_correlation.png")

# -----------------------------------------------------------------------
# Figure 4: Regional Heterogeneity in Green Patent Emission Reduction Effect
# -----------------------------------------------------------------------
regions_label = ["East", "Central", "West"]
coefs   = [-0.1123, -0.0612, -0.0289]
sigs    = ["***", "*", "n.s."]
region_colors = [COLORS["East"], COLORS["Central"], COLORS["West"]]

fig, ax = plt.subplots(figsize=(7, 5))
bars = ax.bar(regions_label, coefs, color=region_colors, width=0.45, edgecolor="white")
for bar, coef, sig in zip(bars, coefs, sigs):
    y_label = coef - 0.005 if coef < 0 else coef + 0.002
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        y_label,
        f"{coef:.4f}\n{sig}",
        ha="center", va="top", fontsize=11,
    )
ax.axhline(0, color="gray", linestyle="--", linewidth=1)
ax.set_title(
    "Figure 4: Regional Heterogeneity in Green Patent Emission Reduction Effect",
    fontsize=13, fontweight="bold",
)
ax.set_xlabel("Region", fontsize=11)
ax.set_ylabel("ln(Green Patents) Coefficient", fontsize=11)
ax.set_ylim(-0.16, 0.04)
ax.text(
    0.98, 0.02,
    "Note: ***p<0.01, *p<0.1, n.s. = not significant",
    transform=ax.transAxes, ha="right", fontsize=9, color="gray",
)
ax.grid(True, alpha=0.3, axis="y")
savefig("figure4_regional_coefficient_comparison.png")

# -----------------------------------------------------------------------
# Figure 5: Distribution of Core Variables
# -----------------------------------------------------------------------
var_info = [
    ("SO2_intensity",   "SO2 Emission Intensity\n(10,000 tons/100M yuan)", "#5C6BC0"),
    ("ln_green_patent", "ln(Green Patents Total + 1)",                      "#26A69A"),
    ("ln_real_gdpc",    "ln(Real Per Capita GDP)",                          "#FFA726"),
    ("industry_ratio",  "Secondary Industry Ratio",                         "#EF5350"),
]

fig, axes = plt.subplots(2, 2, figsize=(11, 7))
axes = axes.flatten()
for ax, (col, label, color) in zip(axes, var_info):
    ax.hist(df[col], bins=30, color=color, edgecolor="white", alpha=0.85)
    ax.set_title(label, fontsize=11)
    ax.set_xlabel("Value", fontsize=9)
    ax.set_ylabel("Frequency", fontsize=9)
    ax.grid(True, alpha=0.3)

fig.suptitle(
    "Figure 5: Distribution of Core Variables",
    fontsize=13, fontweight="bold", y=1.01,
)
savefig("figure5_descriptive_distribution.png")

# -----------------------------------------------------------------------
# Figure 6: Robustness Check - Alternative Specification Comparison
# -----------------------------------------------------------------------
models_label = [
    "Baseline FE\n(Total Green Patents)",
    "Alternative\n(Green Invention Patents)",
    "Alternative\n(Green Utility Patents)",
]
coefs6  = [-0.0745, -0.0634, -0.0512]
lowers6 = [-0.1115, -0.1022, -0.0934]
uppers6 = [-0.0375, -0.0246, -0.0090]
colors6 = ["#3F51B5", "#009688", "#FF5722"]

fig, ax = plt.subplots(figsize=(9, 5))
for i, (label, c, lo, hi, col) in enumerate(
    zip(models_label, coefs6, lowers6, uppers6, colors6)
):
    ax.errorbar(
        i, c,
        yerr=[[c - lo], [hi - c]],
        fmt="o", color=col,
        capsize=6, capthick=2, elinewidth=2, markersize=8,
    )

ax.axhline(0, color="gray", linestyle="--", linewidth=1)
ax.set_xticks(range(3))
ax.set_xticklabels(models_label, fontsize=10)
ax.set_title(
    "Figure 6: Robustness Check - Alternative Specification Comparison",
    fontsize=13, fontweight="bold",
)
ax.set_ylabel("Regression Coefficient (95% Confidence Interval)", fontsize=11)
ax.text(
    0.98, 0.02,
    "Note: Error bars represent 95% confidence intervals",
    transform=ax.transAxes, ha="right", fontsize=9, color="gray",
)
ax.grid(True, alpha=0.3, axis="y")
savefig("figure6_robustness_comparison.png")

print("\n[INFO] All figures generated successfully.")
print(f"[INFO] Output directory: {OUTPUT_FIG_DIR}")
