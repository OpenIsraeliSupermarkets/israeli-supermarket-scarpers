"""Offline checks of Super-Pharm's listing request params (no network)."""

import tempfile
import unittest
import urllib.parse

from il_supermarket_scarper.scrappers.super_pharm import SuperPharm
from il_supermarket_scarper.utils import DiskFileOutput, FileTypesFilters

SAMPLE_NAME = "{}7290172900007-001-224-20261108-070000.xml"


class TestSuperPharmParams(unittest.TestCase):
    """Each file type must ask for a category whose names survive its filter."""

    def _categories(self, files_types):
        with tempfile.TemporaryDirectory() as tmp:
            scraper = SuperPharm(file_output=DiskFileOutput(storage_path=tmp))
            params = scraper.build_params(files_types=files_types)
        return [
            urllib.parse.parse_qs(p.lstrip("?")).get("Category-equals", [None])[0]
            for p in params
        ]

    def test_promo_file_alone_asks_for_promo_category(self):
        """#219: [PROMO_FILE] must not ask for PromoFull; its filter drops it."""
        self.assertEqual(
            self._categories([FileTypesFilters.PROMO_FILE.name]), ["Promo"]
        )

    def test_only_promo_asks_for_both_categories(self):
        """Both promo types list both categories."""
        self.assertEqual(
            self._categories(FileTypesFilters.only_promo()), ["Promo", "PromoFull"]
        )

    def test_every_category_survives_its_own_filter(self):
        """A name from the requested category passes that file type's filter."""
        for file_type in FileTypesFilters.all_types():
            (category,) = self._categories([file_type])
            self.assertTrue(
                FileTypesFilters.is_file_from_type(
                    SAMPLE_NAME.format(category), file_type
                ),
                (file_type, category),
            )
