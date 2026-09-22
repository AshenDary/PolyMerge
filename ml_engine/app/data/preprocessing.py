"""Leakage-safe preprocessing helpers for Sprint 4 model comparison."""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.data.sprint3_dataset import FEATURE_COLUMNS, METADATA_COLUMNS, TARGET_COLUMN


def get_feature_columns(frame: pd.DataFrame) -> list[str]:
    """Return model input columns, excluding target and row metadata."""
    excluded = set(METADATA_COLUMNS + [TARGET_COLUMN, "split"])
    return [column for column in frame.columns if column not in excluded]


def split_features_target(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Return X/y without leaking metadata or the target into X."""
    return frame[get_feature_columns(frame)].copy(), frame[TARGET_COLUMN].copy()


def build_preprocessing_pipeline(frame: pd.DataFrame | None = None) -> ColumnTransformer:
    """Build a scikit-learn preprocessor to fit on training data only."""
    if frame is None:
        numeric_features = FEATURE_COLUMNS
        categorical_features: list[str] = []
    else:
        feature_frame = frame[get_feature_columns(frame)]
        numeric_features = feature_frame.select_dtypes(include=["number", "bool"]).columns.tolist()
        categorical_features = [
            column for column in feature_frame.columns if column not in numeric_features
        ]

    transformers = []
    if numeric_features:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_features,
            )
        )
    if categorical_features:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            )
        )

    return ColumnTransformer(transformers=transformers, remainder="drop")
