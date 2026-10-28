# B 侧 46007447 最小离线交接包

## 当前 Q4/Q9/Q16 revision 8 后继包

[合并修订ZIP](B-46007447-Q4-Q9-Q16-revision8-HOLD-2026-10-17.zip)固定代码 `af8e17c2ed60219db4f0da40daea6be0396c4b5b`、运行 `pipeline-run-85c20d4acab3496ea33296b54cc5b8e7`，SHA `318cd49d628437989735f8155ce844041e8d814b8e81db23345d4673749da3df`。78个文件、14阶段、原六张图，34题/66答/134问题；新采集的印刷5、7页不在该内容运行内。计划/应用为trial0.3，图谱/检查0.8，旧0.7消费者未迁移，仍MODEL_DRAFT/HOLD和PENDING_A。

固定Git导出下的包内输入[冷/热重放](Q4-Q9-Q16-revision8-replay.json)均接受且最终引用与包一致：冷0缓存、暖14缓存；沿用本机依赖，禁止模型导入/联网。验证命令：`python tools/verify_b_handoff.py handoffs/b/46007447/B-46007447-Q4-Q9-Q16-revision8-HOLD-2026-10-17.zip --self-test`。独立内容审核和章节覆盖仍未达到人工验收。

[印刷7来源增量](source-increment-viewer15-20261017.zip)单独保存真实原图与完整来源报告，SHA `50f053175c487c2f35b1d1a4749aa1e06a65e52cc20b41db2ba3e976a2610d45`。清单仅保留实测原图URL，明确未记录API请求完整URL；它不代表该页内容已经修复。

## 初始历史包

交付文件：[B-46007447-Q16-offline-HOLD-2026-10-17.zip](B-46007447-Q16-offline-HOLD-2026-10-17.zip)，SHA-256 见 [SHA256SUMS.txt](SHA256SUMS.txt)。本仓库可运行 `python tools/verify_b_handoff.py handoffs/b/46007447/B-46007447-Q16-offline-HOLD-2026-10-17.zip --self-test`；包内也附同一校验器。

固定运行 `pipeline-run-0a2c03e193694ef88953f3ca08b8cde2`；14 阶段 `READY` 仅指流水线成功完成，业务判定仍为 `HOLD`。交付的是 5 张已观察题/答页加独立相邻答案资源上的局部候选，不是整章完成稿，更不是网站标注提交。原始来源图片、裁剪图、14 个阶段封装、运行报告、当前 Evidence/G07/Check07 及输入收据均在 ZIP 内；包中 `manifest.json` 列出每个文件的相对路径、大小及 SHA-256。当前图谱含 34 题候选、66 答案候选，检查报告含 127 项问题。

44 个历史 `file_sha256` 输入收据全部在包内按原字节匹配。行内 `inline-package.json` 已从随包素材和清单独立重放生成，同时匹配历史文件 SHA 和内容引用；随包 ZIP 中本次运行实际使用的 95 个成员逐项匹配原运行记录的大小和 SHA-256。

公共合同仍是草案，A 侧接收状态为 `PENDING_A`。整章题页/答页覆盖、可靠资源映射、独立清点及人工内容核准仍待完成。本包未修改网站标注、未包含登录凭证、Cookie 或浏览器状态。

## Q16 来源区域后继包（MODEL_DRAFT / HOLD）

[后继 ZIP](B-46007447-Q16-source-revision-HOLD-2026-10-17.zip) 独立保存固定运行 `pipeline-run-5dccc68b9873417a94d61f32a6df4d52`，代码基线 `56278cbb7e65c613e723ce7c34168e9190e77cf1`；不覆盖上面的旧包。SHA-256 为 `45762cc5d285dbffc66d0611182948504bdd8c87781a2e65823265d40dffdd46`，亦列入校验清单。新包包含同一运行的 E/G07/Check07、14 个阶段封装、六张来源原图、45 个精确输入收据及可执行的离线重放步骤。29 个裁剪收据经原图像素和文件摘要核对。

使用干净代码导出和包内输入完成[冷/热重放](Q16-source-revision-replay.json)：冷运行 14 阶段、0 缓存，热运行 14 阶段、14 缓存；两次最终对象引用均与包清单相同，结构审计接受。内容仍是 `MODEL_DRAFT`，未经过人工转写核准；业务判定始终 `HOLD`，A 接收 `PENDING_A`，整章来源仍未齐备。独立验证命令：`python tools/verify_b_handoff.py handoffs/b/46007447/B-46007447-Q16-source-revision-HOLD-2026-10-17.zip --self-test`。
