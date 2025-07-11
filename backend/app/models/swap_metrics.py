from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel

class SwapMetric(BaseModel):
    """Schema for swap_metrics documents."""

    swap_id: Optional[str] = None
    endpoint: str
    started_at: Union[str, float, datetime]
    completed_at: Optional[datetime] = None
    status: str = "pending"
    txHash: Optional[str] = None
    from_wallet: Optional[str] = None
    to_wallet: Optional[str] = None
    token_in: Optional[str] = None
    token_out: Optional[str] = None
    amount: Optional[Union[str, float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    poll_count: int = 0
