"""Tests for training.steps.custom_metrics module."""

import numpy as np
import pandas as pd
import pytest
from training.steps.custom_metrics import weighted_mean_squared_error


class TestWeightedMeanSquaredError:
    """Tests for weighted_mean_squared_error()."""

    def test_perfect_predictions(self):
        eval_df = pd.DataFrame({"prediction": [2.0, 3.0, 4.0], "target": [2.0, 3.0, 4.0]})
        result = weighted_mean_squared_error(eval_df, {})
        assert result == pytest.approx(0.0)

    def test_known_values(self):
        # predictions=[2, 4], targets=[3, 5]
        # sample_weight = 1/prediction = [0.5, 0.25]
        # MSE with sample_weight: sum(w*(p-t)^2) / sum(w)
        # = (0.5*(2-3)^2 + 0.25*(4-5)^2) / (0.5 + 0.25)
        # = (0.5*1 + 0.25*1) / 0.75
        # = 0.75 / 0.75 = 1.0
        eval_df = pd.DataFrame({"prediction": [2.0, 4.0], "target": [3.0, 5.0]})
        result = weighted_mean_squared_error(eval_df, {})
        assert result == pytest.approx(1.0)

    def test_uses_inverse_prediction_weight(self):
        # With uniform predictions, weights are uniform, so result = standard MSE
        eval_df = pd.DataFrame({"prediction": [5.0, 5.0, 5.0], "target": [6.0, 4.0, 5.0]})
        # All weights = 1/5 = 0.2 (uniform)
        # MSE = (1 + 1 + 0) / 3 = 0.6667
        result = weighted_mean_squared_error(eval_df, {})
        expected = np.mean([(5 - 6) ** 2, (5 - 4) ** 2, (5 - 5) ** 2])
        assert result == pytest.approx(expected, rel=1e-6)

    def test_builtin_metrics_ignored(self):
        eval_df = pd.DataFrame({"prediction": [2.0, 3.0], "target": [2.0, 3.0]})
        result1 = weighted_mean_squared_error(eval_df, {})
        result2 = weighted_mean_squared_error(eval_df, {"some_metric": 42})
        assert result1 == result2
