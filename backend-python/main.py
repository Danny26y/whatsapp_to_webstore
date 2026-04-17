from fastapi import FastAPI, Request, Response
import os
import google.generativeai as genai
from dotenv import load_dotenv
import httpx
import shutil
from PIL import Image
import json
import requests
import asyncio
import time
from pydantic import BaseModel

load_dotenv()

CACHE_FILE = "temp/cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache):
    temp_dir = "temp"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

async def send_whatsapp_message(phone_number: str, text: str):
    phone_id = os.getenv("WHATSAPP_PHONE_ID", "default_id")
    url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": text}
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)

class ProductData(BaseModel):
    Name: str
    Price: float
    Description: str

app = FastAPI()

# Configure the Gemini API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


@app.get("/webhook")
async def webhook_get(request: Request):
    # Handle webhook verification
    if request.query_params.get("hub.verify_token") == os.getenv("WHATSAPP_TOKEN"):
        return Response(content=request.query_params["hub.challenge"], status_code=200)
    return Response(content="Error, wrong validation token", status_code=403)


@app.post("/webhook")
async def webhook_post(request: Request):
    data = await request.json()
    if "entry" in data and data["entry"]:
        entry = data["entry"][0]
        if "changes" in entry and entry["changes"]:
            change = entry["changes"][0]
            if "value" in change and "messages" in change["value"]:
                message = change["value"]["messages"][0]
                if message["type"] == "image":
                    image_id = message["image"]["id"]
                    image_caption = message["image"].get("caption", "")

                    async with httpx.AsyncClient() as client:
                        # Get the image URL from Meta
                        headers = {"Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}"}
                        url = f"https://graph.facebook.com/v20.0/{image_id}"
                        response = await client.get(url, headers=headers)
                        if response.status_code == 200:
                            image_url = response.json()["url"]

                            # Download the image
                            image_response = await client.get(image_url, headers=headers)
                            if image_response.status_code == 200:
                                # Save the image to a temporary file
                                temp_dir = "temp"
                                if not os.path.exists(temp_dir):
                                    os.makedirs(temp_dir)

                                file_path = os.path.join(temp_dir, f"{image_id}.jpg")
                                try:
                                    with open(file_path, "wb") as f:
                                        f.write(image_response.content)

                                    # Call Gemini API with the image and caption
                                    gemini_text = await call_gemini(file_path, image_caption)

                                    # Parse and validate with Pydantic
                                    try:
                                        data_dict = json.loads(gemini_text)
                                        product_data = ProductData(**data_dict)
                                    except Exception as e:
                                        print(f"Validation Error: {e}")
                                        return {"status": "error", "message": "Failed to validate product data"}

                                    whatsapp_number = message.get("from", "unknown")

                                    cache = load_cache()
                                    cache[whatsapp_number] = {
                                        "data": product_data.model_dump(),
                                        "image_url": image_url,
                                        "timestamp": time.time()
                                    }
                                    save_cache(cache)

                                    msg = f"I found: {product_data.Name} at {product_data.Price}. Reply YES to list this or NO to cancel."
                                    await send_whatsapp_message(whatsapp_number, msg)

                                    return {"status": "success", "message": "Pending confirmation"}
                                finally:
                                    if os.path.exists(file_path):
                                        os.remove(file_path)
                elif message["type"] == "text":
                    whatsapp_number = message.get("from", "unknown")
                    text_body = message.get("text", {}).get("body", "").strip().upper()

                    cache = load_cache()
                    if whatsapp_number in cache:
                        entry = cache[whatsapp_number]
                        if time.time() - entry["timestamp"] < 600:
                            if text_body == "YES":
                                product_data = entry["data"]
                                image_url = entry["image_url"]
                                laravel_url = os.getenv("LARAVEL_API_URL", "http://127.0.0.1:8000/api/v1/ingest-product")
                                payload = {
                                    "whatsapp_number": whatsapp_number,
                                    "product_name": product_data["Name"],
                                    "price": product_data["Price"],
                                    "description": product_data["Description"],
                                    "image_url": image_url
                                }
                                headers = {
                                    "Authorization": f"Bearer {os.getenv('API_TOKEN', 'secret-token')}"
                                }
                                await asyncio.to_thread(requests.post, laravel_url, json=payload, headers=headers)
                                await send_whatsapp_message(whatsapp_number, "Product has been successfully listed!")

                                del cache[whatsapp_number]
                                save_cache(cache)
                                return {"status": "success", "action": "listed"}

                            elif text_body == "NO":
                                await send_whatsapp_message(whatsapp_number, "Listing cancelled.")
                                del cache[whatsapp_number]
                                save_cache(cache)
                                return {"status": "success", "action": "cancelled"}

                        else:
                            del cache[whatsapp_number]
                            save_cache(cache)

    return {"status": "success"}


async def call_gemini(image_path: str, caption: str):
    """
    Calls the Gemini API to extract product data from an image and caption.
    Uses Native JSON mode for reliability.
    """
    # Initialize the model with specific config for JSON output
    model = genai.GenerativeModel(
        'gemini-1.5-flash',
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = """
    Analyze this image and caption to extract product details.
    Return a JSON object with these exact keys:
    - Name (string)
    - Price (float, numbers only, no symbols)
    - Description (string)
    """

    # Open the image using PIL (standard way for this library)
    img = Image.open(image_path)

    try:
        # Pass the PIL image object directly
        response = await model.generate_content_async([prompt, caption, img])
        
        # Since we enforced JSON mode, response.text is guaranteed to be clean JSON
        return response.text
        
    except Exception as e:
        print(f"Gemini Error: {e}")
        # Return a safe fallback JSON so the app doesn't crash
        return json.dumps({"error": "Failed to analyze image", "details": str(e)})


@app.get("/")
def read_root():
    return {"Hello": "World"}
