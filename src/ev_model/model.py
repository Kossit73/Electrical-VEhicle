"""Implementation of a light-weight gradient-descent regressor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _std(values: Sequence[float]) -> float:
    mean_value = _mean(values)
    variance = sum((value - mean_value) ** 2 for value in values) / len(values)
    return variance ** 0.5 if variance > 0 else 0.0


@dataclass
class StandardScaler:
    """Simple feature standardiser with lazily computed parameters."""

    mean_: List[float] = field(default_factory=list)
    scale_: List[float] = field(default_factory=list)

    def fit(self, rows: Iterable[Sequence[float]]) -> "StandardScaler":
        columns = list(zip(*rows))
        if not columns:
            raise ValueError("Cannot fit StandardScaler on empty data")
        self.mean_ = [_mean(col) for col in columns]
        self.scale_ = [_std(col) or 1.0 for col in columns]
        return self

    def transform(self, rows: Iterable[Sequence[float]]) -> List[List[float]]:
        if not self.mean_ or not self.scale_:
            raise ValueError("Scaler has not been fitted")
        transformed: List[List[float]] = []
        for row in rows:
            transformed.append(
                [
                    (value - mean) / scale
                    for value, mean, scale in zip(row, self.mean_, self.scale_)
                ]
            )
        return transformed

    def fit_transform(self, rows: Iterable[Sequence[float]]) -> List[List[float]]:
        data = list(rows)
        self.fit(data)
        return self.transform(data)


@dataclass
class EVRangeRegressor:
    """Train a regression model for EV range estimation using gradient descent."""

    learning_rate: float = 0.01
    epochs: int = 4000
    l2_penalty: float = 0.001
    tolerance: float = 1e-7
    scaler: StandardScaler = field(default_factory=StandardScaler, init=False)
    weights_: List[float] = field(default_factory=list, init=False)
    bias_: float = field(default=0.0, init=False)
    history_: List[float] = field(default_factory=list, init=False)

    def fit(self, features: Iterable[Sequence[float]], target: Sequence[float]) -> "EVRangeRegressor":
        data = list(features)
        if not data:
            raise ValueError("features cannot be empty")
        if len(data) != len(target):
            raise ValueError("features and target must have the same length")

        scaled = self.scaler.fit_transform(data)
        self.weights_ = [0.0 for _ in range(len(scaled[0]))]
        self.bias_ = 0.0
        self.history_.clear()

        target_values = list(target)
        prev_loss = float("inf")
        for _ in range(self.epochs):
            predictions = self._predict_scaled(scaled)
            errors = [prediction - actual for prediction, actual in zip(predictions, target_values)]
            loss = self._loss(errors)
            self.history_.append(loss)
            if prev_loss - loss < self.tolerance:
                break
            prev_loss = loss

            gradients = self._gradients(scaled, errors)
            self.weights_ = [w - self.learning_rate * grad for w, grad in zip(self.weights_, gradients)]
            bias_gradient = sum(errors) / len(errors)
            self.bias_ -= self.learning_rate * bias_gradient
        return self

    def predict(self, features: Iterable[Sequence[float]]) -> List[float]:
        if not self.weights_:
            raise ValueError("Model has not been fitted")
        scaled = self.scaler.transform(list(features))
        return self._predict_scaled(scaled)

    def _predict_scaled(self, scaled: Iterable[Sequence[float]]) -> List[float]:
        predictions: List[float] = []
        for row in scaled:
            predictions.append(self.bias_ + sum(w * value for w, value in zip(self.weights_, row)))
        return predictions

    def _gradients(self, scaled: Sequence[Sequence[float]], errors: Sequence[float]) -> List[float]:
        gradients: List[float] = []
        data_len = len(scaled)
        for column in zip(*scaled):
            gradient = sum(error * value for error, value in zip(errors, column)) / data_len
            gradients.append(gradient + self.l2_penalty * self.weights_[len(gradients)])
        return gradients

    def _loss(self, errors: Sequence[float]) -> float:
        mse = sum(error ** 2 for error in errors) / (2 * len(errors))
        regulariser = 0.5 * self.l2_penalty * sum(weight ** 2 for weight in self.weights_)
        return mse + regulariser
