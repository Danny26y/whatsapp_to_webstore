<?php

namespace App\Http\Controllers;

use App\Models\Tenant;

class StorefrontController extends Controller
{
    public function show(string $subdomain)
    {
        $tenant = Tenant::where('subdomain', $subdomain)->firstOrFail();

        $products = $tenant->products()->where('is_available', true)->get();

        return view('storefront', compact('tenant', 'products'));
    }
}
