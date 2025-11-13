"""Utilities for training a simple electric vehicle range model."""

from .data import FEATURES, TARGET, load_dataset, train_test_split, to_matrix
from .model import EVRangeRegressor
from .metrics import mean_absolute_error, mean_squared_error, r2_score, evaluate_regression

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
]
