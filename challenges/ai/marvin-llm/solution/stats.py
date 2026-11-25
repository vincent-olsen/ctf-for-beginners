#!/usr/bin/env python3
"""Count what marvin-llm's "AI" is made of, and redraw the charts in stats/.

Marvin is not a language model. challenge/marvin.py is if-statements, regular
expressions, keyword lists and pools of hand-written replies. This script
counts them (from the source with ast, and from the imported module) and
writes the SVG charts that how-it-works.md shows, a light and a dark copy each.

    python3 stats.py            # print the numbers and redraw stats/*.svg
    python3 stats.py --no-svg   # only print them

Stdlib only. Run it again after changing marvin.py. It stops with an error
when marvin.py gains a regex, keyword list or reply pool it can't place, so
the charts never quietly leave something out.
"""
import argparse
import ast
import collections
import re
import sys
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "challenge" / "marvin.py"
OUT = HERE / "stats"

sys.dont_write_bytecode = True          # leave no __pycache__ in challenge/ (it is ADDed to the image)
sys.path.insert(0, str(SOURCE.parent))
import marvin  # noqa: E402  (stdlib only; importing it starts no server)

# ================================================================ stages ====
# The pipeline stages, in the order respond() runs them, with the module-level
# regexes and keyword lists each one uses.
STAGES = (
    ("Language detection", ("_NO_MARKERS", "_EN_MARKERS")),
    ("Prompt-injection detector", (
        "_INJECT_VERBS", "_INJECT_TARGETS", "_INJECT_PHRASES", "_ASK_VERBS", "_ASK_TARGETS",
        "_NO_INJECT_VERB", "_NO_INJECT_TARGET", "_NO_INJECT_PHRASE", "_NO_ASK", "_NO_ASK_TARGET",
        "_MODE_SWITCH", "_FRAMING", "_GRANDMA", "_ABOUT_ORDERS")),
    ("Encoding detector", ("_ENCODING_RES",)),
    ("Input guard (blocklist)", ("BLOCKED_WORDS", "_BLOCKED_NO", "_SECRET_RE")),
    ("Refusal flavours", ("_REFUSE_KINDS",)),
    ("Wrong-category attacks", ("_WRONG_ATTACKS",)),
    ("Maths, encode, decode, echo", (
        "_QUOTED", "_INLINE_ENCODE", "_LEADING_VERB", "_ENCODE_VERB", "_DECODE_RE", "_ECHO_RE",
        "_SAY_RE", "_MATH_PREFIX", "_MATH_ALLOWED")),
    ("Small talk and lore", ("_INTENTS",)),
    ("Fallbacks", ("_ACK_RE",)),
    ("Output filter", ("_FLAG_RE", "_FLAG_SHAPE_RE", "_ENCODED_FLAGS")),
)
# What a stage's plain strings are, where "keywords" would be the wrong word.
STRING_NOUN = {"Output filter": "encoded flags"}
# A regex written inline (re.search(r"...") inside a function) belongs to the
# stage of the function, or of the module-level name a lambda is assigned to.
INLINE_STAGE = {
    "detect_lang": "Language detection",
    "requested_encoding": "Encoding detector",
    "requested_encodings": "Encoding detector",
    "_decode_base64": "Maths, encode, decode, echo",
    "_decode_hex": "Maths, encode, decode, echo",
    "_decode_binary": "Maths, encode, decode, echo",
    "_decode_codes": "Maths, encode, decode, echo",
    "_DECODERS": "Maths, encode, decode, echo",
    "_decode": "Maths, encode, decode, echo",
    "_math": "Maths, encode, decode, echo",
    "_chat": "Fallbacks",
}
# Tuples of strings that are not words Marvin looks for.
NOT_KEYWORDS = ("_UNDRESSED", "_NEEDS_PAYLOAD", "FRAMES")
# The raw pattern strings that a stage's compiled regexes are built from.
PATTERN_SOURCES = ("_ENCODINGS", "_INTENT_PATTERNS", "_WRONG_ATTACK_PATTERNS")

# Reply pools, grouped by what they are for.
TOPICS = (
    ("Small talk and lore", ("_INTENT_REPLIES",)),
    ("Refusals", ("_REFUSE", "_DEFLECT")),
    ("Giving in to an injection", ("_FRAME_IN", "_REVEAL", "_CODE_PLAIN", "_ENCODED_FLAVOUR",
                                   "_ENCODED_CLOSE", "_TOO_LONG")),
    ("Fallbacks", ("_FALLBACK", "_QUESTION", "_ACK", "_NUMBER", "_SHOUT", "_SYMBOLS", "_LONG", "_EMPTY")),
    ("Maths, encode, decode, echo", ("_UTIL",)),
    ("Wrong-category attacks", ("_WRONG_ATTACK_REPLIES",)),
    ("Role-play with no target", ("_ROLEPLAY", "_GRANDMA_ONLY")),
    ("Sighs and grumbles", ("_MOOD",)),
)

# How many answer kinds each f-string kind in respond() expands to.
KIND_FAMILIES = {
    "frame:": lambda: len(marvin.FRAMES),
    # the code or the prompt, by the first encoding named (a chain is not a kind of its own)
    "inject:": lambda: 2 * len(marvin._ENCODINGS),
    "refuse:": lambda: len(marvin._REFUSE_KINDS) + 1,          # + "direct"
    "attack:": lambda: len(marvin._WRONG_ATTACKS),
    "intent:": lambda: len(marvin._INTENTS),
}


def fail(message):
    sys.exit(f"stats.py: {message}")


# ============================================================== counting ====
def patterns_in(value, seen=None):
    """Every compiled regex inside a module global (tuples, lists, dicts)."""
    seen = set() if seen is None else seen
    if isinstance(value, re.Pattern):
        if id(value) not in seen:
            seen.add(id(value))
            yield value.pattern
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from patterns_in(item, seen)
    elif isinstance(value, dict):
        for item in value.values():
            yield from patterns_in(item, seen)


def is_keyword_list(value):
    return isinstance(value, (tuple, frozenset)) and value and all(isinstance(v, str) for v in value)


def alternatives(pattern):
    """1 + the number of | in the regex outside [character classes]."""
    count, in_class, i = 1, False, 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\":
            i += 2
            continue
        if in_class:
            in_class = c != "]"
        elif c == "[":
            in_class = True
            if pattern[i + 1:i + 2] == "^":
                i += 1
            if pattern[i + 1:i + 2] == "]":       # a ] right after [ or [^ is a literal
                i += 1
        elif c == "|":
            count += 1
        i += 1
    return count


def parents(tree):
    up = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            up[child] = node
    return up


def owner(node, up, tree):
    """The function a node is in, or the module-level name it is assigned to."""
    while node in up:
        node = up[node]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node.name
        if up.get(node) is tree and isinstance(node, ast.Assign):
            return node.targets[0].id
    return None


def count_stages(tree, up):
    stages = {name: collections.Counter() for name, _ in STAGES}
    placed = set()
    for stage, names in STAGES:
        for name in names:
            value = getattr(marvin, name)
            placed.add(name)
            if is_keyword_list(value):
                stages[stage]["keywords"] += len(value)
                continue
            found = list(patterns_in(value))
            if not found:
                fail(f"{name} has neither keywords nor regexes")
            stages[stage]["regexes"] += len(found)
            stages[stage]["alternatives"] += sum(alternatives(p) for p in found)

    # Nothing left out: every module-level regex or keyword list has a stage.
    for name, value in vars(marvin).items():
        if name in placed or name in NOT_KEYWORDS or name in PATTERN_SOURCES or name.startswith("__"):
            continue
        if is_keyword_list(value) or any(True for _ in patterns_in(value)):
            fail(f"{name} is a regex or keyword list with no stage: add it to STAGES")

    # Regexes written inline in a function: re.search(r"...", ...).
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "re"
                and node.args and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            continue
        where = owner(node, up, tree)
        if not any(isinstance(n, (ast.FunctionDef, ast.Lambda)) for n in _ancestors(node, up)):
            continue                       # module level: compiled once, counted above
        if where not in INLINE_STAGE:
            fail(f"inline regex in {where} (line {node.lineno}) has no stage: add it to INLINE_STAGE")
        stage = stages[INLINE_STAGE[where]]
        stage["regexes"] += 1
        stage["alternatives"] += alternatives(node.args[0].value)
    return stages


def _ancestors(node, up):
    while node in up:
        node = up[node]
        yield node


def count_ifs(tree, lines, up):
    """Per function: if / elif statements, x if c else y, comprehension filters, and/or."""
    per_function = collections.defaultdict(collections.Counter)
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            kind = "elif" if lines[node.lineno - 1].lstrip().startswith("elif") else "if"
        elif isinstance(node, ast.IfExp):
            kind = "ternary"
        elif isinstance(node, ast.comprehension):
            if not node.ifs:
                continue
            kind = "filter"
        elif isinstance(node, ast.BoolOp):
            kind = "and/or"
        else:
            continue
        func = next((n.name for n in _ancestors(node, up)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), "(module level)")
        amount = (len(node.ifs) if kind == "filter" else len(node.values) - 1 if kind == "and/or" else 1)
        per_function[func][kind] += amount
    return per_function


def count_pool(value):
    """Hand-written lines in a reply pool, per language ("" padding not counted)."""
    langs = collections.Counter()

    def strings(v):
        if isinstance(v, str):
            return 1 if v.strip() else 0
        if isinstance(v, dict):
            return sum(strings(x) for x in v.values())
        if isinstance(v, (tuple, list)):
            return sum(strings(x) for x in v)
        return 0

    def walk(v):
        if isinstance(v, dict) and {"en", "no"} <= v.keys():
            for lang in ("en", "no"):
                langs[lang] += strings(v[lang])
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)

    walk(value)
    return langs


def count_replies():
    topics = {}
    placed = set()
    for topic, names in TOPICS:
        total = collections.Counter()
        for name in names:
            total += count_pool(getattr(marvin, name))
            placed.add(name)
        topics[topic] = total
    for name, value in vars(marvin).items():
        if name not in placed and isinstance(value, dict) and count_pool(value):
            fail(f"reply pool {name} has no topic: add it to TOPICS")
    return topics


def count_kinds(tree):
    """How many different answer kinds respond() and its helpers can return."""
    constants, total = set(), 0
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple) and node.value.elts):
            continue
        first = node.value.elts[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            constants.add(first.value)
        elif isinstance(first, ast.JoinedStr):
            prefix = first.values[0].value
            if prefix not in KIND_FAMILIES:
                fail(f"answer kind f\"{prefix}...\" (line {node.lineno}) not in KIND_FAMILIES")
            total += KIND_FAMILIES[prefix]()
    return total + len(constants)


def classify_lines(tree, lines):
    """Each source line as replies / patterns / logic / comments / blank."""
    pools = {n for _, names in TOPICS for n in names} | {"SYSTEM_PROMPT"}
    rules = {n for _, names in STAGES for n in names} | set(PATTERN_SOURCES)
    kind = ["logic"] * len(lines)
    for node in tree.body:
        target = node.targets[0].id if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) else None
        label = "replies" if target in pools else "patterns" if target in rules else None
        if label:
            for ln in range(node.lineno - 1, node.end_lineno):
                kind[ln] = label
    for node in ast.walk(tree):                       # docstrings
        body = getattr(node, "body", None)
        if (isinstance(body, list) and body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str)):
            for ln in range(body[0].lineno - 1, body[0].end_lineno):
                kind[ln] = "comments"
    for i, line in enumerate(lines):
        if not line.strip():
            kind[i] = "blank"
        elif line.lstrip().startswith("#"):
            kind[i] = "comments"
    return collections.Counter(kind)


def collect():
    text = SOURCE.read_text(encoding="utf-8")
    lines = text.splitlines()
    tree = ast.parse(text)
    up = parents(tree)
    ifs = count_ifs(tree, lines, up)
    totals = sum(ifs.values(), collections.Counter())
    stages = count_stages(tree, up)
    return {
        "lines": len(lines),
        "line_kinds": classify_lines(tree, lines),
        "ifs": ifs,
        "if_totals": totals,
        "if_statements": totals["if"] + totals["elif"],
        "stages": stages,
        "regexes": sum(s["regexes"] for s in stages.values()),
        "alternatives": sum(s["alternatives"] for s in stages.values()),
        "keywords": sum(s["keywords"] for s in stages.values()),
        "topics": count_replies(),
        "kinds": count_kinds(tree),
        "intents": len(marvin._INTENTS),
        "encodings": len(marvin._ENCODINGS),
    }


# ================================================================ report ====
LINE_KINDS = (
    ("replies", "Hand-written replies"),
    ("patterns", "Regexes and keyword lists"),
    ("logic", "Logic (the actual code)"),
    ("comments", "Comments and docstrings"),
    ("blank", "Blank lines"),
)


def report(s):
    out = []
    w = out.append
    replies = sum(s["topics"].values(), collections.Counter())
    w(f"marvin.py: {s['lines']} lines, 0 language models\n")
    w("Where the lines go")
    for key, label in LINE_KINDS:
        n = s["line_kinds"][key]
        w(f"  {label:<28} {n:5}  {100 * n / s['lines']:4.1f}%")
    t = s["if_totals"]
    w(f"\nif statements: {s['if_statements']} ({t['if']} if + {t['elif']} elif), "
      f"plus {t['ternary']} 'x if c else y', {t['filter']} comprehension filters, {t['and/or']} and/or")
    w("  per function (if + elif):")
    for name, c in sorted(s["ifs"].items(), key=lambda kv: -(kv[1]["if"] + kv[1]["elif"])):
        n = c["if"] + c["elif"]
        if n:
            w(f"    {name:<22} {n:3}")
    w(f"\nRegexes: {s['regexes']} with {s['alternatives']} alternatives; keyword strings: {s['keywords']}")
    w("  per stage (regexes / alternatives / keywords):")
    for name, _ in STAGES:
        c = s["stages"][name]
        w(f"    {name:<30} {c['regexes']:3} / {c['alternatives']:4} / {c['keywords']:4}")
    w(f"\nHand-written reply lines: {replies['en'] + replies['no']} "
      f"({replies['en']} English, {replies['no']} Norwegian)")
    for name, c in sorted(s["topics"].items(), key=lambda kv: -sum(kv[1].values())):
        w(f"    {name:<30} {c['en'] + c['no']:4}  ({c['en']} + {c['no']})")
    w(f"\nKinds of answer respond() can give: {s['kinds']} "
      f"({s['intents']} small-talk intents, {s['encodings']} encodings)")
    return "\n".join(out)


# ================================================================== svgs ====
# Colours: the reference data-viz palette (one hue for ranked bars, the first
# five categorical slots for the segmented bar), light and dark.
THEMES = {
    "light": dict(surface="#fcfcfb", ring="rgba(11,11,11,0.10)", ink="#0b0b0b", ink2="#52514e",
                  muted="#898781", baseline="#c3c2b7", bar="#2a78d6",
                  slots=("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"),
                  on_slot=("#ffffff", "#ffffff", "#ffffff", "#0b0b0b", "#ffffff")),
    "dark": dict(surface="#1a1a19", ring="rgba(255,255,255,0.10)", ink="#f0efec", ink2="#c3c2b7",
                 muted="#898781", baseline="#383835", bar="#3987e5",
                 slots=("#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"),
                 on_slot=("#ffffff",) * 5),
}
FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
WIDTH = 880
PAD = 28


def text_width(s, size=13, bold=False):
    """A generous estimate of rendered width (no font metrics in the stdlib)."""
    narrow, wide = "iljtf.,:;'|!() ", "mwMW%@"
    em = sum(0.32 if c in narrow else 0.86 if c in wide else 0.62 if c.isupper() or c.isdigit() else 0.55
             for c in s)
    return em * size * (1.06 if bold else 1.0)


def fmt(n):
    return f"{n:,}"


def svg(height, title, desc, body, theme):
    th = THEMES[theme]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="t d" font-family="{FONT}">\n'
        f'<title id="t">{escape(title)}</title>\n<desc id="d">{escape(desc)}</desc>\n'
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="12" '
        f'fill="{th["surface"]}" stroke="{th["ring"]}"/>\n{body}</svg>\n')


def heading(title, subtitle, th):
    return (f'<text x="{PAD}" y="40" font-size="17" font-weight="600" fill="{th["ink"]}">{escape(title)}</text>\n'
            f'<text x="{PAD}" y="64" font-size="13" fill="{th["ink2"]}">{escape(subtitle)}</text>\n')


def bar_path(x0, y, length, h, r=4):
    """A horizontal bar: square at the baseline, 4px rounded data end."""
    r = min(r, length / 2, h / 2)
    x1 = x0 + length
    return (f"M{x0:.1f},{y:.1f}H{x1 - r:.1f}A{r},{r} 0 0 1 {x1:.1f},{y + r:.1f}"
            f"V{y + h - r:.1f}A{r},{r} 0 0 1 {x1 - r:.1f},{y + h:.1f}H{x0:.1f}Z")


def ranked_bars(rows, title, subtitle, theme, notes=None):
    """rows: [(label, value)], drawn largest first, every value at its tip."""
    th = THEMES[theme]
    rows = sorted(rows, key=lambda r: -r[1])
    notes = notes or {}
    label_w = max(text_width(label) for label, _ in rows) + 20
    x0 = PAD + label_w
    tip_room = max(text_width(fmt(v), bold=True) + text_width(notes.get(lbl, "")) + 18 for lbl, v in rows)
    span = WIDTH - PAD - x0 - tip_room
    top, row_h, bar_h = 92, 30, 16
    peak = max(v for _, v in rows)
    body = [heading(title, subtitle, th)]
    for i, (label, value) in enumerate(rows):
        y = top + i * row_h
        length = max(2.0, span * value / peak)
        mid = y + bar_h / 2
        body.append(f'<text x="{x0 - 12:.1f}" y="{mid:.1f}" dy="0.35em" text-anchor="end" font-size="13" '
                     f'fill="{th["ink2"]}">{escape(label)}</text>')
        body.append(f'<path d="{bar_path(x0, y, length, bar_h)}" fill="{th["bar"]}"/>')
        tip = f'<tspan font-weight="600" fill="{th["ink"]}">{fmt(value)}</tspan>'
        if label in notes:
            tip += f'<tspan fill="{th["muted"]}">  {escape(notes[label])}</tspan>'
        body.append(f'<text x="{x0 + length + 8:.1f}" y="{mid:.1f}" dy="0.35em" font-size="13">{tip}</text>')
    bottom = top + len(rows) * row_h - (row_h - bar_h)
    body.append(f'<line x1="{x0}" y1="{top - 6}" x2="{x0}" y2="{bottom + 6}" stroke="{th["baseline"]}"/>')
    height = bottom + PAD + 6
    desc = "; ".join(f"{label}: {value}" + (f" ({notes[label]})" if label in notes else "") for label, value in rows)
    return svg(height, f"{title}. {subtitle}", desc, "\n".join(body) + "\n", theme)


def segmented_bar(parts, title, subtitle, unit, theme):
    """One whole split into <= 5 parts: a tall segmented bar and a legend."""
    th = THEMES[theme]
    total = sum(v for _, v in parts)
    x, y, h, gap = PAD, 92, 28, 2
    usable = WIDTH - 2 * PAD - gap * (len(parts) - 1)
    body = [heading(title, subtitle, th)]
    for i, (label, value) in enumerate(parts):
        w = usable * value / total
        body.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h}" rx="4" fill="{th["slots"][i]}"/>')
        share = f"{100 * value / total:.0f}%"
        if text_width(share, bold=True) + 16 <= w:
            body.append(f'<text x="{x + 8:.1f}" y="{y + h / 2}" dy="0.35em" font-size="13" font-weight="600" '
                        f'fill="{th["on_slot"][i]}">{share}</text>')
        x += w + gap
    lx, ly = PAD, y + h + 34
    for i, (label, value) in enumerate(parts):
        item = f"{label} · {fmt(value)} {unit}"
        item_w = 18 + text_width(item) + 26
        if lx + item_w > WIDTH - PAD:
            lx, ly = PAD, ly + 26
        body.append(f'<rect x="{lx}" y="{ly - 9}" width="10" height="10" rx="2" fill="{th["slots"][i]}"/>')
        body.append(f'<text x="{lx + 18}" y="{ly - 4}" dy="0.35em" font-size="13" fill="{th["ink2"]}">'
                    f'{escape(label)} · <tspan fill="{th["ink"]}" font-weight="600">{fmt(value)}</tspan> {unit}</text>')
        lx += item_w
    height = ly + PAD
    desc = "; ".join(f"{label}: {value} {unit} ({100 * value / total:.0f}%)" for label, value in parts)
    return svg(height, f"{title}. {subtitle}", desc, "\n".join(body) + "\n", theme)


def stat_tiles(tiles, theme):
    """A row of headline numbers: label, value, a short caption."""
    th = THEMES[theme]
    n = len(tiles)
    tile_w = (WIDTH - 2 * PAD) / n
    body = []
    for i, (label, value, caption) in enumerate(tiles):
        x = PAD + i * tile_w + (0 if i == 0 else 20)
        if i:
            body.append(f'<line x1="{PAD + i * tile_w:.1f}" y1="26" x2="{PAD + i * tile_w:.1f}" y2="118" '
                        f'stroke="{th["baseline"]}"/>')
        body.append(f'<text x="{x:.1f}" y="44" font-size="13" fill="{th["ink2"]}">{escape(label)}</text>')
        body.append(f'<text x="{x:.1f}" y="88" font-size="38" font-weight="600" fill="{th["ink"]}">{escape(value)}</text>')
        body.append(f'<text x="{x:.1f}" y="112" font-size="12" fill="{th["muted"]}">{escape(caption)}</text>')
    desc = "; ".join(f"{label}: {value} ({caption})" for label, value, caption in tiles)
    return svg(144, "marvin-llm in numbers", desc, "\n".join(body) + "\n", theme)


def charts(s):
    replies = sum(s["topics"].values(), collections.Counter())
    in_ladder = sum(s["ifs"][f]["if"] + s["ifs"][f]["elif"] for f in ("respond", "_chat"))
    tiles = [
        ("Language models", "0", "no model, no API key"),
        ("if statements", fmt(s["if_statements"]), f"{in_ladder} in respond() and _chat()"),
        ("Regular expressions", fmt(s["regexes"]), f"{fmt(s['alternatives'])} alternatives"),
        ("Hand-written replies", fmt(replies["en"] + replies["no"]), f"{fmt(replies['en'])} per language"),
        ("Kinds of answer", fmt(s["kinds"]), "first matching rule wins"),
    ]
    by_function = [(f"{name}()" if not name.startswith("(") else name, c["if"] + c["elif"])
                   for name, c in s["ifs"].items() if c["if"] + c["elif"]]
    stage_rows = [(name, c["alternatives"] + c["keywords"]) for name, c in s["stages"].items()]
    stage_notes = {name: f"{fmt(c['alternatives'])} regex alternatives + {fmt(c['keywords'])} "
                         f"{STRING_NOUN.get(name, 'keywords')}"
                   for name, c in s["stages"].items() if c["alternatives"] and c["keywords"]}
    topic_rows = [(name, c["en"] + c["no"]) for name, c in s["topics"].items()]
    for theme in THEMES:
        yield f"numbers-{theme}.svg", stat_tiles(tiles, theme)
        yield f"lines-{theme}.svg", segmented_bar(
            [(label, s["line_kinds"][key]) for key, label in LINE_KINDS],
            "Where the lines of marvin.py go",
            f"{fmt(s['lines'])} lines. Over half is hand-written replies; "
            f"the logic is {100 * s['line_kinds']['logic'] / s['lines']:.0f}%", "lines", theme)
        yield f"ifs-{theme}.svg", ranked_bars(
            by_function, "if statements per function",
            f"{s['if_statements']} in all (if + elif); respond() and _chat() are the rule ladder every message climbs",
            theme)
        yield f"stages-{theme}.svg", ranked_bars(
            stage_rows, "What each stage looks for",
            "Regex alternatives plus plain strings, per step of the pipeline: the closest thing Marvin has to knowledge",
            theme, notes=stage_notes)
        yield f"replies-{theme}.svg", ranked_bars(
            topic_rows, "Hand-written reply lines, by what they are for",
            f"{fmt(replies['en'] + replies['no'])} lines: {fmt(replies['en'])} in English and the same "
            f"{fmt(replies['no'])} in Norwegian. Each answer picks one at random", theme)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--no-svg", action="store_true", help="only print the numbers")
    args = parser.parse_args()
    s = collect()
    print(report(s))
    if not args.no_svg:
        OUT.mkdir(exist_ok=True)
        for name, content in charts(s):
            (OUT / name).write_text(content, encoding="utf-8")
        print(f"\nwrote {OUT.relative_to(HERE.parent)}/*.svg")


if __name__ == "__main__":
    main()
