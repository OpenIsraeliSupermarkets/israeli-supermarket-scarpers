from il_supermarket_scarper.utils.connection import session_and_check_status


def test_session_and_check_status():
    session_and_check_status("https://www.google.com")
