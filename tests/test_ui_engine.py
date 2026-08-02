"""UIEngine registry must align with ScraperFactory names."""

from il_supermarket_scarper.scrappers_factory import ScraperFactory

from testing_util.ui_engine import UI_DEFERRED, UIEngine, factory_scrapers


def test_ui_engine_keys_are_scraper_factory_members():
    """UIEngine member names must be ScraperFactory members."""
    factory_names = set(ScraperFactory.all_listed_scrappers())
    ui_names = set(UIEngine.__members__.keys())

    unknown = ui_names - factory_names
    assert not unknown, f"UIEngine keys not in ScraperFactory: {sorted(unknown)}"


def test_ui_engine_path_key_matches_member_name():
    """Each UiListingPath.key must equal its UIEngine member name."""
    mismatches = []
    for name, member in UIEngine.__members__.items():
        if member.value.key != name:
            mismatches.append((name, member.value.key))
    assert not mismatches, f"UiListingPath.key != enum name: {mismatches}"


def test_ui_deferred_are_factory_members_not_in_ui_engine():
    """Deferred names must exist in the factory and not already have UI paths."""
    factory_names = set(ScraperFactory.all_listed_scrappers())
    for name in UI_DEFERRED:
        assert name in factory_names, f"UI_DEFERRED {name} is not a factory member"
        assert name not in UIEngine.__members__, (
            f"UI_DEFERRED {name} must not have a UIEngine entry yet"
        )


def test_every_factory_scraper_has_ui_registry():
    """Every factory scraper is either configured in UIEngine or deferred."""
    factory_names = set(factory_scrapers())
    covered = set(UIEngine.__members__) | UI_DEFERRED
    missing = factory_names - covered
    extra = covered - factory_names
    assert not missing, f"ScraperFactory members missing from UIEngine: {sorted(missing)}"
    assert not extra, f"UIEngine/UI_DEFERRED keys not in factory: {sorted(extra)}"
