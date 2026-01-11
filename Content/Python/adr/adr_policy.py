from adr import adr_graph


def evaluate_policies(root_package, graph):
    violations = []

    for edge in graph["edges"]:
        if "editor_only" not in edge["flags"]:
            continue

        violating = edge["to"]
        path = adr_graph.explain_path(graph, violating)

        violations.append({
            "policy_id": "NO_EDITOR_DEPS",
            "severity": "warning",
            "message": (
                "Editor-only / dev content appears in the runtime "
                "dependency graph. This may cause cook or shipping issues."
            ),
            "violating_package": violating,
            "example_path": [p["package"] for p in path],
        })

    seen = set()
    deduped = []

    for v in violations:
        key = (v["policy_id"], v["violating_package"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(v)

    return deduped
