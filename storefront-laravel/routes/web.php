<?php

use App\Http\Controllers\StorefrontController;
use Illuminate\Support\Facades\Route;

Route::get('/{subdomain}', [StorefrontController::class, 'show']);
