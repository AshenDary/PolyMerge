from __future__ import annotations

import pytest

from app.data.ddinter_dataset import FEATURE_COLUMNS
from app.services.ddi_feature_builder import PairFeatureBuilder, PairFeatureUnavailableError


def test_pair_feature_builder_reuses_frozen_feature_contract():
    builder = PairFeatureBuilder()

    features = builder.build_features("Compound::DB00177", "Compound::DB00331")

    assert list(features) == FEATURE_COLUMNS
    assert len(features) == 55
    assert features["hetionet_available_count"] == 2
    assert features["both_hetionet_available"] == 1
    assert "safetyScore" not in features


def test_pair_feature_builder_is_unordered_and_deterministic():
    builder = PairFeatureBuilder()

    forward = builder.build_features("Compound::DB00177", "Compound::DB00331")
    reverse = builder.build_features("Compound::DB00331", "Compound::DB00177")

    assert forward == reverse


def test_pair_feature_builder_fails_closed_for_unmapped_candidate_pair():
    builder = PairFeatureBuilder()

    with pytest.raises(PairFeatureUnavailableError, match="DDInter-Hetionet bridge"):
        builder.build_features("Compound::DOES-NOT-EXIST", "Compound::DB00331")
