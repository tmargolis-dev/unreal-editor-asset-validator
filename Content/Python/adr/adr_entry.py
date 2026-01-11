import unreal
from adr import adr_graph, adr_policy, adr_report

DEFAULT_DEPTH = 4


def get_selected_asset_object_path():
    selected = unreal.EditorUtilityLibrary.get_selected_assets()
    if not selected:
        return None
    return selected[0].get_path_name()


def analyze_selected(depth: int = DEFAULT_DEPTH):
    root_obj = get_selected_asset_object_path()
    if not root_obj:
        return {"error": "No asset selected in Content Browser"}

    graph = adr_graph.build_dependency_graph(
        root_asset_path=root_obj,
        max_depth=depth,
        max_nodes=400
    )

    violations = adr_policy.evaluate_policies(
        graph["root_package"],
        graph
    )

    report_md = adr_report.generate_summary(
        graph["root_package"],
        graph,
        violations
    )

    unreal.log(f"[ADR] Root asset: {graph['root_package']}")
    unreal.log(
        f"[ADR] Nodes={graph['stats']['node_count']} "
        f"Edges={graph['stats']['edge_count']} "
        f"EditorOnlySuspected={graph['stats']['editor_only_suspected']} "
        f"Truncated={graph['truncated']}"
    )
    unreal.log(f"[ADR] Policy violations: {len(violations)}")

    return {
        "root_object": root_obj,
        "root_package": graph["root_package"],
        "graph": graph,
        "violations": violations,
        "report": report_md,
    }


def analyze_selected_tree(depth: int = DEFAULT_DEPTH):
    result = analyze_selected(depth)
    if "error" in result:
        return result

    tree = adr_graph.build_tree_hierarchy(result["graph"])
    result["tree"] = tree
    return result


def open_asset(asset_path: str):
    obj_path = adr_graph.asset_path_to_object_path(asset_path)
    asset_obj = unreal.load_asset(obj_path)

    if not asset_obj:
        unreal.log_warning(f"[ADR] Could not load asset: {obj_path}")
        return False

    try:
        subsystem = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
        subsystem.open_editor_for_assets([asset_obj])
        return True
    except Exception as e:
        unreal.log_warning(f"[ADR] Failed to open asset editor: {e}")
        return False


def get_referencers(asset_path: str):
    obj_path = adr_graph.asset_path_to_object_path(asset_path)
    refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(
        obj_path,
        False
    )
    return [str(r) for r in refs] if refs else []


def quick_test(depth: int = DEFAULT_DEPTH):
    r = analyze_selected(depth)
    if "error" in r:
        unreal.log_warning(f"[ADR] {r['error']}")
        return
    print(r["report"])
