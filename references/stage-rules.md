# Stage rules

How the skill decides whether to suggest a stage change. The saved map
(from setup) supplies each stage's exit criteria and required fields.
HubSpot doesn't expose required stage fields, and Salesforce does only
through Headless 360 (validation rules and Path); either way, the
confirmed map is the source of truth.

## Inputs

- Current stage and its position in the confirmed order.
- Exit criteria for the current stage, the previous stage, and the next
  stage.
- Required fields to enter the next stage (and the current one, for
  backward checks).
- The evidence gathered this run, plus what's already in the mapped
  fields.

## Stages with no exit criteria

If the current stage has no exit criteria in the map, don't suggest
moving forward out of it. Say the stage has no criteria yet and offer to
add some. Backward moves into it are still possible.

## No change (the most common outcome)

Say "Stage looks right" with one sentence on why, and name the one or
two criteria still open for the next stage. That's useful coaching.

## Forward move

Suggest moving forward one stage only when **every** exit criterion for
the current stage is met by sourced evidence (this run or already in the
record). Show each criterion:

```
Stage: Discovery -> Solution Validation (suggested)
  Pain confirmed and quantified   yes  Call 9/18: "we lose about 30 hours a sprint on this"
  Economic buyer identified       yes  Email 9/20 from VP Finance
  Next meeting agreed             yes  Call 9/18: demo booked for 9/30
```

- Never skip stages, even if the evidence supports a later one. Suggest
  the next stage and note that later criteria look met too.
- If one criterion is thin (rep notes only, or internal context only),
  say so. The rep decides.

## Backward move

Suggest moving back only when a specific exit criterion the deal
already passed, as the company wrote it in the saved map, clearly no
longer holds, based on specific evidence. Name that criterion.

Events never trigger a backward move on their own. A champion leaving,
a reorg, a new executive, a budget change, or a reopened decision is
evidence to check against the saved criteria, nothing more. If none of
the passed criteria mentions what changed, the deal stays where it is
and the event shows up as a risk in the review (under the stage section
or Gaps), along with any criterion for the next stage it reopens.

Example: a champion leaves. If the company's criteria for an earlier
stage include "champion identified," that criterion no longer holds and
a backward move can be suggested. If "champion" only appears in the
current stage's criteria (or nowhere), the deal stays, and the review
says the criterion is open again.

Criteria that are uncertain rather than clearly broken (a meeting
cancelled with nothing rescheduled, a slow reply) don't count toward a
backward move. Show them as "unclear" in the criteria table.

State the reason in one sentence and cite the source. General
pessimism, a slow reply, or a missed meeting is not enough; mention it
under Gaps instead.

Move back to the latest stage whose exit criteria still hold, not
further.

## A move the rep already declined

Forward or backward, a declined move comes back only when new evidence
changes an exit criterion's status: not met to met, or met to broken.
New evidence that only reinforces a criterion already met (a budget
confirmed again, a sign-off put in writing) doesn't count. Mention the
move in one line instead: "Perception Analysis still looks met; you
passed on it 9/24."

## Required fields for the target stage

Before proposing any move:

1. List the target stage's required fields from the map.
2. For each empty one: if there's evidence, include an Update for it in
   the same review, linked to the stage change. If not, list it as
   missing.
3. If anything is still missing, the write will fail (a Salesforce
   validation rule or a HubSpot stage rule, both verified). Say which
   field is missing and don't propose the move yet.
4. If a write fails anyway because of a requirement the map didn't
   have, explain it in plain words and, with the rep's OK, add it to the
   saved map (details in each CRM reference file).

The rep can override by giving the missing value themselves in the
conversation (it becomes a "rep notes" source).

## Side effects to show

- Win probability that changes with the stage (HubSpot stage
  probability; Salesforce `DefaultProbability`).
- Forecast category (Salesforce `ForecastCategoryName`, or HubSpot's
  forecast category if the account uses it).
- Anything else the rep said in setup changes with stage (an automated
  email, a handoff task, a notification to a manager).

## Never

- Propose a closed stage (won or lost).
- Propose a stage in a different pipeline, or one outside the deal's
  record type's sales process.
- Bundle the stage change into a bulk approval.
- Write the stage before the fields it depends on.

## Closed-lost signals

If the evidence strongly suggests the deal is dead (the customer chose
another vendor, the project was cancelled), say so plainly at the top
of the review with the source, and suggest the rep talk with their
manager. Don't propose the move.
