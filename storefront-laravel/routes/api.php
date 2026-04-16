<?php

use App\Http\Controllers\ProductIngestionController;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;

Route::get('/user', function (Request $request) {
    return $request->user();
})->middleware('auth:sanctum');

Route::middleware('auth:sanctum')->post('/v1/ingest-product', [ProductIngestionController::class, 'store']);
