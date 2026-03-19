# Architecture

## Overview

This project models the frontend layer of an open web mapping stack.

## Flow

1. Sample dashboard layer metadata is loaded from checked-in JSON.
2. Filter state narrows the visible map layers by region and status.
3. Summary cards and layer cards reflect the filtered set.
4. A live MapLibre surface renders OpenStreetMap raster tiles and a GeoJSON overlay generated from the filtered layer metadata.

## Why It Works Publicly

- Demonstrates frontend GIS interaction without relying on proprietary products.
- Keeps the repo runnable in a standard Vite toolchain.
- Shows a real open-stack map implementation while preserving a simple extension path toward richer MapLibre or OpenLayers behavior.
