"""
screener_v3.py - Production Engineering Liquid Loading Screener (Version 3)

CHANGES FROM V2 (screener_v2.py)
----------------------------------
- Removed Sigma_dynescm as a required CSV column. Surface tension is now
  CALCULATED instead of manually supplied:
    - Oil/condensate side: Baker & Swerdloff (1956) dead-oil correlation,
      using OilSG (already in the CSV) plus THP/THT. See
      calc_oil_gas_surface_tension().
    - Water side: a single fixed literature-typical value
      (WATER_GAS_SIGMA_DEFAULT), NOT a full pressure/temperature
      correlation -- justified because SPE 20280 finding #4 found
      surface tension has only a MINOR impact on the result (it enters
      the critical velocity formula as a fourth root), unlike pressure
      and flow area which dominate. See the constant's comment below.
    - Blended by water_cut, same approach as liquid density.
- Qgas is now entered in MMscfd (the common field-reporting unit)
  instead of Mscfd; converted internally.
- Sutton (1985) pseudo-critical coefficients are now CONFIRMED against
  the user's own copy of SPE-14265 (previously flagged as unverified
  training-data recall in v1/v2). Also added a validity-range check
  (Yg = 0.571-1.679, per the paper's underlying regression database)
  that flags wells outside that range rather than silently
  extrapolating.
- Documented limitation: no Wichert-Aziz sour-gas correction is applied
  to the pseudo-critical properties, since CO2/H2S composition isn't
  collected in this CSV schema. Per SPE-14265, that correction should be
  applied BEFORE using Ppc/Tpc if the gas is sour. This tool currently
  assumes a sweet gas.

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
        low-pressure gas wells better -> used directly below.
      - Onset of loading is generally controlled by flowing WELLHEAD
        conditions -> the primary (tubing) check needs only THP/THT.
      - Liquid RATE is not a primary driver of critical velocity, but
        liquid COMPOSITION (density, surface tension) is -> this is why
        WGR/CGR feed a density/surface-tension blend rather than a rate.
      - Pressure and flow area are the dominant variables; fluid
        properties incl. surface tension have only MINOR impact -> the
        justification for using a fixed default water surface tension
        instead of a full correlation (see WATER_GAS_SIGMA_DEFAULT).
      - Wells where gas flows through more than one diameter should be
        checked at the LARGEST diameter section -> see the casing-ID
        check in generate_engineering_comments().
      - Condensed water (not formation water) is often the dominant
        loading liquid in low-pressure wells, and forms essentially
        fresh (near-zero salinity) -> see calc_liquid_density().

Li, X. et al. (2001). "A New Look at Prediction of Liquid Loading."
    Li critical velocity model (0.7241 coefficient).

Ikpeka, P.M. & Okolo, M.O. (2018). "Li and Turner Modified Model for
    Predicting Liquid Loading in Gas Wells." Journal of Petroleum
    Exploration and Production Technology.
    https://doi.org/10.1007/s13202-018-0585-6
    Blending coefficient (2.261921523) taken verbatim from this paper.

Dranchuk, P.M. & Abou-Kassem, H. (1975). "Calculation of Z Factors for
    Natural Gases Using Equations of State." Journal of Canadian
    Petroleum Technology, 14(3).
    Eleven-constant equation of state fit to the Standing-Katz Z-factor
    chart, solved iteratively for reduced gas density -- see
    calc_z_factor_dak(). Sanity-checked against expected Standing-Katz
    Z-factor ranges during development.

Sutton, R.P. (1985). "Compressibility Factors for High-Molecular-Weight
    Reservoir Gases." SPE 14265.
    Correlates gas specific gravity to pseudo-critical temperature and
    pressure when full gas composition isn't available -- see
    calc_pseudo_criticals(). Coefficients CONFIRMED directly against the
    user's copy of this paper (July 2026):
        Ppc [psia] = 756.8 - 131.0*Yg - 3.6*Yg^2
        Tpc [degR] = 169.2 + 349.5*Yg - 74.0*Yg^2
    Underlying regression database spans Yg = 0.571-1.679; this module
    flags (does not block) wells outside that range. Sutton presents a
    single unified correlation (no dry/wet gas branching). The paper
    calls for a separate Wichert-Aziz correction for sour gas (CO2/H2S),
    which is NOT applied here -- see limitations above.

McCain, W.D. Jr. (1990). "Properties of Petroleum Fluids," 2nd ed.
    PennWell Corp. Source of the formation water density correlation
    used in calc_water_density().

Baker, O. & Swerdloff, W. (1956). "Calculation of Surface Tension 6 -
    Finding Surface Tension of Hydrocarbon Liquids." Oil & Gas Journal
    (2 January 1956): 125.
    Dead-oil gas/oil surface tension correlation from API gravity and
    temperature, with a pressure correction for dissolved gas -- see
    calc_oil_gas_surface_tension(). Formula confirmed via a source
    reproducing the full equation set (incl. the pressure correction
    factor), cross-referenced against the SPE/PetroWiki description of
    the same method (Beggs' 68-100degF interpolation/clamping rule).
"""

import math
from typing import Optional, Tuple

import pandas as pd

# ---------------------------------------------------------------------------
# Named constants -- each tied to a specific source noted above.
# ---------------------------------------------------------------------------

# Standard sea-level atmospheric pressure, used to convert THP from psig
# (gauge, what's usually reported at the wellhead) to psia (absolute).
# If your field sits at meaningful elevation, replace with a field-
# specific atmospheric pressure.
ATMOSPHERIC_PRESSURE_PSI = 14.696

# Real-gas density constant: 28.97 (air molar mass) / 10.732 (gas constant,
# psia-ft3/lbmol-R) ~= 2.7.
GAS_DENSITY_CONST = 2.7

# Critical gas rate constant (unit-conversion factor for the
# Qc = 3060 * P * A * Vc / (T * Z) equation, giving Mscf/d).
CRITICAL_RATE_CONST = 3060.0

# Turner (1969) original coefficient, per SPE 20280's finding that the
# +20% uplift is unnecessary for low-pressure gas wells.
TURNER_COEFF = 1.593

# Li et al. (2001) coefficient.
LI_COEFF = 0.7241

# Ikpeka & Okolo (2018) blending coefficient, taken verbatim from the
# published paper (Ikpeka Modified Velocity equation).
IKPEKA_BLEND_COEFF = 2.261921523

# Screening thresholds (loading ratio = Q_actual / Q_critical).
HEALTHY_THRESHOLD = 1.20
WATCHLIST_THRESHOLD = 1.00
NEAR_LOADING_THRESHOLD = 0.80

# WHFP above which the SPE 20280 "no uplift needed" finding is less
# certain to apply -- advisory only, does not change the calculation.
SPE20280_LOW_PRESSURE_LIMIT_PSIA = 500.0

# Fresh/condensed water reference density (McCain, 1990), i.e. the
# calc_water_density() formula evaluated at zero salinity.
FRESH_WATER_DENSITY_LBFT3 = 62.428

# Reference density used to convert oil SG to lb/ft3 (fresh water at
# standard conditions).
WATER_REFERENCE_DENSITY_LBFT3 = 62.4

# Sutton (1985) pseudo-critical property correlation coefficients.
# Confirmed against the user's copy of SPE-14265 (July 2026).
# Tpc [degR] = SUTTON_TPC_0 + SUTTON_TPC_1*Yg + SUTTON_TPC_2*Yg^2
# Ppc [psia] = SUTTON_PPC_0 + SUTTON_PPC_1*Yg + SUTTON_PPC_2*Yg^2
SUTTON_TPC_0, SUTTON_TPC_1, SUTTON_TPC_2 = 169.2, 349.5, -74.0
SUTTON_PPC_0, SUTTON_PPC_1, SUTTON_PPC_2 = 756.8, -131.0, -3.6

# Gas gravity range Sutton's regression database actually covered.
# Wells outside this range get an advisory comment, not a hard error.
SUTTON_SG_VALID_MIN, SUTTON_SG_VALID_MAX = 0.571, 1.679

# Dranchuk & Abou-Kassem (1975) equation-of-state constants.
DAK_A1, DAK_A2, DAK_A3, DAK_A4, DAK_A5 = 0.3265, -1.0700, -0.5339, 0.01569, -0.05165
DAK_A6, DAK_A7, DAK_A8 = 0.5475, -0.7361, 0.1844
DAK_A9, DAK_A10, DAK_A11 = 0.1056, 0.6134, 0.7210

# Fixed default gas/water surface tension (dynes/cm). NOT a full pressure/
# temperature correlation -- a single literature-typical value for the
# water fraction of the liquid blend. Justified by SPE 20280 finding #4:
# surface tension has only a MINOR impact on critical velocity (it enters
# as a fourth root), so a reasonable constant is a defensible screening
# simplification, unlike pressure or flow area which get full treatment.
WATER_GAS_SIGMA_DEFAULT = 60.0


# ---------------------------------------------------------------------------
# Unit conversions
# ---------------------------------------------------------------------------

def psig_to_psia(pressure_psig: float, atmospheric_psi: float = ATMOSPHERIC_PRESSURE_PSI) -> float:
    """Converts gauge pressure (psig, as usually reported at the wellhead) to absolute (psia)."""
    return pressure_psig + atmospheric_psi


def celsius_to_rankine(temp_c: float) -> float:
    """Converts temperature in degC to degR: R = (C + 273.15) * 1.8."""
    return (temp_c + 273.15) * 1.8


def celsius_to_fahrenheit(temp_c: float) -> float:
    """Converts temperature in degC to degF: F = C * 9/5 + 32."""
    return temp_c * 9.0 / 5.0 + 32.0


def sg_to_api(sg_oil: float) -> float:
    """Converts oil specific gravity to API gravity: API = 141.5/SG - 131.5."""
    return 141.5 / sg_oil - 131.5


# ---------------------------------------------------------------------------
# Gas properties (density, Z-factor)
# ---------------------------------------------------------------------------

def calc_pseudo_criticals(sg: float) -> Tuple[float, float]:
    """
    Sutton (1985, SPE-14265) correlation: estimates pseudo-critical
    temperature (degR) and pressure (psia) from gas specific gravity
    alone. Coefficients confirmed against the source paper.
    """
    tpc = SUTTON_TPC_0 + SUTTON_TPC_1 * sg + SUTTON_TPC_2 * (sg ** 2)
    ppc = SUTTON_PPC_0 + SUTTON_PPC_1 * sg + SUTTON_PPC_2 * (sg ** 2)
    return tpc, ppc


def calc_z_factor_dak(pressure_psia: float, temp_r: float, sg: float,
                       tol: float = 1e-10, max_iter: int = 100) -> float:
    """
    Calculates the gas compressibility factor (Z) using the
    Dranchuk & Abou-Kassem (1975) equation of state, solved iteratively
    (Newton-Raphson) for the reduced gas density. Pseudo-critical inputs
    come from calc_pseudo_criticals() (Sutton, 1985).
    """
    tpc, ppc = calc_pseudo_criticals(sg)
    tpr = temp_r / tpc
    ppr = pressure_psia / ppc

    c1 = DAK_A1 + DAK_A2 / tpr + DAK_A3 / tpr ** 3 + DAK_A4 / tpr ** 4 + DAK_A5 / tpr ** 5
    c2 = DAK_A6 + DAK_A7 / tpr + DAK_A8 / tpr ** 2
    c3 = DAK_A9 * (DAK_A7 / tpr + DAK_A8 / tpr ** 2)

    y = 0.27 * ppr / tpr  # initial guess assuming Z = 1

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
            y_new = y / 2.0  # guard against Newton-Raphson overshoot into non-physical density
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
    """Real-gas density approximation (lb/ft3): rho_g = 2.7 * SG * P / (Z * T)."""
    return (GAS_DENSITY_CONST * sg * pressure_psia) / (z_factor * temp_r)


# ---------------------------------------------------------------------------
# Flow area
# ---------------------------------------------------------------------------

def calc_pipe_area(id_in: float) -> float:
    """Full-bore cross-sectional area (ft2) of a pipe given its ID in inches."""
    return (math.pi / 4.0) * ((id_in / 12.0) ** 2)


# ---------------------------------------------------------------------------
# Liquid properties (density and surface tension from composition)
# ---------------------------------------------------------------------------

def calc_water_density(salinity_ppm: float) -> float:
    """
    Formation water (brine) density at standard conditions (lb/ft3),
    per McCain (1990): rho_w = salinity[mg/L] / 25000 + 62.428.
    """
    return (salinity_ppm / 25000.0) + FRESH_WATER_DENSITY_LBFT3


def calc_water_cut(wgr_bbl_mmscf: float, cgr_bbl_mmscf: float) -> Tuple[float, str]:
    """
    Computes water cut (fraction) from WGR and CGR, used as a COMPOSITION
    ratio (not a rate -- see module docstring). If both are zero/missing,
    assumes 100% condensed (fresh) water per SPE 20280's finding that
    condensed water is often the dominant loading liquid even when no
    liquid is measured at surface.

    Returns (water_cut, note).
    """
    total = wgr_bbl_mmscf + cgr_bbl_mmscf
    if total <= 0:
        return 1.0, "No WGR/CGR reported: assumed condensed (fresh) water per SPE 20280"
    return wgr_bbl_mmscf / total, ""


def calc_liquid_density(water_cut: float, oil_sg: float, salinity_ppm: float) -> float:
    """Blends water and oil density by water_cut into a single liquid density (lb/ft3)."""
    effective_salinity = 0.0 if water_cut >= 1.0 else salinity_ppm
    rho_water = calc_water_density(effective_salinity)
    rho_oil = WATER_REFERENCE_DENSITY_LBFT3 * oil_sg
    return water_cut * rho_water + (1.0 - water_cut) * rho_oil


def calc_oil_gas_surface_tension(oil_sg: float, pressure_psia: float, temp_f: float) -> float:
    """
    Baker & Swerdloff (1956) dead-oil gas/oil surface tension correlation
    (dynes/cm), with a pressure correction for dissolved gas:

        Sigma68  = 39.0 - 0.2571 * API
        Sigma100 = 37.5 - 0.2571 * API
        Sigma_T  = Sigma68 - (T - 68) * (Sigma68 - Sigma100) / 32
        Fc       = 1.0 - 0.025 * P^0.45
        Sigma_oil = Fc * Sigma_T

    Per Beggs' commonly-cited extension of this method, temperature is
    clamped to the 68-100 degF range the correlation was fit over rather
    than extrapolated. Result is clamped at zero (surface tension
    approaches zero near miscibility pressure, per the same literature).
    """
    api = sg_to_api(oil_sg)
    temp_f_clamped = min(max(temp_f, 68.0), 100.0)
    sigma_68 = 39.0 - 0.2571 * api
    sigma_100 = 37.5 - 0.2571 * api
    sigma_t = sigma_68 - (temp_f_clamped - 68.0) * (sigma_68 - sigma_100) / 32.0
    fc = max(1.0 - 0.025 * (pressure_psia ** 0.45), 0.0)
    return max(fc * sigma_t, 0.0)


def calc_liquid_surface_tension(water_cut: float, oil_sg: float, pressure_psia: float, temp_f: float) -> float:
    """Blends water (fixed default) and oil (Baker-Swerdloff) surface tension by water_cut."""
    sigma_oil = calc_oil_gas_surface_tension(oil_sg, pressure_psia, temp_f)
    return water_cut * WATER_GAS_SIGMA_DEFAULT + (1.0 - water_cut) * sigma_oil


# ---------------------------------------------------------------------------
# Critical velocity / critical rate (Turner, Li, Ikpeka)
# ---------------------------------------------------------------------------

def calc_critical_velocities(sigma_dynes: float, rho_l: float, rho_g: float) -> dict:
    """
    Calculates critical velocities (ft/s) under the Turner, Li, and
    Ikpeka-modified models.

    Raises ValueError if liquid density does not exceed gas density,
    since (rho_l - rho_g) is raised to a fractional power -- with a
    negative base, Python's ** operator silently returns a complex
    number instead of raising, which would otherwise corrupt downstream
    results without warning.
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

    return {
        "vcrit_turner": v_crit_turner,
        "vcrit_li": v_crit_li,
        "vcrit_ikpeka": v_crit_ikpeka,
    }


def calc_critical_rate(p_psia: float, temp_r: float, z: float, area_ft2: float, v_crit_fps: float) -> float:
    """Critical gas rate (Mscf/d): Qc = 3060 * P * A * Vc / (T * Z)."""
    return (CRITICAL_RATE_CONST * p_psia * area_ft2 * v_crit_fps) / (temp_r * z)


def classify_health(loading_ratio: float) -> str:
    """Classifies liquid loading risk based on Q_actual / Q_critical ratio."""
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
    Suggests a smaller tubing ID that would bring the loading ratio up to
    target_ratio, per SPE 20280 finding that smaller tubing raises gas
    velocity at a given rate and improves liquid lifting.

    A_new = A_old * (loading_ratio / target_ratio), converted back to ID.
    Returns None if already at/above target, or if the ratio is non-physical.
    This is a first-pass sizing hint, not a nodal-analysis result.
    """
    if loading_ratio >= target_ratio or loading_ratio <= 0:
        return None
    current_area_ft2 = calc_pipe_area(current_tubing_id_in)
    required_area_ft2 = current_area_ft2 * (loading_ratio / target_ratio)
    required_id_in = math.sqrt((4.0 * required_area_ft2) / math.pi) * 12.0
    return round(required_id_in, 3)


def generate_engineering_comments(pressure_psia: float, gas_sg: float, loading_ratio_tubing: float,
                                   loading_ratio_casing: float, liquid_note: str) -> str:
    """
    Generates field diagnostic comments.

    The casing-ID check re-uses SURFACE THP for the casing/open-hole area
    below the tubing shoe -- a deliberate simplification, not an actual
    pressure-at-depth estimate (see module docstring). A "below critical"
    result here is a genuine reason to investigate further with a full
    well/network model (e.g. Prosper/GAP); a "clear" result does NOT
    prove the below-tubing section is safe, since it ignores the higher
    actual pressure at depth.
    """
    comments = []

    if loading_ratio_casing < 1.0:
        comments.append(
            "Using THP at Casing ID: below critical velocity -- possible "
            "below-tubing loading risk, investigate further (e.g. Prosper/GAP nodal model)"
        )

    if liquid_note:
        comments.append(liquid_note)

    if loading_ratio_tubing < NEAR_LOADING_THRESHOLD:
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

def screen_well(row: dict, model_preference: str = "turner") -> dict:
    """
    Screens a single well using raw field-units input (as they'd appear in
    the CSV -- see load_wells_from_csv() for the exact column names) and
    returns SPE 20280-style screening metrics.

    Expected keys in row:
        Well, THP_psig, THT_C, Qgas_MMscfd, CGR_bbl_MMscf, WGR_bbl_MMscf,
        TubingID_in, CasingID_in, GasSG, OilSG, WaterSalinity_ppm
    """
    pressure_psia = psig_to_psia(row["THP_psig"])
    temp_r = celsius_to_rankine(row["THT_C"])
    temp_f = celsius_to_fahrenheit(row["THT_C"])

    z = calc_z_factor_dak(pressure_psia, temp_r, row["GasSG"])
    rho_g = calc_gas_density(row["GasSG"], pressure_psia, temp_r, z)

    water_cut, liquid_note = calc_water_cut(row["WGR_bbl_MMscf"], row["CGR_bbl_MMscf"])
    rho_l = calc_liquid_density(water_cut, row["OilSG"], row["WaterSalinity_ppm"])
    sigma_l = calc_liquid_surface_tension(water_cut, row["OilSG"], pressure_psia, temp_f)

    v_crits = calc_critical_velocities(sigma_l, rho_l, rho_g)
    v_crit_selected = v_crits.get(f"vcrit_{model_preference.lower()}", v_crits["vcrit_turner"])

    tubing_area = calc_pipe_area(row["TubingID_in"])
    casing_area = calc_pipe_area(row["CasingID_in"])

    q_crit_tubing_mscfd = calc_critical_rate(pressure_psia, temp_r, z, tubing_area, v_crit_selected)
    q_crit_casing_mscfd = calc_critical_rate(pressure_psia, temp_r, z, casing_area, v_crit_selected)

    q_actual_mscfd = row["Qgas_MMscfd"] * 1000.0
    q_actual_mmscfd = row["Qgas_MMscfd"]
    q_crit_tubing_mmscfd = q_crit_tubing_mscfd / 1000.0

    loading_ratio_tubing = q_actual_mscfd / q_crit_tubing_mscfd
    loading_ratio_casing = q_actual_mscfd / q_crit_casing_mscfd
    safety_margin_pct = 100.0 * (q_actual_mmscfd - q_crit_tubing_mmscfd) / q_crit_tubing_mmscfd
    status = classify_health(loading_ratio_tubing)

    comments = generate_engineering_comments(
        pressure_psia, row["GasSG"], loading_ratio_tubing, loading_ratio_casing, liquid_note
    )

    tubing_recommendation_in = recommend_tubing_size(row["TubingID_in"], loading_ratio_tubing)

    return {
        "Well Name": row["Well"],
        "Gas Rate (MMscfd)": round(q_actual_mmscfd, 2),
        "THP (psia)": round(pressure_psia, 1),
        "Z-Factor": round(z, 4),
        "Gas Density (lb/ft3)": round(rho_g, 3),
        "Water Cut": round(water_cut, 2),
        "Liquid Density (lb/ft3)": round(rho_l, 1),
        "Liquid Surface Tension (dynes/cm)": round(sigma_l, 1),
        "Critical Rate - Tubing (MMscfd)": round(q_crit_tubing_mmscfd, 2),
        "Loading Ratio - Tubing": round(loading_ratio_tubing, 2),
        "Loading Ratio - Casing ID": round(loading_ratio_casing, 2),
        "Safety Margin (%)": f"{round(safety_margin_pct, 1)}%",
        "Status": status,
        "Recommended Tubing ID (in)": tubing_recommendation_in,
        "Comments": comments,
    }


def load_wells_from_csv(csv_path: str) -> pd.DataFrame:
    """
    Loads a well-test CSV into a DataFrame, with basic column presence
    validation. Expected header (exact names):

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


def screen_wells(wells_df: pd.DataFrame, model_preference: str = "turner") -> pd.DataFrame:
    """Batch-screens a DataFrame of wells (from load_wells_from_csv) and returns a results table."""
    rows = wells_df.to_dict(orient="records")
    results = [screen_well(row, model_preference=model_preference) for row in rows]
    return pd.DataFrame(results)


def screen_wells_from_csv(csv_path: str, model_preference: str = "turner") -> pd.DataFrame:
    """Convenience wrapper: load a CSV and screen every well in it in one call."""
    wells_df = load_wells_from_csv(csv_path)
    return screen_wells(wells_df, model_preference=model_preference)


if __name__ == "__main__":
    # Minimal worked example so this file can be run directly without any
    # external CSV, to confirm the install works before pointing it at
    # real field data.
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
