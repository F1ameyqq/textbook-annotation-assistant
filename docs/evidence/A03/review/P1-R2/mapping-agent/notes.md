# P1-R2 mapping and neighboring prefix review

Static helper review of final `940a5de33a24b1a3a9ded6e69ade1dd0609ed83a`, design `a250a76dc0b3f13b9dee3bcd2c3d7414032b9768`, from the coordinator-selected exact Git copy. No floating executor files were used. The main reviewer owns package identity/export verification and the final conclusion.

- `mapping-summary.json`: 69 unique exact mappings, actual file SHA matches, 54 byte-identical case files and 15 derived files. 72 cases adds exactly the three requested neighbors. All seven candidate-profile Schema SHA values match actual bytes. The unchanged API signature set has 56 recursively found fields whose key contains `signature`, including `current_signature` and `proposed_signature`; this differs in counting convention from the author's 46 fields with key exactly `signature`, with no semantic discrepancy.
- `changed-case-diffs.json` records every changed JSON scalar/path. `trigger-resource-results.json` independently checks all 15 primary triggers against actual R1/R2 content and equal plan, result/attempt, progress, pending and pause projections. The 54 unmodified case files retain 70 reachable safe Resource byte hashes. One intentionally invalid `../P1/assets/prepared-before-1.json` path was not read; invalid candidate paths are preserved as input rather than followed.
- `neighbors-results.json`: an independent canonical-byte/hash and per-action sequence oracle computes the expected acceptance before calling the pure subject `prefix_rules.validate_prefix`. Positive, all three author neighbors, and five independently created neighbors agree. Deleting acceptance or A dispatch in the supplied author candidates has contiguous recomputed hashes, so corresponding failures are attributable to omitted events; missing acceptance also causes expected reservation/state prerequisite findings. B dispatch or consumption removal with a fully recomputed chain and `complete=true` still refuses. A valid chain with `complete=false` passes, confirming the flag is not authority.
- These deletion/rechain neighbors are explicitly `PRE_ADMISSION_INPUT`. They retain the legal context basis but are not claimed committed fact graphs. Body/resource references that belonged to the valid context are not reconstructed as committed events in these rejected candidate inputs. Results prove the prefix-layer checks only. No runtime refusal, durable intent, SQLite, recovery or target effect was executed.

No blocker found within this helper's bounded mapping/profile/signature/neighbor scope. It does not independently decide whole-P1 acceptance, release P2/I01, or claim B confirmation, complete JSON Schema standards validation or runtime authority.

Final captured reproduction:

```powershell
python -B D:/1800/docs/evidence/A03/review/P1-R2/mapping-agent/run_commands.py D:/1800/.local/stages/A03-review-P1-R2/940a5de33a24b1a3a9ded6e69ade1dd0609ed83a
```

`command-receipts.json` records real argv/cwd/Python, PIDs, finite timeout, returncodes, stdout/stderr and observed child exits. All launched children are finite and awaited; zero background processes were created. No unrelated process/service scan or termination occurred. The outer command also exited before helper handoff.

Relevant memory was used only to recheck the historical design-only phase and exact recursive consumer-reference boundaries; current evidence comes from the frozen copy. Memory: `MEMORY.md:28-38`, originating rollout `01a145aa-2fea-7942-97f9-ad260acf4e30`.
