# A24 A 侧停止与 B 侧接力交接

本文件落实根协调转达的用户最新指令：结束已启动的 411ec375 唯一真实轮，固定实际结果和释放，推送现有成果后由 B 侧接力。A 侧在本轮冻结后停止 schema 实现、测试和新 live。冻结 REPORT.md 中“作者继续离线实现”的旧续作安排由本文件取代；原冻结报告和清单不改写。

## 当前交付及状态

- 作者 checkout：`D:/1800-worktrees/a24-first-save`，分支 `codex/a24-first-save`。根 checkout `D:/1800` 未编辑。没有额外 schema 改动或未提交产品改动。
- 固定实际 final：`d3c8abcf0c1fa89af123e4b242964f818f1a011c`；内容提交 `173c5e40a38d9d75afc4036103be6502764a3008`。
- 实际包：`D:/1800-worktrees/a24-first-save/docs/evidence/A24/controlled-capture-current-body-actual/`。
- 唯一最终 raw 清单：该目录的 `delivery-final-manifest.json`，SHA256 `0542873bcfa6d6a9343a1786c059bca8a37d59cfa1297ded20b357acb6d5008b`。26 个成员加清单自排除；16 个私有 refs 均按长度和 SHA256 复核。33,521 个旧 mode/type/blob 成员全部保全，无产品源码改动。
- 固定启动 final `61fb7157eb335d2a0b9348e8496ea0b4b8d17ad0`，产品 `576fe90a98b2f0e933c69062c4e73d9e6210bd86`。启动前核验 158 个候选依赖及 4 个已安装 Playwright 源文件。Python 3.9.13 / Playwright 1.58.0。
- 正式实际验收仍为 **PENDING_SAME_REVIEWER**，原 reviewer `01a15cf8-68e0-7b63-91a3-657a567b344c`。本次作者静态核验不构成独立接受。根协调 `01a15dfa-9556-7812-9ed5-1b3bce53555e` 负责收验收及推送；A 侧未自行 push。

## 本轮实际事实和释放

Authority SHA256 `411ec3757822ed374ed7f4c13e6a0becc571609d2d2b4117991c8acc20c4e244`；run `A24-first-save-r1-controlled-capture-body-20261021t143424z`。唯一轮已耗 1，余 0，不重试、不延长、不复用 activation，不恢复任何历史额度。

Bootstrap、session completion 和 viewer admission 完成，四个原定 GET 全部 HTTP 200：book 4,186 bytes、directory 14,019、full frames 46,219、natural export 11,625。结果为 **PREWRITE_BLOCKED_NO_EFFECT / CURRENT_SCHEMA_UNBOUND**，后继 NOT_RUN，write_allowed=false。HTTP 200 仅证明本轮有界采集完成；当前自然 schema、完整旧题保全、身份和写入资格仍未证明。book 仅保留长度/哈希，冻结 collector 未保存其原响应，不得编造 book 字段。

实际 signature、upload、commit/save、author refresh、independent reopen、login、credential configuration、model/OCR 均为 0。context 已关闭，runtime 已停止，无清理错误；两份安全 audit 均完整 14/14 events、无 guard 首错、无 pending callback。launcher/product/worker/occupancy 四个 held identity 前后一致，观察 exit 均为 0，四个 Job 已空并关闭、四个持有 handle 已关闭。外部 supervisor 证明实际 launcher 的退出/释放，其自身 OS exit identity 仍 NOT_SELF_CERTIFIED。原 profile 保留，不清锁、不重置、不探测。

## 私有原件精确位置

Run 根目录：`D:/1800/.local/stages/A24-first-save-r1-controlled-capture-body-20261021t143424z/`。全部 16 refs 及其完整哈希以固定包的 `private-raw-manifest.json` 为准，不把正文、原脚本、源 URL 或 token 加入 Git。

| 原件 | 路径（相对上述 run 根目录） | SHA256 |
|---|---|---|
| 当前目录 | `private/directory-snapshot.bin` | `724059d435270a50c40e56a9de31970bbd08ed426a44c147eaf9ea028e6de34d` |
| 全部框 | `private/frames-snapshot.bin` | `6c3fad1aeee1d20623c9f4d3d4baef3981713cd6cfa775242f71a03bfcb0fdab` |
| 自然导出 | `private/export-snapshot.bin` | `02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c` |
| 当前 Script | `private/source-capture/static-assets/1-d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41.bin` | `d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41` |

Script 的 provenance 位于同 basename 的 `.bin.source.json`，capture marker 为 `private/source-capture/capture-owner.json`；完整精确路径以 private 清单为准。八个阶段 stdout/stderr 位于 `private/owner-{launcher,product,worker,occupancy}-{stdout,stderr}.bin`。外部 launcher stream 两份副本和 supervisor 位于 `D:/1800/.local/stages/a24-controlled-capture-current-body-supervisor/`。不要向冻结 run 新增离线派生文件。

## B 侧剩余工作及最小下一步

先取得原独立对上述固定 actual 的正式结论和根收口状态，然后只读使用三份新原件，离线确认 natural export 的真实格式/字段、全五区正文及元数据覆盖、完整旧框、目录/目标书身份、全局 order 与合法 append/newness、save-page 映射。不得从历史 22 题/68 框或资源页 13/172 推定当前完整性或保存页 14/173；book 原 body 缺失必须保持为缺口。下一次必要读取也须由根另行精确绑定，不能借本轮。

实现入口为 `src/annotation/delivery/live_pilot/{wire,usense}.py`、`src/annotation/runtime/live_pilot/{authority,owner,runner,private_payload}.py` 及 `src/annotation/quality/live_pilot.py`。现有自然导出 codec 仍要求 evidence-bound 的 full-body route qualification，不能为了适配真实格式虚构 metadata 行或放松完整性。schema/request/profile/plan/count/guard 应作为一个最小修订一起冻结，再交同一独立。当前条件性 17 GET（有独立 info 时 20 GET）只是未激活方案，不能当作 live 权限。

唯一目标仍是 book `46007447`、目标叶 `dir-1792063578574-g0n3ulsni` 的一个普通选择题；接入既有 accepted 内容后，经新鲜 prewrite 保全和资格校验、一次实际 save、作者 fresh get/refresh、原独立 fresh reopen 才能证明完成。禁止第二题或整书提交。严格业务 receipt 必须有服务器实际 stable ID/order/file ID/inserted 与六框绑定，不得把预期 order 当 receipt，UNKNOWN 保存不得重发。

固定内容不重跑：`D:/1800/.local/stages/a24-model-one-question/reviewed-candidate-v1.json`，SHA256 `cd4ee0c6a379fa5bf8cc87dccdb010c423a9e2f9a2382336efaa00cefe103b5a`；native draft 为 `D:/1800/.local/stages/a24-first-save-r1-inputs/author-content-v1/request-accepted-content-v2.json`，SHA256 `b3a20ce748e08659e88562ea0937b10fd9c8a93789de669d611b466e91f38727`，仍是 PROPOSAL_ONLY/schema_profile=null。既有六张裁图、内容独立接受及旧失败保留，不再 OCR、模型调用、内容复审或旧 suite/live。

## 可粘贴接力指令

> 接力同一 A24 剩余首题保存工作。先读 `D:/1800-worktrees/a24-first-save/docs/handoffs/A24-A-to-B-current-body-20261021.md`，确认根对 actual final `d3c8abcf0c1fa89af123e4b242964f818f1a011c` 的原独立验收与推送状态。第一项产品工作仅为离线分析清单绑定的 directory/fullframes/natural-export 三份私有原件，列清真实 schema 与旧题全量保全、身份、append/save-page 缺口，再做一个最小整体修订。当前没有新 live/save 权限；411ec375 及全部历史轮已耗尽，不重跑，不清锁/状态，不新建书源，不再 OCR/模型/内容复审，不处理第二题，不自验收。后续实际保存与 refresh/reopen 必须等待根在新固定候选和独立有限接受后绑定精确权限。

A 侧冻结后仅整理本交接，无额外 schema 实现或测试；保留原实际冻结包，不重封装。后续由根派 B 侧，A 侧停止。
