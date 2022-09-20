



class FileTypesFilters:
    promo_file = lambda x: "promo" in x.lower() and "null" not in x.lower()
    #large_promo_file = lambda x: "promo" in x.lower() and "full" in x.lower()
    store_file = lambda x: "store" in x.lower() and "null" not in x.lower()
    #large_store_file = lambda x: "store" in x.lower() and "full" in x.lower()
    price_file = lambda x: "price" in x.lower()  and "null" not in x.lower()
    #large_price_file = lambda x: "price" in x.lower() and "full" in x.lower()

    @classmethod
    def all_types(cls):
        """Returns a list of all the enum keys."""
        return ['promo_file',
                "store_file",
                "price_file"]
    
    @classmethod
    def only_promo(cls):
        return ['promo_file']

    @classmethod
    def only_store(cls):
        return ['store_file']

    @classmethod
    def only_price(cls):
        return ['price_file']


    @classmethod
    def all_large(cls):
        return cls.all_types()

    @classmethod
    def filter(cls, file_type, iterable,by=None):
        """Returns the type of the file."""
        lambda_ = getattr(cls,file_type)
        if by:
            iner_lambda = getattr(cls,file_type)
            lambda_ = lambda x: iner_lambda(by(x))
        return list(filter(lambda_,iterable))




