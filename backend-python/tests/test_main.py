from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app
import os
import pytest
import io
from PIL import Image

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}

def test_webhook_get_verification():
    os.environ["WHATSAPP_TOKEN"] = "test_token"
    params = {
        "hub.verify_token": "test_token",
        "hub.challenge": "test_challenge"
    }
    response = client.get("/webhook", params=params)
    assert response.status_code == 200
    assert response.text == "test_challenge"

def test_webhook_get_verification_invalid():
    os.environ["WHATSAPP_TOKEN"] = "test_token"
    params = {
        "hub.verify_token": "wrong_token",
        "hub.challenge": "test_challenge"
    }
    response = client.get("/webhook", params=params)
    assert response.status_code == 403
    assert response.text == "Error, wrong validation token"

@patch("main.httpx.AsyncClient.get")
@patch("main.genai.GenerativeModel.generate_content_async")
def test_webhook_post_image(mock_gemini, mock_httpx_get):
    # Mock the response from Meta API to get the image URL
    mock_meta_response = MagicMock()
    mock_meta_response.status_code = 200
    mock_meta_response.json.return_value = {"url": "http://example.com/image.jpg"}

    # Create a dummy image for testing
    img = Image.new('RGB', (100, 100), color = 'red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()

    # Mock the response for downloading the image
    mock_image_response = MagicMock()
    mock_image_response.status_code = 200
    mock_image_response.content = img_byte_arr

    mock_httpx_get.side_effect = [mock_meta_response, mock_image_response]

    # Mock the response from Gemini
    mock_gemini_response = MagicMock()
    mock_gemini_response.text = '{"Name": "Test Product", "Price": 100.0, "Description": "Test Description"}'
    mock_gemini.return_value = mock_gemini_response

    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "1234567890",
                        "type": "image",
                        "image": {
                            "id": "12345",
                            "caption": "Test caption"
                        }
                    }]
                }
            }]
        }]
    }

    with patch('main.requests.post') as mock_requests_post:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = '{"product_id": 1}'
        mock_requests_post.return_value = mock_response

        response = client.post("/webhook", json=payload)

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["status"] == "success"
        assert response_json["laravel_status"] == 201
        assert response_json["product_data"] == {"Name": "Test Product", "Price": 100.0, "Description": "Test Description"}
