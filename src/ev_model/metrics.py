"""Evaluation utilities for regression models."""

from __future__ import annotations

from typing import Iterable, Mapping


def mean_squared_error(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    true = list(y_true)
    pred = list(y_pred)
    if len(true) != len(pred):
        raise ValueError("y_true and y_pred must be the same length")
    if not true:
        raise ValueError("y_true and y_pred cannot be empty")
    errors = [(t - p) ** 2 for t, p in zip(true, pred)]
    return sum(errors) / len(errors)


def mean_absolute_error(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    true = list(y_true)
    pred = list(y_pred)
    if len(true) != len(pred):
        raise ValueError("y_true and y_pred must be the same length")
    if not true:
        raise ValueError("y_true and y_pred cannot be empty")
    errors = [abs(t - p) for t, p in zip(true, pred)]
    return sum(errors) / len(errors)


def r2_score(y_true: Iterable[float], y_pred: Iterable[float]) -> float:
    true = list(y_true)
    pred = list(y_pred)
    if len(true) != len(pred):
        raise ValueError("y_true and y_pred must be the same length")
    if not true:
        raise ValueError("y_true and y_pred cannot be empty")

    mean_true = sum(true) / len(true)
    ss_tot = sum((value - mean_true) ** 2 for value in true)
    ss_res = sum((t - p) ** 2 for t, p in zip(true, pred))
    if ss_tot == 0:
        return 0.0
    return 1 - ss_res / ss_tot


def evaluate_regression(
    y_true: Iterable[float], y_pred: Iterable[float]
) -> Mapping[str, float]:
    """Return a dictionary of common regression metrics."""

    return {
        "mae": mean_absolute_error(y_true, y_pred),
        "mse": mean_squared_error(y_true, y_pred),
        "r2": r2_score(y_true, y_pred),
    }
