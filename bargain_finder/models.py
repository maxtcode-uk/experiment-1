from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Listing:
    platform: str            # "vinted" or "ebay"
    id: str
    title: str
    price: float             # item price as listed
    shipping: float          # shipping cost to the buyer (0 if unknown/free)
    currency: str
    url: str
    brand: str = ""
    size: str = ""
    condition: str = ""
    image_url: str = ""
    buyer_fee: float = 0.0   # platform fee charged to the buyer (e.g. Vinted buyer protection)

    @property
    def total_cost(self) -> float:
        """What it actually costs to buy this item and get it delivered."""
        return round(self.price + self.shipping + self.buyer_fee, 2)


@dataclass
class Deal:
    listing: Listing
    resale_platform: str
    est_resale_price: float   # what we expect it to sell for
    resale_fees: float        # fees + postage we pay when reselling
    comparables: int          # how many listings the estimate is based on

    @property
    def profit(self) -> float:
        return round(self.est_resale_price - self.resale_fees - self.listing.total_cost, 2)

    @property
    def margin(self) -> float:
        """Profit as a fraction of the resale price."""
        if self.est_resale_price <= 0:
            return 0.0
        return self.profit / self.est_resale_price

    @property
    def roi(self) -> float:
        """Profit as a fraction of money spent buying the item."""
        cost = self.listing.total_cost
        return self.profit / cost if cost > 0 else 0.0
