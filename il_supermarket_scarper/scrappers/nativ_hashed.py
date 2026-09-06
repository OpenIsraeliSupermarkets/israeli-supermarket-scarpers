from datetime import timedelta

from il_supermarket_scarper.engines.web import WebBase
from il_supermarket_scarper.utils import DumpFolderNames, _now


# Listed on gov.il as https://app.netiv-hesed.com/
class NetivHased(WebBase):
    """scraper for nativ Hased"""

    utilize_date_param = False
    # The site Date filter defaults to today; the UI can open prior days.
    _LISTING_LOOKBACK_DAYS = 3

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.NETIV_HASED,
            chain_id="7290058160839",
            url="https://app.netiv-hesed.com/",
            file_output=file_output,
            status_database=status_database,
        )

    def _listing_dates(self, when_date):
        """Dates the listing UI can show: a requested day, or today plus lookback."""
        if when_date is not None:
            day = when_date.date() if hasattr(when_date, "date") else when_date
            return [day]
        today = _now().date()
        return [
            today - timedelta(days=offset)
            for offset in range(self._LISTING_LOOKBACK_DAYS)
        ]

    async def get_request_url(
        self, files_types=None, store_id=None, when_date=None
    ):  # pylint: disable=unused-argument
        """List each Date the UI date filter can open (plus optional store)."""
        for day in self._listing_dates(when_date):
            query = f"Date={day.isoformat()}"
            if store_id is not None:
                query += f"&StoreNumber={store_id}"
            yield {
                "url": f"{self.url}?{query}",
                "method": "GET",
            }
