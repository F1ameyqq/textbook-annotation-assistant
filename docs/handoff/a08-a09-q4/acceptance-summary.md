# A08 / A09 固定范围与证据索引

2026-10-19。本页说明当前结论；冻结报告与B原件按原字节保留，旧报告的待核准/仅本地措辞不改写。

| 层次 | A08只读接收 | A09第一课时Q4离线模拟 |
|---|---|---|
| 产品/实际运行 | `04762d78eae18449d7fcf3c0de20aec23b1f6881` | `29c82b0997be3080f53dfde2afbb1d7457b04197` |
| 作者交付 | `83f119fae8e84b30332ac50288b74049514c9b4e` | `439423ebf4277e3825aba24fed6f56546ef66a2b` |
| 独立交付 | `c4b7575841ee1bed1320eb6351b90e4dcc25f092` | `25fcf2171df87bd7da97528efbe5bc24399d336a` |
| 调度接受 | `32c6e2cd18fec01b46260361533f1a327d758589` | `76a6b4cee0d667131139499400b973611abfffc2` |
| 本地集成 | `abc45f49532d8001be8441b54cedefab32c91e87` | `4fdfebd80f6efc3097e3d92c2659f3055d48f55b` |
| 有效范围 | ACCEPTED_FIXED_BATCH_READONLY_HOLD_ONLY | ACCEPTED_FIXED_Q4_OFFLINE_FOUR_FRAMES |
| 已用验证 | 作者/独立各1原包+11负例 | 作者/独立各1正常尝试/成功/dispatch+10拒绝 |

B输入固定 `a76e5a925fec76f20818dfdefa4145aa132ec8a8`，原ZIP SHA256 `b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673`，1,440,149 bytes。外包 `b-complex-batch-evidence-package/0.1`、batch `ComplexCaseBatchProposal/b-complex-batch-proposal/0.1`；完整外部G0.8/Check0.8/plan0.3仅声明，未加载。已归档原包在[独立输入](../../evidence/A09/review/archive/inputs/stage.zip)，包内B程序仅原件，不运行。

第4题 `q-260d10c51f2b7c16fb6fefb5` → 答案 `a-92c4d2164ab878c8e6d4c88d`，文本13。新A[授权](../../approvals/A09-Q4-offline-business-approval.json) SHA256 `5c73af50262f6bd7e48e2b0d46148026c1c3a953d1ee93c8262e356733d99010`；原[proposal](../../reviews/q4-first-lesson/proposal.json) SHA256 `e8146fc7a4fe2e16c1fc1194d49de1caa1fe029dd6907848bbaa6c9082dc0bbe`。

| 顺序 | 角色/类型 | 原图 | 半开坐标 | 内容 |
|---|---|---|---|---|
| 1 | Q/image | viewer-10 | [334,975,581,1077] | 完整几何图，text=null |
| 2 | Q/text | viewer-10 | [100,1118,592,1193] | 去题号的前两行题干，排版换行合并 |
| 3 | Q/text | viewer-10 | [99,1202,220,1235] | ____ cm.，避开相邻Q5图 |
| 4 | A/text | viewer-173 | [324,239,342,257] | 仅13，不含题号及邻题答案 |

原图viewer-10 SHA `eb7cc17e6b58a55a005ce1cdef5bd5058ad258c3dd44dc891b3d830ed3db3626`、1217×1691；viewer-173 SHA `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`、1148×1621。viewer-173对应resource index172，不能混同resource-173。原4题片段+1答案来源区与新批准四框是不同层，不把来源片段数量当执行框数。

一题四框，无W/E或原书解析。印刷4.及“第4题图”仅定位依据。fill_blank显式映射free_response、来源保留；题干三组在同页，cross_page=false。实际frame_projections的类型/文本与基础frame角色/坐标/题绑定均独立核对，不只是计划和自己输出互相一致。

独立模拟回执：[a09-receipt-a09-q4-50888](../../evidence/A09/review/archive/candidate-1/trial/normal/receipt.json)，revision1，content_hash `82346ba80d6b44bd5d609464b7b9de58e9404d08f05ab6bdca94b579172e2bef`。实际[读回](../../evidence/A09/review/archive/candidate-1/trial/normal/assets/readback.json) SHA256 `5c568274409cd7740d879bb5d0482e54282c752381dd90e84ed30a5cdf0df048`，APPLIED/MATCH、不可重放，NOT_SUBMITTED/PENDING保持。

冻结清单：[A08作者](../../evidence/A08/execution/delivery-raw-manifest.json)、[A08独立](../../evidence/A08/review/review-raw-manifest.json)、[A09作者](../../evidence/A09/execution/delivery-member-manifest.json)、[A09独立](../../evidence/A09/review/review-member-manifest.json)。A08为51+69成员，A09为95+92成员，四份清单均排除自身避免循环。调度[第4题核证](../../evidence/coordinator/a09-acceptance-20261019/verification.json)及[集成检查](../../evidence/coordinator/a09-acceptance-20261019/integration-check.json)保留；静态检查器误差和纠正也保留，不作为产品失败或掩盖复跑。

A09合法重封image→text能通过C01，但在原结构/政策类型语义门HOLD；其他9个固定拒绝也零新增变更。A08 R6只证明库存结构门，不冒称公式语义通过。发布不运行这些检查，不恢复任何额度。

其他三例HOLD、无题关系；完整外部对象、复杂题批处理、OCR、B共同采用、公共合同冻结和真实平台均不由本次离线结果证明。A04阻断保持。[返回入口](../../a08-a09-q4-handoff.md)。
