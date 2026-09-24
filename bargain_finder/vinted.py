"""Search Vinted listings.

Vinted has no public API. This uses the same JSON endpoint the website
calls, after picking up a session cookie from the homepage. It can break
if Vinted changes its site, and automated access may conflict with their
Terms of Service — keep volumes low and use it for personal research.
"""

import time
from typing import List, Optional

import requests

from .config import Settings
from .models import Listing

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)

# Vinted "status_ids" for item condition.
CONDITIONS = {
    "new_with_tags": 6,
    "new_without_tags": 1,
    "very_good": 2,
    "good": 3,
    "satisfactory": 4,
}


class VintedClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base = f"https://{settings.vinted_domain}"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        self._has_cookie = False

    def _ensure_cookie(self):
        if not self._has_cookie:
            self.session.get(self.base, timeout=20)
            self._has_cookie = True

    def search(
        self,
        query: str,
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        conditions: Optional[List[str]] = None,
        pages: int = 1,
        per_page: int = 96,
    ) -> List[Listing]:
        self._ensure_cookie()
        results: List[Listing] = []
        for page in range(1, pages + 1):
            params = {
                "search_text": query,
                "page": page,
                "per_page": per_page,
                "order": "newest_first",
                "currency": self.settings.currency,
            }
            if max_price is not None:
                params["price_to"] = max_price
            if min_price is not None:
                params["price_from"] = min_price
            if conditions:
                params["status_ids[]"] = [CONDITIONS[c] for c in conditions if c in CONDITIONS]

            resp = self.session.get(f"{self.base}/api/v2/catalog/items", params=params, timeout=20)
            if resp.status_code == 401:
                # Session cookie expired: grab a new one and retry once.
                self._has_cookie = False
                self._ensure_cookie()
                resp = self.session.get(f"{self.base}/api/v2/catalog/items", params=params, timeout=20)
            resp.raise_for_status()

            items = resp.json().get("items", [])
            results.extend(self._parse(i) for i in items)
            if len(items) < per_page:
                break
            time.sleep(self.settings.request_delay)
        return results

    def _parse(self, item: dict) -> Listing:
        fees = self.settings.fees
        price = _money(item.get("price"))
        currency = _currency(item.get("price")) or self.settings.currency

        # Newer responses include the buyer protection fee directly.
        service_fee = _money(item.get("service_fee"))
        if not service_fee:
            service_fee = round(fees.vinted_buyer_fixed + price * fees.vinted_buyer_pct, 2)

        photo = item.get("photo") or {}
        url = item.get("url") or f"{self.base}/items/{item.get('id')}"
        return Listing(
            platform="vinted",
            id=str(item.get("id")),
            title=item.get("title", ""),
            price=price,
            shipping=fees.vinted_default_shipping,
            buyer_fee=service_fee,
            currency=currency,
            url=url,
            brand=item.get("brand_title", "") or "",
            size=item.get("size_title", "") or "",
            condition=item.get("status", "") or "",
            image_url=photo.get("url", "") or "",
        )


def _money(value) -> float:
    """Vinted returns prices either as '12.0' or {'amount': '12.0', 'currency_code': 'GBP'}."""
    if value is None:
        return 0.0
    if isinstance(value, dict):
        value = value.get("amount", 0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _currency(value) -> str:
    if isinstance(value, dict):
        return value.get("currency_code", "")
    return ""
