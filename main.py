import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Food Ordering API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility to convert Mongo documents

def serialize_doc(doc):
    if not doc:
        return doc
    d = dict(doc)
    _id = d.get("_id")
    if isinstance(_id, ObjectId):
        d["id"] = str(_id)
        del d["_id"]
    return d


# Seed data route (idempotent) to populate a couple of restaurants and menu items
@app.post("/seed")
def seed():
    try:
        # Only seed if empty
        if db["restaurant"].count_documents({}) == 0:
            r1_id = db["restaurant"].insert_one({
                "name": "Spice Route",
                "cuisine": "Indian",
                "image_url": "https://images.unsplash.com/photo-1544025162-d76694265947",
                "rating": 4.6,
                "delivery_time_min": 30,
            }).inserted_id

            r2_id = db["restaurant"].insert_one({
                "name": "Pasta Palace",
                "cuisine": "Italian",
                "image_url": "https://images.unsplash.com/photo-1521389508051-d7ffb5dc8bbf",
                "rating": 4.4,
                "delivery_time_min": 25,
            }).inserted_id

            # Menu items
            db["menuitem"].insert_many([
                {"restaurant_id": str(r1_id), "name": "Butter Chicken", "description": "Creamy tomato gravy", "price": 13.99, "is_veg": False, "spicy_level": 1, "image_url": "https://images.unsplash.com/photo-1604909052743-87e9f2fba5a2"},
                {"restaurant_id": str(r1_id), "name": "Paneer Tikka", "description": "Grilled cottage cheese", "price": 10.5, "is_veg": True, "spicy_level": 1, "image_url": "https://images.unsplash.com/photo-1601050690597-8df8f1864d84"},
                {"restaurant_id": str(r2_id), "name": "Margherita Pizza", "description": "Classic with basil", "price": 11.0, "is_veg": True, "spicy_level": 0, "image_url": "https://images.unsplash.com/photo-1548365328-9f547fb09530"},
                {"restaurant_id": str(r2_id), "name": "Pesto Pasta", "description": "Fresh basil pesto", "price": 12.75, "is_veg": True, "spicy_level": 0, "image_url": "https://images.unsplash.com/photo-1521389508051-d7ffb5dc8bbf"},
            ])
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def read_root():
    return {"message": "Food Ordering API is running"}


@app.get("/restaurants")
def list_restaurants():
    try:
        docs = db["restaurant"].find({}).limit(50)
        return [serialize_doc(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/restaurants/{restaurant_id}/menu")
def get_menu(restaurant_id: str):
    try:
        items = db["menuitem"].find({"restaurant_id": restaurant_id}).limit(200)
        return [serialize_doc(i) for i in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CartItem(BaseModel):
    menuitem_id: str
    quantity: int

class PlaceOrderRequest(BaseModel):
    restaurant_id: str
    items: List[CartItem]
    customer_name: str
    address: str
    phone: str
    notes: Optional[str] = None


@app.post("/orders")
def place_order(payload: PlaceOrderRequest):
    try:
        # Compute total by fetching item prices
        menu_ids = [i.menuitem_id for i in payload.items]
        menu_docs = list(db["menuitem"].find({"_id": {"$in": [ObjectId(mid) for mid in menu_ids]}}))
        price_map = {str(d["_id"]): float(d.get("price", 0)) for d in menu_docs}
        total = 0.0
        items = []
        for i in payload.items:
            price = price_map.get(i.menuitem_id, 0.0)
            items.append({"menuitem_id": i.menuitem_id, "quantity": i.quantity, "price": price})
            total += price * i.quantity

        order_doc = {
            "restaurant_id": payload.restaurant_id,
            "items": items,
            "customer_name": payload.customer_name,
            "address": payload.address,
            "phone": payload.phone,
            "notes": payload.notes,
            "status": "placed",
            "total": round(total, 2),
        }
        order_id = db["order"].insert_one(order_doc).inserted_id
        return {"id": str(order_id), "total": round(total, 2), "status": "placed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders")
def list_orders(limit: int = 20):
    try:
        docs = db["order"].find({}).sort("_id", -1).limit(limit)
        return [serialize_doc(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
