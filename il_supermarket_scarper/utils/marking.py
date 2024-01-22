from .logger import Logger

class FlakyScraper:
    def __init__(self, cls):
        self.cls = cls

    def __call__(self, *args, **kwargs):
        instance = self.cls(*args, **kwargs)
        setattr(instance, '_is_flaky', True)
        for name, method in vars(self.cls).items():
            if callable(method):
                setattr(instance, name, self.wrap_method(method))
        return instance

    def wrap_method(self, method):
        def wrapper(*args, **kwargs):
            Logger.warning("This Scraper is marked FLAKY! Shame upon the developer!")
            return method(self,*args, **kwargs)
        return wrapper