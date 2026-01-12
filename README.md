# AI Chatbot and Product Information API

## Overview

This project is a Python-based backend service that combines an AI-powered chatbot with a product information retrieval system. It exposes REST APIs using FastAPI to handle conversational AI with memory and to fetch product details such as prices and offers from external sources. The system also includes caching and persistent storage to improve performance and maintain conversation history.

---

## Core Features

- AI chatbot powered by Google Gemini
- Conversation memory stored in a database
- Product search with price conversion and offer extraction
- Caching layer to reduce repeated external API calls
- REST APIs built using FastAPI
- SQLite database for persistence

---

## How the System Works

The application initializes a FastAPI server and connects to a local SQLite database. Two main workflows are supported: AI chat and product information retrieval.

For chat requests, user messages are sent to the Gemini model, responses are generated, and both the user input and AI response are stored in the database. Each interaction is associated with a unique conversation ID to support conversation history tracking.

For product queries, the system fetches shopping results from an external search API. Product prices are extracted, converted from USD to INR, and enriched with offer details scraped from product pages. Results are cached locally to avoid unnecessary repeated API calls.

---

## Execution Flow

### AI Chat Flow

1. User sends a message along with a user ID
2. The message is sent to the Gemini model
3. The AI response is generated
4. Conversation data is stored in SQLite
5. Response is returned to the client

### Product Search Flow

1. User requests product details by name
2. Cache is checked for existing data
3. If not cached, external shopping API is called
4. Prices are extracted and converted to INR
5. Offer details are scraped from product pages
6. Results are cached and returned

---

## API Endpoints

### Health Check

## GET /

Returns a welcome message to verify the service is running.

---

## AI Chat Endpoint

### POST /chat/

#### Request Body
```json
{
  "user_id": "string",
  "message": "string"
}
```

#### Response
```json
{
  "conversation_id": "string",
  "response": "string"
}
```

---

### Fetch Conversation History
1. GET /get-conversations/?user_id=<user_id>
2. Returns all past conversations for the given user.

### Product Information Endpoint
```bash
GET /product/?product_name=<product_name>
```
Returns a list of products with:
  1. Name
  2. Price converted to INR
  3. Product URL
  4. Extracted offers
  5. Caching and Persistence
  6. Product data is cached in SQLite with timestamps
  7. Cached data expires after a configurable duration
  8. Conversation history is permanently stored for retrieval
  9. SQLite is used for simplicity and local persistence

---

### Environment Configuration
**The application uses environment variables for sensitive configuration.**
```json
GOOGLE_API_KEY=<your_gemini_api_key>
```

---

## How to Run
1. Install dependencies
2. Set environment variables
3. Start the server
```bash
python main.py
```
4. The API will run on:
```bash
http://0.0.0.0:8000
```
---
## Summary

This project demonstrates a practical backend system that integrates conversational AI with real-world product data retrieval. It highlights API design, caching, persistence, and external service integration in a clean and extensible architecture.
