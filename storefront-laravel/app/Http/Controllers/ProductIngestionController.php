<?php

namespace App\Http\Controllers;

use App\Models\Product;
use App\Models\Tenant;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;

class ProductIngestionController extends Controller
{
    public function ingest(Request $request)
    {
        // 1. Bearer Token Authentication
        $token = $request->bearerToken();
        if ($token !== config('app.api_token')) {
            return response()->json(['error' => 'Unauthorized'], 401);
        }

        // 2. Request Validation
        $validator = Validator::make($request->all(), [
            'phone_number' => 'required|string|exists:tenants,phone_number',
            'product_json' => 'required|json',
            'image_url' => 'required|string|url',
        ]);

        if ($validator->fails()) {
            return response()->json(['errors' => $validator->errors()], 422);
        }

        // 3. Find Tenant
        $tenant = Tenant::where('phone_number', $request->input('phone_number'))->first();

        // 4. Create Product
        $productData = json_decode($request->input('product_json'), true);

        $product = new Product();
        $product->tenant_id = $tenant->id;
        $product->name = $productData['name'];
        $product->price = $productData['price'];
        $product->category = $productData['category'];
        $product->image_url = $request->input('image_url');
        $product->save();

        // 5. Return Response
        return response()->json(['message' => 'Product ingested successfully', 'product' => $product], 201);
    }
}
