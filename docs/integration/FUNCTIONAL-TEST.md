# HuellaX integrated functional test (Ego)

Date: 2026-11-15  
Environment: local sandbox, ports DB 8907 / app 8900 / view 8944 / B 8949 / C 8950 / cover 8945  
Source: integration `develop` (MoveScope primary + AstroNova legacy)

## Results

| Area | Result |
|---|---|
| Launcher | **6/6 healthy** |
| Cover EN default | PASS; GitHub/App/View/Legacy links present |
| Cover ES switch | PASS; `?lang=es`, title/URL updated |
| MoveScope EN/ES | PASS; EN default, ES selector, no visible CJK |
| Barnard analysis | PASS; `REAL`, 4 epochs, `L`, `catalog_prior`, Gaia known |
| A batch | PASS; 130 known / 36 ambiguous / 45 no_match / 4 insufficient |
| C batch | PASS; 61 known / 9 ambiguous / 41 no_match |
| Cascade mode | PASS; same canvas; L1/masked/residual counts |
| Tracks mode | PASS; D0 45 / D1 11 / D2 0 / D3 5 / D4 189, total 250 |
| Unified directory | PASS; 467 rows / 217 unique sources / 250 tracks; 131 known / 36 ambiguous / 46 no_match / 4 insufficient / 0 conflict |
| Sky View EN/ES | PASS |
| AstroNova legacy banner | PASS; links to primary app/GitHub/upstream |
| JS errors | none observed |

## Notes

- The cover links point to the default production ports (8790/8830), not the sandbox ports; this is intentional for the default launcher, but a sandbox run should use direct app/view URLs.
- AstroNova remains Spanish legacy with an English/Spanish banner; its UI was not fully translated.
- Candidate/discovery boundaries remain intact: no positive “new planet/discovery” wording.
