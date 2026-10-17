# B 侧 46007447 最小离线交接包

交付文件：[B-46007447-Q16-offline-HOLD-2026-10-17.zip](B-46007447-Q16-offline-HOLD-2026-10-17.zip)，SHA-256 见 [SHA256SUMS.txt](SHA256SUMS.txt)。本仓库可运行 `python tools/verify_b_handoff.py handoffs/b/46007447/B-46007447-Q16-offline-HOLD-2026-10-17.zip --self-test`；包内也附同一校验器。

固定运行 `pipeline-run-0a2c03e193694ef88953f3ca08b8cde2`；14 阶段 `READY` 仅指流水线成功完成，业务判定仍为 `HOLD`。交付的是 5 张已观察题/答页加独立相邻答案资源上的局部候选，不是整章完成稿，更不是网站标注提交。原始来源图片、裁剪图、14 个阶段封装、运行报告、当前 Evidence/G07/Check07 及输入收据均在 ZIP 内；包中 `manifest.json` 列出每个文件的相对路径、大小及 SHA-256。当前图谱含 34 题候选、66 答案候选，检查报告含 127 项问题。

44 个历史 `file_sha256` 输入收据全部在包内按原字节匹配。行内 `inline-package.json` 已从随包素材和清单独立重放生成，同时匹配历史文件 SHA 和内容引用；随包 ZIP 中本次运行实际使用的 95 个成员逐项匹配原运行记录的大小和 SHA-256。

公共合同仍是草案，A 侧接收状态为 `PENDING_A`。整章题页/答页覆盖、可靠资源映射、独立清点及人工内容核准仍待完成。本包未修改网站标注、未包含登录凭证、Cookie 或浏览器状态。

## Q16 来源区域后继包（MODEL_DRAFT / HOLD）

[后继 ZIP](B-46007447-Q16-source-revision-HOLD-2026-10-17.zip) 独立保存固定运行 `pipeline-run-5dccc68b9873417a94d61f32a6df4d52`，代码基线 `56278cbb7e65c613e723ce7c34168e9190e77cf1`；不覆盖上面的旧包。SHA-256 为 `45762cc5d285dbffc66d0611182948504bdd8c87781a2e65823265d40dffdd46`，亦列入校验清单。新包包含同一运行的 E/G07/Check07、14 个阶段封装、六张来源原图、45 个精确输入收据及可执行的离线重放步骤。29 个裁剪收据经原图像素和文件摘要核对。

使用干净代码导出和包内输入完成[冷/热重放](Q16-source-revision-replay.json)：冷运行 14 阶段、0 缓存，热运行 14 阶段、14 缓存；两次最终对象引用均与包清单相同，结构审计接受。内容仍是 `MODEL_DRAFT`，未经过人工转写核准；业务判定始终 `HOLD`，A 接收 `PENDING_A`，整章来源仍未齐备。独立验证命令：`python tools/verify_b_handoff.py handoffs/b/46007447/B-46007447-Q16-source-revision-HOLD-2026-10-17.zip --self-test`。
