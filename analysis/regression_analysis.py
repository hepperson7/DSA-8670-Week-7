"""Regression of Ames home sale price on size, bedrooms, bathrooms, and neighborhood."""

from pathlib import Path
import os

import pandas as pd
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().with_name(".mplconfig")))
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter


DATA = Path(__file__).resolve().parents[1] / "AmesHousing-1.csv"

df = pd.read_csv(DATA)

# Half baths count as 0.5 bathroom. Basement and above-ground fixtures are
# summed into one interpretable bathroom-equivalent measure.
df["BathroomEquiv"] = (
    df["Bsmt Full Bath"] + 0.5 * df["Bsmt Half Bath"]
    + df["Full Bath"] + 0.5 * df["Half Bath"]
)

# Neighborhood summary statistics for the requested count variables.
summary = (
    df.groupby("Neighborhood")[["Bedroom AbvGr", "BathroomEquiv"]]
    .agg(["mean", "std", "min", "max"])
    .sort_index()
)
summary.columns = [f"{variable}_{stat}" for variable, stat in summary.columns]
summary_csv = Path(__file__).with_name("summary_statistics_by_neighborhood.csv")
summary_md = Path(__file__).with_name("summary_statistics_by_neighborhood.md")
summary_transcript = Path(__file__).with_name("summary_statistics_transcript.md")
summary.round(2).to_csv(summary_csv, index_label="Neighborhood", na_rep="NA")

headers = ["Neighborhood"] + [
    f"{variable} {stat}"
    for variable in ("Bedroom AbvGr", "Bathroom Equivalent")
    for stat in ("Mean", "SD", "Min", "Max")
]
md_lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
for neighborhood, row in summary.iterrows():
    values = [neighborhood] + ["—" if pd.isna(row[column]) else f"{row[column]:.2f}" for column in summary.columns]
    md_lines.append("| " + " | ".join(values) + " |")
table_text = "\n".join(md_lines)
summary_md.write_text("# Summary statistics by neighborhood\n\nStandard deviation is the sample standard deviation. An em dash indicates a neighborhood with one sale, so its standard deviation is undefined.\n\n" + table_text + "\n", encoding="utf-8")
summary_transcript.write_text(
    '# Transcript: summary statistics by neighborhood\n\n'
    '## User request\n\n'
    '> Generate a table of summary statistics - mean, standard deviation, minimum, maximum. '
    'Calculate these statistics for Bedroom AbvGr and Bathroom Equivalent. Group results by Neighborhood.\n\n'
    '## Calculation\n\n'
    'Using `AmesHousing-1.csv`, the records were grouped by `Neighborhood`. '
    '`Bathroom Equivalent` is calculated as `Bsmt Full Bath + 0.5 * Bsmt Half Bath + Full Bath + 0.5 * Half Bath`. '
    'The standard deviation is the sample standard deviation. The dash indicates standard deviation is undefined for Landmrk, which has one sale.\n\n'
    '## Results\n\n' + table_text + '\n',
    encoding="utf-8",
)
print(f"Saved neighborhood summary statistics: {summary_csv}")

cols = ["SalePrice", "Gr Liv Area", "Bedroom AbvGr", "BathroomEquiv", "Neighborhood"]
model_df = df[cols].dropna().copy()
counts = model_df["Neighborhood"].value_counts()
model_df["SlopeGroup"] = model_df["Neighborhood"].where(
    model_df["Neighborhood"].map(counts) >= 20, "Other (fewer than 20 sales)"
)

# Neighborhood fixed effects adjust for different baseline prices. Interactions
# let slopes differ by neighborhood; neighborhoods with fewer than 20 sales share
# one slope group because individual estimates would be unreliable.
formula = (
    'Q("SalePrice") ~ C(Neighborhood)'
    ' + Q("Gr Liv Area") + Q("Gr Liv Area"):C(SlopeGroup)'
    ' + Q("Bedroom AbvGr") + Q("Bedroom AbvGr"):C(SlopeGroup)'
    ' + BathroomEquiv + BathroomEquiv:C(SlopeGroup)'
)
fit = smf.ols(formula, data=model_df).fit(cov_type="HC3")
base = smf.ols(
    'Q("SalePrice") ~ Q("Gr Liv Area") + Q("Bedroom AbvGr")'
    ' + BathroomEquiv + C(Neighborhood)', data=model_df
).fit(cov_type="HC3")

print(f"Rows used: {len(model_df)}; neighborhoods: {model_df['Neighborhood'].nunique()}; slope groups: {model_df['SlopeGroup'].nunique()}")
print(f"R-squared (common slopes): {base.rsquared:.4f}")
print(f"R-squared (neighborhood slope groups): {fit.rsquared:.4f}")
print("\nCommon slope model (HC3 robust standard errors):")
for term in ['Q("Gr Liv Area")', 'Q("Bedroom AbvGr")', 'BathroomEquiv']:
    print(f"{term}: beta={base.params[term]:.2f}, SE={base.bse[term]:.2f}, p={base.pvalues[term]:.4g}")

print("\nJoint tests that neighborhood slope groups differ:")
for variable, label in [
    ('Q("Gr Liv Area")', "Gr Liv Area"),
    ('Q("Bedroom AbvGr")', "Bedroom AbvGr"),
    ("BathroomEquiv", "BathroomEquiv"),
]:
    terms = [name for name in fit.params.index if ":" in name and variable in name and "C(SlopeGroup)" in name]
    restriction = ", ".join(f"{term} = 0" for term in terms)
    test = fit.f_test(restriction)
    print(f"{label}: F={float(test.fvalue):.3f}, df={test.df_num:g},{test.df_denom:g}, p={float(test.pvalue):.4g}")

print("\nSlope group effects (dollars per square foot, bedroom, and bathroom equivalent):")
design_info = fit.model.data.orig_exog.design_info
for group in sorted(model_df["SlopeGroup"].unique()):
    row = {
        "SlopeGroup": group,
        "Gr Liv Area": model_df["Gr Liv Area"].median(),
        "Bedroom AbvGr": model_df["Bedroom AbvGr"].median(),
        "BathroomEquiv": model_df["BathroomEquiv"].median(),
    }
    # For a linear model, finite differences in the design matrix yield each
    # neighborhood-specific slope directly, including the reference category.
    from patsy import build_design_matrices
    def vector(area, beds, baths):
        values = pd.DataFrame([{
            "Neighborhood": model_df.loc[model_df["SlopeGroup"] == group, "Neighborhood"].iloc[0],
            "SlopeGroup": group,
            "Gr Liv Area": area,
            "Bedroom AbvGr": beds,
            "BathroomEquiv": baths,
        }])
        return build_design_matrices([design_info], values)[0][0]

    a, b, c = row["Gr Liv Area"], row["Bedroom AbvGr"], row["BathroomEquiv"]
    x0 = vector(a, b, c)
    slopes = [
        float((vector(a + 1, b, c) - x0) @ fit.params),
        float((vector(a, b + 1, c) - x0) @ fit.params),
        float((vector(a, b, c + 1) - x0) @ fit.params),
    ]
    print(f"{group}: ${slopes[0]:,.2f}/sq ft; ${slopes[1]:,.2f}/bedroom; ${slopes[2]:,.2f}/bath-equivalent")

# A horizontal boxplot, ordered by median, makes the 28 neighborhood
# distributions easier to compare while keeping every neighborhood label legible.
plot_data = df[["Neighborhood", "SalePrice"]].dropna()
neighborhood_order = (
    plot_data.groupby("Neighborhood")["SalePrice"].median().sort_values().index.tolist()
)
fig_height = max(8, 0.34 * len(neighborhood_order))
fig, ax = plt.subplots(figsize=(11, fig_height), constrained_layout=True)
box = ax.boxplot(
    [plot_data.loc[plot_data["Neighborhood"] == n, "SalePrice"] for n in neighborhood_order],
    orientation="horizontal",
    tick_labels=neighborhood_order,
    patch_artist=True,
    flierprops={"marker": ".", "markersize": 2, "alpha": 0.3},
)
for patch in box["boxes"]:
    patch.set_facecolor("#8ecae6")
    patch.set_edgecolor("#23627c")
for median in box["medians"]:
    median.set_color("#d1495b")
    median.set_linewidth(1.5)
ax.set_title("Sale Price by Neighborhood")
ax.set_xlabel("Sale price (USD)")
ax.set_ylabel("Neighborhood (ordered by median sale price)")
ax.xaxis.set_major_formatter(StrMethodFormatter("${x:,.0f}"))
ax.grid(axis="x", color="#d9d9d9", linewidth=0.7)
ax.set_axisbelow(True)
fig.savefig(Path(__file__).with_name("saleprice_by_neighborhood.png"), dpi=180)
plt.close(fig)
print(f"\nSaved boxplot: {Path(__file__).with_name('saleprice_by_neighborhood.png')}")
