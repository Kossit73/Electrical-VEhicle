"""Train the EV range model and report evaluation metrics."""

from __future__ import annotations

from pathlib import Path

from ev_model import (
    FEATURES,
    TARGET,
    EVRangeRegressor,
    evaluate_regression,
    load_dataset,
    to_matrix,
    train_test_split,
)


def main() -> None:
    dataset_path = Path(__file__).resolve().parents[1] / "data" / "ev_specs.csv"
    records = load_dataset(dataset_path)
    train, test = train_test_split(records, test_ratio=0.25, seed=123)
    x_train, y_train = to_matrix(train)
    x_test, y_test = to_matrix(test)

    model = EVRangeRegressor(learning_rate=0.02, epochs=6000, l2_penalty=0.0005)
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    metrics = evaluate_regression(y_test, predictions)

    print("Trained on", len(train), "samples and evaluated on", len(test))
    print("Features:", ", ".join(FEATURES))
    print("Target:", TARGET)
    for name, value in metrics.items():
        print(f"{name.upper()}: {value:.3f}")


if __name__ == "__main__":
    main()
