from app.integrations.contracts.pricing import PricingProvider, PricingQuery, PriceQuote


class TestPricingProvider(PricingProvider):
    """
    Honest placeholder PricingProvider. No authoritative HCME pricing source
    is confirmed to exist anywhere in this codebase (docs/PHASE_2_SUMMARY.md
    §"No confirmed pricing source"). This provider therefore ALWAYS returns
    NOT_AVAILABLE / unit_price=None — it never fabricates a number, in any
    environment, unlike the shipping-rate mock which returns illustrative
    test figures. Order creation must display "Price unavailable from
    current source" whenever this is the active provider.
    """

    def get_price(self, query: PricingQuery) -> PriceQuote:
        return PriceQuote(
            part_number=query.part_number,
            unit_price=None,
            currency=None,
            status="NOT_AVAILABLE",
            is_confirmed=False,
        )
