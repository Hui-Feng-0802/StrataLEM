"""Evaluate the manuscript's scalar height equations without reading a section."""
import json
from stratalem import FoundationInputs, FoundationClassification, calculate_foundation_height


if __name__ == '__main__':
    inputs = FoundationInputs(
        e0=0.564, a=1.2e-4, gamma1=18.5, c0=30, phi0=20, q=370,
        classification=FoundationClassification(
            e1=0.40, dm=0.60, beta=22, gamma0=21, thickness=10),
        q_basis='Adopted surcharge pressure at foundation level specified for this study: 370kPa.',
        q_basis_confirmed=True)
    print(json.dumps(calculate_foundation_height(inputs), indent=2, allow_nan=False))
