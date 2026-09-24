from bargain_finder.config import Fees, Settings
from bargain_finder.models import Listing
from bargain_finder.pricing import (
    find_deals,
    looks_like_junk,
    matches_query,
    remove_outliers,
    resale_fees,
)


def make_settings(**kw):
    s = Settings(ebay_client_id="x", ebay_client_secret="y", resale_haircut=1.0, min_comparables=3,
                 fees=Fees(resale_postage=3.0))
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def listing(platform, price, title="Carhartt Jacket", shipping=0.0, buyer_fee=0.0, id="1"):
    return Listing(platform=platform, id=id, title=title, price=price, shipping=shipping,
                   currency="GBP", url=f"https://example.com/{id}", buyer_fee=buyer_fee)


def test_matches_query_needs_every_word():
    assert matches_query("Vintage Carhartt Detroit Jacket", "carhartt jacket")
    assert not matches_query("Carhartt beanie", "carhartt jacket")


def test_junk_filter():
    assert looks_like_junk("Carhartt jacket BUNDLE x5")
    assert looks_like_junk("carhartt jacket - small hole on sleeve")
    assert not looks_like_junk("Carhartt Detroit jacket")


def test_remove_outliers_drops_extremes():
    prices = [40, 42, 45, 44, 41, 43, 400]
    assert 400 not in remove_outliers(prices)


def test_total_cost_includes_fees_and_postage():
    l = listing("vinted", 10.0, shipping=2.99, buyer_fee=1.20)
    assert l.total_cost == 14.19


def test_resale_fees_by_platform():
    s = make_settings()
    assert resale_fees("vinted", 50, s) == 0
    assert resale_fees("ebay", 50, s) == 3.0  # postage only for a private seller


def test_find_deals_ranks_cheap_listing_first():
    s = make_settings()
    listings = [listing("ebay", p, id=f"e{i}") for i, p in enumerate([50, 55, 60, 52, 58])]
    listings += [
        listing("vinted", 12, shipping=3, buyer_fee=1.3, id="cheap"),
        listing("vinted", 30, shipping=3, buyer_fee=2.2, id="okay"),
        listing("vinted", 50, id="v1"),
        listing("vinted", 48, id="v2"),
        listing("vinted", 52, id="v3"),
    ]
    deals = find_deals("carhartt jacket", listings, s, min_profit=5, min_margin=0.2)
    assert deals[0].listing.id == "cheap"
    assert deals[0].resale_platform == "ebay"
    # eBay median ask 55, minus 3 postage, minus 16.30 cost
    assert deals[0].profit == 35.70


def test_max_buy_filters_candidates_but_not_estimate():
    s = make_settings()
    listings = [listing("ebay", p, id=f"e{i}") for i, p in enumerate([50, 55, 60])]
    listings.append(listing("vinted", 20, id="v"))
    deals = find_deals("carhartt jacket", listings, s, min_profit=1, min_margin=0, max_buy=15)
    assert deals == []
