from il_supermarket_scarper.utils import FileTypesFilters


def test_file_type():
    assert (
        FileTypesFilters.get_type_from_file("Price7290058108879-339-202409181941")
        == FileTypesFilters.PRICE_FILE
    )
    assert (
        FileTypesFilters.get_type_from_file("PriceFull7290058108879-339-202409181041")
        == FileTypesFilters.PRICE_FULL_FILE
    )

    assert (
        FileTypesFilters.get_type_from_file("StoresFull7290058108879-000-202409181041")
        == FileTypesFilters.STORE_FILE
    )
    assert (
        FileTypesFilters.get_type_from_file("Promo7290058108879-336-202409181544")
        == FileTypesFilters.PROMO_FILE
    )
    assert (
        FileTypesFilters.get_type_from_file("PromoFull7290058108879-339-202409181149")
        == FileTypesFilters.PROMO_FULL_FILE
    )
    assert (
        FileTypesFilters.get_type_from_file("Proasdull7290058108879-339-202409181149")
        is None
    )
