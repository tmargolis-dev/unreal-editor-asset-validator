import unreal
from preflight import preflight_core

# Tune as needed
DEPTH = 4
UNUSED_LIMIT = 2000

report = preflight_core.run_preflight(depth=DEPTH, unused_limit=UNUSED_LIMIT)
md_path, json_path = preflight_core.save_report_files(report)

unreal.log(f"[PREFLIGHT] Status: {report.status.upper()}")
if report.root_asset:
    unreal.log(f"[PREFLIGHT] Root: {report.root_asset}")
unreal.log(f"[PREFLIGHT] Wrote markdown: {md_path}")
unreal.log(f"[PREFLIGHT] Wrote json: {json_path}")

# Print markdown to output log (optional)
print(preflight_core.to_markdown(report))
