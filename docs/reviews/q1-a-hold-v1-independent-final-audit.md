# Q1 A02 HOLD probe — independent final audit

Date: 2026-10-18  
Scope: book `46007447`, question `q-e92a499995ca1bbd570a2a09` only  
Frozen A identity: reported commit `37089f9e0229da76ae1c45461b7e63929590be56`, verified by the exact 76-member source pin  
Technical verdict: **PASS — negative gate closure only**  
Business/content verdict: **HOLD**  
Positive simulation verdict: **NOT PERFORMED / NOT ESTABLISHED**

## Verdict

The submitted real-Q1 A/B diagnostic chain is accepted as a technically valid fail-closed result. The observed Q1 source, evidence, and graph enter unchanged A contracts; a clearly synthetic empty target causes A02 TARGET to return `EXCEPTION`; the planner produces a zero-action `BLOCKED` plan; execution returns `NOT_EXECUTED`; no action is dispatched and target state is byte-identical before and after.

This proves that the negative safety gate stayed closed. It does not approve the Q1 mapping, answer D, platform capabilities, content correctness, a positive simulation, or business delivery.

## Frozen evidence

- A source pin: `3174f9981ffc336b3d576d78afe3e6932e042521011555272dc94d9b564e1fe0`; all 76 pinned source members matched.
- Mapping JSON: `09f9937a411a5ed5a7003019306a456937a422fc874a9baaae52817f02ccf06a`.
- Mapping manifest: `a831da5d89f2620220cff19565c5aff1825e47c5b0d900f7e269c61dbd590e2f`.
- Executed bundle: `81e50431bfdd97fa64edcdd28fded06b2a339d82ed7943a065f09d30be61e33d`.
- Run summary: `990d617fcb77fb2a759397d3cc0d9fe6689b40a40e3ac707a2deb29a92dbe2da`.
- Target before and after: identical SHA-256 `e1976d9f8261e791c05ba8eec80d1692a05ae9d14d791f00313cb154626825a5`.
- Empty action log: `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`.
- Final integration driver: `a6d212bd3ec796cebde580b1949925ef926c754f260be6be58b724ffa3fb367e`.
- Final mapper: `fecffb512c4a5a574281170db2bc803f7153b67400fe7e55cfaec67261904c0e`.

Both production invocations exited 0 and both stderr captures are empty.

## Independent checks completed

1. Recomputed the 76-file frozen-A inventory before importing A.
2. Loaded the mapping and all four derived stages through frozen A with direct asset verification:
   `c01-candidate-bundle.json` → `prechecked.json` → `targetchecked.json` → `planned.json` → `executed.json`.
3. Verified the stage chain is append-only: prior policy, evidence, and artifact bytes are preserved as exact prefixes.
4. Correctly excluded only the top-level manifest while checking recursive inventory. The mapping manifest is exact at 10/10 members; the source-candidate manifest is exact at 24/24 members; every listed byte count and SHA-256 matches.
5. Checked all nine JSON/Markdown members in the portable `mapping/` tree for machine-local absolute paths; none were found.
6. Confirmed one intended book and one intended Q1, six unique semantic geometries, two original source assets, observed source/evidence/graph provenance, and an unresolved answer relation with no selected fragment.
7. Confirmed PRE_APPLY is `HOLD`, contains the required five checks, and has explicit blocking issues.
8. Confirmed TARGET is `EXCEPTION` for independent blocking reasons including unsupported observed inputs, unresolved policy/choice, absent selected-answer closure, missing verified capabilities, and no `CREATE_FRAMES` authorization.
9. Confirmed the plan is `BLOCKED`, its action list is empty, and its blocking ledger exactly matches the blocking PRE/TARGET issues.
10. Confirmed the receipt is `NOT_EXECUTED`, has no results, and has `write_disposition=NOT_EXECUTED`.
11. Confirmed summary counters remain zero for actions, dispatches, platform requests, and model calls, and every acceptance/positive-simulation flag remains false.

## Independent negative tests

The reproducible checker passed all eight adversarial cases:

- a blocked plan is rejected by eligibility with `PLAN_BLOCKED`;
- a changed current snapshot invalidates the old chain with `TARGET_CHANGED`;
- a changed graph cannot reuse the old reports (`VERSION_CONFLICT`);
- a changed policy cannot reuse the old reports (`VERSION_CONFLICT`);
- a wrong source digest is rejected (`RESOURCE_HASH`);
- an unknown candidate fragment is rejected (`MISSING_REFERENCE`);
- an out-of-bounds box is rejected by schema validation;
- distinct region IDs with exact duplicate geometry are accepted by generic C01 but rejected by the Q1 high-level guard.

The last case is an important contract boundary: exact duplicate geometry is not a generic C01 guarantee and must remain an explicit Q1 mapper/precheck assertion.

## Provenance and timestamp review

The mapping artifacts use the frozen mapping timestamp `2026-10-18T12:05:44Z`. The newly produced PRE, synthetic target snapshot, TARGET report, plan, and receipt consistently use the later probe timestamp `2026-10-18T12:08:20+00:00`. No newly produced diagnostic artifact reuses the historical source timestamp.

An auxiliary `independent-replay-receipt.json` records a separate successful replay with a different probe timestamp and therefore different derived bundle hashes. It supports repeatability, but its per-file hashes must not be substituted for the current run hashes listed above. Likewise, invocation and verification records intentionally contain local execution paths; the portability finding applies specifically to the self-contained `mapping/` package.

## Capability boundary

An observed source/graph plus a synthetic diagnostic target is valid here because observed artifacts do not depend on synthetic artifacts; only later synthetic diagnostic artifacts depend on the observed inputs. This is valid solely for the fail-closed diagnostic route.

No A formal PRE_APPLY PASS, A mapping acceptance, platform observation, platform authorization, actual write, answer approval, human verification, content verification, positive execution, or business acceptance is established. Historical Q22 evidence was neither executed nor used as a substitute.

## Reproducible QA artifacts

- `work/q1_a_hold_acceptance.py` — independent checker and negative-test harness.
- `outputs/q1-a-hold-independent-acceptance.json` — machine-readable PASS receipt.
- `outputs/q1-a02-hold-probe-independent-static-review.md` — pre-execution contract review retained as historical review context; its “pending” verdict is superseded by this final audit.

No blocking technical defect remains within the authorized negative-gate scope.
