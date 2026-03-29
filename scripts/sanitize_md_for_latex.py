#!/usr/bin/env python3
"""Sanitize Markdown files for LaTeX conversion.
Converts inline code spans `like_this` to \texttt{like\_this} in .md files # pyright: ignore[reportInvalidStringEscapeSequence] # type: ignore
under projects/strata/paper and its submission_jmlr subfolder.
Skips fenced code blocks (```).
"""
import re
from pathlib import Path

ROOTS = [Path("projects/strata/paper"), Path("projects/strata/paper/submission_jmlr")]

INLINE_CODE_RE = re.compile(r"(`+)([^`\n]+?)\1")

def escape_for_tex(s: str) -> str:
    s = s.replace('\\', '\\textbackslash{}')
    s = s.replace('{', '\\{')
    s = s.replace('}', '\\}')
    s = s.replace('%', '\\%')
    s = s.replace('_', '\\_')
    s = s.replace('#', '\\#')
    s = s.replace('&', '\\&')
    s = s.replace('^', '\\^{}')
    s = s.replace('~', '\\~{}')
    s = s.replace('$', '\\$')
    return s


def transform_content(text: str) -> str:
    lines = text.splitlines()
    out_lines = []
    in_fence = False
    fence_mark = None
    for line in lines:
        m = re.match(r"^(\s*)(```+)(.*)$", line)
        if m:
            fence = m.group(2)
            if not in_fence:
                in_fence = True
                fence_mark = fence
            elif fence == fence_mark:
                in_fence = False
                fence_mark = None
            out_lines.append(line)
            continue
        if in_fence:
            out_lines.append(line)
            continue
        # Replace inline code spans
        def repl(match):
            content = match.group(2)
            # avoid replacing long spans with newlines (shouldn't happen due to regex)
            esc = escape_for_tex(content)
            return r"\\texttt{" + esc + r"}"
        new_line = INLINE_CODE_RE.sub(repl, line)
        out_lines.append(new_line)
    return "\n".join(out_lines) + ("\n" if text.endswith("\n") else "")


def process_file(p: Path) -> bool:
    text = p.read_text(encoding='utf8')
    new_text = transform_content(text)
    if new_text != text:
        p.write_text(new_text, encoding='utf8')
        print(f"Patched: {p}")
        return True
    return False


def main():
    patched = 0
    for root in ROOTS:
        if not root.exists():
            continue
        for p in root.rglob('*.md'):
            try:
                if process_file(p):
                    patched += 1
            except Exception as e:
                print(f"Error processing {p}: {e}")
    print(f"Done. Files patched: {patched}")

if __name__ == '__main__':
    main()
