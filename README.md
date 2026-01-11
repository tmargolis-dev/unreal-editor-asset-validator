# Unreal Pipeline Tools – Asset Validation

This repository contains a simple Unreal Engine **Editor Python tool** that demonstrates
pipeline-style asset validation inside the Unreal Editor.

## What This Tool Does

The validation script checks selected assets for **naming convention compliance**
based on asset type:

- Materials must start with `M_`
- Textures must start with `T_`
- Blueprints must start with `BP_`

Assets that do not follow these rules are reported as warnings in the Unreal Output Log.

## Why This Exists

Consistent asset naming is a common requirement in production pipelines.
This tool demonstrates how editor scripting can be used to:

- Enforce conventions
- Reduce manual review
- Provide fast feedback to content creators

## How to Run

### Option 1: Output Log
1. Open the Unreal Editor
2. Select one or more assets
3. Open **Window → Developer Tools → Output Log**
4. Run:
   ```python
   import validate_assets
