# experiment-1: Clothing Bargain Finder

Searches **Vinted** and **eBay** for clothes, works out what each item
normally sells for, and ranks listings by the profit you'd make buying on
one platform and reselling on the other.

## How it works

1. **Search both sites** for each search term, e.g. `carhartt jacket`.
2. **Clean the results.** It drops listings whose title doesn't contain every
   search word, and anything that looks like a bundle, fake or damaged item.
3. **Estimate the going rate** on each platform: the median asking price with
   outliers removed, multiplied by a haircut (default 0.85), because items
   usually sell for less than their asking price.
4. **Cost every listing.** That's the item price plus postage plus buyer fees
   (Vinted buyer protection is £0.70 + 5%).
5. **Try both resale routes** (sell on Vinted or sell on eBay, after fees and
   postage) and keep whichever makes more.
6. **Rank the deals** by profit, keeping only those that clear your minimum
   profit and margin.

```
profit = est. resale price − resale fees − (price + postage + buyer fee)
margin = profit / est. resale price
ROI    = profit / (price + postage + buyer fee)
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
```

Get free eBay API keys:

1. Sign up at <https://developer.ebay.com>.
2. Create a **Production** keyset under *Application Keys*.
3. Put the Client ID and Client Secret in `.env`.

Vinted doesn't need keys.

## Usage

```bash
# One or more searches
python -m bargain_finder "carhartt jacket" "ralph lauren polo"

# Spend at most £20 per item, need at least £10 profit and a 40% margin, save to CSV
python -m bargain_finder "patagonia fleece" --max-buy 20 --min-profit 10 --min-margin 0.4 --csv deals.csv

# Run a list of searches from a file
python -m bargain_finder --queries-file queries.example.txt --top 10

# Vinted only (no eBay keys needed)
python -m bargain_finder "stone island jumper" --no-ebay
```

Example output:

```
=== carhartt jacket ===
  vinted median ask GBP 38.00 -> est. resale 32.30 (171 comparables)
  ebay   median ask GBP 54.99 -> est. resale 46.74 (188 comparables)
  buy on    cost  sell on  resale  profit  margin  title / link
  vinted   17.44  ebay      46.74   25.80    55%   Carhartt Detroit jacket brown M
```

Useful options: `--pages`, `--category mens|womens`, `--condition new_with_tags`
(repeatable) and `--no-vinted`. Run `python -m bargain_finder -h` to see them all.

## Tests

```bash
pytest
```

## Caveats

- **The estimates come from asking prices, not sold prices.** Before you buy,
  check eBay's *Sold items* filter to see what the item really goes for. If you
  get access to eBay's Marketplace Insights API, you can plug in sold data instead.
- **Size, condition and exact model all change the value.** Specific searches
  like `barbour bedale` give better estimates than broad ones like `barbour`.
- **Vinted has no public API.** This tool uses the site's internal JSON endpoint,
  which can change without warning. Automated access may breach Vinted's Terms
  of Service, so keep request volumes low and use it for personal research.
- **Fees change.** Check the numbers in `.env` against each platform's current
  fee pages. If you sell as a business on eBay, set `EBAY_SELLER_PCT` and
  `EBAY_SELLER_FIXED`.
