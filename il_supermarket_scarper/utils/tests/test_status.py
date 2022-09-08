from il_supermarket_scarper.utils.status import get_status,get_status_date
import datetime


def test_status():
    num_of_scarpers = get_status()
    assert type(num_of_scarpers) == int


def test_status_date():
    date = get_status_date()
    assert type(date) == datetime.datetime