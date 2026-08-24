# Champion/challenger lifecycle

The local lifecycle layer separates immutable evidence from replaceable alias state.

## Evidence

Every promotion, rejection, review outcome, and rollback is represented by an immutable `PromotionDecision` in the filesystem registry. A decision records:

- exact candidate ID/version;
- exact evaluation run ID;
- exact promotion policy ID/version;
- accept, reject, or review outcome;
- reasons;
- incumbent candidate when one exists;
- lifecycle channel and action metadata.

Existing decision IDs cannot be overwritten because they use the registry's immutable write path.

## Promotion policies

`PromotionPolicy` is versioned independently by `policy_id` and `version`. Saved policy versions are immutable. Policies compose the deterministic `MetricGate` type from the evaluation engine and may additionally require human review.

A policy can gate absolute values, regression versus incumbent evidence, protected slices, and calibration metrics using the same metric-gate mechanics as evaluation comparison.

## Champion alias

The current champion is a small replaceable pointer under `lifecycle/channels/<channel>.json`. It contains the candidate reference plus the exact accepted decision and evaluation run supporting that alias.

The alias moves only after an `ACCEPT` decision has been persisted successfully. `REJECT` and `REVIEW` decisions remain in history but leave the alias unchanged.

Once a channel has a champion, an attempted promotion without incumbent evaluation evidence produces `REVIEW`; it cannot silently promote a challenger without comparison evidence.

## Rollback

Rollback does not edit or delete prior history. It:

1. verifies the target candidate was previously accepted in the same lifecycle channel;
2. verifies the supplied evaluation run references that candidate;
3. appends a new accepted `PromotionDecision` with action `rollback`;
4. updates the champion alias to the target.

This preserves the complete sequence of lifecycle decisions while allowing local state to return to an earlier champion.

## Human review

When `require_human_review` is enabled, a challenger that otherwise satisfies deterministic gates receives a `REVIEW` decision. The local lifecycle does not infer human approval or mutate the alias on that path. A future human-approval workflow can append a separate acceptance decision rather than rewriting the review record.
