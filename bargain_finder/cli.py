"""Command line: python -m bargain_finder "nike tech fleece" "carhartt jacket" """

import argparse
import csv
import sys
from typing import List

from .config import Settings
from .models import Deal, Listing
from .pricing import find_deals, market_summary


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Find underpriced clothes on Vinted and eBay and rank them by resale profit."
    )
    p.add_argument("queries", nargs="*", help="Search terms, e.g. \"ralph lauren polo\"")
    p.add_argument("--queries-file", help="Text file with one search term per line")
    p.add_argument("--max-buy", type=float, default=None, help="Most you'll spend per item, incl. postage and fees")
    p.add_argument("--min-profit", type=float, default=5.0, help="Minimum profit per item (default 5)")
    p.add_argument("--min-margin", type=float, default=0.25, help="Minimum profit / resale price (default 0.25)")
    p.add_argument("--pages", type=int, default=2, help="Vinted result pages per search (96 items each)")
    p.add_argument("--category", default="clothing", help="eBay category: clothing, mens, womens or a category ID")
    p.add_argument("--condition", action="append",
                   choices=["new_with_tags", "new_without_tags", "very_good", "good", "used"],
                   help="Only include these conditions (repeatable)")
    p.add_argument("--no-vinted", action="store_true", help="Skip Vinted")
    p.add_argument("--no-ebay", action="store_true", help="Skip eBay")
    p.add_argument("--top", type=int, default=20, help="How many deals to show per search")
    p.add_argument("--csv", help="Also save every deal to this CSV file")
    return p.parse_args(argv)


def gather(query: str, args, settings: Settings) -> List[Listing]:
    listings: List[Listing] = []
    # No price cap here: expensive listings are needed to work out the
    # going rate. The budget is applied afterwards in find_deals.
    if not args.no_vinted:
        from .vinted import VintedClient
        try:
            vinted_conditions = [c for c in (args.condition or []) if c != "used"]
            listings += VintedClient(settings).search(query, conditions=vinted_conditions, pages=args.pages)
        except Exception as e:
            print(f"  ! Vinted search failed: {e}", file=sys.stderr)
    if not args.no_ebay:
        from .ebay import EbayClient
        try:
            ebay_conditions = [c for c in (args.condition or []) if c not in ("very_good", "good")]
            if args.condition and any(c in ("very_good", "good") for c in args.condition):
                ebay_conditions.append("used")
            listings += EbayClient(settings).search(query, category=args.category, conditions=ebay_conditions)
        except Exception as e:
            print(f"  ! eBay search failed: {e}", file=sys.stderr)
    return listings


def print_deals(query: str, deals: List[Deal], summary, top: int, currency: str):
    print(f"\n=== {query} ===")
    for platform, est in summary.items():
        if est:
            print(f"  {platform:6} median ask {currency} {est['median_ask']:.2f} "
                  f"-> est. resale {est['price']:.2f} ({est['comparables']} comparables)")
        else:
            print(f"  {platform:6} not enough comparable listings")
    if not deals:
        print("  No deals met your profit/margin thresholds.")
        return
    print(f"  {'buy on':7}{'cost':>8}  {'sell on':7}{'resale':>8}{'profit':>8}{'margin':>8}  title / link")
    for d in deals[:top]:
        l = d.listing
        print(f"  {l.platform:7}{l.total_cost:8.2f}  {d.resale_platform:7}{d.est_resale_price:8.2f}"
              f"{d.profit:8.2f}{d.margin:7.0%}   {l.title[:60]}")
        print(f"  {'':54}{l.url}")


def write_csv(path: str, rows):
    fields = ["query", "buy_platform", "title", "brand", "size", "condition", "price", "shipping",
              "buyer_fee", "total_cost", "resale_platform", "est_resale_price", "resale_fees",
              "profit", "margin", "roi", "comparables", "url"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for query, d in rows:
            l = d.listing
            w.writerow({
                "query": query, "buy_platform": l.platform, "title": l.title, "brand": l.brand,
                "size": l.size, "condition": l.condition, "price": l.price, "shipping": l.shipping,
                "buyer_fee": l.buyer_fee, "total_cost": l.total_cost,
                "resale_platform": d.resale_platform, "est_resale_price": d.est_resale_price,
                "resale_fees": d.resale_fees, "profit": d.profit, "margin": round(d.margin, 3),
                "roi": round(d.roi, 3), "comparables": d.comparables, "url": l.url,
            })


def main(argv=None):
    args = parse_args(argv)
    queries = list(args.queries)
    if args.queries_file:
        with open(args.queries_file, encoding="utf-8") as f:
            queries += [line.strip() for line in f if line.strip() and not line.startswith("#")]
    if not queries:
        print("Give at least one search term, e.g.  python -m bargain_finder \"carhartt jacket\"")
        return 1

    settings = Settings()
    all_rows = []
    for query in queries:
        print(f"Searching: {query} ...", file=sys.stderr)
        listings = gather(query, args, settings)
        deals = find_deals(query, listings, settings, args.min_profit, args.min_margin, args.max_buy)
        print_deals(query, deals, market_summary(query, listings, settings), args.top, settings.currency)
        all_rows += [(query, d) for d in deals]

    if args.csv:
        write_csv(args.csv, all_rows)
        print(f"\nSaved {len(all_rows)} deals to {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
