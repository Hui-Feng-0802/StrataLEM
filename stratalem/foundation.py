"""Optional implementation of the manuscript's adopted height equations.

Units: m, kPa, kN/m3, kPa^-1 and degrees. This module does not alter geometry.
The bearing calculation is the manuscript's TWO-TERM expression, not a general
implementation of all Terzaghi bearing-capacity terms or design factors.
"""
from dataclasses import asdict, dataclass
import math
import numbers


def _finite(name, value, *, minimum=None, positive=False):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number, not a boolean.")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive.")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}.")
    return value


@dataclass(frozen=True)
class FoundationClassification:
    """Inputs to Eqs. (1)-(4); beta is an assumed overall slope angle."""
    e1: float
    dm: float
    beta: float
    gamma0: float
    thickness: float


@dataclass(frozen=True)
class FoundationMaterialMap:
    """Map scalar foundation inputs to the LEM [c,phi,gamma] material rows."""
    waste_index: int
    soil_index: int


def check_foundation_materials(inputs, parameters, mapping):
    if mapping is None:
        return {"status": "mapping_not_supplied"}
    if not isinstance(mapping, FoundationMaterialMap):
        raise TypeError("foundation_material_map must be FoundationMaterialMap or None.")
    for value in (mapping.waste_index, mapping.soil_index):
        if (isinstance(value, bool) or not isinstance(value, numbers.Integral)
                or not 0 <= value < len(parameters)):
            raise ValueError("Foundation material indices must be valid nonnegative integers.")
    fill, soil = parameters[mapping.waste_index], parameters[mapping.soil_index]
    comparisons = {'gamma1': (float(inputs.gamma1), float(fill[2])),
                   'c0': (float(inputs.c0), float(soil[0])),
                   'phi0': (float(inputs.phi0), float(soil[1]))}
    if inputs.classification is not None:
        comparisons['gamma0'] = (float(inputs.classification.gamma0), float(soil[2]))
    mismatches = [key for key, (a, b) in comparisons.items()
                  if not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10)]
    return {'status': 'mismatch' if mismatches else 'matched',
            'mapping': asdict(mapping), 'values_foundation_vs_stability': comparisons,
            'mismatched_parameters': mismatches}


@dataclass(frozen=True)
class FoundationInputs:
    """Symbols match Eqs. (5)-(9) and the original manuscript.

    q is entered independently. It is never calculated as gamma1 * unknown H.
    q_basis records the adopted surcharge assumption. q_basis_confirmed means
    the user has explicitly acknowledged that assumption and the two-term
    formulation; it is not a claim that field measurements were verified.
    """
    e0: float
    a: float
    gamma1: float
    c0: float
    phi0: float
    q: float
    classification: FoundationClassification | None = None
    compression_fraction: float = 0.20
    height_step: float = 1.0
    q_basis: str = ""
    q_basis_confirmed: bool = False


def classify_foundation(inputs):
    if inputs.classification is None:
        return {"status": "not_evaluated"}
    soil = inputs.classification
    e1 = _finite("e1", soil.e1, positive=True)
    dm = _finite("dm", soil.dm, positive=True)
    beta = _finite("beta", soil.beta, positive=True)
    if beta >= 90:
        raise ValueError("beta must be in (0,90) degrees.")
    gamma0 = _finite("gamma0", soil.gamma0, positive=True)
    thickness = _finite("thickness", soil.thickness, positive=True)
    ratio = e1 / (1.0 + e1)
    if ratio >= 1:
        raise ValueError("e1 is too large for a resolvable void ratio.")
    n_minimum = math.log(0.01) / math.log(ratio) - 1.0
    n = max(1, math.ceil(n_minimum))
    # Closed geometric sum equals the manuscript's sum for integer n.
    h1 = dm * ratio * (-math.expm1(n * math.log(ratio))) / (1.0 - ratio)
    h2 = 2.0 * float(inputs.c0) / (math.tan(math.radians(beta)) * gamma0)
    h0 = h1 + h2
    return {"status": "thick" if thickness > h0 else "not_thick",
            "n_minimum": n_minimum, "n": n, "h1_m": h1, "h2_m": h2,
            "h0_m": h0, "actual_thickness_m": thickness, "beta_degrees": beta}


def calculate_foundation_height(inputs):
    """Evaluate adopted equations at full precision; no fitted output values."""
    if not isinstance(inputs, FoundationInputs):
        raise TypeError("foundation must be FoundationInputs or None.")
    e0 = _finite("e0", inputs.e0, minimum=0)
    a = _finite("a", inputs.a, positive=True)
    gamma = _finite("gamma1", inputs.gamma1, positive=True)
    cohesion = _finite("c0", inputs.c0, minimum=0)
    phi = _finite("phi0", inputs.phi0, minimum=0)
    if phi >= 60:
        raise ValueError("This implementation supports phi0 in [0,60) degrees.")
    q = _finite("q", inputs.q, minimum=0)
    strain = _finite("compression_fraction", inputs.compression_fraction, positive=True)
    if strain >= 1:
        raise ValueError("compression_fraction must be < 1.")
    step = _finite("height_step", inputs.height_step, positive=True)
    if not isinstance(inputs.q_basis, str) or not isinstance(inputs.q_basis_confirmed, bool):
        raise ValueError("q_basis must be text and q_basis_confirmed must be boolean.")
    if inputs.q_basis_confirmed and not inputs.q_basis.strip():
        raise ValueError("Document q_basis before confirming it.")
    hd = strain * (1.0 + e0) / (a * gamma)
    rad = math.radians(phi)
    # Equivalent to exp(pi*tan(phi))*tan(pi/4+phi/2)^2.
    # expm1 avoids cancellation in Nc as phi approaches zero.
    log_nq = math.pi * math.tan(rad) + 2.0 * math.asinh(math.tan(rad))
    nq = math.exp(log_nq)
    nc = math.pi + 2.0 if phi == 0 else math.expm1(log_nq) / math.tan(rad)
    ps = cohesion * nc + q * nq
    hb = ps / gamma
    limit = min(hd, hb)
    # Downward rounding remains conservative, including fractional steps.
    adopted = math.floor(limit / step) * step
    while adopted > limit:
        adopted -= step
    soil = classify_foundation(inputs)
    issues = []
    if soil["status"] == "not_evaluated":
        issues.append("Foundation classification was not evaluated.")
    elif soil["status"] == "not_thick":
        issues.append("The thick-surficial-soil condition h > h0 is not met.")
    if not inputs.q_basis_confirmed:
        issues.append("The adopted q assumption and two-term formulation have not been acknowledged.")
    if adopted <= 0:
        issues.append("The adopted height is zero after downward rounding.")
    return {"formulation": "manuscript_two_term_bearing_and_compression",
            "inputs": asdict(inputs), "classification": soil,
            "compression_height_m": hd, "Nq": nq, "Nc": nc,
            "bearing_capacity_kPa": ps, "bearing_height_m": hb,
            "controlling_height_m": limit, "adopted_height_m": adopted,
            "controlling_method": "compression" if hd <= hb else "bearing_capacity",
            "q_basis_confirmed": inputs.q_basis_confirmed,
            "bearing_safety_factor_applied": False, "issues": issues}
