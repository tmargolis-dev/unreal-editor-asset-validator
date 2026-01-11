# Unreal Editor Asset Validator

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

1. Open the Unreal Editor
2. Select one or more assets
3. Go to **Tools → Execute Python Script…**
4. Run `Content/Python/validate_assets.py`

## Notes

This tool is intentionally small and focused.
It is meant to demonstrate editor scripting and pipeline thinking rather than be a complete validation framework.
