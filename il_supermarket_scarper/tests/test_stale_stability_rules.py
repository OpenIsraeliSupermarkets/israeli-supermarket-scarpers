"""Stale-rule warning: a stability rule approved "no files" but files came back."""

import json
import warnings
from datetime import datetime
from unittest.mock import patch

import pytest

from il_supermarket_scarper import ScraperFactory, ScraperStability
from il_supermarket_scarper.scraper_stability import (
    STALE_STABILITY_RULE_MARKER,
    ScraperKind,
    StaleStabilityRuleWarning,
)
from il_supermarket_scarper.utils.files.file_types import FileTypesFilters

STORE_ONLY = [FileTypesFilters.STORE_FILE.name]


def _payload(record):
    message = str(record.message)
    assert message.startswith(STALE_STABILITY_RULE_MARKER + " ")
    return json.loads(message[len(STALE_STABILITY_RULE_MARKER) + 1 :])


def test_warning_is_not_filtered_by_pytest_ini():
    """pytest.ini ignores UserWarning; this warning must stay visible."""
    assert not issubclass(StaleStabilityRuleWarning, UserWarning)


def test_warns_when_store_rule_approved_but_files_found():
    """Yellow's "no store files" rule with a store file back is reported."""
    with pytest.warns(StaleStabilityRuleWarning) as records:
        assert ScraperStability.warn_if_files_found_when_empty_approved(
            "YELLOW", 1, limit=1, files_types=STORE_ONLY
        )
    payload = _payload(records[0])
    assert payload == {
        "scraper": "YELLOW",
        "rule": "Yellow",
        "files_found": 1,
        "files_types": STORE_ONLY,
        "store_id": None,
        "when_date": None,
        "limit": 1,
    }


def test_warns_for_store_id_rule_with_date():
    """Cofix approves any single-store request; files back means it may be stale."""
    when = datetime(2026, 11, 1, 10, 0, 0)
    with pytest.warns(StaleStabilityRuleWarning) as records:
        assert ScraperStability.warn_if_files_found_when_empty_approved(
            "COFIX", 3, store_id=5, when_date=when
        )
    payload = _payload(records[0])
    assert payload["scraper"] == "COFIX"
    assert payload["rule"] == "PublishOnlyStores"
    assert payload["store_id"] == 5
    assert payload["when_date"] == when.isoformat()
    assert payload["files_types"] is None


@pytest.mark.parametrize(
    "scraper, files_found, kwargs",
    [
        ("YELLOW", 0, {"files_types": STORE_ONLY}),  # empty, as the rule says
        ("YELLOW", 1, {"files_types": None}),  # rule did not approve empty
        (ScraperFactory.BAREKET.name, 1, {"files_types": STORE_ONLY}),  # no rule
        ("QUIK", 1, {}),  # deprecated, never run
    ],
)
def test_no_warning(scraper, files_found, kwargs):
    """Only a chain rule that approved "no files", with files back, warns."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", StaleStabilityRuleWarning)
        assert not ScraperStability.warn_if_files_found_when_empty_approved(
            scraper, files_found, **kwargs
        )


def test_no_warning_when_only_generic_probe_window_approved():
    """The generic before-morning window is not a chain-specific claim."""
    with patch(
        "il_supermarket_scarper.scraper_stability.FullyStable.failire_valid",
        return_value=True,
    ), warnings.catch_warnings():
        warnings.simplefilter("error", StaleStabilityRuleWarning)
        assert not ScraperStability.warn_if_files_found_when_empty_approved(
            "YELLOW", 1, files_types=STORE_ONLY
        )


def test_no_warning_for_always_failing():
    """Always-failing scrapers already fail their test when files come back."""
    with patch.object(
        ScraperStability, "kind_of", return_value=ScraperKind.ALWAYS_FAILING
    ), warnings.catch_warnings():
        warnings.simplefilter("error", StaleStabilityRuleWarning)
        assert not ScraperStability.warn_if_files_found_when_empty_approved(
            "YELLOW", 1, files_types=STORE_ONLY
        )


def test_no_warning_after_rule_expired():
    """An expired rule no longer approves "no files", so it can't be stale."""
    with patch.object(
        ScraperStability.YELLOW.value,
        "pass_expiration_date",
        return_value=datetime(2000, 1, 1),
    ), warnings.catch_warnings():
        warnings.simplefilter("error", StaleStabilityRuleWarning)
        assert not ScraperStability.warn_if_files_found_when_empty_approved(
            "YELLOW", 1, files_types=STORE_ONLY
        )
