from typing import List
from app.config import settings
from app.integrations.contracts.routing import RoutingProvider, RouteQuery, RouteOption

class TestRoutingProvider(RoutingProvider):
    def find_routes(self, query: RouteQuery) -> List[RouteOption]:
        # Rule: In production with no confirmed carrier, return UNKNOWN route
        if settings.ENVIRONMENT == "production":
            return [
                RouteOption(
                    route_id=f"route-prod-unknown-{query.origin_location_id}",
                    origin_location_id=query.origin_location_id,
                    destination_branch_id=query.destination_branch_id,
                    transport_mode="UNKNOWN",
                    carrier_code="UNKNOWN",
                    service_level="UNKNOWN",
                    estimated_transit_days=3,
                    is_confirmed=False
                )
            ]

        origin = query.origin_location_id.upper()
        dest = query.destination_branch_id.upper()

        routes: List[RouteOption] = []

        # Dealer stock / same branch -> Immediate / Local pickup
        if "DEALER" in origin or origin == dest:
            routes.append(
                RouteOption(
                    route_id=f"route-local-{origin}-{dest}",
                    origin_location_id=query.origin_location_id,
                    destination_branch_id=query.destination_branch_id,
                    transport_mode="INTERNAL_TRANSFER",
                    carrier_code="DEALER_FLEET",
                    service_level="SAME_DAY",
                    estimated_transit_days=0,
                    is_confirmed=False
                )
            )
        elif "REGIONAL" in origin or "AMS" in origin or "NL" in origin:
            # Regional depot -> Standard road freight & Express courier
            routes.append(
                RouteOption(
                    route_id=f"route-road-std-{origin}-{dest}",
                    origin_location_id=query.origin_location_id,
                    destination_branch_id=query.destination_branch_id,
                    transport_mode="ROAD",
                    carrier_code="LOGISTICS_PARTNER_STD",
                    service_level="STANDARD",
                    estimated_transit_days=1,
                    is_confirmed=False
                )
            )
            routes.append(
                RouteOption(
                    route_id=f"route-courier-exp-{origin}-{dest}",
                    origin_location_id=query.origin_location_id,
                    destination_branch_id=query.destination_branch_id,
                    transport_mode="COURIER",
                    carrier_code="LOGISTICS_PARTNER_EXP",
                    service_level="EXPRESS",
                    estimated_transit_days=1,
                    is_confirmed=False
                )
            )
        elif "REMAN" in origin:
            # Reman facility -> Dedicated road haulage
            routes.append(
                RouteOption(
                    route_id=f"route-reman-road-{origin}-{dest}",
                    origin_location_id=query.origin_location_id,
                    destination_branch_id=query.destination_branch_id,
                    transport_mode="ROAD",
                    carrier_code="REMAN_SPECIALIST_FREIGHT",
                    service_level="STANDARD",
                    estimated_transit_days=2,
                    is_confirmed=False
                )
            )
        else:
            # Central depot or cross-border
            routes.append(
                RouteOption(
                    route_id=f"route-central-road-{origin}-{dest}",
                    origin_location_id=query.origin_location_id,
                    destination_branch_id=query.destination_branch_id,
                    transport_mode="ROAD",
                    carrier_code="INTERMODAL_FREIGHT",
                    service_level="STANDARD",
                    estimated_transit_days=4,
                    is_confirmed=False
                )
            )

        return routes
