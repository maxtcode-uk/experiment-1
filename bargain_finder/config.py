"""Fee and search settings. Check these against the platforms' current fee
pages before trusting the numbers — fees change regularly."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Fees:
    # Vinted UK: sellers pay nothing; buyers pay "buyer protection"
    # of a fixed amount plus a percentage of the item price.
    vinted_buyer_fixed: float = 0.70
    vinted_buyer_pct: float = 0.05
    vinted_default_shipping: float = 2.99   # typical cheapest parcel option
    vinted_seller_pct: float = 0.0

    # eBay UK: private sellers currently pay no final value fee on most
    # items; business sellers pay roughly 12.8% + £0.30 per order on clothing.
    ebay_seller_pct: float = 0.0
    ebay_seller_fixed: float = 0.0

    # What you pay to post an item when you resell it.
    resale_postage: float = 3.50


@dataclass
class Settings:
    ebay_client_id: str = os.getenv("EBAY_CLIENT_ID", "")
    ebay_client_secret: str = os.getenv("EBAY_CLIENT_SECRET", "")
    ebay_marketplace: str = os.getenv("EBAY_MARKETPLACE", "EBAY_GB")
    vinted_domain: str = os.getenv("VINTED_DOMAIN", "www.vinted.co.uk")
    currency: str = os.getenv("CURRENCY", "GBP")

    # Asking prices are higher than what things actually sell for, so the
    # resale estimate is the median asking price multiplied by this.
    resale_haircut: float = float(os.getenv("RESALE_HAIRCUT", "0.85"))
    # Ignore estimates built from fewer comparable listings than this.
    min_comparables: int = int(os.getenv("MIN_COMPARABLES", "5"))
    # Seconds to wait between requests so we don't hammer either site.
    request_delay: float = float(os.getenv("REQUEST_DELAY", "1.5"))

    fees: Fees = None

    def __post_init__(self):
        if self.fees is None:
            self.fees = Fees(
                ebay_seller_pct=float(os.getenv("EBAY_SELLER_PCT", "0")),
                ebay_seller_fixed=float(os.getenv("EBAY_SELLER_FIXED", "0")),
                resale_postage=float(os.getenv("RESALE_POSTAGE", "3.50")),
            )
