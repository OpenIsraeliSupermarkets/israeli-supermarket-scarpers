# pylint: disable=arguments-differ,arguments-renamed
from enum import Enum
from datetime import datetime
import json
import os

from il_supermarket_scarper.utils import (
    _now,
    _testing_now,
    datetime_in_tlv,
    FileTypesFilters,
    hour_files_expected_to_be_accassible,
)
from il_supermarket_scarper.utils.logger import Logger


def _load_gov_il_links():
    """Load gov.il links from cached JSON file."""
    json_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts",
        "gov_il_links.json",
    )
    if not os.path.exists(json_path):
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {link["scraper"]: link for link in data.get("links", [])}


class FullyStable:
    """fully stable is stablity"""

    # If True, the retailer is no longer on gov.il and scraper is expected to not work
    is_deprecated = False

    # Expected URL from gov.il (if different from scraper's hardcoded URL)
    # Set this when gov.il lists a different URL than what the scraper uses
    expected_gov_il_url = None

    @classmethod
    def pass_expiration_date(cls):
        """return the expiration date"""
        return datetime(2027, 1, 1)

    @classmethod
    def executes_between_midnight_and_morning_and_requested_today(
        cls,
        when_date=None,
        utilize_date_param=False,
    ):
        """it is stable if the execution is between midnight
        and morning and the requested date is the test probe date"""
        del utilize_date_param  # kept for call-site compatibility
        execution_time = _now()
        # Before the usual morning publish window, scraper tests probe with
        # `_testing_now()` (rolled back from calendar today). Suppress missing
        # files only for that probe date—not arbitrary historical when_date.
        return (
            when_date is not None
            and execution_time.hour >= 0
            and execution_time.hour < hour_files_expected_to_be_accassible()
            and when_date.date() == _testing_now().date()
        )

    @classmethod
    def executed_after_date(cls, when_date, date):
        """check if executed after date"""
        return when_date > date

    @classmethod
    def failire_valid(cls, when_date=None, utilize_date_param=True, **_):
        """return true if the parser is stble"""

        return cls.executes_between_midnight_and_morning_and_requested_today(
            when_date=when_date, utilize_date_param=utilize_date_param
        )


class SuperFlaky(FullyStable):
    """super flaky is stablity"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)

    @classmethod
    def failire_valid(cls, **_):
        return True


class NetivHased(FullyStable):
    """Netiv Hased site moved from hardcoded IP to new domain.

    Evidence: upstream returns HTTP 500 for http://141.226.203.152/ as of
    2026-07-24 (CI NetivHasefTestCase all failing). However, gov.il lists
    the retailer at https://app.netiv-hesed.com/ which is live and serving files.

    Status: UNSTABLE (not deprecated) - retailer still on gov.il, URL needs update.
    """

    is_deprecated = False
    expected_gov_il_url = "https://app.netiv-hesed.com/"

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)

    @classmethod
    def failire_valid(cls, **_):
        """return true if missing files are expected"""
        return True


class CityMarketGivataim(FullyStable):
    """Netiv Hased is stablity"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)

    @classmethod
    def searching_for_update_promo(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.PROMO_FILE.name]

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return (
            super(cls, CityMarketGivataim).failire_valid(when_date=when_date)
            or cls.searching_for_update_promo(files_types=files_types)
            or when_date is not None
            and cls.executed_after_date(
                when_date=when_date,
                date=datetime_in_tlv(
                    year=2024, month=11, day=5, hour=0, minute=0, second=0
                ),
            )
        )


class CityMarketKiratOno(FullyStable):
    """Netiv Hased is stablity"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)

    @classmethod
    def searching_for_update_promo(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.PROMO_FILE.name]

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return super(cls, CityMarketKiratOno).failire_valid(
            when_date=when_date
        ) or cls.searching_for_update_promo(files_types=files_types)


class CityMarketKiratGat(FullyStable):
    """City Market Kiryat Gat stability.

    Note: The `or True` was removed on 2026-08-30 because the site
    (https://citymarketkiryatgat.binaprojects.com/) is now working and
    actively publishing files. The previous "active issue" appears resolved.

    Status: UNSTABLE during promo_full file requests only (inherits from FullyStable).
    """

    is_deprecated = False

    @classmethod
    def pass_expiration_date(cls):
        """return the expiration date"""
        return datetime(2027, 3, 1)

    @classmethod
    def searching_for_update_promo_full(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.PROMO_FULL_FILE.name]

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return super(cls, CityMarketKiratGat).failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or cls.searching_for_update_promo_full(files_types=files_types)


class DoNotPublishStores(FullyStable):
    """stablity for chains that doesn't pubish stores"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(9999, 5, 1)  # quik is only, they don't publish stores

    @classmethod
    def searching_for_store_full(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.STORE_FILE.name]

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return super(cls, DoNotPublishStores).failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or cls.searching_for_store_full(files_types=files_types)


class SuperYuda(FullyStable):
    """Super Yuda is stablity"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)

    @classmethod
    def searching_for_store_full(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.STORE_FILE.name]

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return super(cls, SuperYuda).failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or cls.searching_for_store_full(files_types=files_types)


class QuikSiteIsDown(FullyStable):
    """Quik site is down (DNS resolution fails for prices.quik.co.il).

    Status: UNSTABLE (not deprecated) - retailer still on gov.il but site is unreachable.
    This is a retailer-side issue, not our scraper's fault.
    """

    is_deprecated = False

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 5, 1)

    @classmethod
    def failire_valid(cls, **_):
        return True


class PublishOnlyStores(FullyStable):
    """Publish only stores"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 5, 1)

    @classmethod
    def searching_for_not_store_full(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return (
            files_types is not None
            and FileTypesFilters.STORE_FILE.name not in files_types
        )

    @classmethod
    def search_for_a_specific_store(cls, store_id=None, **_):
        """if the store id is match"""
        return store_id is not None

    @classmethod
    def failire_valid(
        cls,
        when_date=None,
        files_types=None,
        utilize_date_param=True,
        store_id=None,
        **_,
    ):
        return (
            super(cls, PublishOnlyStores).failire_valid(
                when_date=when_date,
                files_types=files_types,
                utilize_date_param=utilize_date_param,
            )
            or cls.searching_for_not_store_full(
                files_types=files_types, store_id=store_id
            )
            or cls.search_for_a_specific_store(store_id=store_id)
        )


class DoNotPublishPromo(FullyStable):
    """stablity for chains that doesn't pubish stores"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)  # will give it one more year

    @classmethod
    def searching_for_promo_full(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [
            FileTypesFilters.PROMO_FILE.name,
            FileTypesFilters.PROMO_FULL_FILE.name,
        ]

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return super(cls, DoNotPublishPromo).failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or cls.searching_for_promo_full(files_types=files_types)


class VictoryMovedToNewSource(FullyStable):
    """Victory moved to new source (VICTORY_NEW_SOURCE).

    Status: DEPRECATED - this scraper is replaced by VICTORY_NEW_SOURCE.
    The old Victory scraper should not be used; gov.il now lists the new source.
    """

    is_deprecated = True

    @classmethod
    def pass_expiration_date(cls):
        return datetime(9999, 5, 1)

    @classmethod
    def failire_valid(cls, **_):
        return True


class ScraperStability(Enum):
    """tracker for the stablity of the scraper"""

    # COFIX = DoNotPublishStores
    NETIV_HASED = NetivHased
    QUIK = QuikSiteIsDown
    SUPER_YUDA = SuperYuda
    COFIX = PublishOnlyStores
    # SALACH_DABACH = DoNotPublishStores
    # # CITY_MARKET_GIVATAYIM = CityMarketGivataim
    # CITY_MARKET_KIRYATONO = CityMarketKiratOno
    CITY_MARKET_KIRYATGAT = CityMarketKiratGat
    MESHMAT_YOSEF_1 = DoNotPublishPromo
    VICTORY = VictoryMovedToNewSource
    # YOHANANOF = DoNotPublishStores

    @classmethod
    def is_validate_scraper_found_no_files(
        cls,
        scraper_enum,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        utilize_date_param=False,
    ):
        """return true if its ok the scarper reuturn no enrty"""

        stabler = FullyStable
        if scraper_enum in ScraperStability.__members__:
            stabler = ScraperStability[scraper_enum].value

        expected_to_fail = (
            stabler.failire_valid(
                limit=limit,
                files_types=files_types,
                store_id=store_id,
                when_date=when_date,
                utilize_date_param=utilize_date_param,
            )
            and stabler.pass_expiration_date() > datetime.now()
        )

        if expected_to_fail:
            Logger.warning(
                f"scraper {scraper_enum} is not stable, "
                f"pass_expiration_date: {stabler.pass_expiration_date().strftime('%Y-%m-%d')}, "
                f"datetime.now(): {datetime.now().strftime('%Y-%m-%d')}"
            )
        return expected_to_fail

    @classmethod
    def get_permanently_failing_scrapers(cls):
        """Return scraper names with unconditional failire_valid() methods.

        These are scrapers whose failire_valid() always returns True regardless
        of parameters, indicating a permanent site outage. If such a scraper
        starts returning files, it may have recovered and should be re-evaluated.
        """
        unconditional = []
        for name in cls.__members__:
            stabler = cls[name].value
            if stabler.pass_expiration_date() <= datetime.now():
                continue
            test_result = stabler.failire_valid(
                when_date=None,
                files_types=None,
                store_id=None,
                utilize_date_param=False,
            )
            if test_result:
                unconditional.append(name)
        return unconditional

    @classmethod
    def get_deprecated_scrapers(cls):
        """Return scraper names that are deprecated (not expected on gov.il).

        Deprecated scrapers are those whose retailers are no longer listed on
        gov.il (e.g., merged with another chain, went out of business, or
        replaced by a new source).
        """
        deprecated = []
        for name in cls.__members__:
            stabler = cls[name].value
            if getattr(stabler, "is_deprecated", False):
                deprecated.append(name)
        return deprecated

    @classmethod
    def get_unstable_scrapers(cls):
        """Return scraper names that are unstable but NOT deprecated.

        Unstable scrapers are those whose failire_valid() always returns True
        but the retailer is still listed on gov.il. These need investigation:
        - URL may have changed (check expected_gov_il_url)
        - Site may have recovered
        - Site may be temporarily down (retailer's fault)
        """
        permanently_failing = set(cls.get_permanently_failing_scrapers())
        deprecated = set(cls.get_deprecated_scrapers())
        return list(permanently_failing - deprecated)

    @classmethod
    def get_url_drift(cls):
        """Return scrapers where our URL differs from gov.il expected URL.

        Returns dict of {scraper_name: {"expected": url, "reason": str}}.
        Only includes scrapers with expected_gov_il_url set.
        """
        drift = {}
        for name in cls.__members__:
            stabler = cls[name].value
            expected_url = getattr(stabler, "expected_gov_il_url", None)
            if expected_url:
                drift[name] = {
                    "expected_gov_il_url": expected_url,
                    "reason": (stabler.__doc__ or "").split("\n")[0].strip(),
                }
        return drift

    @classmethod
    def validate_against_gov_il(cls):
        """Check if unstable scrapers are still listed on gov.il.

        Returns dict with:
        - "unstable_on_gov_il": scrapers that are unstable AND on gov.il (need fixing)
        - "unstable_not_on_gov_il": scrapers marked unstable but NOT on gov.il
        - "url_drift": scrapers where our URL differs from gov.il
        """
        gov_il_links = _load_gov_il_links()
        gov_il_scrapers = set(gov_il_links.keys())

        unstable = set(cls.get_unstable_scrapers())

        result = {
            "unstable_on_gov_il": [],
            "unstable_not_on_gov_il": [],
            "url_drift": {},
        }

        for name in unstable:
            if name in gov_il_scrapers:
                result["unstable_on_gov_il"].append(name)
                # Check for URL drift
                stabler = cls[name].value
                expected_url = getattr(stabler, "expected_gov_il_url", None)
                if expected_url:
                    result["url_drift"][name] = {
                        "scraper_expected": expected_url,
                        "gov_il_href": gov_il_links[name].get("href"),
                    }
            else:
                result["unstable_not_on_gov_il"].append(name)

        return result
