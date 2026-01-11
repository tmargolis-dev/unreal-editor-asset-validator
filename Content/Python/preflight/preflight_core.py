import json
import os
import time
import unreal
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

# Reuse your ADR module for dependency reasoning + policy
from adr import adr_graph, adr_policy


# -----------------------------
# Config
# -----------------------------

NAMING_RULES = {
    "Material": "M_",
    "MaterialInstanceConstant": "MI_",
    "Texture2D": "T_",
    "Blueprint": "BP_",
    "WidgetBlueprint": "WBP_",
    "StaticMesh": "SM_",
    "SkeletalMesh": "SK_",
}

# Limiters to keep editor responsive
DEFAULT_MAX_DEPTH = 4
DEFAULT_MAX_NODES = 600
DEFAULT_UNUSED_SCAN_LIMIT = 3000  # number of assets to consider in unused scan


# -----------------------------
# Result models
# -----------------------------

@dataclass
class Finding:
    severity: str  # "error" | "warning" | "info"
    code: str
    hint: str
    asset: Optional[str] = None
    details: Optional[dict] = None


@dataclass
class PreflightReport:
    status: str  # "pass" | "warn" | "fail"
    root_asset: Optional[str]
    timestamp_utc: str
    duration_sec: float
    findings: List[Finding]
    stats: Dict


# -----------------------------
# Helpers
# -----------------------------

def _utc_timestamp():
    # Unreal Python has no timezone lib guarantee; keep it simple
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _get_selected_assets_object_paths() -> List[str]:
    selected = unreal.EditorUtilityLibrary.get_selected_assets()
    if not selected:
        return []
    return [a.get_path_name() for a in selected]


def _find_asset_data(object_path: str):
    try:
        return unreal.EditorAssetLibrary.find_asset_data(object_path)
    except Exception:
        return None


def _asset_name_from_object_path(object_path: str) -> str:
    # /Game/Foo/Bar.Bar -> Bar
    if not object_path:
        return ""
    s = object_path
    if "." in s:
        s = s.split(".", 1)[1]
    return s


def _ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def _saved_reports_dir() -> str:
    saved = unreal.Paths.project_saved_dir()
    out_dir = os.path.join(saved, "PreflightReports")
    _ensure_dir(out_dir)
    return out_dir


def _write_text(path: str, text: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _write_json(path: str, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


# -----------------------------
# Check 1: Naming validation
# -----------------------------

def check_naming_for_assets(object_paths: List[str]) -> List[Finding]:
    findings: List[Finding] = []

    for obj_path in object_paths:
        ad = _find_asset_data(obj_path)
        if not ad:
            findings.append(Finding(
                severity="warning",
                code="NAMING_ASSET_DATA_MISSING",
                hint="Could not read asset data for selected asset.",
                asset=obj_path
            ))
            continue

        # asset_class_path.asset_name is typically reliable in UE5
        try:
            class_name = str(ad.asset_class_path.asset_name)
        except Exception:
            class_name = "Unknown"

        expected_prefix = NAMING_RULES.get(class_name)
        if not expected_prefix:
            # Not covered by rules; ignore
            continue

        asset_name = _asset_name_from_object_path(obj_path)
        if not asset_name.startswith(expected_prefix):
            findings.append(Finding(
                severity="warning",
                code="NAMING_PREFIX_MISMATCH",
                hint=f"Expected prefix '{expected_prefix}' for class '{class_name}'.",
                asset=obj_path,
                details={"class": class_name, "expected_prefix": expected_prefix, "actual_name": asset_name}
            ))

    return findings


# -----------------------------
# Check 2: Unused asset scan (heuristic)
# -----------------------------

def _list_game_assets(limit: int = DEFAULT_UNUSED_SCAN_LIMIT) -> List[str]:
    """
    Return a list of object paths under /Game (up to limit).
    """
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    # FARFilter is supported but can vary; use path listing via AssetRegistry where possible.
    try:
        flt = unreal.ARFilter(
            package_paths=["/Game"],
            recursive_paths=True
        )
        assets = registry.get_assets(flt) or []
        out = []
        for a in assets[:limit]:
            # a.object_path returns a Name, stringify
            out.append(str(a.object_path))
        return out
    except Exception:
        # Fallback (slower): EditorAssetLibrary
        paths = unreal.EditorAssetLibrary.list_assets("/Game", recursive=True, include_folder=False) or []
        return paths[:limit]


def check_unused_assets(limit: int = DEFAULT_UNUSED_SCAN_LIMIT) -> List[Finding]:
    """
    Heuristic unused scan:
    - Consider assets under /Game
    - Mark as "potentially unused" if no package referencers are found
    """
    findings: List[Finding] = []
    assets = _list_game_assets(limit=limit)

    for obj_path in assets:
        # Skip maps for now (can be huge ref graphs)
        if obj_path.endswith(".umap") or obj_path.lower().endswith(".umap"):
            continue

        try:
            refs = unreal.EditorAssetLibrary.find_package_referencers_for_asset(obj_path, False) or []
            if len(refs) == 0:
                findings.append(Finding(
                    severity="info",
                    code="UNUSED_POSSIBLE",
                    hint="No package referencers found (heuristic). Verify before deletion.",
                    asset=obj_path
                ))
        except Exception:
            # If API fails for some assets, keep tool robust
            continue

    # Don’t overwhelm: cap reported items
    if len(findings) > 50:
        findings = findings[:50]
        findings.append(Finding(
            severity="info",
            code="UNUSED_TRUNCATED",
            hint="Unused scan results truncated for readability.",
            asset=None,
            details={"reported": 50}
        ))

    return findings


# -----------------------------
# Check 3: ADR dependency policy scan
# -----------------------------

def check_dependency_policies(root_object_path: str,
                              max_depth: int = DEFAULT_MAX_DEPTH,
                              max_nodes: int = DEFAULT_MAX_NODES) -> Tuple[List[Finding], Dict]:
    """
    Run ADR graph + policy evaluation against the selected root asset.
    """
    findings: List[Finding] = []

    graph = adr_graph.build_dependency_graph(
        root_asset_path=root_object_path,
        max_depth=max_depth,
        max_nodes=max_nodes
    )

    violations = adr_policy.evaluate_policies(graph["root_package"], graph)

    for v in violations:
        findings.append(Finding(
            severity="warning" if v.get("severity") == "warning" else "error",
            code=v.get("policy_id", "ADR_POLICY"),
            hint=v.get("message", "Policy violation detected."),
            asset=v.get("violating_package"),
            details={"example_path": v.get("example_path", [])}
        ))

    stats = {
        "adr_nodes": graph.get("stats", {}).get("node_count", 0),
        "adr_edges": graph.get("stats", {}).get("edge_count", 0),
        "adr_editor_only_suspected": graph.get("stats", {}).get("editor_only_suspected", 0),
        "adr_truncated": graph.get("truncated", False),
    }

    return findings, stats


# -----------------------------
# Main preflight runner
# -----------------------------

def run_preflight(depth: int = DEFAULT_MAX_DEPTH,
                  unused_limit: int = DEFAULT_UNUSED_SCAN_LIMIT) -> PreflightReport:
    start = time.time()
    findings: List[Finding] = []
    stats: Dict = {}

    selected = _get_selected_assets_object_paths()
    root = selected[0] if selected else None

    if not selected:
        findings.append(Finding(
            severity="error",
            code="NO_SELECTION",
            hint="Select at least one asset in the Content Browser before running preflight.",
            asset=None
        ))
    else:
        # Naming check over selection
        findings.extend(check_naming_for_assets(selected))
        stats["selected_count"] = len(selected)

        # ADR policy check only on the root selection (fast + meaningful)
        adr_findings, adr_stats = check_dependency_policies(
            root_object_path=root,
            max_depth=depth,
            max_nodes=DEFAULT_MAX_NODES
        )
        findings.extend(adr_findings)
        stats.update(adr_stats)

    # Unused scan is independent — do it even if no selection, but keep it light
    unused_findings = check_unused_assets(limit=unused_limit)
    findings.extend(unused_findings)
    stats["unused_scanned_limit"] = unused_limit
    stats["unused_flagged_count"] = sum(1 for f in unused_findings if f.code == "UNUSED_POSSIBLE")

    # Determine status
    has_error = any(f.severity == "error" for f in findings)
    has_warning = any(f.severity == "warning" for f in findings)

    status = "fail" if has_error else ("warn" if has_warning else "pass")

    dur = time.time() - start

    return PreflightReport(
        status=status,
        root_asset=root,
        timestamp_utc=_utc_timestamp(),
        duration_sec=round(dur, 3),
        findings=findings,
        stats=stats
    )


# -----------------------------
# Formatting / output
# -----------------------------

def to_markdown(report: PreflightReport) -> str:
    lines = []
    lines.append("# Pipeline Preflight Report")
    lines.append("")
    lines.append(f"**Status:** `{report.status.upper()}`")
    lines.append(f"**Timestamp (UTC):** `{report.timestamp_utc}`")
    if report.root_asset:
        lines.append(f"**Root Asset:** `{report.root_asset}`")
    lines.append(f"**Duration:** `{report.duration_sec}s`")
    lines.append("")

    lines.append("## Summary Stats")
    for k, v in report.stats.items():
        lines.append(f"- {k}: **{v}**")
    lines.append("")

    # Group view
    errors = [f for f in report.findings if f.severity == "error"]
    warns = [f for f in report.findings if f.severity == "warning"]
    infos = [f for f in report.findings if f.severity == "info"]

    def dump_group(title: str, arr: List[Finding]):
        lines.append(f"## {title} ({len(arr)})")
        if not arr:
            lines.append("- None")
            lines.append("")
            return
        for f in arr:
            asset = f" `{f.asset}`" if f.asset else ""
            lines.append(f"- **{f.code}** — {f.hint}{asset}")
            if f.details and isinstance(f.details, dict) and f.details.get("example_path"):
                lines.append("  - Example path:")
                for p in f.details["example_path"]:
                    lines.append(f"    - `{p}`")
        lines.append("")

    dump_group("Errors", errors)
    dump_group("Warnings", warns)
    dump_group("Info", infos)

    lines.append("---")
    lines.append("_Preflight is heuristic by design; it highlights risk and supports safe decisions._")
    return "\n".join(lines)


def save_report_files(report: PreflightReport) -> Tuple[str, str]:
    out_dir = _saved_reports_dir()
    safe_time = report.timestamp_utc.replace(":", "").replace("-", "")
    base = f"preflight_{safe_time}"

    md_path = os.path.join(out_dir, base + ".md")
    json_path = os.path.join(out_dir, base + ".json")

    _write_text(md_path, to_markdown(report))
    _write_json(json_path, {
        "status": report.status,
        "root_asset": report.root_asset,
        "timestamp_utc": report.timestamp_utc,
        "duration_sec": report.duration_sec,
        "stats": report.stats,
        "findings": [asdict(f) for f in report.findings],
    })

    return md_path, json_path
