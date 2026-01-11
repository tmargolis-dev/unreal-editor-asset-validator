import unreal

asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
assets = unreal.EditorUtilityLibrary.get_selected_assets()

if not assets:
    unreal.log_warning("No assets selected.")
else:
    unreal.log("Checking for unused assets...")

    options = unreal.AssetRegistryDependencyOptions(
        True,   # include_hard
        True,   # include_soft
        False,  # include_searchable_names
        False,  # include_soft_manage
        False   # include_hard_manage
    )

    unused = []

    for asset in assets:
        asset_data = asset_registry.get_asset_by_object_path(asset.get_path_name())
        referencers = asset_registry.get_referencers(asset_data.package_name, options)

        if not referencers:
            unreal.log_warning(f"[Unused] {asset.get_name()} has no referencers")
            unused.append(asset.get_name())
        else:
            unreal.log(f"[Used] {asset.get_name()} referenced by {len(referencers)} asset(s)")

    if unused:
        unreal.log_warning(f"Unused assets found: {', '.join(unused)}")
    else:
        unreal.log("No unused assets found.")
