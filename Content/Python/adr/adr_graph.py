import unreal
from collections import deque

EDITOR_ONLY_MARKERS = (
    "/Editor/",
    "/Developers/",
    "/Test/",
    "/Debug/",
)

MAX_DEFAULT_NODES = 400


def asset_path_to_object_path(asset_path: str) -> str:
    if not asset_path:
        return asset_path

    s = asset_path.strip()

    if "'" in s and s.endswith("'"):
        s = s[s.find("'") + 1 : s.rfind("'")]

    if "." not in s:
        leaf = s.split("/")[-1]
        s = f"{s}.{leaf}"

    return s


def object_path_to_package_name(object_path: str) -> str:
    s = asset_path_to_object_path(object_path)
    return s.split(".", 1)[0]


def get_asset_class_name(path: str) -> str:
    try:
        ad = unreal.EditorAssetLibrary.find_asset_data(
            asset_path_to_object_path(path)
        )
        if ad and hasattr(ad, "asset_class_path"):
            return str(ad.asset_class_path.asset_name)
    except Exception:
        pass
    return "Unknown"


def is_editor_only_suspected(path: str) -> bool:
    return any(marker in path for marker in EDITOR_ONLY_MARKERS)


def _get_dependencies_hard_soft(package_name: str):
    registry = unreal.AssetRegistryHelpers.get_asset_registry()

    hard_opts = unreal.AssetRegistryDependencyOptions(
        include_hard_package_references=True,
        include_soft_package_references=False,
        include_searchable_names=False,
        include_soft_management_references=False,
        include_hard_management_references=False,
    )

    soft_opts = unreal.AssetRegistryDependencyOptions(
        include_hard_package_references=False,
        include_soft_package_references=True,
        include_searchable_names=False,
        include_soft_management_references=False,
        include_hard_management_references=False,
    )

    hard = registry.get_dependencies(package_name, hard_opts) or []
    soft = registry.get_dependencies(package_name, soft_opts) or []

    return [str(x) for x in hard], [str(x) for x in soft]


def classify_dependency(root_package, from_package, to_package, dep_kind, depth):
    flags = []

    reason = (
        "Soft Reference (optional)"
        if dep_kind == "Soft"
        else "Hard Runtime Reference"
    )

    if is_editor_only_suspected(to_package):
        reason = "Editor-only Suspected"
        flags.append("editor_only")

    if root_package.startswith("/Game/") and is_editor_only_suspected(to_package):
        flags.append("suspicious")

    if depth > 1:
        reason += " (Transitive)"

    return reason, flags


def build_dependency_graph(root_asset_path, max_depth=4, max_nodes=MAX_DEFAULT_NODES):
    root_object = asset_path_to_object_path(root_asset_path)
    root_package = object_path_to_package_name(root_object)

    nodes = {}
    edges = []
    parents = {}
    edge_by_child = {}
    truncated = False

    def ensure_node(pkg):
        if pkg not in nodes:
            nodes[pkg] = {
                "package": pkg,
                "class": get_asset_class_name(pkg),
                "flags": ["editor_only"] if is_editor_only_suspected(pkg) else [],
            }

    ensure_node(root_package)

    visited = {root_package}
    queue = deque([(root_package, 0)])

    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        if len(nodes) >= max_nodes:
            truncated = True
            break

        hard, soft = _get_dependencies_hard_soft(current)
        deps = {d: "Hard" for d in hard}
        for d in soft:
            deps.setdefault(d, "Soft")

        for dep, kind in deps.items():
            if dep == current:
                continue

            ensure_node(dep)
            reason, flags = classify_dependency(
                root_package, current, dep, kind, depth + 1
            )

            edge = {
                "from": current,
                "to": dep,
                "dep_type": kind,
                "reason": reason,
                "flags": flags,
                "depth": depth + 1,
            }

            edges.append(edge)

            if dep not in parents:
                parents[dep] = current
                edge_by_child[dep] = edge

            if dep not in visited:
                visited.add(dep)
                queue.append((dep, depth + 1))

    stats = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "editor_only_suspected": sum(
            1 for n in nodes.values() if "editor_only" in n["flags"]
        ),
        "soft_edges": sum(1 for e in edges if e["dep_type"] == "Soft"),
        "hard_edges": sum(1 for e in edges if e["dep_type"] == "Hard"),
    }

    return {
        "root_object": root_object,
        "root_package": root_package,
        "nodes": nodes,
        "edges": edges,
        "parents": parents,
        "edge_by_child": edge_by_child,
        "truncated": truncated,
        "stats": stats,
    }


def explain_path(graph, target_package):
    root = graph["root_package"]
    parents = graph["parents"]
    edge_by_child = graph["edge_by_child"]

    target = object_path_to_package_name(target_package)
    if target not in graph["nodes"]:
        return []

    chain = [target]
    while chain[-1] != root and chain[-1] in parents:
        chain.append(parents[chain[-1]])

    chain.reverse()

    steps = [{"package": chain[0], "reason": "ROOT", "flags": []}]
    for pkg in chain[1:]:
        edge = edge_by_child.get(pkg, {})
        steps.append({
            "package": pkg,
            "reason": edge.get("reason", "Unknown"),
            "flags": edge.get("flags", []),
        })

    return steps


def build_tree_hierarchy(graph):
    root = graph["root_package"]
    children_map = {}
    edge_lookup = {}

    for e in graph["edges"]:
        children_map.setdefault(e["from"], []).append(e["to"])
        edge_lookup[(e["from"], e["to"])] = e

    def build_node(pkg, depth):
        node = {
            "package": pkg,
            "children": [],
            "reason": "ROOT" if depth == 0 else "",
            "flags": graph["nodes"][pkg]["flags"],
            "depth": depth,
        }

        for child in children_map.get(pkg, []):
            edge = edge_lookup[(pkg, child)]
            child_node = {
                "package": child,
                "children": [],
                "reason": edge["reason"],
                "flags": edge["flags"],
                "depth": depth + 1,
            }
            child_node["children"] = build_node(child, depth + 1)["children"]
            node["children"].append(child_node)

        return node

    return build_node(root, 0)
