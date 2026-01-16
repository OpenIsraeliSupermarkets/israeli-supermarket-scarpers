#!/usr/bin/env python3
"""Health check script for Docker container.
Checks if scrapers have recent activity based on last_modified timestamps in status databases.
"""
import os
import sys
import datetime
from il_supermarket_scarper import ScraperFactory
from il_supermarket_scarper.utils.databases import create_status_database_for_scraper
from il_supermarket_scarper.utils.status import _now


def load_configuration():
    """Load configuration from environment variables."""
    # Get enabled scrapers
    enabled_scrapers = os.getenv("ENABLED_SCRAPERS", None)
    if enabled_scrapers:
        enabled_scrapers = enabled_scrapers.split(",")
        # Validate scrapers
        not_valid = list(
            filter(
                lambda scraper: scraper not in ScraperFactory.all_scrapers_name(),
                enabled_scrapers,
            )
        )
        if not_valid:
            print(f"ERROR: ENABLED_SCRAPERS contains invalid {not_valid}", file=sys.stderr)
            sys.exit(1)
    else:
        # Use all scrapers if not specified
        enabled_scrapers = ScraperFactory.all_scrapers_name()

    # Get status database configuration
    status_database_type = os.getenv("STATUS_DATABASE_TYPE", "json").lower()
    if status_database_type not in ["json", "mongo"]:
        print(
            f"ERROR: STATUS_DATABASE_TYPE must be 'json' or 'mongo', but got {status_database_type}",
            file=sys.stderr,
        )
        sys.exit(1)

    status_configuration = {
        "database_type": status_database_type,
    }

    if status_database_type == "json":
        status_configuration["base_path"] = os.getenv(
            "STATUS_DATABASE_PATH", "dumps/status"
        )

    # Get timeout (default: 30 minutes = 1800 seconds)
    timeout_in_seconds = int(os.getenv("TIMEOUT_IN_SECONDS", "1800"))

    return enabled_scrapers, status_configuration, timeout_in_seconds


def check_health():
    """Check health of all enabled scrapers."""
    enabled_scrapers, status_configuration, timeout_in_seconds = load_configuration()

    if not enabled_scrapers:
        # No scrapers enabled, consider healthy (process is running)
        print("INFO: No scrapers enabled, health check passed")
        return 0

    current_time = _now()
    unhealthy_scrapers = []

    for scraper_name in enabled_scrapers:
        try:
            # Create status database instance using the utility function
            status_db = create_status_database_for_scraper(
                scraper_name, status_configuration
            )

            # Get last modified timestamp
            last_modified = status_db.get_last_modified()

            if last_modified is None:
                # No activity recorded yet (first run or database not initialized)
                print(
                    f"WARNING: {scraper_name} has no recorded activity",
                    file=sys.stderr,
                )
                unhealthy_scrapers.append(scraper_name)
                continue

            # Ensure it's a datetime object (get_last_modified should return datetime)
            if not isinstance(last_modified, datetime.datetime):
                print(
                    f"WARNING: {scraper_name} has invalid timestamp type",
                    file=sys.stderr,
                )
                unhealthy_scrapers.append(scraper_name)
                continue

            # Ensure timezone-aware
            if last_modified.tzinfo is None:
                import pytz
                last_modified = pytz.timezone("Asia/Jerusalem").localize(last_modified)

            time_diff = (current_time - last_modified).total_seconds()

            if time_diff > timeout_in_seconds:
                print(
                    f"WARNING: {scraper_name} last activity was {time_diff:.0f} seconds ago "
                    f"(threshold: {timeout_in_seconds} seconds)",
                    file=sys.stderr,
                )
                unhealthy_scrapers.append(scraper_name)
            else:
                print(f"INFO: {scraper_name} is healthy (last activity: {time_diff:.0f}s ago)")

        except Exception as e:
            print(
                f"ERROR: Failed to check {scraper_name}: {e}",
                file=sys.stderr,
            )
            unhealthy_scrapers.append(scraper_name)

    if unhealthy_scrapers:
        print(
            f"ERROR: {len(unhealthy_scrapers)} scraper(s) unhealthy: {', '.join(unhealthy_scrapers)}",
            file=sys.stderr,
        )
        return 1

    print(f"INFO: All {len(enabled_scrapers)} scraper(s) are healthy")
    return 0


if __name__ == "__main__":
    sys.exit(check_health())
