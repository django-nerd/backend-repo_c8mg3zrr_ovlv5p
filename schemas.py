"""
Database Schemas

Pydantic models that define MongoDB collections for the Food Ordering app.
Each model name maps to a lowercase collection name.

Example: class Restaurant(BaseModel) -> "restaurant" collection
"""
from pydantic import BaseModel, Field
from typing import Optional, List

class Restaurant(BaseModel):
    name: str = Field(..., description="Restaurant name")
    cuisine: str = Field(..., description="Cuisine type")
    image_url: Optional[str] = Field(None, description="Cover image URL")
    rating: Optional[float] = Field(4.5, ge=0, le=5, description="Average rating")
    delivery_time_min: Optional[int] = Field(25, ge=5, le=120, description="Estimated delivery time in minutes")

class Menuitem(BaseModel):
    restaurant_id: str = Field(..., description="ID of the restaurant this item belongs to")
    name: str = Field(..., description="Dish name")
    description: Optional[str] = Field(None, description="Short description")
    price: float = Field(..., ge=0, description="Price in dollars")
    image_url: Optional[str] = Field(None, description="Dish image URL")
    is_veg: Optional[bool] = Field(False, description="Vegetarian flag")
    spicy_level: Optional[int] = Field(0, ge=0, le=3, description="0-3 scale")

class Order(BaseModel):
    restaurant_id: str = Field(..., description="Restaurant ID")
    items: List[dict] = Field(..., description="List of items with quantity: [{'menuitem_id': str, 'quantity': int}]")
    customer_name: str = Field(..., description="Customer full name")
    address: str = Field(..., description="Delivery address")
    phone: str = Field(..., description="Contact number")
    notes: Optional[str] = Field(None, description="Special instructions")
    status: str = Field("placed", description="Order status")
    total: Optional[float] = Field(None, ge=0, description="Computed order total")
