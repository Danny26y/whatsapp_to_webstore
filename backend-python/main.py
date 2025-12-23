from fastapi import FastAPI, Request, Response
import os
import google.generativeai as genai
from dotenv import load_dotenv
import httpx
import shutil
from PIL import Image

load_dotenv()

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
                                    gemini_response = await call_gemini(file_path, image_caption)
                                    return gemini_response
                                finally:
                                    if os.path.exists(file_path):
                                        os.remove(file_path)

    return {"status": "success"}


import json # Add this import at the top

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
    - product_name (string)
    - price (integer, numbers only, no symbols)
    - currency (string, default to NGN if unsure)
    - category (string, e.g., 'Fashion', 'Electronics')
    - size_or_variant (string or null)
    """

    # Open the image using PIL (standard way for this library)
    img = Image.open(image_path)

    try:
        # Pass the PIL image object directly
        response = await model.generate_content_async([prompt, caption, img])
        
        # Since we enforced JSON mode, response.text is guaranteed to be clean JSON
        return Response(content=response.text, media_type="application/json")
        
    except Exception as e:
        print(f"Gemini Error: {e}")
        # Return a safe fallback JSON so the app doesn't crash
        return Response(
            content=json.dumps({"error": "Failed to analyze image", "details": str(e)}), 
            status_code=500, 
            media_type="application/json"
        )


@app.get("/")
def read_root():
    return {"Hello": "World"}
