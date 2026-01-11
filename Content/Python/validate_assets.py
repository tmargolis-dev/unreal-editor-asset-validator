import unreal

PREFIX_RULES = {
    "Material": "M_",
    "Texture2D": "T_",
    "Blueprint": "BP_",
}

assets = unreal.EditorUtilityLibrary.get_selected_assets()

if not assets:
    unreal.log_warning("No assets selected.")
else:
    unreal.log("Running asset validation...")
    issues_found = False

    for asset in assets:
        name = asset.get_name()
        asset_class = asset.get_class().get_name()
        expected = PREFIX_RULES.get(asset_class)

        if expected and not name.startswith(expected):
            unreal.log_warning(
                f"[Naming] {name} ({asset_class}) should start with '{expected}'"
            )
            issues_found = True

    if not issues_found:
        unreal.log("Validation complete. No issues found.")
