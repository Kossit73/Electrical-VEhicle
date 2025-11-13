"""Utilities for EV range modelling and financial analysis."""

from .data import FEATURES, TARGET, load_dataset, to_matrix, train_test_split
from .finance import (
    DepreciationCalculator,
    DepreciationMethod,
    DepreciationParameters,
    EVAcquisitionCalculator,
    EVComparisonAnalyzer,
    EVEnergyCostsCalculator,
    EVOperatingCostsCalculator,
    EVSensitivityAnalyzer,
    EVTotalCostOfOwnershipAnalyzer,
    EVVehicleSpecs,
    EnergyParameters,
    OperatingCostCalculator,
    TaxIncentives,
    TotalCostOfOwnershipCalculator,
    VehicleComparison,
    VehicleFinancing,
    VehicleType,
)
from .metrics import evaluate_regression, mean_absolute_error, mean_squared_error, r2_score
from .model import EVRangeRegressor

try:  # pragma: no cover - importing API router is optional
    from .api import ev_router
except ModuleNotFoundError:  # pragma: no cover - FastAPI not installed
    ev_router = None  # type: ignore

__all__ = [
    "FEATURES",
    "TARGET",
    "load_dataset",
    "train_test_split",
    "to_matrix",
    "EVRangeRegressor",
    "mean_absolute_error",
    "mean_squared_error",
    "r2_score",
    "evaluate_regression",
    "DepreciationCalculator",
    "DepreciationMethod",
    "DepreciationParameters",
    "EVAcquisitionCalculator",
    "EVComparisonAnalyzer",
    "EVEnergyCostsCalculator",
    "EVOperatingCostsCalculator",
    "EVSensitivityAnalyzer",
    "EVTotalCostOfOwnershipAnalyzer",
    "EVVehicleSpecs",
    "EnergyParameters",
    "OperatingCostCalculator",
    "TaxIncentives",
    "TotalCostOfOwnershipCalculator",
    "VehicleComparison",
    "VehicleFinancing",
    "VehicleType",
    "ev_router",
]
