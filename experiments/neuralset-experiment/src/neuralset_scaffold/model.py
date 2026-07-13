"""Baseline classifier with session-aware cross-validation.

Uses GroupKFold (or leave-one-session-out) so that windows from the same
recording session never appear in both train and test folds. This avoids the
optimistic bias of session leakage — a common pitfall in EEG pipelines.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .config import Model
from .features import FeatureMatrix


@dataclass
class FoldResult:
    fold: int
    test_sessions: list[str]
    n_test: int
    accuracy: float
    balanced_accuracy: float
    f1_macro: float


@dataclass
class EvalResult:
    classes: list[str]
    n_windows: int
    n_features: int
    cv_scheme: str
    folds: list[FoldResult] = field(default_factory=list)
    confusion: list[list[int]] = field(default_factory=list)
    chance_level: float = 0.0
    feature_importance: dict[str, float] = field(default_factory=dict)

    @property
    def mean_accuracy(self) -> float:
        return float(np.mean([f.accuracy for f in self.folds])) if self.folds else 0.0

    @property
    def std_accuracy(self) -> float:
        return float(np.std([f.accuracy for f in self.folds])) if self.folds else 0.0

    @property
    def mean_balanced_accuracy(self) -> float:
        return (
            float(np.mean([f.balanced_accuracy for f in self.folds])) if self.folds else 0.0
        )

    @property
    def mean_f1_macro(self) -> float:
        return float(np.mean([f.f1_macro for f in self.folds])) if self.folds else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "classes": self.classes,
            "n_windows": self.n_windows,
            "n_features": self.n_features,
            "cv_scheme": self.cv_scheme,
            "chance_level": round(self.chance_level, 4),
            "mean_accuracy": round(self.mean_accuracy, 4),
            "std_accuracy": round(self.std_accuracy, 4),
            "mean_balanced_accuracy": round(self.mean_balanced_accuracy, 4),
            "mean_f1_macro": round(self.mean_f1_macro, 4),
            "folds": [
                {
                    "fold": f.fold,
                    "test_sessions": f.test_sessions,
                    "n_test": f.n_test,
                    "accuracy": round(f.accuracy, 4),
                    "balanced_accuracy": round(f.balanced_accuracy, 4),
                    "f1_macro": round(f.f1_macro, 4),
                }
                for f in self.folds
            ],
            "confusion_matrix": self.confusion,
            "top_features": dict(
                sorted(self.feature_importance.items(), key=lambda kv: -abs(kv[1]))[:15]
            ),
        }


class ModelError(ValueError):
    """Raised when the data cannot support evaluation."""


def build_estimator(cfg: Model) -> Pipeline:
    if cfg.kind == "lda":
        clf: object = LinearDiscriminantAnalysis()
    else:
        clf = LogisticRegression(max_iter=1000, random_state=cfg.random_state)
    steps = []
    if cfg.standardize:
        steps.append(("scale", StandardScaler()))
    steps.append(("clf", clf))
    return Pipeline(steps)


def _choose_cv(groups: np.ndarray, n_splits: int) -> tuple[object, str]:
    unique = np.unique(groups)
    n_groups = len(unique)
    if n_groups < 2:
        raise ModelError(
            f"Session-aware CV needs >= 2 sessions, found {n_groups}. "
            "Record more sessions or relax the grouping."
        )
    if n_groups <= n_splits:
        return LeaveOneGroupOut(), "leave-one-session-out"
    return GroupKFold(n_splits=n_splits), f"group-{n_splits}fold"


def evaluate(features: FeatureMatrix, cfg: Model) -> EvalResult:
    """Run session-aware cross-validation and aggregate metrics."""
    X, y, groups = features.X, features.y, features.groups
    if X.shape[0] == 0:
        raise ModelError("No windows/features available to evaluate.")
    classes = sorted(set(y.tolist()))
    if len(classes) < 2:
        raise ModelError(f"Need >= 2 classes, found {classes}.")

    cv, scheme = _choose_cv(groups, cfg.n_splits)
    result = EvalResult(
        classes=classes,
        n_windows=int(X.shape[0]),
        n_features=int(X.shape[1]),
        cv_scheme=scheme,
        chance_level=_chance_level(y),
    )

    y_true_all: list[str] = []
    y_pred_all: list[str] = []
    coef_accum = np.zeros(X.shape[1])
    coef_folds = 0

    for i, (train_idx, test_idx) in enumerate(cv.split(X, y, groups)):
        est = build_estimator(cfg)
        est.fit(X[train_idx], y[train_idx])
        pred = est.predict(X[test_idx])
        yt = y[test_idx]
        result.folds.append(
            FoldResult(
                fold=i,
                test_sessions=sorted(set(groups[test_idx].tolist())),
                n_test=int(len(test_idx)),
                accuracy=float(accuracy_score(yt, pred)),
                balanced_accuracy=float(balanced_accuracy_score(yt, pred)),
                f1_macro=float(f1_score(yt, pred, average="macro", zero_division=0)),
            )
        )
        y_true_all.extend(yt.tolist())
        y_pred_all.extend(pred.tolist())

        clf = est.named_steps["clf"]
        if hasattr(clf, "coef_"):
            coef_accum += np.abs(np.asarray(clf.coef_)).mean(axis=0)
            coef_folds += 1

    result.confusion = confusion_matrix(y_true_all, y_pred_all, labels=classes).tolist()
    if coef_folds:
        importance = coef_accum / coef_folds
        result.feature_importance = {
            name: float(val) for name, val in zip(features.feature_names, importance, strict=False)
        }
    return result


def _chance_level(y: np.ndarray) -> float:
    _, counts = np.unique(y, return_counts=True)
    return float(counts.max() / counts.sum())
