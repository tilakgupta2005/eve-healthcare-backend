import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(gt=0, decimal_places=2)


class TestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    centre_id: uuid.UUID
    name: str
    price: Decimal
    created_at: datetime
