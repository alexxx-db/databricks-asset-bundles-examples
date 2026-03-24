"""Tests for training.steps.transform module."""

import pandas as pd
import pytest
from sklearn.pipeline import Pipeline
from training.steps.transform import calculate_features, transformer_fn


class TestCalculateFeatures:
    """Tests for calculate_features()."""

    def _make_df(self, pickup, dropoff):
        return pd.DataFrame(
            {
                "tpep_pickup_datetime": pd.to_datetime([pickup]),
                "tpep_dropoff_datetime": pd.to_datetime([dropoff]),
            }
        )

    def test_adds_pickup_dow(self):
        # 2023-01-02 is a Monday (dayofweek == 0)
        df = self._make_df("2023-01-02 08:00:00", "2023-01-02 08:30:00")
        result = calculate_features(df)
        assert "pickup_dow" in result.columns
        assert result["pickup_dow"].iloc[0] == 0

    def test_adds_pickup_hour(self):
        df = self._make_df("2023-01-02 14:00:00", "2023-01-02 14:30:00")
        result = calculate_features(df)
        assert "pickup_hour" in result.columns
        assert result["pickup_hour"].iloc[0] == 14

    def test_pickup_dow_range(self):
        # Sunday = 6
        df = self._make_df("2023-01-01 10:00:00", "2023-01-01 10:15:00")
        result = calculate_features(df)
        assert 0 <= result["pickup_dow"].iloc[0] <= 6
        assert result["pickup_dow"].iloc[0] == 6  # Sunday

    def test_pickup_hour_range(self):
        df = self._make_df("2023-01-02 23:45:00", "2023-01-03 00:15:00")
        result = calculate_features(df)
        assert 0 <= result["pickup_hour"].iloc[0] <= 23
        assert result["pickup_hour"].iloc[0] == 23

    def test_trip_duration_minutes(self):
        df = self._make_df("2023-01-02 08:00:00", "2023-01-02 08:45:00")
        result = calculate_features(df)
        assert "trip_duration" in result.columns
        assert result["trip_duration"].iloc[0] == pytest.approx(45.0)

    def test_drops_datetime_columns(self):
        df = self._make_df("2023-01-02 08:00:00", "2023-01-02 08:30:00")
        result = calculate_features(df)
        assert "tpep_pickup_datetime" not in result.columns
        assert "tpep_dropoff_datetime" not in result.columns

    def test_multiple_rows(self):
        df = pd.DataFrame(
            {
                "tpep_pickup_datetime": pd.to_datetime(
                    ["2023-01-02 08:00:00", "2023-01-03 16:00:00"]
                ),
                "tpep_dropoff_datetime": pd.to_datetime(
                    ["2023-01-02 08:20:00", "2023-01-03 16:50:00"]
                ),
            }
        )
        result = calculate_features(df)
        assert result["pickup_dow"].tolist() == [0, 1]  # Monday, Tuesday
        assert result["pickup_hour"].tolist() == [8, 16]
        assert result["trip_duration"].tolist() == pytest.approx([20.0, 50.0])


class TestTransformerFn:
    """Tests for transformer_fn()."""

    def test_returns_pipeline(self):
        pipeline = transformer_fn()
        assert isinstance(pipeline, Pipeline)

    def test_has_two_steps(self):
        pipeline = transformer_fn()
        assert len(pipeline.steps) == 2

    def test_step_names(self):
        pipeline = transformer_fn()
        step_names = [name for name, _ in pipeline.steps]
        assert step_names == ["calculate_time_and_duration_features", "encoder"]

    def test_fit_transform(self):
        pipeline = transformer_fn()
        df = pd.DataFrame(
            {
                "tpep_pickup_datetime": pd.to_datetime(
                    ["2023-01-02 08:00:00", "2023-01-03 16:00:00", "2023-01-04 12:00:00"]
                ),
                "tpep_dropoff_datetime": pd.to_datetime(
                    ["2023-01-02 08:30:00", "2023-01-03 16:45:00", "2023-01-04 13:00:00"]
                ),
                "trip_distance": [3.5, 7.2, 5.0],
            }
        )
        result = pipeline.fit_transform(df)
        # Should produce encoded output without errors
        assert result.shape[0] == 3
        # Columns: one-hot for hour (3 unique hours), one-hot for dow (3 unique days),
        # scaled trip_distance, scaled trip_duration = 3 + 3 + 2 = 8
        assert result.shape[1] == 8
