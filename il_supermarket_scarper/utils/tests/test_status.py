from il_supermarket_scarper.utils.status import get_status,get_status_date
from il_supermarket_scarper.utils.connection import disable_when_outside_israel
import datetime


@disable_when_outside_israel
def test_status():
    num_of_scarpers = get_status()
    assert type(num_of_scarpers) == int

@disable_when_outside_israel
def test_status_date():
    date = get_status_date()
    assert type(date) == datetime.datetime