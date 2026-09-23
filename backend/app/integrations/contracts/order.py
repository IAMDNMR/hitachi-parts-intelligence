from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


class OrderSubmission(BaseModel):
    order_id: str
    part_number: str
    quantity: int
    source_id: str
    destination_branch_id: str


class OrderSubmissionResult(BaseModel):
    accepted: bool
    external_order_reference: Optional[str] = None
    status: str = "NOT_CONNECTED"  # NOT_CONNECTED | ACCEPTED | REJECTED
    message: str = ""


class OrderProvider(ABC):
    @abstractmethod
    def submit_order(self, submission: OrderSubmission) -> OrderSubmissionResult:
        """
        Submit an order to the authoritative HCME order/ERP system.

        No real HCME order endpoint is confirmed to exist. Any implementation
        used in this codebase MUST honestly report NOT_CONNECTED rather than
        fabricate acceptance from a real system.
        """
        pass
