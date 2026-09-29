# Field rules

How each proposed change is classified, formatted, and checked before
it reaches the review table. Field types are normalized to the "Treat
as" column in `crm-hubspot.md` or `crm-salesforce.md`.

## Actions

| Action | Meaning | Bulk approval? |
|---|---|---|
| Update | Field is empty; write the new value | Yes |
| Add to | Text field has content; append a new entry | Yes |
| Keep | Existing value already says it; write nothing | n/a |
| Replace | Non-text field; swap the old value for a new one | No, one at a time |
| Review | Conflict, or an append that won't fit; rep decides what to write | No, one at a time |
| Can't update | Rep lacks permission or the field is read-only | n/a |

## Placeholder values

Fields often hold filler instead of real content: "Yes", ".", "-",
"TBD", "To be added", "Unknown", "N/A", "none", "see notes".
`append_entry.py check` flags these as `existing_is_placeholder`.

- Don't append under a placeholder. "Yes" followed by a dated entry
  reads badly and helps no one.
- Don't treat it as empty either. Someone typed it, and it may mean
  something.
- Propose a **Review** replacement, one field at a time, showing the old
  value and the new one. Never bulk-approvable.
- If the placeholder could be a real answer to the field's question,
  keep its meaning in the new text. A "Pricing Review" field holding
  "Yes" likely means pricing was reviewed, so the replacement starts
  with that: "Yes, reviewed. [2026-09-22 | Call w/ R. Carter] Budget
  flat vs last year; must stay under $40K with added devices."
- The old value goes in the audit note, like any replacement.

## By field type

**Long text and rich text**
- Empty: Update with one entry.
- Has content: Add to with a new entry, unless the duplicate check says
  it's already there (then Keep).
- New evidence contradicts an earlier entry: Review. Show both. The rep
  can choose to append a correcting entry (usual) or, with explicit
  approval, replace the whole field.

**Short text (255 characters or a single-line field)**
- Empty: Update.
- Has content and the entry fits: Add to.
- Some single-line fields can't hold line breaks (Salesforce `Text`,
  verified: a break is stored as a space). There, join the new entry to
  the existing text with a single space; its date tag marks where it
  starts. Run `append_entry.py check --single-line` so the length and
  duplicate checks match what will be stored. HubSpot single-line text
  fields kept line breaks in testing.
- Won't fit: Review, with a proposed condensed version of the whole
  field that keeps the existing facts. Never drop the rep's existing
  facts without showing exactly what's being removed.

**Status fields (Next Step, and any text field the rep says holds only
the current status)**
- Appending makes these read like a history, which isn't their job.
  Propose the new status as a Review replacement, showing the old text,
  approved on its own. The old status is kept in the audit note.

**Picklist, checkbox, number, date, lookup**
- Empty: Update (bulk-approvable, since nothing is overwritten).
- Has a value the evidence says is wrong or out of date: Replace. Show
  old and new, with the source. Picklists offer only options that exist
  in the field.
- Evidence is ambiguous: don't propose. Mention it under Gaps if it
  matters.

**Multi-select**
- Adding an option: Add to.
- Removing an option: Replace.

## Append entry format

**Match the field first.** If the field already has dated entries in a
format of its own, new entries follow that format so the field reads
consistently. `append_entry.py check` reports the field's
`existing_style`:

- `date-paren` (for example "2026-05-19 (discovery): ..."): format the
  new entry the same way with `append_entry.py format --style
  date-paren`.
- Another dated format the script doesn't recognize: copy it by hand
  and say so in the review.
- `default`, `none` (free text with no dated entries), or `empty`: use
  the skill's default format below.

Never reformat existing entries to match the new one.

Default format, one entry per append, on its own line (plain text) or
paragraph (rich text):

```
[YYYY-MM-DD | Source] Text of the entry.
```

- Date is the date of the source record, not today.
- Source is short: `Call w/ J. Rivera`, `Email from CFO`, `Rep notes`,
  `Internal thread`. Several sources: `Call 9/18 + email 9/20`.
- Text is one to three sentences. Concrete. Customer wording where it
  carries the point.
- Newest entry goes at the bottom, so the field reads as a timeline.
  (If the existing field clearly runs newest-first, follow that instead
  and say so.)
- Never edit or reformat existing entries or the rep's own text.

Example, for a field labeled "Decision Process":

```
Security review, then procurement. PO required.
[2026-09-18 | Call w/ D. Okafor] Security review takes about two weeks; their team starts once the questionnaire is back.
[2026-09-22 | Email from procurement] Procurement needs a signed MSA before issuing the PO; typical turnaround is 5 business days.
```

## Duplicate check

Before proposing an Add to, run `scripts/append_entry.py check` with the
existing field text and the new entry. It flags:
- the same source tag and date already present, and
- an existing line whose wording closely overlaps the new text.

A flagged entry becomes Keep unless it adds a real detail the existing
text lacks (a number, a name, a date). If it does, trim the entry to
just the new detail.

## Length check

`append_entry.py` also compares the combined length against the field's
limit from the schema. If it won't fit, the item becomes Review with a
condensed proposal. Never let the CRM truncate text silently.

## Values the rep edits

If the rep rewrites a proposed value in the review, their wording wins.
Keep the date and source tag unless they remove it.
