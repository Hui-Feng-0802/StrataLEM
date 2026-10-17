"""StrataLEM: stratigraphy-resolved ordinary-method stability calculations."""
from .framework import StrataLEM
from .legacy_interface import Slope
from .foundation import FoundationInputs, FoundationClassification, FoundationMaterialMap, calculate_foundation_height
from .section_checks import SectionReference

__version__ = "1.2.0"
__all__ = ["StrataLEM", "Slope", "FoundationInputs", "FoundationClassification",
           "FoundationMaterialMap", "SectionReference", "calculate_foundation_height"]
