"""Turn raw listings into ranked deals.

For each platform we estimate what an item matching the search usually
sells for (median asking price of comparable listings, outliers removed,
with a haircut because asking prices beat real sale prices). Every
listing is then priced as "buy here, resell there" on both platforms and
the better route is kept.
"""

import re
import statistics
from typing import Dict, Iterable, List, Optional

from .config import Settings
from .models import Deal, Listing

# Words that suggest the listing isn't a normal wearable item.
JUNK_WORDS = {
    "bundle", "job lot", "joblot", "wholesale", "fake", "replica", "inspired",
    "damaged", "faulty", "for parts", "stain", "stained", "hole", "ripped",
    "empty box", "box only", "tag only", "dust bag only",
}


def matches_query(title: str, query: str) -> bool:
    """Keep only listings whose title contains every word of the search."""
    title = title.lower()
    return all(word in title for word in query.lower().split())


def looks_like_junk(title: str) -> bool:
    title = title.lower()
    return any(re.search(rf"\b{re.escape(w)}\b", title) for w in JUNK_WORDS)


def remove_outliers(prices: List[float]) -> List[float]:
    """Drop prices outside 1.5x the interquartile range."""
    if len(prices) < 4:
        return prices
    q1, _, q3 = statistics.quantiles(prices, n=4)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return [p for p in prices if lo <= p <= hi]


def buyer_price(listing: Listing) -> float:
    """What a buyer on that platform pays for the item itself.
    On eBay the seller usually covers postage in the price or charges it
    separately, so both count. On Vinted the buyer pays postage and fees on
    top, so only the item price matters to the seller."""
    if listing.platform == "ebay":
        return listing.price + listing.shipping
    return listing.price


def estimate_resale(listings: Iterable[Listing], settings: Settings) -> Optional[Dict]:
    prices = remove_outliers(sorted(buyer_price(l) for l in listings if l.price > 0))
    if len(prices) < settings.min_comparables:
        return None
    median = statistics.median(prices)
    return {
        "price": round(median * settings.resale_haircut, 2),
        "median_ask": round(median, 2),
        "comparables": len(prices),
    }


def resale_fees(platform: str, sale_price: float, settings: Settings) -> float:
    fees = settings.fees
    if platform == "vinted":
        # Vinted sellers pay no fees and the buyer pays for postage.
        return round(sale_price * fees.vinted_seller_pct, 2)
    return round(sale_price * fees.ebay_seller_pct + fees.ebay_seller_fixed + fees.resale_postage, 2)


def find_deals(
    query: str,
    listings: List[Listing],
    settings: Settings,
    min_profit: float = 5.0,
    min_margin: float = 0.25,
    max_buy: Optional[float] = None,
) -> List[Deal]:
    relevant = [l for l in listings if matches_query(l.title, query) and not looks_like_junk(l.title)]

    by_platform: Dict[str, List[Listing]] = {}
    for l in relevant:
        by_platform.setdefault(l.platform, []).append(l)

    estimates = {p: estimate_resale(ls, settings) for p, ls in by_platform.items()}
    estimates = {p: e for p, e in estimates.items() if e}

    deals: List[Deal] = []
    # All relevant listings feed the price estimate, but only ones under the
    # budget are candidates to buy.
    for listing in relevant:
        if max_buy is not None and listing.total_cost > max_buy:
            continue
        best: Optional[Deal] = None
        for platform, est in estimates.items():
            deal = Deal(
                listing=listing,
                resale_platform=platform,
                est_resale_price=est["price"],
                resale_fees=resale_fees(platform, est["price"], settings),
                comparables=est["comparables"],
            )
            if best is None or deal.profit > best.profit:
                best = deal
        if best and best.profit >= min_profit and best.margin >= min_margin:
            deals.append(best)

    deals.sort(key=lambda d: (d.profit, d.margin), reverse=True)
    return deals


def market_summary(query: str, listings: List[Listing], settings: Settings) -> Dict[str, Optional[Dict]]:
    relevant = [l for l in listings if matches_query(l.title, query) and not looks_like_junk(l.title)]
    out: Dict[str, Optional[Dict]] = {}
    for platform in ("vinted", "ebay"):
        out[platform] = estimate_resale([l for l in relevant if l.platform == platform], settings)
    return out
