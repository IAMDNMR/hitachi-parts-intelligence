from app.integrations.contracts.order import OrderProvider, OrderSubmission, OrderSubmissionResult


class TestOrderProvider(OrderProvider):
    """
    Honest placeholder OrderProvider. No real HCME order/ERP submission
    endpoint is confirmed to exist or is connected in this codebase — this
    class follows the exact same pattern as TestInventoryProvider /
    TestRoutingProvider / TestShippingRateProvider: it never claims a real
    external system accepted the order.

    The Order module's internal DRAFT/CREATED/ACCEPTED state machine is
    backed by Neo4j and functions for development/testing regardless of
    this provider's status, but callers/UI MUST label it TEST/DEVELOPMENT
    and never present `submit_order` as a real HCME integration.
    """

    def submit_order(self, submission: OrderSubmission) -> OrderSubmissionResult:
        return OrderSubmissionResult(
            accepted=False,
            external_order_reference=None,
            status="NOT_CONNECTED",
            message=(
                "No real HCME order system is connected. This order exists only as an "
                "internal, test/development workflow record in this platform's own Neo4j store."
            ),
        )
