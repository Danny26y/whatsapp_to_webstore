<?php

namespace App\Http\Controllers;

use App\Models\Product;
use App\Models\Tenant;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use CloudinaryLabs\CloudinaryLaravel\Facades\Cloudinary;

class ProductIngestionController extends Controller
{
    public function store(Request $request)
    {
        // Validation
        $validator = Validator::make($request->all(), [
            'whatsapp_number' => 'required|string',
            'product_name' => 'required|string',
            'price' => 'required|numeric',
            'description' => 'required|string',
            'image_url' => 'required|string|url',
        ]);

        if ($validator->fails()) {
            return response()->json(['errors' => $validator->errors()], 422);
        }

        // Find Tenant
        $tenant = Tenant::where('phone_number', $request->input('whatsapp_number'))->first();

        if (!$tenant) {
            return response()->json(['error' => 'Tenant not found'], 404);
        }

        // Handle Image Upload to Cloudinary
        $secureUrl = Cloudinary::upload($request->image_url)->getSecurePath();

        // Create Product
        $product = new Product();
        $product->tenant_id = $tenant->id;
        $product->name = $request->input('product_name');
        $product->price = $request->input('price');
        $product->category = $request->input('description'); // Mapping description to category as requested
        $product->image_url = $secureUrl;
        $product->save();

        // Return Response
        return response()->json(['product_id' => $product->id], 201);
    }
}
