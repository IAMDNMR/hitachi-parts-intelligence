from typing import Optional
from app.config import settings
from app.integrations.contracts.shipping_rate import ShippingRateProvider, ShippingRateQuery, ShippingRate

class TestShippingRateProvider(ShippingRateProvider):
    def get_rate(self, query: ShippingRateQuery) -> Optional[ShippingRate]:
        if settings.ENVIRONMENT == "production":
            return ShippingRate(
                carrier_code="UNKNOWN",
                service_level=query.service_level,
                shipping_cost=0.0,
                currency="EUR",
                estimated_delivery_days=3,
                is_confirmed=False
            )

        carrier = query.carrier_code.upper()
        level = query.service_level.upper()

        if "DEALER" in carrier or level == "SAME_DAY":
            cost = 15.0
            days = 0
        elif level == "EXPRESS":
            cost = 65.0
            days = 1
        elif "REMAN" in carrier:
            cost = 45.0
            days = 2
        elif "INTERMODAL" in carrier:
            cost = 85.0
            days = 4
        else:
            # Standard road
            cost = 35.0
            days = 1

        return ShippingRate(
            carrier_code=query.carrier_code,
            service_level=query.service_level,
            shipping_cost=cost,
            currency="EUR",
            estimated_delivery_days=days,
            is_confirmed=False
        )
