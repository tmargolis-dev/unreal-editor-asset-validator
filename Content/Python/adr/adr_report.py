from adr import adr_graph


def generate_summary(root_package, graph, violations):
    stats = graph["stats"]
    lines = []

    lines.append("# Asset Dependency Reasoner Report")
    lines.append("")
    lines.append(f"**Root Asset:** `{graph['root_package']}`")
    lines.append("")

    lines.append("## Summary")
    lines.append(f"- Total assets scanned: **{stats['node_count']}**")
    lines.append(f"- Total dependency edges: **{stats['edge_count']}**")
    lines.append(f"- Hard references: **{stats['hard_edges']}**")
    lines.append(f"- Soft references: **{stats['soft_edges']}**")
    lines.append(
        f"- Editor-only suspected assets: **{stats['editor_only_suspected']}**"
    )
    lines.append("")

    lines.append("## Policy Violations")
    if not violations:
        lines.append("- None detected")
    else:
        for v in violations:
            lines.append(
                f"- **[{v['severity'].upper()}] {v['policy_id']}** — {v['message']}"
            )
            for p in v["example_path"]:
                lines.append(f"  - `{p}`")
    lines.append("")

    example = None
    for n in graph["nodes"].values():
        if "editor_only" in n["flags"]:
            example = n["package"]
            break

    if example:
        lines.append("## Example Explanation Path")
        steps = adr_graph.explain_path(graph, example)
        for i, s in enumerate(steps):
            if i == 0:
                lines.append(f"- `{s['package']}` *(ROOT)*")
            else:
                lines.append(
                    f"- `{s['package']}` — {s['reason']} "
                    f"{'(flags: ' + ', '.join(s['flags']) + ')' if s['flags'] else ''}"
                )

    return "\n".join(lines)
