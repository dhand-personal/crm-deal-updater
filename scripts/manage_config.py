#!/usr/bin/env python3
"""Read and write the crm-deal-updater config.

The config lives at ~/.crm-deal-updater/config.json (override with the
CRM_DEAL_UPDATER_CONFIG env var). It holds one entry per CRM instance,
keyed "<crm>:<instance>", for example "hubspot:12345678",
"salesforce:00D5g000001abcd", or, in snapshot mode, a name the rep
chooses such as "other:acme-pipedrive".

Snapshot mode has no internal names or stored values, only labels. Use
the label as "value" for pipelines and stages and as "name" for fields.

Usage:
  manage_config.py --list
  manage_config.py --show --crm hubspot --instance 12345678
  manage_config.py --init --crm hubspot --instance 12345678 --json setup.json
  manage_config.py --set  --crm hubspot --instance 12345678 \
      --path audit_note --value false
  manage_config.py --template          # print an empty instance entry

--json and --value accept a file path or a literal JSON string.
--path is dotted; list items are addressed by index
(e.g. "field_map.3.field.label"). An index one past the end appends.

Exit codes: 0 ok, 1 not found, 2 invalid input.

Instance entry shape (see --template):
{
  "crm": "hubspot" | "salesforce" | "other",
  "crm_name": "<display name, e.g. Pipedrive; required when crm is other>",
  "access": "connector" | "snapshot",
  "notes_location": "<snapshot mode: where notes go, e.g. 'Notes column'>",
  "instance": "<account or org id, or a rep-chosen name in snapshot mode>",
  "rep": {"id": "...", "name": "..."},
  "methodology": ["MEDDPICC", "Command of the Message"],
  "audit_note": true,
  "pipelines": [
    {
      "value": "<stored pipeline id or record type id>",
      "label": "New Business",
      "record_type": null,
      "stages": [
        {
          "value": "<stored stage value>",
          "label": "Discovery",
          "order": 1,
          "probability": 0.1,
          "closed": false,
          "exit_criteria": [{"text": "...", "origin": "crm" | "proposed" | "rep"}],
          "required_fields": ["<internal field name>"],
          "side_effects": ["..."]
        }
      ]
    }
  ],
  "field_map": [
    {
      "methodology": "MEDDPICC",
      "element": "Economic Buyer",
      "field": {"name": "<internal>", "label": "Economic Buyer",
                "type": "long_text", "length": 32000}
    },
    {
      "methodology": "Standard",
      "element": "Next Step",
      "field": {"name": "hs_next_step", "label": "Next step",
                "type": "short_text", "length": 255, "status_field": true}
    }
  ],
  "unmapped_elements": [{"methodology": "MEDDPICC", "element": "Paper Process"}],
  "ignored_fields": ["<internal field name>"],
  "deals": {
    "<deal slug>": {
      "deal": "<deal label>",
      "last_run": "<ISO date>",
      "processed_through": "<full ISO timestamp of newest source used>",
      "approved": [{"field": "<label>", "action": "update|add_to|replace|review",
                    "text": "<exact text or new value>"}],
      "stage_to": "<stage label or null>",
      "declined": [{"item": "<field label, 'Stage', or 'Evidence note'>",
                    "text": "<proposed text, value, or stage label>",
                    "date": "<ISO date declined>"}]
    }
  },
  "updated_at": "<ISO timestamp>"
}

"deals" is used in snapshot mode, where the skill can't confirm what the
rep entered. Use a slug without dots (e.g. "larkspur-freight-pick-path").
"approved", "stage_to", "last_run", and "processed_through" hold only the
latest run; "declined" accumulates across runs. After each run:

  First run on a deal (no deals.<slug> yet): save the whole object once
    --set --path deals.<slug> --value '<json with "declined": [...]>'
  Later runs: update the run fields one at a time, never the whole object
    --set --path deals.<slug>.approved --value '[...]'
    --set --path deals.<slug>.stage_to --value '"<label>"' (or null)
    --set --path deals.<slug>.last_run --value '"<ISO date>"'
    --set --path deals.<slug>.processed_through --value '"<timestamp>"'
  then add each new decline at the end of the list (index = current length)
    --set --path deals.<slug>.declined.<n> --value '{"item": ..., "text": ..., "date": ...}'

Compare the saved list against the next snapshot.

Standard deal fields that aren't methodology elements (Close Date,
Amount, Next Step, Forecast Category) go in "field_map" with
"methodology": "Standard" and the field's own name as "element". Mark
status fields such as Next Step with "status_field": true.

Field "type" uses the normalized names from field-rules.md:
short_text, long_text, rich_text, picklist, multi_select, checkbox,
number, date, lookup.
"""

import argparse
import datetime as dt
import json
import os
import sys

CRMS = {"hubspot", "salesforce", "other"}
ACCESS = {"connector", "snapshot"}
FIELD_TYPES = {"short_text", "long_text", "rich_text", "picklist",
               "multi_select", "checkbox", "number", "date", "lookup"}
ORIGINS = {"crm", "proposed", "rep"}


def config_path():
    return os.environ.get(
        "CRM_DEAL_UPDATER_CONFIG",
        os.path.join(os.path.expanduser("~"), ".crm-deal-updater", "config.json"),
    )


def load():
    path = config_path()
    if not os.path.exists(path):
        return {"version": 1, "instances": {}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(cfg):
    path = config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def read_json_arg(value):
    if os.path.exists(value):
        with open(value, encoding="utf-8") as f:
            return json.load(f)
    return json.loads(value)


def key(crm, instance):
    return f"{crm}:{instance}"


def template(crm="hubspot", instance=""):
    return {
        "crm": crm,
        "crm_name": {"hubspot": "HubSpot", "salesforce": "Salesforce"}.get(crm, ""),
        "access": "connector" if crm in ("hubspot", "salesforce") else "snapshot",
        "instance": instance,
        "rep": {"id": "", "name": ""},
        "methodology": [],
        "audit_note": True,
        "notes_location": "",
        "pipelines": [],
        "field_map": [],
        "unmapped_elements": [],
        "ignored_fields": [],
        "deals": {},
        "updated_at": "",
    }


def validate(entry):
    """Return a list of problems. Empty list means valid."""
    problems = []
    if entry.get("crm") not in CRMS:
        problems.append(f"crm must be one of {sorted(CRMS)}")
    if not entry.get("instance"):
        problems.append("instance is required")
    if entry.get("access") not in ACCESS:
        problems.append(f"access must be one of {sorted(ACCESS)}")
    if entry.get("crm") == "other":
        if not entry.get("crm_name"):
            problems.append("crm_name is required when crm is other")
        if entry.get("access") != "snapshot":
            problems.append("crm other only supports access snapshot")
    if not isinstance(entry.get("methodology"), list) or not entry["methodology"]:
        problems.append("methodology must be a non-empty list")
    if not isinstance(entry.get("audit_note"), bool):
        problems.append("audit_note must be true or false")
    if not isinstance(entry.get("deals", {}), dict):
        problems.append("deals must be an object keyed by deal slug")

    pipelines = entry.get("pipelines") or []
    if not pipelines:
        problems.append("at least one pipeline is required")
    for p_i, p in enumerate(pipelines):
        where = f"pipelines[{p_i}]"
        for k in ("value", "label"):
            if not p.get(k):
                problems.append(f"{where}.{k} is required")
        stages = p.get("stages") or []
        if not stages:
            problems.append(f"{where} has no stages")
        orders = []
        for s_i, s in enumerate(stages):
            sw = f"{where}.stages[{s_i}]"
            for k in ("value", "label"):
                if not s.get(k):
                    problems.append(f"{sw}.{k} is required")
            if not isinstance(s.get("order"), int):
                problems.append(f"{sw}.order must be an integer")
            else:
                orders.append(s["order"])
            if not isinstance(s.get("closed"), bool):
                problems.append(f"{sw}.closed must be true or false")
            for c in s.get("exit_criteria") or []:
                if not c.get("text"):
                    problems.append(f"{sw} has an exit criterion with no text")
                if c.get("origin") not in ORIGINS:
                    problems.append(f"{sw} exit criterion origin must be one of {sorted(ORIGINS)}")
        if len(orders) != len(set(orders)):
            problems.append(f"{where} has duplicate stage order numbers")

    names = set()
    for f_i, m in enumerate(entry.get("field_map") or []):
        where = f"field_map[{f_i}]"
        if not m.get("element"):
            problems.append(f"{where}.element is required")
        field = m.get("field") or {}
        for k in ("name", "label"):
            if not field.get(k):
                problems.append(f"{where}.field.{k} is required")
        if field.get("type") not in FIELD_TYPES:
            problems.append(f"{where}.field.type must be one of {sorted(FIELD_TYPES)}")
        names.add(field.get("name"))

    for p in pipelines:
        for s in p.get("stages") or []:
            for rf in s.get("required_fields") or []:
                if rf not in names:
                    problems.append(
                        f"required field '{rf}' on stage '{s.get('label')}' is not in field_map "
                        "(add it to field_map so the skill can read and fill it)"
                    )
    return problems


def resolve(obj, dotted):
    parts = dotted.split(".")
    for part in parts[:-1]:
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj, parts[-1]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true")
    mode.add_argument("--show", action="store_true")
    mode.add_argument("--init", action="store_true")
    mode.add_argument("--set", action="store_true")
    mode.add_argument("--template", action="store_true")
    ap.add_argument("--crm", choices=sorted(CRMS))
    ap.add_argument("--instance")
    ap.add_argument("--json")
    ap.add_argument("--path")
    ap.add_argument("--value")
    args = ap.parse_args()

    if args.template:
        print(json.dumps(template(args.crm or "hubspot", args.instance or ""), indent=2))
        return 0

    cfg = load()

    if args.list:
        if not cfg["instances"]:
            print("No CRM instances configured.")
            return 1
        for k, e in cfg["instances"].items():
            print(f"{k}\t{', '.join(e.get('methodology', []))}\tupdated {e.get('updated_at', '')}")
        return 0

    if not args.crm or not args.instance:
        print("--crm and --instance are required", file=sys.stderr)
        return 2
    k = key(args.crm, args.instance)

    if args.show:
        entry = cfg["instances"].get(k)
        if entry is None:
            print(f"NOT_CONFIGURED {k}", file=sys.stderr)
            return 1
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return 0

    if args.init:
        if not args.json:
            print("--init needs --json", file=sys.stderr)
            return 2
        entry = template(args.crm, args.instance)
        entry.update(read_json_arg(args.json))
        entry["crm"], entry["instance"] = args.crm, args.instance
        entry["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        problems = validate(entry)
        if problems:
            print("Config not saved. Problems:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 2
        cfg["instances"][k] = entry
        save(cfg)
        print(f"Saved {k} to {config_path()}")
        return 0

    if args.set:
        entry = cfg["instances"].get(k)
        if entry is None:
            print(f"NOT_CONFIGURED {k}", file=sys.stderr)
            return 1
        if not args.path or args.value is None:
            print("--set needs --path and --value", file=sys.stderr)
            return 2
        candidate = json.loads(json.dumps(entry))
        candidate.setdefault("deals", {})
        try:
            parent, last = resolve(candidate, args.path)
            value = read_json_arg(args.value)
            if isinstance(parent, list):
                i = int(last)
                if i == len(parent):
                    parent.append(value)   # index one past the end appends
                else:
                    parent[i] = value
            else:
                parent[last] = value
        except (KeyError, IndexError, ValueError, TypeError) as e:
            print(f"Bad --path or --value: {e}", file=sys.stderr)
            return 2
        problems = validate(candidate)
        if problems:
            print("Change not saved. Problems:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 2
        candidate["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        cfg["instances"][k] = candidate
        save(cfg)
        print(f"Updated {args.path} for {k}")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
