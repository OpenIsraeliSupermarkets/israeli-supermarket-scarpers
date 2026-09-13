"""Ensure setup.py packages= lists every shippable package."""

from scripts.check_setup_packages import check_setup_packages


def test_setup_packages_list_is_complete():
    """Static packages= must match discoverable shippable packages."""
    check_setup_packages()
