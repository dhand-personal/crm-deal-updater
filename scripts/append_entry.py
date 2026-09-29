#!/usr/bin/env python3
"""Format an append entry and check it against a field's existing text.

Subcommands:

  format  Build one entry. Default style is "[date | source] text".
          append_entry.py format --date 2026-09-18 --source "Call w/ J. Rivera" \
              --text "Security review takes about two weeks." [--rich] \
              [--style default|date-paren]
          date-paren gives "2026-09-18 (Call w/ J. Rivera): text", for fields
          that already use that convention (see "existing_style" below).

  check   Compare a new entry to the existing field text. Add --single-line
          for fields that can't hold line breaks (Salesforce Text): entries
          are then joined with a space, and entries that already run
          together on one line are still told apart by their date tags.
          Prints JSON:
          {
            "duplicate": bool,        # likely already recorded
            "reasons": [...],         # why it was flagged
            "combined_text": "...",   # what the field would hold after append
            "combined_length": int,
            "limit": int | null,
            "fits": bool,
            "existing_is_placeholder": bool,  # "Yes", ".", "TBD", "To be added"...
            "existing_style": "empty" | "default" | "date-paren" | "none"
          }
          existing_style tells you which entry format the field already
          uses, so new entries can match it. "none" means free text with
          no dated entries; use the default style.
          append_entry.py check --entry "[2026-09-18 | Call w/ J. Rivera] ..." \
              (--existing "text" | --existing-file path | --existing-file - for stdin) \
              [--limit 32000] [--rich] [--threshold 0.5]

Duplicate rules:
  1. The same "[date | source]" tag already appears in the existing text,
     and the entry text overlaps with that line.
  2. Any existing line (tags stripped) overlaps the new entry text at or
     above the threshold (see overlap() for how the score is computed).

No existing text given means the field is empty.

This is a guard, not a judge. A flagged entry can still be proposed if
it adds a real new detail; SKILL.md and field-rules.md explain how.
"""

import argparse
import difflib
import html
import json
import re
import sys

TAG_RE = re.compile(r"^\s*\[(\d{4}-\d{2}-\d{2})\s*\|\s*([^\]]+)\]\s*")
# "2026-05-19 (discovery): text" and "2026-05-19 - Call: text" style entries
ALT_TAG_RE = re.compile(r"^\s*(\d{4}-\d{2}-\d{2})(?:/[\d-]+)?\s*(?:\(([^)]*)\)|[-:]\s*([^:]{1,40}))?\s*:\s*")
PLACEHOLDERS = {"yes", "no", "y", "n", "tbd", "tba", "to be added", "to be determined",
                "unknown", "n/a", "na", "none", "null", "-", "--", ".", "..", "...",
                "?", "x", "see notes", "pending", "todo", "to do"}
WORD_RE = re.compile(r"[a-z0-9$%.]+")
STOP = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is",
        "are", "was", "were", "be", "it", "that", "this", "with", "they",
        "their", "we", "our", "as", "at", "by", "from", "about",
        # hedges that change wording without changing the fact
        "still", "around", "roughly", "approximately", "approx", "nearly",
        "some", "currently", "now"}
CLAUSE_RE = re.compile(r";\s+|(?<=[a-z0-9%)])\.\s+")


def format_entry(date, source, text, rich=False, style="default"):
    text = " ".join(text.split())
    source = " ".join(source.split())
    if style == "date-paren":
        entry = f"{date} ({source}): {text}"
    else:
        entry = f"[{date} | {source}] {text}"
    if rich:
        return f"<p>{html.escape(entry)}</p>"
    return entry


def strip_html(s):
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s)


def normalize(s):
    s = s.lower()
    s = re.sub(r"(\d)\s*(percent|pct)\b", r"\1%", s)
    s = re.sub(r"\bper\s*cent\b", "%", s)
    return s


def words(s):
    return {w.strip(".") for w in WORD_RE.findall(normalize(s))} - STOP - {""}


def clauses(text):
    """Split a line into clauses so one fact isn't diluted by others."""
    parts = [c.strip() for c in CLAUSE_RE.split(text) if c.strip()]
    return parts or [text]


def split_tag(line):
    m = TAG_RE.match(line)
    if m:
        return (m.group(1), m.group(2).strip().lower()), line[m.end():].strip()
    m = ALT_TAG_RE.match(line)
    if m:
        src = (m.group(2) or m.group(3) or "").strip().lower()
        return (m.group(1), src), line[m.end():].strip()
    return None, line.strip()


def is_placeholder(text):
    """True for filler like "Yes", ".", "TBD", "To be added"."""
    t = " ".join(text.split()).strip().lower().rstrip(".!")
    if not text.strip():
        return False
    if t in PLACEHOLDERS or text.strip() in PLACEHOLDERS:
        return True
    return not re.search(r"[a-z0-9]", t)


def existing_style(text):
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return "empty"
    if any(TAG_RE.match(ln) for ln in lines):
        return "default"
    if any(ALT_TAG_RE.match(ln) for ln in lines):
        return "date-paren"
    return "none"


def overlap(a, b):
    """Similarity score between 0 and 1.

    Word-set Jaccard, raised to the containment score when the shorter
    text has at least 4 content words and nearly all of them appear in
    the longer one, or to the character similarity when that is very
    high (near-identical wording).
    """
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return 0.0
    inter = len(wa & wb)
    score = inter / len(wa | wb)
    shorter = min(len(wa), len(wb))
    if shorter >= 4 and inter / shorter >= 0.8:
        score = max(score, inter / shorter)
    seq = difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
    if seq >= 0.85:
        score = max(score, seq)
    return score


ENTRY_START = re.compile(r"(?=\[\d{4}-\d{2}-\d{2} \|)|(?<=\s)(?=\d{4}-\d{2}-\d{2} \()")


def split_entries(text):
    """Split field text into entries: by line, and also where a dated
    entry starts mid-line (single-line fields join entries with a space)."""
    out = []
    for ln in text.splitlines():
        out.extend(p for p in ENTRY_START.split(ln))
    return [p for p in out if p.strip()]


def check(existing, entry, limit=None, rich=False, threshold=0.5, single_line=False):
    existing = existing or ""
    plain_existing = strip_html(existing) if rich else existing
    plain_entry = strip_html(entry) if rich else entry

    new_tag, new_text = split_tag(plain_entry.strip())
    reasons = []

    for line in split_entries(plain_existing):
        tag, text = split_tag(line)
        score = max([overlap(new_text, text)] +
                    [overlap(new_text, c) for c in clauses(text)])
        if new_tag and tag == new_tag and score >= threshold / 2:
            reasons.append(f"same source tag already present: {line.strip()[:120]}")
        elif score >= threshold:
            reasons.append(f"overlaps existing line ({score:.2f}): {line.strip()[:120]}")

    if rich:
        combined = existing + entry
    elif single_line:
        combined = (existing.strip() + " " + entry) if existing.strip() else entry
    else:
        combined = (existing.rstrip("\n") + "\n" + entry) if existing.strip() else entry

    fits = True if limit is None else len(combined) <= limit
    return {
        "existing_is_placeholder": is_placeholder(plain_existing),
        "existing_style": existing_style(plain_existing),
        "duplicate": bool(reasons),
        "reasons": reasons,
        "combined_text": combined,
        "combined_length": len(combined),
        "limit": limit,
        "fits": fits,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("format")
    f.add_argument("--date", required=True)
    f.add_argument("--source", required=True)
    f.add_argument("--text", required=True)
    f.add_argument("--rich", action="store_true")
    f.add_argument("--style", choices=["default", "date-paren"], default="default")

    c = sub.add_parser("check")
    c.add_argument("--entry", required=True)
    g = c.add_mutually_exclusive_group()
    g.add_argument("--existing")
    g.add_argument("--existing-file")
    c.add_argument("--limit", type=int)
    c.add_argument("--rich", action="store_true")
    c.add_argument("--threshold", type=float, default=0.5)
    c.add_argument("--single-line", action="store_true",
                   help="field can't hold line breaks (Salesforce Text): join entries with a space")

    args = ap.parse_args()

    if args.cmd == "format":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
            print("--date must be YYYY-MM-DD", file=sys.stderr)
            return 2
        print(format_entry(args.date, args.source, args.text, args.rich, args.style))
        return 0

    if args.existing is not None:
        existing = args.existing
    elif args.existing_file == "-":
        existing = sys.stdin.read()
    elif args.existing_file:
        with open(args.existing_file, encoding="utf-8") as fh:
            existing = fh.read()
    else:
        existing = ""
    result = check(existing, args.entry, args.limit, args.rich, args.threshold,
                   single_line=args.single_line)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
