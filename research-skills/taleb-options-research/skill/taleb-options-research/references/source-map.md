# Source map

Use stable IDs and locators to navigate evidence. These entries are not download links.

| Source ID | Primary research role | Locator convention |
|---|---|---|
| `XZ-E43` | Xu Zhe interview claims, structure hints, roll ambiguity | timestamp range |
| `DH-PDF-1997` | option structure, Greeks, path, execution, compound and exotic contracts | physical/printed page |
| `TALEB-ANTIFRAGILE` | convexity, optionality, barbell, model fragility | chapter/page anchor |
| `TALEB-BLACK-SWAN` | tail uncertainty and model-extrapolation limits | chapter/physical/printed page |
| `TALEB-FOOLED` | selection, luck, path, sampling and multiplicity | chapter/physical/printed page |
| `TALEB-SKIN` | ruin, time probability, incentives and account survival | chapter/page anchor |
| `SCOFT-3E-2025` | preasymptotics, fat-tail estimation, option-price measures, hedge error, dependence and tail constraints | physical PDF page/chapter/equation/figure |
| `CROSS-SOURCE` | project-authored formulas and governance synthesis | stable record ID |

Search examples:

```text
rg '"claim_id":"XZ-D-03"' references/claim-registry.release.jsonl
rg '"formula_id":"DH-A-WING-PAYOFF-01"' references/formula-registry.release.jsonl
rg '"rule_id":"RULE-SCOFT-PREASYMPTOTIC-01"' references/rule-registry.release.jsonl
rg '"family":"F3"' references/rule-registry.release.jsonl
```
