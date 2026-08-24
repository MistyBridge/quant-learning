# Evidence and parameter governance

## Contents

1. Evidence levels
2. Release record contract
3. Parameter status
4. Conflict and withholding
5. BYOS verification

## 1. Evidence levels

- `D`: direct statement or unambiguous source record with locator.
- `B`: source-supported interpretation that does not fully determine a strategy.
- `C`: cross-source synthesis; never attribute the synthesis to one author.
- `A`: independently derived or recomputed formula/result with stated assumptions.
- `U`: unresolved, contradictory, missing, or not safely inferable.

Do not upgrade evidence without a source ID and locator. A precise locator does not turn an interpretation into a direct quotation.

## 2. Release record contract

The public registries contain project-authored summaries, mathematical expressions, evidence levels, locators, limitations, and stable IDs. They do not contain original books, full OCR, page images, or audio.

Use:

- `claim-registry.release.jsonl` for propositions and limitations;
- `formula-registry.release.jsonl` for expressions, assumptions, and anomaly status;
- `visual-registry.release.jsonl` for what a source visual supports or does not support;
- `rule-registry.release.jsonl` for candidate and hard-guardrail rules.

Treat `WITHHELD_FROM_PUBLIC_RELEASE` as an auditable record, not as evidence. Keep referenced withheld IDs unresolved.

## 3. Parameter status

- `CONTRACT`: definition required to identify payoff or settlement.
- `LITERATURE`: source example or context; never a production default.
- `CALIBRATE`: estimate only from declared point-in-time training data.
- `USER_POLICY`: risk budget or preference only the user can set.
- `STRESS`: deliberately chosen scenario, not an empirical estimate.
- `MISSING_FROM_SOURCE`: the source does not provide a value.
- `UNKNOWN`: unresolved or contradictory.

For `MISSING_FROM_SOURCE` and `UNKNOWN`, keep `source_value=null` unless recording the conflicting alternatives. Do not fill a blank with market convention.

## 4. Conflict and withholding

Preserve source anomalies and disagreements:

- record the competing interpretations;
- record the locator and verification status;
- show which strategy field depends on the conflict;
- prevent execution or higher decision states until resolved.

The E43 replacement-put buy/sell action is `U`. Do not resolve it through majority OCR, contextual intuition, or a profitability argument.

Public summaries are length-limited. A record that cannot be safely summarized retains its ID with `release_status=WITHHELD_FROM_PUBLIC_RELEASE`.

## 5. BYOS verification

BYOS means the user supplies a legally obtained local edition. The local index:

- computes SHA-256 for that specific file;
- records source ID, format, size, and local path;
- compares source ID and supported format with the public manifest;
- reports `AVAILABLE_UNVERIFIED_EDITION`, `MISMATCH`, or `UNKNOWN_SOURCE`;
- never promotes a user file hash into a universal canonical hash.

The local evidence cache may contain user-specific page/OCR mappings. Store it outside the Skill and public repository. Never upload it.

Without BYOS, cite release summaries as project evidence and say that the original page was not directly re-checked in the current session.

For `SCOFT-3E-2025`, edition-sensitive equations and visuals use physical PDF-page locators. The public Skill includes only transformed summaries, expressions, limitations, and visual metadata. Keep the Third Edition PDF, EPUB, full OCR, page images, source hashes, and manual-review manifests in the user's private evidence layer.
