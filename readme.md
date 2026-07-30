# Gas Well Liquid Loading Screener v2

A Python tool for first-pass screening of gas wells for liquid loading risk.

Implements the Turner (1969), Li (2001), and Ikpeka & Okolo (2018) critical
velocity models side by side, with supporting correlations for gas
compressibility (Z-factor), liquid density, and surface tension — so a well
test CSV in common field-reporting units (psig, °C, MMscfd) can be screened
without needing lab-measured PVT data for every property.

## 📖 Background

This script is based on SPE literature and standard petroleum engineering
correlations:

- **Turner, Hubbard & Dukler (1969)** — minimum flow rate for continuous
  liquid removal; the original (non-uplifted) critical velocity coefficient
  is used as the tool's governing model.
- **Coleman et al. (1991, SPE 20280)** — "A New Look at Predicting Gas-Well
  Load-Up." Confirmed that the original Turner coefficient (no +20% uplift)
  matches low-pressure wells better, that wellhead conditions are usually
  sufficient without a full pressure traverse, and that liquid *composition*
  (not liquid *rate*) is what actually affects critical velocity. Several of
  this tool's design choices trace directly back to this paper — see the
  comments in `screener_v2.py` for exactly which line implements which
  finding.
- **Li et al. (2001)** — a less conservative critical velocity model, shown
  alongside Turner for comparison.
- **Ikpeka & Okolo (2018)** — a blended Turner/Li model, coefficient taken
  verbatim from the published paper.
- **Sutton (1985, SPE 14265)** — pseudo-critical property correlation
  (gas specific gravity → Tpc, Ppc), used as an input to the Z-factor
  calculation. Coefficients in this tool were cross-checked against the
  original paper.
- **Dranchuk & Abou-Kassem (1975)** — the equation-of-state Z-factor
  correlation, solved iteratively for reduced gas density.
- **McCain (1990)**, *Properties of Petroleum Fluids* — formation water
  density as a function of salinity.
- **Baker & Swerdloff (1956)** — dead-oil gas/oil surface tension from API
  gravity, temperature, and pressure.

This tool is intended as a **screening aid, not a full nodal analysis**.
Wells flagged here should be investigated further with a proper well/network
model (e.g. Prosper, GAP) before any operational decision is made.

## ⚙️ Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/lucasnasution/GasWell-liquid-loading-screener.git
cd GasWell-liquid-loading-screener
pip install pandas
```

## 🚀 Usage

**Quick check (no setup needed):** run the script with no arguments to see a
built-in worked example and confirm the install works:

```bash
python screener_v2.py
```

This prints the results to screen, plus a glossary, and writes
`demo_results.csv` so you can see what the Excel output looks like.

**Screening your own wells:** fill in a CSV using the column format below
(see `wells_template.csv` for a starting point), then run:

```bash
python screener_v2.py your_wells.csv results.csv
```

This writes `results.csv` — open it in Excel. The on-screen table gets
cluttered with this many columns; the CSV is the intended way to review
results for more than a couple of wells.

You can also use it directly from Python:

```python
from screener_v2 import screen_wells_to_csv

screen_wells_to_csv("your_wells.csv", "results.csv")
```

## 📥 Input CSV format

| Column | Meaning | Units |
|---|---|---|
| `Well` | Well name | — |
| `THP_psig` | Flowing tubing head pressure | psig |
| `THT_C` | Flowing tubing head temperature | °C |
| `Qgas_MMscfd` | Actual gas rate | MMscf/d |
| `CGR_bbl_MMscf` | Condensate-gas ratio | bbl/MMscf |
| `WGR_bbl_MMscf` | Water-gas ratio | bbl/MMscf |
| `TubingID_in` | Tubing inside diameter | inches |
| `CasingID_in` | Casing (or open-hole) inside diameter below the tubing shoe | inches |
| `GasSG` | Gas specific gravity (air = 1) | dimensionless |
| `OilSG` | Oil/condensate specific gravity (water = 1) | dimensionless |
| `WaterSalinity_ppm` | Formation water salinity | ppm (≈ mg/L) |

CGR and WGR are used to compute a **water cut fraction** (`WGR / (WGR +
CGR)`), which blends water and oil/condensate density and surface tension.
If a well reports zero for both, the tool assumes the liquid is condensed
water (fresh, near-zero salinity) rather than formation brine — see
*Assumptions & limitations* below.

Surface tension, gas density, Z-factor, and liquid density are all
*calculated* internally from the columns above — you don't need to supply
them directly.

## 📤 Output columns

| Column | Meaning |
|---|---|
| `Well Name`, `THP (psig)`, `Gas Rate (MMscfd)` | Echoed back from your input, for reference |
| `Qcrit Turner`, `Qcrit Li`, `Qcrit Ikpeka` (MMscfd) | Critical gas rate under each of the three models |
| `Loading Ratio (Turner)` | Actual rate ÷ Turner critical rate. Above 1.0 = adequate velocity; below 1.0 = possible loading. **This is the governing number** — see below. |
| `Safety Margin (%)` | Same comparison as Loading Ratio, expressed as a percentage above/below critical |
| `Status` | Loading Ratio bucketed into plain language: Healthy / Watchlist / Near Loading / High Risk |
| `Below-Tubing Risk (Casing ID)` | Yes/No flag: would the well clear critical velocity at the *Casing ID* using today's surface THP? A simplified check, not a full pressure-at-depth calculation — see limitations |
| `Comments` | Any additional flags (e.g. assumed condensed water, gas SG outside Sutton's validated range) |

**Why only Turner drives Status/Safety Margin/Below-Tubing Risk:** SPE 20280
specifically recommends the original Turner coefficient for low-pressure gas
wells, and it's the most conservative of the three models. Li and Ikpeka are
shown for comparison — some fields track one model better than another based
on local well history, so seeing all three side by side is more useful than
hiding two of them.

**A "Yes" on Below-Tubing Risk next to a "Healthy" Status is not a
contradiction.** It can indicate gas percolating up through a standing
liquid level in the casing/annulus, with liquid left behind at the larger
diameter until the gas reaches the smaller tubing ID, where it may be moving
fast enough to lift whatever liquid does arrive. Confirm with an echometer
(acoustic fluid level) survey or a flowing gradient survey before drawing a
conclusion either way.

## ⚠️ Assumptions & limitations

This is a **screening tool**, not a substitute for nodal analysis. Specific
simplifications worth knowing before you rely on results:

- **No pressure-at-depth calculation.** The Below-Tubing Risk check reuses
  the surface THP at the Casing ID rather than estimating actual pressure at
  the tubing shoe / perforations (which is higher, and would raise gas
  density and lower critical velocity there). A "No" does not prove the
  below-tubing section is safe.
- **No sour-gas correction.** Sutton's pseudo-critical correlation calls for
  a separate Wichert-Aziz correction when CO2/H2S is present; this tool
  assumes a sweet gas, since composition isn't part of the input schema.
- **Fixed default water surface tension**, rather than a full pressure/
  temperature correlation — justified by SPE 20280's own finding that
  surface tension has only a minor effect on the result compared to
  pressure and flow area.
- **Sutton's correlation is validated for gas SG 0.571–1.679**; wells
  outside that range get a comment flag, not a blocked result.
- **Condensed-water default:** wells reporting zero WGR and zero CGR are
  assumed to be loading on fresh condensed water rather than treated as
  liquid-free, per SPE 20280's finding that condensed water is often the
  dominant loading liquid even when nothing is measured at surface.

## 🗂️ Version history

- **v1** — initial published version: CSV input, DAK Z-factor, blended
  liquid density from WGR/CGR/OilSG/salinity, manual surface tension input.
- **v2** (this version) — removed manual surface tension input (now
  calculated via Baker-Swerdloff + a fixed water default); confirmed Sutton
  coefficients against the source paper; gas rate now in MMscfd; output
  simplified to hide internal physics values by default; all three critical
  rate models shown side by side; Below-Tubing Risk simplified to a Yes/No
  flag; added CSV output for Excel review; added a glossary.

## 📄 License

*(Add your preferred license here — e.g. MIT — if you haven't already.)*
