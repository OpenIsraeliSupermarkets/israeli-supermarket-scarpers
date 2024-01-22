from .logger import Logger


class FlakyScraper:
    """
    A decorator class to mark a scraper as flaky, wrapping its methods with a warning message.

    Parameters:
    - cls: The class to be decorated as a flaky scraper.

    Example:
    ```
    @FlakyScraper
    class MyScraper:
        def __init__(self, name):
            self.name = name

        def scrape(self):
            print(f"Scraping with {self.name}")
    ```
    """

    def __init__(self, cls):
        self.cls = cls

    def __call__(self, *args, **kwargs):
        """
        Call method to create an instance of the decorated class and wrap its methods.

        Returns:
        - An instance of the decorated class with wrapped methods.
        """
        instance = self.cls(*args, **kwargs)
        setattr(instance, "_is_flaky", True)
        for name, method in vars(self.cls).items():
            if callable(method):
                setattr(instance, name, self.wrap_method(method))
        return instance

    def wrap_method(self, method):
        """
        Wrapper method to add a warning message before calling the original method.

        Parameters:
        - method: The original method of the decorated class.

        Returns:
        - A wrapped method with a warning message.
        """

        def wrapper(*args, **kwargs):
            Logger.warning("This Scraper is marked FLAKY! Shame upon the developer!")
            return method(self, *args, **kwargs)

        return wrapper
