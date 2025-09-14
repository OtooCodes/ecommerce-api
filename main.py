from fastapi import FastAPI, Form, HTTPException, status, Depends
from db import products_collection, users_collection, carts_collection, orders_collection
from pydantic import BaseModel
from bson.objectid import ObjectId
from utils import replace_mongo_id, hash_password, verify_password
from typing import Annotated, List, Dict, Any
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

tags_metadata = [
    {
        "name": "Home",
        "description": "Welcome endpoint",
    },
    {
        "name": "Products",
        "description": "Product management endpoints",
    },
    {
        "name": "Authentication",
        "description": "User registration and login",
    },
    {
        "name": "Cart",
        "description": "Shopping cart management",
    },
    {
        "name": "Checkout",
        "description": "Order processing and checkout",
    },
]

app = FastAPI(
    title="E-commerce API",
    description="A complete e-commerce API with product management, user authentication, and shopping cart functionality",
    openapi_tags=tags_metadata
)

# Root endpoint
@app.get("/", tags=["Home"])
def get_root():
    return {"message": "Welcome to our E-commerce API"}

# Get all products
@app.get("/products", tags=["Products"])
def get_all_products():
    """Get all available products"""
    products = products_collection.find().to_list()
    return {"products": list(map(replace_mongo_id, products))}

# Get single product by ID
@app.get("/products/{product_id}", tags=["Products"])
def get_product(product_id: str):
    """Get detailed information for a single product"""
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid product ID format"
        )
    
    product = products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return replace_mongo_id(product)

# User registration
@app.post("/register", tags=["Authentication"])
def register_user(
    username: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()]
):
    """Register a new user"""
    # Check if username or email already exists
    existing_user = users_collection.find_one({
        "$or": [
            {"username": username},
            {"email": email}
        ]
    })
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists"
        )
    
    # Create new user
    user_data = {
        "username": username,
        "email": email,
        "password": hash_password(password),
        "created_at": datetime.utcnow().isoformat()
    }
    
    result = users_collection.insert_one(user_data)
    
    # Create empty cart for the user
    carts_collection.insert_one({
        "user_id": result.inserted_id,
        "items": [],
        "updated_at": datetime.utcnow().isoformat()
    })
    
    return {
        "message": "User registered successfully",
        "user_id": str(result.inserted_id)
    }

# User login
@app.post("/login", tags=["Authentication"])
def login_user(
    username_or_email: Annotated[str, Form()],
    password: Annotated[str, Form()]
):
    """Login with username/email and password"""
    # Find user by username or email
    user = users_collection.find_one({
        "$or": [
            {"username": username_or_email},
            {"email": username_or_email}
        ]
    })
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verify password
    if not verify_password(password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    return {
        "message": "Login successful",
        "user_id": str(user["_id"]),
        "username": user["username"]
    }

# Add item to cart
@app.post("/cart", tags=["Cart"])
def add_to_cart(
    user_id: Annotated[str, Form()],
    product_id: Annotated[str, Form()],
    quantity: Annotated[int, Form()] = 1
):
    """Add a product to user's shopping cart"""
    # Validate user ID
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user ID"
        )
    
    # Validate product ID
    if not ObjectId.is_valid(product_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid product ID"
        )
    
    # Check if product exists
    product = products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Get user's cart or create if it doesn't exist
    cart = carts_collection.find_one({"user_id": ObjectId(user_id)})
    
    if not cart:
        # Create new cart
        cart_data = {
            "user_id": ObjectId(user_id),
            "items": [{"product_id": ObjectId(product_id), "quantity": quantity}],
            "updated_at": datetime.utcnow().isoformat()
        }
        carts_collection.insert_one(cart_data)
    else:
        # Check if product already in cart
        item_exists = False
        for item in cart["items"]:
            if item["product_id"] == ObjectId(product_id):
                item["quantity"] += quantity
                item_exists = True
                break
        
        # If product not in cart, add it
        if not item_exists:
            cart["items"].append({"product_id": ObjectId(product_id), "quantity": quantity})
        
        # Update cart
        carts_collection.update_one(
            {"_id": cart["_id"]},
            {"$set": {
                "items": cart["items"],
                "updated_at": datetime.utcnow().isoformat()
            }}
        )
    
    return {"message": "Product added to cart successfully"}

# Get user's cart
@app.get("/cart/{user_id}", tags=["Cart"])
def get_cart(user_id: str):
    """Get all items in user's shopping cart"""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user ID"
        )
    
    cart = carts_collection.find_one({"user_id": ObjectId(user_id)})
    
    if not cart or not cart["items"]:
        return {"message": "Cart is empty", "items": []}
    
    # Get detailed product information for each item
    cart_items = []
    for item in cart["items"]:
        product = products_collection.find_one({"_id": item["product_id"]})
        if product:
            cart_items.append({
                "product": replace_mongo_id(product),
                "quantity": item["quantity"],
                "subtotal": product["price"] * item["quantity"]
            })
    
    return {
        "user_id": user_id,
        "items": cart_items,
        "total_items": sum(item["quantity"] for item in cart["items"])
    }

# Checkout process
@app.post("/checkout/{user_id}", tags=["Checkout"])
def checkout(user_id: str):
    """Process checkout and create order"""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user ID"
        )
    
    # Get user's cart
    cart = carts_collection.find_one({"user_id": ObjectId(user_id)})
    
    if not cart or not cart["items"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty"
        )
    
    # Calculate total and prepare order items
    order_items = []
    grand_total = 0
    
    for item in cart["items"]:
        product = products_collection.find_one({"_id": item["product_id"]})
        if product:
            subtotal = product["price"] * item["quantity"]
            order_items.append({
                "product_id": item["product_id"],
                "product_name": product["name"],
                "quantity": item["quantity"],
                "price": product["price"],
                "subtotal": subtotal
            })
            grand_total += subtotal
    
    # Create order
    order_data = {
        "user_id": ObjectId(user_id),
        "items": order_items,
        "total_amount": grand_total,
        "status": "completed",
        "created_at": datetime.utcnow().isoformat()
    }
    
    order_result = orders_collection.insert_one(order_data)
    
    # Clear the cart after successful checkout
    carts_collection.update_one(
        {"user_id": ObjectId(user_id)},
        {"$set": {
            "items": [],
            "updated_at": datetime.utcnow().isoformat()
        }}
    )
    
    return {
        "message": "Checkout successful",
        "order_id": str(order_result.inserted_id),
        "order_summary": {
            "items": order_items,
            "total_amount": grand_total,
            "total_items": sum(item["quantity"] for item in order_items)
        }
    }

# Get user orders
@app.get("/orders/{user_id}", tags=["Checkout"])
def get_user_orders(user_id: str):
    """Get all orders for a user"""
    if not ObjectId.is_valid(user_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user ID"
        )
    
    orders = orders_collection.find({"user_id": ObjectId(user_id)}).sort("created_at", -1).to_list()
    
    return {
        "user_id": user_id,
        "orders": list(map(replace_mongo_id, orders)),
        "total_orders": len(orders)
    }