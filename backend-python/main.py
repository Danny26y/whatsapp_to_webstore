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


async def call_gemini(image_path: str, caption: str):
    """
    Calls the Gemini API to extract product data from an image and caption.
    """
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = "Extract product name, price (integer), currency, and category from this image and caption. Return strictly JSON."

    # Open the image file
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()

    # Create the payload for the Gemini API
    with Image.open(image_path) as img:
        mime_type = f"image/{img.format.lower()}"

    image_parts = [
        {"mime_type": mime_type, "data": image_data}
    ]

    contents = [image_parts[0], {"text": f"{prompt}\n\n{caption}"}]

    try:
        response = await model.generate_content_async(contents)
        # Clean the response to ensure it's valid JSON
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        return Response(content=cleaned_response, media_type="application/json")
    except Exception as e:
        return Response(content={"error": str(e)}, status_code=500, media_type="application/json")


@app.get("/")
def read_root():
    return {"Hello": "World"}
