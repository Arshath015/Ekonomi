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
from uuid import uuid4
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Constants
USD_TO_INR = 86  
DB_NAME = "product_cache.db"
generativeai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
llm = generativeai.GenerativeModel("gemini-1.5-flash")

# Database Initialization
def initialize_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create Product Cache Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_cache (
            product_name TEXT PRIMARY KEY,
            product_data TEXT,
            timestamp INTEGER
        )
    """)
    
    # Create Conversation History Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            user_message TEXT NOT NULL,
            ai_response TEXT NOT NULL,
            timestamp INTEGER
        )
    """)
    
    conn.commit()
    conn.close()

initialize_db()

# Fetch Data from Cache
def fetch_from_cache(product_name, expiry_duration=86400):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT product_data, timestamp FROM product_cache WHERE product_name = ?", (product_name,))
    result = cursor.fetchone()
    conn.close()
    if result and (int(time.time()) - result[1]) < expiry_duration:
        return json.loads(result[0])
    return None

# Store Data in Cache
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

# Extract Price from String
def extract_price(price_str):
    price = re.sub(r'[^\d.]', '', price_str)
    try:
        return float(price)
    except ValueError:
        return 0

# Convert USD to INR
def convert_to_inr(usd_price):
    return round(usd_price * USD_TO_INR, 2)

# Fetch Product Details
def fetch_product_details(product_name):
    cached_data = fetch_from_cache(product_name)
    if cached_data:
        return cached_data
    
    url = f'https://google-search-master-mega.p.rapidapi.com/shopping?q={product_name}&gl=us&hl=en&autocorrect=true&num=50&page=1'
    headers = {'x-rapidapi-host': 'google-search-master-mega.p.rapidapi.com', 'x-rapidapi-key': 'a645acb05emsh907eb026e3240d3p13fedejsn0a0f36fb077c'}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch data from API")

    products = response.json().get("shopping", [])
    product_list = []
    
    for product in products:
        title, price, link = product['title'].strip(), product['price'], product['link']
        price_value = extract_price(price)
        price_in_inr = convert_to_inr(price_value)
        offer = fetch_offer_details(link)  # Fetch detailed offers from the product URL
        
        product_list.append({
            "name": title,
            "price_in_inr": price_in_inr,
            "url": link,
            "offer": offer
        })

    if product_list:
        store_in_cache(product_name, product_list)
    
    return product_list

# Extract Relevant Offers
def extract_relevant_offers(text):
    offers = []
    patterns = [
        r"(\d+% off)", r"(Free Delivery|free shipping)",
        r"(\d+\s*interest-free payments)", r"(\d+% off using [a-zA-Z\s]+)",
        r"(Buy \d+,? get \d+ free)", r"(Extra \d+% off)"
    ]
    for pattern in patterns:
        match = re.findall(pattern, text, re.IGNORECASE)
        if match:
            offers.extend(match)
    return " | ".join(offers) if offers else "No specific offers found"

# Fetch Offer Details from Product Page
def fetch_offer_details(product_url):
    try:
        response = requests.get(product_url, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            return extract_relevant_offers(soup.get_text(separator=" ", strip=True))
        return "Could not retrieve offers"
    except Exception:
        return "Error fetching offer details"

# Store Conversations in DB
def store_conversation(user_id, conversation_id, user_message, ai_response):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = int(time.time())
    
    cursor.execute("""
        INSERT INTO conversations (user_id, conversation_id, user_message, ai_response, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, conversation_id, user_message, ai_response, timestamp))
    
    conn.commit()
    conn.close()

# Fetch Conversation History
def get_conversation_history(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT conversation_id, user_message, ai_response, timestamp FROM conversations
        WHERE user_id = ? ORDER BY timestamp DESC
    """, (user_id,))
    
    conversations = cursor.fetchall()
    conn.close()

    return [
        {"conversation_id": row[0], "user_message": row[1], "ai_response": row[2], "timestamp": row[3]}
        for row in conversations
    ]

# Request Models
class ChatRequest(BaseModel):
    user_id: str
    message: str

# API Endpoints
@app.get("/")
def home():
    return {"message": "Welcome to AI Chatbot & Product API"}

@app.post("/chat/")
def chat_with_ai(request: ChatRequest):
    """AI Chatbot with Memory"""
    try:
        conversation_id = str(uuid4())  # Unique conversation ID
        response = llm.generate_content(request.message)
        
        ai_reply = response.text if response else "No response available."
        
        # Store conversation in DB
        store_conversation(request.user_id, conversation_id, request.message, ai_reply)

        return {"conversation_id": conversation_id, "response": ai_reply}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-conversations/")
def get_conversations(user_id: str):
    """Fetch Conversation History for UI Integration"""
    try:
        conversations = get_conversation_history(user_id)
        return {"user_id": user_id, "conversations": conversations}

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
