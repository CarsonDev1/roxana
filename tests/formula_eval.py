"""Tiny evaluator for the COUNTIF / COUNTA formulas build_excel writes (no LibreOffice on this machine)."""
import re

TERM = re.compile(r"""(?P<fn>COUNTIF|COUNTA)\('(?P<sheet>[^']+)'!(?P<col>[A-Z]+):(?P=col)"""
                  r"""(?:,"(?P<crit>(?:[^"]|"")*)")?\)(?P<minus>-1)?""")


def _criterion_regex(criterion: str) -> re.Pattern:
    out, i = [], 0
    while i < len(criterion):
        ch = criterion[i]
        if ch == "~" and i + 1 < len(criterion):
            out.append(re.escape(criterion[i + 1]))
            i += 2
            continue
        out.append(".*" if ch == "*" else "." if ch == "?" else re.escape(ch))
        i += 1
    return re.compile("^" + "".join(out) + "$", re.IGNORECASE | re.DOTALL)


def _column(wb, sheet: str, col: str) -> list:
    ws = wb[sheet]
    return [ws[f"{col}{r}"].value for r in range(1, ws.max_row + 1)]


def eval_formula(wb, formula: str) -> int:
    assert formula.startswith("="), formula
    body, total, pos = formula[1:], 0, 0
    for m in TERM.finditer(body):
        assert body[pos:m.start()] in ("", "+"), f"unsupported formula: {formula}"
        pos = m.end()
        values = _column(wb, m["sheet"], m["col"])
        if m["fn"] == "COUNTA":
            total += sum(1 for v in values if v not in (None, "")) - (1 if m["minus"] else 0)
        else:
            rx = _criterion_regex(m["crit"].replace('""', '"'))
            total += sum(1 for v in values if v is not None and rx.match(str(v)))  # như Excel: tính cả dòng tiêu đề
    assert pos == len(body), f"unsupported formula: {formula}"
    return total
