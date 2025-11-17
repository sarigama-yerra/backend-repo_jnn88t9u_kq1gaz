import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Book, Order, Price

app = FastAPI(title="Magical Children's Book API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateBookRequest(BaseModel):
    meta: Dict[str, Any]


class UpdateBookRequest(BaseModel):
    meta: Optional[Dict[str, Any]] = None
    json_content: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    progress: Optional[int] = None


@app.get("/")
def read_root():
    return {"service": "books", "status": "ok"}


@app.get("/test")
def test_database():
    try:
        collections = db.list_collection_names() if db else []
        return {"backend": "ok", "db": bool(db), "collections": collections[:10]}
    except Exception as e:
        return {"backend": "ok", "db": False, "error": str(e)}


@app.post("/api/books")
def create_book(payload: CreateBookRequest):
    # Initialize a draft book entry
    book = Book(meta=payload.meta, status="generating", priceCents=0, progress=1)
    book_id = create_document("book", book)
    # Simulate async generation by storing a placeholder json_content
    return {"id": book_id, "status": book.status, "progress": book.progress}


@app.get("/api/books/{book_id}")
def get_book(book_id: str):
    docs = get_documents("book", {"_id": {"$eq": __import__('bson').ObjectId(book_id)}})
    if not docs:
        raise HTTPException(status_code=404, detail="Book not found")
    doc = docs[0]
    # Transform _id to string
    doc["id"] = str(doc.pop("_id"))
    return doc


@app.put("/api/books/{book_id}")
def update_book(book_id: str, payload: UpdateBookRequest):
    # Basic update using pymongo directly for partial updates
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")
    from bson import ObjectId

    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    updates["updated_at"] = datetime.now(timezone.utc)
    res = db["book"].update_one({"_id": ObjectId(book_id)}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"id": book_id, "updated": True}


@app.get("/api/prices")
def get_prices():
    # Seed default prices if empty
    if not db:
        return {"prices": [
            {"sku": "ebook", "label": "eBook (PDF)", "amountCents": 1900, "currency": "USD"},
            {"sku": "hardcover", "label": "Hardcover", "amountCents": 3900, "currency": "USD"},
        ]}
    existing = list(db["price"].find())
    if not existing:
        for p in [
            Price(sku="ebook", label="eBook (PDF)", amountCents=1900),
            Price(sku="hardcover", label="Hardcover", amountCents=3900),
        ]:
            create_document("price", p)
        existing = list(db["price"].find())
    for e in existing:
        e["id"] = str(e.pop("_id"))
    return {"prices": existing}


class CreateOrderRequest(BaseModel):
    bookId: str
    sku: str


@app.post("/api/orders")
def create_order(payload: CreateOrderRequest):
    # Very light order creation (no Stripe integration in this scaffold)
    from bson import ObjectId
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")

    book = db["book"].find_one({"_id": ObjectId(payload.bookId)})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    price = db["price"].find_one({"sku": payload.sku}) or {"amountCents": 1900, "currency": "USD"}
    subtotal = int(price["amountCents"]) 
    shipping = 0  # global free shipping promo
    discount = 0
    total = subtotal + shipping - discount

    order = Order(
        bookId=payload.bookId,
        items=[{"sku": payload.sku, "qty": 1, "amountCents": subtotal}],
        subtotalCents=subtotal,
        shippingCents=shipping,
        discountCents=discount,
        totalCents=total,
    )
    order_id = create_document("order", order)
    return {"id": order_id, "totalCents": total}


@app.get("/api/locales")
def list_locales():
    # Provide a basic list; frontend i18n can expand
    locales = [
        "en", "es", "fr", "de", "it", "pt", "nl", "sv", "no", "da",
        "fi", "pl", "cs", "sk", "hu", "ro", "bg", "el", "tr", "ru",
        "uk", "ar", "he", "hi", "zh", "ja", "ko"
    ]
    return {"locales": locales[:25]}


# Simple signed URL generator placeholder
@app.get("/api/books/{book_id}/download")
def get_download_link(book_id: str):
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")
    from bson import ObjectId
    book = db["book"].find_one({"_id": ObjectId(book_id)})
    if not book or book.get("status") != "ready":
        raise HTTPException(status_code=400, detail="Book not ready")

    # Simulate signed URL valid 24 hours
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    url = f"https://files.example.com/download/{book_id}?exp={int(expires.timestamp())}"
    db["book"].update_one({"_id": ObjectId(book_id)}, {"$set": {"download_url": url, "expires_at": expires}})
    return {"url": url, "expires_at": expires.isoformat()}
