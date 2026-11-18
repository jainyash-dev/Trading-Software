"""Replaceable provider boundary.

No provider is enabled. Public NSE downloads, paid market data, broker APIs,
and external model APIs are not called. Research eligibility does not use this
package.
"""

from __future__ import annotations


class ProviderDisabled(RuntimeError):
    """Raised when a provider method is called. Downloads stay off."""


class MarketDataProvider:
    name = "disabled"

    def fetch_session(self, trade_date: str) -> None:
        raise ProviderDisabled("PUBLIC_NSE_DOWNLOAD_DISABLED")
