"""
Database Schemas for Magical Children's Book app

Each Pydantic model corresponds to a MongoDB collection. The collection name
is the lowercase of the class name.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class Book(BaseModel):
    """Books collection schema -> collection name: "book"""
    ownerId: Optional[str] = Field(None, description="Owner user id if logged in")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Book metadata like title, age, theme")
    json_content: Dict[str, Any] = Field(default_factory=dict, description="Structured story content + layout JSON")
    status: str = Field("draft", description="draft|generating|ready|error")
    priceCents: int = Field(0, ge=0, description="Price at time of creation in cents")
    progress: int = Field(0, ge=0, le=100, description="Generation progress 0-100")
    download_url: Optional[str] = Field(None, description="Temporary signed download URL valid 24h when ready")
    expires_at: Optional[datetime] = Field(None, description="Expiry of download link")


class Order(BaseModel):
    """Orders collection schema -> collection name: "order"""
    bookId: str = Field(..., description="Related book id")
    ownerId: Optional[str] = Field(None, description="User id if logged in")
    items: List[Dict[str, Any]] = Field(default_factory=list, description="Line items")
    subtotalCents: int = Field(..., ge=0)
    shippingCents: int = Field(0, ge=0)
    discountCents: int = Field(0, ge=0)
    totalCents: int = Field(..., ge=0)
    currency: str = Field("USD")
    status: str = Field("created", description="created|paid|fulfilled|cancelled")


class Price(BaseModel):
    """Prices collection schema -> collection name: "price"""
    sku: str = Field(..., description="ebook or hardcover")
    label: str = Field(...)
    amountCents: int = Field(..., ge=0)
    currency: str = Field("USD")


# Example user schema retained for reference if needed
class User(BaseModel):
    name: str
    email: str
    is_active: bool = True
