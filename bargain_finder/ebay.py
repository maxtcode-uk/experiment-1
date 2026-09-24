"""Search eBay with the official Browse API.

Needs a free eBay developer account: https://developer.ebay.com
Create a production keyset and put the Client ID / Client Secret in .env.
"""

import base64
import time
from typing import List, Optional

import requests

from .config import Settings
from .models import Listing

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
SCOPE = "https://api.ebay.com/oauth/api_scope"

# eBay category IDs for clothing.
CATEGORIES = {
    "clothing": "11450",   # Clothes, Shoes & Accessories
    "mens": "1059",        # Men's Clothing
    "womens": "15724",     # Women's Clothing
}

# eBay condition IDs.
CONDITIONS = {
    "new_with_tags": "1000",
    "new_without_tags": "1500",
    "new_with_defects": "1750",
    "used": "3000",
}


class EbayClient:
    def __init__(self, settings: Settings):
        if not settings.ebay_client_id or not settings.ebay_client_secret:
            raise RuntimeError("Set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET in your .env file.")
        self.settings = settings
        self.session = requests.Session()
        self._token: Optional[str] = None
        self._token_expires = 0.0

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        creds = f"{self.settings.ebay_client_id}:{self.settings.ebay_client_secret}"
        resp = requests.post(
            TOKEN_URL,
            headers={
                "Authorization": "Basic " + base64.b64encode(creds.encode()).decode(),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials", "scope": SCOPE},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires = time.time() + int(data.get("expires_in", 7200))
        return self._token

    def search(
        self,
        query: str,
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        category: str = "clothing",
        conditions: Optional[List[str]] = None,
        limit: int = 200,
        buy_it_now_only: bool = True,
    ) -> List[Listing]:
        filters = [f"priceCurrency:{self.settings.currency}"]
        if min_price is not None or max_price is not None:
            lo = "" if min_price is None else min_price
            hi = "" if max_price is None else max_price
            filters.append(f"price:[{lo}..{hi}]")
        if buy_it_now_only:
            filters.append("buyingOptions:{FIXED_PRICE}")
        if conditions:
            ids = "|".join(CONDITIONS[c] for c in conditions if c in CONDITIONS)
            if ids:
                filters.append(f"conditionIds:{{{ids}}}")

        params = {
            "q": query,
            "category_ids": CATEGORIES.get(category, category),
            "filter": ",".join(filters),
            "limit": min(limit, 200),
        }
        resp = self.session.get(
            SEARCH_URL,
            params=params,
            headers={
                "Authorization": f"Bearer {self._get_token()}",
                "X-EBAY-C-MARKETPLACE-ID": self.settings.ebay_marketplace,
            },
            timeout=20,
        )
        resp.raise_for_status()
        time.sleep(self.settings.request_delay)
        return [self._parse(i) for i in resp.json().get("itemSummaries", [])]

    def _parse(self, item: dict) -> Listing:
        price = item.get("price", {})
        shipping = 0.0
        options = item.get("shippingOptions") or []
        if options:
            try:
                shipping = float(options[0].get("shippingCost", {}).get("value", 0))
            except (TypeError, ValueError):
                shipping = 0.0

        return Listing(
            platform="ebay",
            id=item.get("itemId", ""),
            title=item.get("title", ""),
            price=float(price.get("value", 0) or 0),
            shipping=shipping,
            currency=price.get("currency", self.settings.currency),
            url=item.get("itemWebUrl", ""),
            condition=item.get("condition", ""),
            image_url=(item.get("image") or {}).get("imageUrl", ""),
        )
