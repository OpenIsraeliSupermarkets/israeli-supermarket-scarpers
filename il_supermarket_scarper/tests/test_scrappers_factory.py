import tempfile

from il_supermarket_scarper import ScraperStability, ScraperFactory, datetime_in_tlv
from il_supermarket_scarper.scraper_stability import ScraperKind
from il_supermarket_scarper.utils.deprecated_scrapers import DeprecatedScrapers
from il_supermarket_scarper.utils.folders_name import DumpFolderNames
from il_supermarket_scarper.utils.status import get_cpfta_retailer_hosts, href_host
from il_supermarket_scarper.utils.file_output import DiskFileOutput


def test_stable_scraper():
    """test sample stable scarper"""
    assert not ScraperStability.is_validate_scraper_found_no_files(
        ScraperFactory.VICTORY_NEW_SOURCE.name
    )


def test_not_active():
    """Always-failing factory scrapers are skipped in production (all_active)."""
    test_date = datetime_in_tlv(2024, 12, 12, 0, 0, 0)
    all_listed = set(ScraperFactory.all_listed_scrappers())
    all_active = set(ScraperFactory.all_scrapers_name(when_date=test_date))

    expected_not_active = (
        set(ScraperStability.get_always_failing_scrapers()) & all_listed
    )
    actual_not_active = all_listed - all_active

    assert actual_not_active == expected_not_active, (
        f"Not-active scrapers mismatch. "
        f"Expected: {expected_not_active}, "
        f"Actual: {actual_not_active}."
    )


def test_scraper_kinds():
    """Three kinds: edge-case, always-failing (still on gov.il), deprecated."""
    assert set(ScraperStability.get_deprecated_scrapers()) == {"QUIK", "VICTORY"}
    assert set(ScraperStability.get_always_failing_scrapers()) == set()

    factory_names = set(ScraperFactory.all_listed_scrappers())
    for name in ScraperStability.get_deprecated_scrapers():
        assert name not in factory_names, f"deprecated {name} must not be in factory"

    for name in ScraperStability.get_always_failing_scrapers():
        assert name in factory_names, f"always-failing {name} must stay in factory"
        assert ScraperStability.kind_of(name) is ScraperKind.ALWAYS_FAILING


def test_deprecated_scrapers_match_factory_and_folders():
    """DeprecatedScrapers is the single list used by factory listing and dump folders."""
    deprecated = DeprecatedScrapers.names()
    factory_members = {member.name for member in ScraperFactory}
    folder_members = {member.name for member in DumpFolderNames}

    assert deprecated <= factory_members
    assert deprecated <= folder_members
    assert set(ScraperFactory.get_deprecated_scrapers()) == deprecated
    assert set(ScraperFactory.all_listed_scrappers()) & deprecated == set()
    assert set(DumpFolderNames.active_folder_names()) & deprecated == set()
    assert set(DumpFolderNames.active_folder_names()) == set(
        ScraperFactory.all_listed_scrappers()
    )
    assert set(ScraperFactory.all_listed_scrappers(include_deprecated=True)) == (
        factory_members
    )
    assert factory_members == folder_members


def test_all_active_excludes_deprecated():
    """Production all_scrapers_name() must not return deprecated scrapers."""
    deprecated = DeprecatedScrapers.names()
    assert set(ScraperFactory.all_scrapers_name()) & deprecated == set()
    for name in deprecated:
        assert ScraperFactory.is_deprecated(name)
        assert not ScraperFactory.is_scraper_enabled(ScraperFactory[name])


def test_always_failing_login_details_match_gov_il():
    """Always-failing scrapers must still be listed in the cached gov.il HTML."""
    gov_il_hosts = get_cpfta_retailer_hosts()
    for name in ScraperStability.get_always_failing_scrapers():
        scraper_cls = ScraperFactory[name].value
        with tempfile.TemporaryDirectory() as tmp:
            instance = scraper_cls(file_output=DiskFileOutput(storage_path=tmp))
            login_details = instance.get_login_details()
            host = href_host(login_details.url)
            assert host in gov_il_hosts, (
                f"{name} host {host!r} from {login_details!r} "
                "is not in cpfta_prices_regulations"
            )


def _login_details_for(name):
    scraper_cls = ScraperFactory[name].value
    with tempfile.TemporaryDirectory() as tmp:
        instance = scraper_cls(file_output=DiskFileOutput(storage_path=tmp))
        return instance.get_login_details()


def test_login_details_include_credentials_when_set():
    """Username and password are included only when the scraper has them."""
    web = _login_details_for("NETIV_HASED")
    assert web.url == "https://app.netiv-hesed.com/"
    assert web.username is None
    assert web.password is None

    ftp_user_only = _login_details_for("RAMI_LEVY")
    assert ftp_user_only.url == "ftp://url.retail.publishedprices.co.il/"
    assert ftp_user_only.username == "RamiLevi"
    assert ftp_user_only.password is None

    ftp_with_password = _login_details_for("YELLOW")
    assert ftp_with_password.url == "ftp://url.retail.publishedprices.co.il/"
    assert ftp_with_password.username == "Paz_bo"
    assert ftp_with_password.password == "paz468"
   