"""Utilities for EV range modelling and financial analysis."""

from .data import FEATURES, TARGET, load_dataset, to_matrix, train_test_split
from .finance import (
    DepreciationCalculator,
    DepreciationMethod,
    DepreciationParameters,
    EVAcquisitionCalculator,
    EVOperatingCostsCalculator,
    EVEnergyCostsCalculator,
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
    "EVOperatingCostsCalculator",
    "EVEnergyCostsCalculator",
    "EVVehicleSpecs",
    "EnergyParameters",
    "OperatingCostCalculator",
    "TaxIncentives",
    "TotalCostOfOwnershipCalculator",
    "VehicleComparison",
    "VehicleFinancing",
    "VehicleType",
]
