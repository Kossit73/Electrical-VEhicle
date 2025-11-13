from pathlib import Path

from ev_model import (
    EVRangeRegressor,
    evaluate_regression,
    load_dataset,
    to_matrix,
    train_test_split,
)


def test_regressor_produces_reasonable_error_bounds():
    dataset_path = Path(__file__).resolve().parents[1] / "data" / "ev_specs.csv"
    records = load_dataset(dataset_path)
    train, test = train_test_split(records, test_ratio=0.3, seed=99)
    x_train, y_train = to_matrix(train)
    x_test, y_test = to_matrix(test)

    model = EVRangeRegressor(learning_rate=0.03, epochs=7000, l2_penalty=0.0003)
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    metrics = evaluate_regression(y_test, predictions)

    assert metrics["mae"] < 25
    assert metrics["mse"] < 900
    assert metrics["r2"] > 0.7


def test_model_converges_decreasing_loss():
    dataset_path = Path(__file__).resolve().parents[1] / "data" / "ev_specs.csv"
    records = load_dataset(dataset_path)
    train, _ = train_test_split(records, test_ratio=0.2, seed=12)
    x_train, y_train = to_matrix(train)

    model = EVRangeRegressor(learning_rate=0.02, epochs=500, l2_penalty=0.0005)
    model.fit(x_train, y_train)
    history = model.history_

    assert len(history) > 10
    assert history[0] > history[-1]
    assert history[-1] < history[len(history) // 2]
