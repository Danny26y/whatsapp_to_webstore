# Agents Instructions and Repository Documentation

This repository contains a multi-service architecture encompassing a Laravel 11 web application for e-commerce multi-tenancy and a Python FastAPI microservice for WhatsApp integration via Gemini.

## Repository Structure

*   `storefront-laravel/`: Contains the Laravel 11 web application.
*   `backend-python/`: Contains the Python FastAPI microservice.

## Laravel 11 Multi-Tenancy

The multi-tenancy implementation relies primarily on the `Tenant` model located at `storefront-laravel/app/Models/Tenant.php`.

### Key Relationships
*   **Tenant and WhatsApp:** A crucial part of the multi-tenancy involves associating incoming WhatsApp messages with a specific store. This is achieved via the `phone_number` attribute on the `Tenant` model. When processing a webhook from WhatsApp, the phone number should map to exactly one tenant.
*   **Users & Products:** The `Tenant` model holds one-to-many relationships with the `User` and `Product` models (`hasMany`). Users and products are thereby isolated per tenant.

## Python Microservice (Gemini & WhatsApp)

The microservice located in `backend-python/main.py` is responsible for processing incoming WhatsApp webhooks containing images and extracting structured data using Google's Gemini Vision model (`gemini-1.5-flash`).

### Processing Workflow
1.  **Webhook Reception:** The FastAPI app receives a webhook via the `/webhook` endpoint.
2.  **Image Handling:** If the incoming message is an image, the microservice downloads the image from Meta using the provided `WHATSAPP_TOKEN`.
3.  **Gemini Analysis:** The downloaded image and its caption are sent to the Gemini API. The system prompt is configured to analyze the image and extract specific product details into a strict JSON format.
4.  **Extracted Fields:** The expected JSON structure includes:
    *   `product_name` (string)
    *   `price` (integer)
    *   `currency` (string, defaults to NGN)
    *   `category` (string)
    *   `size_or_variant` (string or null)

## Development and Testing
*   **Laravel Environment:** The Laravel backend requires `php-xml`, `php-dom`, `php-sqlite3`, and `php-mbstring`. An Application key needs to be generated (`php artisan key:generate`).
*   **Laravel Tests:** Tests can be run from the `storefront-laravel` directory using `php artisan test`.
*   **Python Tests:** Tests can be run using pytest, taking care to set the `PYTHONPATH` correctly: `PYTHONPATH=./backend-python pytest backend-python/tests/`.
*   **Python Dependencies:** Required dependencies for the microservice are located in `backend-python/requirements.txt` and include packages like `fastapi`, `httpx`, `Pillow`, and `google-generativeai`.
