from il_supermarket_scarper.engines.engine import Engine
import il_supermarket_scarper.scrappers as all_scrappers


def get_all_listed_scarpers():
    """list all scrapers possible to use"""

    all_scrapers = []
    for _, value in all_scrappers.__dict__.items():
        if callable(value) and isinstance(value(), Engine):
            all_scrapers.append(value)
    return all_scrapers


def get_all_listed_scarpers_class_names():
    """get the class name of all listed scrapers"""
    result = []
    for class_instance in get_all_listed_scarpers():
        result.append(class_instance.__name__)
    return result


def get_scraper_by_class(class_names):
    """get a scraper by class name"""
    for class_instance in get_all_listed_scarpers():
        if class_instance.__name__ == class_names:
            return class_instance
    raise ValueError(f"class_names {class_names} not found")
