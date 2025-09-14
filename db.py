from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
mongo_client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))

# Access database
ecommerce_db = mongo_client["ecommerce_db"]

# Collections
products_collection = ecommerce_db["products"]
users_collection = ecommerce_db["users"]
carts_collection = ecommerce_db["carts"]
orders_collection = ecommerce_db["orders"]

# Initialize sample products if collection is empty
if products_collection.count_documents({}) == 0:
    sample_products = [
        {
            "name": "Laptop",
            "description": "High-performance gaming laptop",
            "price": 999.99,
            "image": "https://example.com/laptop.jpg",
            "category": "Electronics"
        },
        {
            "name": "Smartphone",
            "description": "Latest smartphone with great camera",
            "price": 699.99,
            "image": "https://example.com/phone.jpg",
            "category": "Electronics"
        },
        {
            "name": "Headphones",
            "description": "Wireless noise-cancelling headphones",
            "price": 199.99,
            "image": "https://example.com/headphones.jpg",
            "category": "Electronics"
        },
        {
            "name": "T-Shirt",
            "description": "Cotton t-shirt with cool design",
            "price": 29.99,
            "image": "https://example.com/tshirt.jpg",
            "category": "Clothing"
        },
        {
            "name": "Coffee Mug",
            "description": "Ceramic coffee mug with handle",
            "price": 12.99,
            "image": "https://example.com/mug.jpg",
            "category": "Home"
        }
    ]
    products_collection.insert_many(sample_products)