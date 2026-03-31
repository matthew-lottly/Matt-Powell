"""Convert a cProfile .prof file into a simple HTML report (top callers)."""
from __future__ import annotations

import pstats
from pathlib import Path


def main(src: str = "tuner_profile.prof", out: str = "outputs/tuner_profile.html") -> None:
    p = Path(src)
    if not p.exists():
        print(f"Profile file {src} not found")
        return

    stats = pstats.Stats(str(p)).sort_stats("cumtime")
    rows = []
    for i, (func, (cc, nc, tt, ct, callers)) in enumerate(stats.stats.items()):
        if i >= 200:
            break
        file, line, name = func
        rows.append((f"{name} ({file}:{line})", cc, nc, tt, ct))

    outp = Path(out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open("w", encoding="utf8") as fh:
        fh.write('<!doctype html><html><head><meta charset="utf-8"><title>Profile</title>')
        fh.write("<style>body{font-family:sans-serif}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:6px;text-align:left}th{background:#f3f3f3}</style>")
        fh.write('</head><body>')
        fh.write('<h2>tuner_profile.prof — top functions by cumulative time</h2>')
        fh.write('<table><thead><tr><th>function (file:line)</th><th>call count</th><th>primitive calls</th><th>total time</th><th>cumulative time</th></tr></thead><tbody>')
        for name, cc, nc, tt, ct in rows:
            fh.write(f"<tr><td>{name}</td><td>{cc}</td><td>{nc}</td><td>{tt:.6f}</td><td>{ct:.6f}</td></tr>")
        fh.write('</tbody></table>')
        fh.write('<p>Generated from tuner_profile.prof</p>')
        fh.write('</body></html>')

    print(f"Wrote {outp}")


if __name__ == "__main__":
    main()
