"""Guard: a new engine class must get a status round-trip case."""

import inspect
import unittest

from il_supermarket_scarper.engines.engine import Engine

from .status_roundtrip.cases import ENGINE_CASES


class TestStatusRoundtripCoverage(unittest.TestCase):
    """Keep ``ENGINE_CASES`` in step with the engine classes."""

    @staticmethod
    def _concrete_engines():
        """All non-abstract engine classes defined under ``engines``."""
        found, pending = set(), list(Engine.__subclasses__())
        while pending:
            cls = pending.pop()
            pending.extend(cls.__subclasses__())
            is_engine_module = cls.__module__.startswith(
                "il_supermarket_scarper.engines."
            ) and ".tests." not in cls.__module__
            if is_engine_module and not inspect.isabstract(cls):
                found.add(cls)
        return found

    def test_every_engine_class_has_a_case(self):
        """A new engine class must be added to ``ENGINE_CASES``."""
        covered = {case.engine_cls for case in ENGINE_CASES}
        missing = sorted(c.__name__ for c in self._concrete_engines() - covered)
        self.assertEqual(missing, [], "add these engines to ENGINE_CASES")

    def test_case_scrapers_use_their_engine(self):
        """Each case scraper must be built on its engine class."""
        for case in ENGINE_CASES:
            with self.subTest(engine=case.engine_cls.__name__):
                self.assertTrue(issubclass(case.scraper_cls, case.engine_cls))


if __name__ == "__main__":
    unittest.main()
