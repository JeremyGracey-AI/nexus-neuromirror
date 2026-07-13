from __future__ import annotations

import numpy as np
import pytest

from neuralset_scaffold import neuralset_adapter
from neuralset_scaffold.config import Model
from neuralset_scaffold.features import FeatureMatrix
from neuralset_scaffold.model import ModelError, _choose_cv, evaluate


def _features(n_per_session=10, n_sessions=3, sep=3.0, seed=0):
    rng = np.random.default_rng(seed)
    X_rows, y, groups = [], [], []
    for s in range(n_sessions):
        for _ in range(n_per_session):
            for lab, mean in (("A", 0.0), ("B", sep)):
                X_rows.append(rng.standard_normal(4) + mean)
                y.append(lab)
                groups.append(f"s{s}")
    return FeatureMatrix(
        X=np.asarray(X_rows),
        y=np.array(y, dtype=object),
        groups=np.array(groups, dtype=object),
        feature_names=[f"f{i}" for i in range(4)],
    )


def test_choose_cv_leave_one_session_out():
    groups = np.array(["a", "a", "b", "b", "c", "c"], dtype=object)
    cv, scheme = _choose_cv(groups, n_splits=5)
    assert scheme == "leave-one-session-out"


def test_choose_cv_group_kfold():
    groups = np.array([f"s{i}" for i in range(10)], dtype=object)
    cv, scheme = _choose_cv(groups, n_splits=5)
    assert scheme == "group-5fold"


def test_choose_cv_requires_two_sessions():
    groups = np.array(["only"] * 10, dtype=object)
    with pytest.raises(ModelError):
        _choose_cv(groups, n_splits=5)


def test_evaluate_separable_above_chance():
    fm = _features(sep=4.0)
    res = evaluate(fm, Model(kind="logreg", n_splits=3))
    assert res.mean_accuracy > res.chance_level
    assert res.cv_scheme == "leave-one-session-out"
    assert len(res.folds) == 3
    assert res.feature_importance  # logreg exposes coef_


def test_evaluate_lda_runs():
    fm = _features(sep=4.0)
    res = evaluate(fm, Model(kind="lda", n_splits=3))
    assert 0.0 <= res.mean_accuracy <= 1.0


def test_evaluate_empty_raises():
    fm = FeatureMatrix(
        X=np.empty((0, 4)),
        y=np.array([], dtype=object),
        groups=np.array([], dtype=object),
        feature_names=["f0", "f1", "f2", "f3"],
    )
    with pytest.raises(ModelError):
        evaluate(fm, Model())


def test_adapter_reports_availability():
    desc = neuralset_adapter.describe()
    assert "available" in desc
    assert isinstance(desc["available"], bool)
    assert desc["available"] == neuralset_adapter.is_available()


def test_adapter_construction_matches_availability():
    if neuralset_adapter.is_available():
        adapter = neuralset_adapter.NeuralSetAdapter()
        assert adapter is not None
    else:
        with pytest.raises(neuralset_adapter.NeuralSetUnavailableError):
            neuralset_adapter.NeuralSetAdapter()
