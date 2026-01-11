# Unreal Engine Editor Tools (Python)

This repository contains a small collection of **Unreal Engine Editor Python tools**
focused on pipeline safety, asset validation, and dependency analysis inside the Unreal Editor.

The tools are intentionally editor-only and system-oriented, demonstrating how automation
can reduce human error, improve reliability, and support production pipelines.

---

## Asset Naming Validator

This tool is a simple Unreal Engine **Editor Python script** that demonstrates
pipeline-style asset validation inside the Unreal Editor.

### What This Tool Does

The validation script checks selected assets for **naming convention compliance**
based on asset type:

- Materials must start with `M_`
- Textures must start with `T_`
- Blueprints must start with `BP_`

Assets that do not follow these rules are reported as warnings in the Unreal Output Log.

### Why This Exists

Consistent asset naming is a common requirement in production pipelines.
This tool demonstrates how editor scripting can be used to:

- Enforce conventions
- Reduce manual review
- Provide fast feedback to content creators

### How to Run

1. Open the Unreal Editor
2. Select one or more assets
3. Go to **Tools → Execute Python Script…**
4. Run `Content/Python/validate_assets.py`

### Notes

This tool is intentionally small and focused.
It is meant to demonstrate editor scripting and pipeline thinking rather than be a complete validation framework.

---

## Asset Dependency Reasoner

This editor tool analyzes asset dependencies using the Unreal Asset Registry
to explain **why** assets are referenced, identify potentially risky dependencies,
and enforce simple pipeline safety rules.

### What This Tool Does

- Builds a dependency graph for a selected asset (depth-limited)
- Classifies dependencies (hard, soft, transitive, editor-only suspected)
- Flags policy violations such as editor/dev content referenced by runtime assets
- Provides “explain why” paths that show how a dependency is introduced
- Displays results in an Editor Utility Widget using a TreeView

### Why This Exists

Unexpected asset dependencies are a common source of:
- Broken cooks
- Bloated builds
- Assets that cannot be safely deleted

This tool demonstrates how editor tooling can move beyond reporting
and instead **reason about dependency structure**, highlight risk,
and guide safe remediation.

### Notes

This tool uses heuristic classification rather than strict guarantees.
It is designed to support human decision-making, not replace it.

---

Each tool in this repository is intentionally scoped to demonstrate
clear ownership, practical editor scripting, and production-oriented design.
