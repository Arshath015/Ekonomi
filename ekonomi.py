import requests
import re
from bs4 import BeautifulSoup
import os
import time
import sqlite3
import json
import google.generativeai as generativeai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from typing import Dict, List
import uvicorn

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Constants
USD_TO_INR = 86  
DB_NAME = "product_cache.db"
generativeai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
llm = generativeai.GenerativeModel("gemini-1.5-flash")

# Database Cache Management
def initialize_cache():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_cache (
            product_name TEXT PRIMARY KEY,
            product_data TEXT,
            timestamp INTEGER
        )
    """)
    conn.commit()
    conn.close()

initialize_cache()

def fetch_from_cache(product_name, expiry_duration=86400):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT product_data, timestamp FROM product_cache WHERE product_name = ?", (product_name,))
    result = cursor.fetchone()
    conn.close()
    if result and (int(time.time()) - result[1]) < expiry_duration:
        return json.loads(result[0])
    return None

def store_in_cache(product_name, product_data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = int(time.time())
    cursor.execute("""
        INSERT OR REPLACE INTO product_cache (product_name, product_data, timestamp) 
        VALUES (?, ?, ?)
    """, (product_name, json.dumps(product_data), timestamp))
    conn.commit()
    conn.close()

def extract_price(price_str):
    price = re.sub(r'[^\d.]', '', price_str)
    try:
        return float(price)
    except ValueError:
        return 0

def convert_to_inr(usd_price):
    return round(usd_price * USD_TO_INR, 2)

def fetch_product_details(product_name):
    cached_data = fetch_from_cache(product_name)
    if cached_data:
        return cached_data
    
    url = f'https://google-search-master-mega.p.rapidapi.com/shopping?q={product_name}&gl=us&hl=en&autocorrect=true&num=50&page=1'
    headers = {'x-rapidapi-host': 'google-search-master-mega.p.rapidapi.com', 'x-rapidapi-key': '702c9a04c2msh51c070c034c6e99p18f0b5jsnf74a3c74907a'}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch data from API")

    products = response.json().get("shopping", [])
    product_list = []
    
    for product in products:
        title, price, link = product['title'].strip(), product['price'], product['link']
        price_value = extract_price(price)
        price_in_inr = convert_to_inr(price_value)
        offer = product.get('offer', 'No offer available')  # Extracting offer details
        
        product_list.append({
            "name": title,
            "price_in_inr": price_in_inr,
            "url": link,
            "offer": offer
        })

    if product_list:
        store_in_cache(product_name, product_list)
    
    return product_list

# API Endpoints

@app.get("/")
def home():
    return {"message": "Welcome to AI Chatbot & Product API"}

@app.get("/chat/")
def chat_response(query: str):
    """AI Chatbot Endpoint"""
    try:
        response = llm.generate_content(query)
        return {"response": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/product/")
def get_product_details(product_name: str):
    """Fetch Product Details"""
    try:
        product_data = fetch_product_details(product_name)
        return {"products": product_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
