import pandas as pd
import pytest

from nq.research.holdout import HoldoutViolation, assert_pre_holdout, clip_to_train


def _s(end):
    return pd.Series(1.0, index=pd.date_range("2024-06-01", end, freq="B"))


def test_pre_holdout_series_passes():
    assert assert_pre_holdout(_s("2024-06-28")) is None


def test_series_past_train_end_raises():
    with pytest.raises(HoldoutViolation):
        assert_pre_holdout(_s("2024-07-01"))


def test_valid_unseal_token_allows_and_is_returned():
    assert assert_pre_holdout(_s("2025-01-01"), unseal_token="AMD-2027-01-0153") == "AMD-2027-01-0153"


def test_malformed_token_still_raises():
    with pytest.raises(HoldoutViolation):
        assert_pre_holdout(_s("2025-01-01"), unseal_token="please")


def test_date_column_frame_and_clip():
    df = pd.DataFrame({"date": pd.to_datetime(["2024-06-30", "2024-07-02"]), "r": [1, 2]})
    with pytest.raises(HoldoutViolation):
        assert_pre_holdout(df)
    s = clip_to_train(_s("2024-08-01"))
    assert assert_pre_holdout(s) is None and s.index.max() <= pd.Timestamp("2024-06-30")
