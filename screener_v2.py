"""
screener_v4.py - Production Engineering Liquid Loading Screener
(maps to screener_v2.py in the GitHub repo, since the previous internal
v3 was published there as screener_v1.py)

CHANGES FROM THE PUBLISHED screener_v1.py
-------------------------------------------
- Output now shows THP in psig (what the user typed in), not the
  internally-converted psia value.
- Internal-only physics values (Z-factor, gas density, water cut,
  liquid density, liquid surface tension) are no longer in the default
  output table -- they still get calculated the same way, just aren't
  shown, since a reader doesn't need them to act on a result. They are
  available via screen_wells(..., verbose=True) if you ever want to
  sanity-check a strange result.
- All THREE critical rates (Turner, Li, Ikpeka) are now shown side by
  side, instead of silently defaulting to one with no indication of
  which. There's no point calculating three models and only surfacing
  one -- showing all three lets you see how sensitive the call is to
  which model you trust.
- Status, Safety Margin, and the below-tubing check are governed by
  TURNER ONLY (the model SPE 20280 specifically recommends for
  low-pressure wells, and the most conservative of the three). This is
  now stated explicitly above the results table, not left implicit.
- The below-tubing (casing ID) check is now a simple Yes/No flag
  instead of a numeric ratio -- it's a screening trigger to go run a
  real nodal model (Prosper/GAP), not a number to analyze on its own.
- Removed the tubing-size recommendation from the output table (kept
  as a callable function, recommend_tubing_size(), for anyone who wants
  it directly -- but this tool is a screener, not a production
  enhancement design tool, so it's no longer part of the default
  results).
- A glossary of the less-common terms (Loading Ratio, Safety Margin,
  Below-Tubing Risk) is now printed once at the end, instead of
  requiring the reader to already know what they mean.

WHAT THIS TOOL DELIBERATELY DOES NOT DO
-----------------------------------------
This is a first-pass SCREENING tool, not a nodal analysis model. It does
not run a pressure or temperature traverse down the wellbore -- the
below-tubing (casing ID) check re-uses surface THP as an approximation,
not actual pressure at depth. It does not correct for sour gas. Any well
flagged here should be investigated further with a proper well/network
model (e.g. Prosper, GAP) before any operational decision is made.

References
----------
Turner, R.G., Hubbard, M.G., & Dukler, A.E. (1969). "Analysis and
    Prediction of Minimum Flow Rate for the Continuous Removal of
    Liquids from Gas Wells." JPT.

Coleman, S.B., Clay, H.B., McCurdy, D.G., & Norris, H.L. (1991).
    "A New Look at Predicting Gas-Well Load-Up." SPE 20280.
    Key findings applied in this module:
      - Original Turner coefficient (1.593, no +20% uplift) matches
        low-pressure gas wells better -> used as the GOVERNING model
        for Status/Safety Margin/Below-Tubing Risk below.
      - Onset of loading is generally controlled by flowing WELLHEAD
        conditions -> the primary (tubing) check needs only THP/THT.
      - Liquid RATE is not a primary driver of critical velocity, but
        liquid COMPOSITION (density, surface tension) is -> this is why
        WGR/CGR feed a density/surface-tension blend rather than a rate.
      - Pressure and flow area are the dominant variables; fluid
        properties incl. surface tension have only MINOR impact -> the
        justification for using a fixed default water surface tension
        instead of a full correlation.
      - Wells where gas flows through more than one diameter should be
        checked at the LARGEST diameter section -> see the Below-Tubing
        Risk flag.
      - Condensed water (not formation water) is often the dominant
        loading liquid in low-pressure wells, and forms essentially
        fresh (near-zero salinity) -> see calc_liquid_density().

Li, X. et al. (2001). "A New Look at Prediction of Liquid Loading."
    Li critical velocity model (0.7241 coefficient) -- less conservative
    than Turner; shown for comparison only, does not govern Status.

Ikpeka, P.M. & Okolo, M.O. (2018). "Li and Turner Modified Model for
    Predicting Liquid Loading in Gas Wells." Journal of Petroleum
    Exploration and Production Technology.
    https://doi.org/10.1007/s13202-018-0585-6
    Blending coefficient (2.261921523) taken verbatim from this paper;
    shown for comparison only, does not govern Status.

Dranchuk, P.M. & Abou-Kassem, H. (1975). "Calculation of Z Factors for
    Natural Gases Using Equations of State." Journal of Canadian
    Petroleum Technology, 14(3). Used internally for Z-factor; not
    shown in the default output (see verbose=True).

Sutton, R.P. (1985). "Compressibility Factors for High-Molecular-Weight
    Reservoir Gases." SPE 14265. Coefficients confirmed directly against
    the user's copy of this paper (July 2026):
        Ppc [psia] = 756.8 - 131.0*Yg - 3.6*Yg^2
        Tpc [degR] = 169.2 + 349.5*Yg - 74.0*Yg^2
    Valid range Yg = 0.571-1.679 (flagged, not blocked, outside this).
    No Wichert-Aziz sour-gas correction applied (not collected in this
    CSV schema) -- documented limitation, assumes sweet gas.

McCain, W.D. Jr. (1990). "Properties of Petroleum Fluids," 2nd ed.
    PennWell Corp. Formation water density correlation, used internally.

Baker, O. & Swerdloff, W. (1956). "Calculation of Surface Tension 6 -
    Finding Surface Tension of Hydrocarbon Liquids." Oil & Gas Journal
    (2 January 1956): 125. Gas/oil surface tension from API gravity and
    temperature, used internally.
"""

import math
from typing import Optional, Tuple

import pandas as pd

# ---------------------------------------------------------------------------
# Named constants -- each tied to a specific source noted above.
# ---------------------------------------------------------------------------

ATMOSPHERIC_PRESSURE_PSI = 14.696  # sea-level default for psig -> psia
GAS_DENSITY_CONST = 2.7            # 28.97 (air MW) / 10.732 (gas constant)
CRITICAL_RATE_CONST = 3060.0       # Qc = 3060*P*A*Vc/(T*Z) unit-conversion constant

TURNER_COEFF = 1.593               # Turner (1969) original, no +20% uplift, per SPE 20280
LI_COEFF = 0.7241                  # Li et al. (2001)
IKPEKA_BLEND_COEFF = 2.261921523   # Ikpeka & Okolo (2018), verbatim from source

GOVERNING_MODEL = "turner"         # drives Status / Safety Margin / Below-Tubing Risk

HEALTHY_THRESHOLD = 1.20
WATCHLIST_THRESHOLD = 1.00
NEAR_LOADING_THRESHOLD = 0.80

SPE20280_LOW_PRESSURE_LIMIT_PSIA = 500.0   # advisory only

FRESH_WATER_DENSITY_LBFT3 = 62.428          # McCain (1990) at zero salinity
WATER_REFERENCE_DENSITY_LBFT3 = 62.4        # for SG -> density conversion

# Sutton (1985) pseudo-critical coefficients, confirmed against source.
SUTTON_TPC_0, SUTTON_TPC_1, SUTTON_TPC_2 = 169.2, 349.5, -74.0
SUTTON_PPC_0, SUTTON_PPC_1, SUTTON_PPC_2 = 756.8, -131.0, -3.6
SUTTON_SG_VALID_MIN, SUTTON_SG_VALID_MAX = 0.571, 1.679

# Dranchuk & Abou-Kassem (1975) equation-of-state constants.
DAK_A1, DAK_A2, DAK_A3, DAK_A4, DAK_A5 = 0.3265, -1.0700, -0.5339, 0.01569, -0.05165
DAK_A6, DAK_A7, DAK_A8 = 0.5475, -0.7361, 0.1844
DAK_A9, DAK_A10, DAK_A11 = 0.1056, 0.6134, 0.7210

WATER_GAS_SIGMA_DEFAULT = 60.0     # fixed default, minor-impact variable per SPE 20280 finding #4

GLOSSARY = """
GLOSSARY
--------
Loading Ratio        : Actual gas rate divided by the critical gas rate
                        needed to lift liquids out of the well. Above 1.0
                        means the well is flowing fast enough to unload
                        liquids; below 1.0 means it may not be.
Safety Margin (%)     : The same comparison as Loading Ratio, expressed
                        as a percentage: 100 x (Actual - Critical) /
                        Critical. +60% means flowing 60% above the
                        minimum critical rate; -20% means flowing 20%
                        below it (already at risk of loading).
Below-Tubing Risk     : A simplified check using the Casing ID (instead
                        of Tubing ID) at the SAME surface wellhead
                        pressure -- it does NOT account for the higher
                        actual pressure at depth. "Yes" is a flag to
                        investigate further with a full well/network
                        model (e.g. Prosper, GAP); "No" does not prove
                        the below-tubing section is safe.
Governing Model       : Status, Safety Margin, and Below-Tubing Risk are
                        all based on the Turner (original) model only,
                        per SPE 20280's recommendation for low-pressure
                        wells. The Li and Ikpeka critical rates are
                        shown alongside for comparison, but do not
                        change the Status verdict.

NOTE: A "Yes" on Below-Tubing Risk alongside a "Healthy" tubing Status
is NOT a contradiction. It can indicate gas percolating up through a
standing liquid level in the casing/annulus -- the liquid is left
behind at the larger diameter, and once the gas reaches the smaller
tubing ID it may be moving fast enough to carry any liquid that does
reach that point. Confirm with an echometer (acoustic fluid level)
survey or a flowing gradient survey before concluding there's no issue
either way.
"""


# ---------------------------------------------------------------------------
# Unit conversions
# ---------------------------------------------------------------------------

def psig_to_psia(pressure_psig: float, atmospheric_psi: float = ATMOSPHERIC_PRESSURE_PSI) -> float:
    return pressure_psig + atmospheric_psi


def celsius_to_rankine(temp_c: float) -> float:
    return (temp_c + 273.15) * 1.8


def celsius_to_fahrenheit(temp_c: float) -> float:
    return temp_c * 9.0 / 5.0 + 32.0


def sg_to_api(sg_oil: float) -> float:
    return 141.5 / sg_oil - 131.5


# ---------------------------------------------------------------------------
# Gas properties (density, Z-factor)
# ---------------------------------------------------------------------------

def calc_pseudo_criticals(sg: float) -> Tuple[float, float]:
    """Sutton (1985, SPE-14265), coefficients confirmed against source."""
    tpc = SUTTON_TPC_0 + SUTTON_TPC_1 * sg + SUTTON_TPC_2 * (sg ** 2)
    ppc = SUTTON_PPC_0 + SUTTON_PPC_1 * sg + SUTTON_PPC_2 * (sg ** 2)
    return tpc, ppc


def calc_z_factor_dak(pressure_psia: float, temp_r: float, sg: float,
                       tol: float = 1e-10, max_iter: int = 100) -> float:
    """Dranchuk & Abou-Kassem (1975), solved via Newton-Raphson on reduced density."""
    tpc, ppc = calc_pseudo_criticals(sg)
    tpr = temp_r / tpc
    ppr = pressure_psia / ppc

    c1 = DAK_A1 + DAK_A2 / tpr + DAK_A3 / tpr ** 3 + DAK_A4 / tpr ** 4 + DAK_A5 / tpr ** 5
    c2 = DAK_A6 + DAK_A7 / tpr + DAK_A8 / tpr ** 2
    c3 = DAK_A9 * (DAK_A7 / tpr + DAK_A8 / tpr ** 2)

    y = 0.27 * ppr / tpr

    for _ in range(max_iter):
        expo = math.exp(-DAK_A11 * y ** 2)
        f = (
            y + c1 * y ** 2 + c2 * y ** 3 - c3 * y ** 6
            + DAK_A10 * (1 + DAK_A11 * y ** 2) * (y ** 3 / tpr ** 3) * expo
            - 0.27 * ppr / tpr
        )
        f_prime = (
            1 + 2 * c1 * y + 3 * c2 * y ** 2 - 6 * c3 * y ** 5
            + (DAK_A10 / tpr ** 3) * expo * (3 * y ** 2 + 3 * DAK_A11 * y ** 4 - 2 * DAK_A11 ** 2 * y ** 6)
        )
        y_new = y - f / f_prime
        if y_new <= 0:
            y_new = y / 2.0
        if abs(y_new - y) < tol:
            y = y_new
            break
        y = y_new

    z = (
        1 + c1 * y + c2 * y ** 2 - c3 * y ** 5
        + DAK_A10 * (1 + DAK_A11 * y ** 2) * (y ** 2 / tpr ** 3) * math.exp(-DAK_A11 * y ** 2)
    )
    return z


def calc_gas_density(sg: float, pressure_psia: float, temp_r: float, z_factor: float) -> float:
    return (GAS_DENSITY_CONST * sg * pressure_psia) / (z_factor * temp_r)


# ---------------------------------------------------------------------------
# Flow area
# ---------------------------------------------------------------------------

def calc_pipe_area(id_in: float) -> float:
    return (math.pi / 4.0) * ((id_in / 12.0) ** 2)


# ---------------------------------------------------------------------------
# Liquid properties (density and surface tension from composition)
# ---------------------------------------------------------------------------

def calc_water_density(salinity_ppm: float) -> float:
    """McCain (1990): rho_w = salinity[mg/L] / 25000 + 62.428."""
    return (salinity_ppm / 25000.0) + FRESH_WATER_DENSITY_LBFT3


def calc_water_cut(wgr_bbl_mmscf: float, cgr_bbl_mmscf: float) -> Tuple[float, str]:
    """
    water_cut = WGR / (WGR + CGR). If both are zero, assumes 100%
    condensed (fresh) water per SPE 20280's condensed-water finding.
    """
    total = wgr_bbl_mmscf + cgr_bbl_mmscf
    if total <= 0:
        return 1.0, "No WGR/CGR reported: assumed condensed (fresh) water per SPE 20280"
    return wgr_bbl_mmscf / total, ""


def calc_liquid_density(water_cut: float, oil_sg: float, salinity_ppm: float) -> float:
    effective_salinity = 0.0 if water_cut >= 1.0 else salinity_ppm
    rho_water = calc_water_density(effective_salinity)
    rho_oil = WATER_REFERENCE_DENSITY_LBFT3 * oil_sg
    return water_cut * rho_water + (1.0 - water_cut) * rho_oil


def calc_oil_gas_surface_tension(oil_sg: float, pressure_psia: float, temp_f: float) -> float:
    """Baker & Swerdloff (1956), temperature clamped to the fitted 68-100 degF range."""
    api = sg_to_api(oil_sg)
    temp_f_clamped = min(max(temp_f, 68.0), 100.0)
    sigma_68 = 39.0 - 0.2571 * api
    sigma_100 = 37.5 - 0.2571 * api
    sigma_t = sigma_68 - (temp_f_clamped - 68.0) * (sigma_68 - sigma_100) / 32.0
    fc = max(1.0 - 0.025 * (pressure_psia ** 0.45), 0.0)
    return max(fc * sigma_t, 0.0)


def calc_liquid_surface_tension(water_cut: float, oil_sg: float, pressure_psia: float, temp_f: float) -> float:
    sigma_oil = calc_oil_gas_surface_tension(oil_sg, pressure_psia, temp_f)
    return water_cut * WATER_GAS_SIGMA_DEFAULT + (1.0 - water_cut) * sigma_oil


# ---------------------------------------------------------------------------
# Critical velocity / critical rate (Turner, Li, Ikpeka)
# ---------------------------------------------------------------------------

def calc_critical_velocities(sigma_dynes: float, rho_l: float, rho_g: float) -> dict:
    """
    Raises ValueError if liquid density does not exceed gas density (see
    prior versions' docstrings for why this guard matters in Python).
    """
    density_diff = rho_l - rho_g
    if density_diff <= 0:
        raise ValueError(
            f"Liquid density ({rho_l:.2f} lb/ft3) must exceed gas density "
            f"({rho_g:.3f} lb/ft3) for the critical velocity model to be valid."
        )
    v_crit_turner = TURNER_COEFF * (sigma_dynes ** 0.25) * (density_diff ** 0.25) / (rho_g ** 0.5)
    v_crit_li = LI_COEFF * (sigma_dynes ** 0.25) * (density_diff ** 0.25) / (rho_g ** 0.5)
    v_crit_ikpeka = v_crit_li + IKPEKA_BLEND_COEFF * (v_crit_turner - v_crit_li)
    return {"vcrit_turner": v_crit_turner, "vcrit_li": v_crit_li, "vcrit_ikpeka": v_crit_ikpeka}


def calc_critical_rate(p_psia: float, temp_r: float, z: float, area_ft2: float, v_crit_fps: float) -> float:
    """Qc = 3060 * P * A * Vc / (T * Z), returns Mscf/d."""
    return (CRITICAL_RATE_CONST * p_psia * area_ft2 * v_crit_fps) / (temp_r * z)


def classify_health(loading_ratio: float) -> str:
    if loading_ratio >= HEALTHY_THRESHOLD:
        return "Healthy"
    elif WATCHLIST_THRESHOLD <= loading_ratio < HEALTHY_THRESHOLD:
        return "Watchlist"
    elif NEAR_LOADING_THRESHOLD <= loading_ratio < WATCHLIST_THRESHOLD:
        return "Near Loading"
    else:
        return "High Risk"


def recommend_tubing_size(current_tubing_id_in: float, loading_ratio: float,
                           target_ratio: float = HEALTHY_THRESHOLD) -> Optional[float]:
    """
    Kept as a standalone utility (not part of default screening output --
    see module docstring). Suggests a smaller tubing ID that would bring
    the loading ratio up to target_ratio.
    """
    if loading_ratio >= target_ratio or loading_ratio <= 0:
        return None
    current_area_ft2 = calc_pipe_area(current_tubing_id_in)
    required_area_ft2 = current_area_ft2 * (loading_ratio / target_ratio)
    required_id_in = math.sqrt((4.0 * required_area_ft2) / math.pi) * 12.0
    return round(required_id_in, 3)


def generate_engineering_comments(pressure_psia: float, gas_sg: float, loading_ratio_governing: float,
                                   liquid_note: str) -> str:
    """Comments not already captured by a dedicated column (Below-Tubing Risk has its own column)."""
    comments = []
    if liquid_note:
        comments.append(liquid_note)
    if loading_ratio_governing < NEAR_LOADING_THRESHOLD:
        comments.append("Candidate for artificial lift / velocity string sizing")
    if pressure_psia > SPE20280_LOW_PRESSURE_LIMIT_PSIA:
        comments.append(
            f"WHFP above {SPE20280_LOW_PRESSURE_LIMIT_PSIA:.0f} psia: "
            "SPE 20280's no-uplift finding was validated on lower-pressure wells"
        )
    if not (SUTTON_SG_VALID_MIN <= gas_sg <= SUTTON_SG_VALID_MAX):
        comments.append(
            f"Gas SG {gas_sg:.3f} is outside Sutton's validated range "
            f"({SUTTON_SG_VALID_MIN}-{SUTTON_SG_VALID_MAX}): Z-factor may be extrapolated"
        )
    return "; ".join(comments) if comments else "-"


# ---------------------------------------------------------------------------
# Well-level and batch screening
# ---------------------------------------------------------------------------

def screen_well(row: dict, verbose: bool = False) -> dict:
    """
    Screens a single well using raw field-units input. Expected keys:
        Well, THP_psig, THT_C, Qgas_MMscfd, CGR_bbl_MMscf, WGR_bbl_MMscf,
        TubingID_in, CasingID_in, GasSG, OilSG, WaterSalinity_ppm

    Set verbose=True to include internal physics values (Z-factor, gas
    density, water cut, liquid density, surface tension) in the result --
    off by default per the "users don't need internal parameters" request.
    """
    thp_psig = row["THP_psig"]
    pressure_psia = psig_to_psia(thp_psig)
    temp_r = celsius_to_rankine(row["THT_C"])
    temp_f = celsius_to_fahrenheit(row["THT_C"])

    z = calc_z_factor_dak(pressure_psia, temp_r, row["GasSG"])
    rho_g = calc_gas_density(row["GasSG"], pressure_psia, temp_r, z)

    water_cut, liquid_note = calc_water_cut(row["WGR_bbl_MMscf"], row["CGR_bbl_MMscf"])
    rho_l = calc_liquid_density(water_cut, row["OilSG"], row["WaterSalinity_ppm"])
    sigma_l = calc_liquid_surface_tension(water_cut, row["OilSG"], pressure_psia, temp_f)

    v_crits = calc_critical_velocities(sigma_l, rho_l, rho_g)

    tubing_area = calc_pipe_area(row["TubingID_in"])
    casing_area = calc_pipe_area(row["CasingID_in"])

    q_actual_mscfd = row["Qgas_MMscfd"] * 1000.0
    q_actual_mmscfd = row["Qgas_MMscfd"]

    # All three critical rates, tubing-based, for side-by-side comparison.
    q_crit_mmscfd = {}
    loading_ratio = {}
    for model in ("turner", "li", "ikpeka"):
        q_crit_mscfd = calc_critical_rate(pressure_psia, temp_r, z, tubing_area, v_crits[f"vcrit_{model}"])
        q_crit_mmscfd[model] = q_crit_mscfd / 1000.0
        loading_ratio[model] = q_actual_mscfd / q_crit_mscfd

    # Governing model (Turner) drives Status / Safety Margin / Below-Tubing Risk.
    governing_ratio = loading_ratio[GOVERNING_MODEL]
    governing_q_crit_mmscfd = q_crit_mmscfd[GOVERNING_MODEL]
    safety_margin_pct = 100.0 * (q_actual_mmscfd - governing_q_crit_mmscfd) / governing_q_crit_mmscfd
    status = classify_health(governing_ratio)

    q_crit_casing_mscfd = calc_critical_rate(pressure_psia, temp_r, z, casing_area, v_crits[f"vcrit_{GOVERNING_MODEL}"])
    loading_ratio_casing = q_actual_mscfd / q_crit_casing_mscfd
    below_tubing_risk = "Yes" if loading_ratio_casing < 1.0 else "No"

    comments = generate_engineering_comments(pressure_psia, row["GasSG"], governing_ratio, liquid_note)

    result = {
        "Well Name": row["Well"],
        "THP (psig)": round(thp_psig, 1),
        "Gas Rate (MMscfd)": round(q_actual_mmscfd, 2),
        "Qcrit Turner (MMscfd)": round(q_crit_mmscfd["turner"], 2),
        "Qcrit Li (MMscfd)": round(q_crit_mmscfd["li"], 2),
        "Qcrit Ikpeka (MMscfd)": round(q_crit_mmscfd["ikpeka"], 2),
        "Loading Ratio (Turner)": round(governing_ratio, 2),
        "Safety Margin (%)": f"{round(safety_margin_pct, 1)}%",
        "Status": status,
        "Below-Tubing Risk (Casing ID)": below_tubing_risk,
        "Comments": comments,
    }

    if verbose:
        result["_Z-Factor"] = round(z, 4)
        result["_Gas Density (lb/ft3)"] = round(rho_g, 3)
        result["_Water Cut"] = round(water_cut, 2)
        result["_Liquid Density (lb/ft3)"] = round(rho_l, 1)
        result["_Liquid Surface Tension (dynes/cm)"] = round(sigma_l, 1)

    return result


def load_wells_from_csv(csv_path: str) -> pd.DataFrame:
    """
    Expected header (exact names):
        Well, THP_psig, THT_C, Qgas_MMscfd, CGR_bbl_MMscf, WGR_bbl_MMscf,
        TubingID_in, CasingID_in, GasSG, OilSG, WaterSalinity_ppm
    """
    required_columns = [
        "Well", "THP_psig", "THT_C", "Qgas_MMscfd", "CGR_bbl_MMscf", "WGR_bbl_MMscf",
        "TubingID_in", "CasingID_in", "GasSG", "OilSG", "WaterSalinity_ppm",
    ]
    df = pd.read_csv(csv_path)
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required column(s): {missing}. Expected: {required_columns}")
    return df


def screen_wells(wells_df: pd.DataFrame, verbose: bool = False) -> pd.DataFrame:
    """Batch-screens a DataFrame of wells and returns a results table."""
    rows = wells_df.to_dict(orient="records")
    results = [screen_well(row, verbose=verbose) for row in rows]
    return pd.DataFrame(results)


def screen_wells_from_csv(csv_path: str, verbose: bool = False) -> pd.DataFrame:
    """Convenience wrapper: load a CSV and screen every well in it in one call."""
    wells_df = load_wells_from_csv(csv_path)
    return screen_wells(wells_df, verbose=verbose)


def screen_wells_to_csv(input_csv_path: str, output_csv_path: str, verbose: bool = False) -> pd.DataFrame:
    """
    Loads wells from input_csv_path, screens them, and writes the results
    table to output_csv_path (opens cleanly in Excel -- the full column
    set gets cluttered on screen, but a spreadsheet handles it fine).
    Returns the results DataFrame as well, in case you're calling this
    from another script.
    """
    results_df = screen_wells_from_csv(input_csv_path, verbose=verbose)
    results_df.to_csv(output_csv_path, index=False)
    return results_df


if __name__ == "__main__":
    import sys

    print(f"Critical velocity model governing Status/Safety Margin/Below-Tubing Risk: "
          f"{GOVERNING_MODEL.capitalize()} (per SPE 20280 recommendation for low-pressure wells)\n")

    if len(sys.argv) >= 3:
        # Usage: python screener_v2.py wells_input.csv results_output.csv
        input_path, output_path = sys.argv[1], sys.argv[2]
        results_df = screen_wells_to_csv(input_path, output_path)
        print(f"Screened {len(results_df)} well(s) from {input_path}")
        print(f"Results written to {output_path} -- open in Excel to view.")
    else:
        # No arguments given: run the built-in worked example so the
        # install can be confirmed without needing a real CSV yet.
        example_rows = [
            {
                "Well": "A-01", "THP_psig": 335.3, "THT_C": 65.6, "Qgas_MMscfd": 2.2,
                "CGR_bbl_MMscf": 3.0, "WGR_bbl_MMscf": 1.0, "TubingID_in": 2.441,
                "CasingID_in": 6.184, "GasSG": 0.65, "OilSG": 0.75, "WaterSalinity_ppm": 15000.0,
            },
            {
                "Well": "A-04", "THP_psig": 285.3, "THT_C": 71.1, "Qgas_MMscfd": 0.9,
                "CGR_bbl_MMscf": 0.0, "WGR_bbl_MMscf": 0.0, "TubingID_in": 2.992,
                "CasingID_in": 6.184, "GasSG": 0.68, "OilSG": 0.78, "WaterSalinity_ppm": 12000.0,
            },
        ]
        example_df = pd.DataFrame(example_rows)
        results_df = screen_wells(example_df)
        print(results_df.to_string(index=False))
        print(GLOSSARY)
        results_df.to_csv("demo_results.csv", index=False)
        print("\nDemo results also written to demo_results.csv -- open in Excel to view.")
        print("To screen your own wells: python screener_v2.py your_wells.csv results.csv")
