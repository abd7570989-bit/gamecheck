"""Plain-text report for the command line (GameCheck.exe --report)."""

from .compare import NOTES


def _fmt(value):
    if value is None:
        return "?"
    if isinstance(value, float):
        return f"{value:.1f}"
    if isinstance(value, list):
        return " / ".join(value) if value else "-"
    return str(value)


def render(me: dict, results: list, library_info: dict) -> str:
    lines = [
        "GameCheck - system",
        f"  CPU : {me['cpu_name'] or '?'}" + (f"  [{me['cpu_model']}]" if me["cpu_model"] else "  [not recognised]"),
        f"  GPU : {me['gpu_name'] or '?'}" + (f"  [{me['gpu_model']}]" if me["gpu_model"] else "  [not recognised]"),
        f"  VRAM: {_fmt(me['vram_gb'])} GB   RAM: {_fmt(me['ram_gb'])} GB   Free disk: {_fmt(me['free_disk_gb'])} GB",
        f"  OS  : {me['os'].get('name', '?')}",
        f"  Library v{library_info['library_version']} ({library_info['source']}), {library_info['games']} games",
        "",
    ]
    for r in results:
        warn = "  [not enough free disk space]" if r["needs_disk_space"] else ""
        lines.append(f"{r['name']}: {r['verdict']}{warn}")
        for c in r["components"]:
            note = f"  ({NOTES[c['note']]})" if c.get("note") else ""
            lines.append(f"    {c['label']:<22} {c['status']:<12} yours: {_fmt(c['yours'])}{note}")
        lines.append("")
    return "\n".join(lines)
