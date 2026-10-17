# A04 coordinate-R3：原始 Git 字节证据补充

2026-10-17。继续原独立验收对话，明确 `xhigh`。本任务只修正验收证据的字节来源和相应结论，不向执行者派功能返工，不修改产品或扩大真实平台范围。

## 已核对事实

- 固定目标仍是 `6c8137a4fadddc01a47906d564ab3460277c8958`，实现 `81d62255b545b88f344849d08011a2a859c49c5e`。
- 原报告为 [R3 复验](A04-coordinate-R3-review-report.md)，SHA256 `ce6bc599c0b1533e58095366c4f8b499248079aa6c571e8569e1b585d4a82e61`。原355项清单及报告全部磁盘摘要一致，完成对话及自有27个进程身份结束记录已核对。
- 主调度逐个比较原 `inputs/frozen-inputs.tar.gz` 的212项和 `git cat-file --batch` 返回的目标 blob，发现59项不同，全部为CRLF/LF差异：55个Python文件、一个 `.gitattributes`、三张ASCII PGM。原清单准确绑定了实际archive字节，但这些不是全量原始Git字节。不能把文本归一比较当作原字节一致。
- [差异明细与首次失败](../evidence/A04/coordinator/coordinate-R3-acceptance/archive-preflight-failure.json)保留，失败发生在产品运行和stage写入前。`git archive`本次受换行转换影响，不能仅凭使用该命令断言原始字节。
- 主调度随后直接从cat-file写出212项原始blob到新的隔离目录，重放未改精确反例：wrapper退出0、产品CLI退出2、无输出目录/历史/最终包。见 [核对与复现](../evidence/A04/coordinator/coordinate-R3-acceptance/checks.json)。没有发现新的产品缺陷；相关完整独立结论仍待本补充。

## 唯一允许工作

1. 保留原R3报告、清单、tar、脚本、原始流及所有旧材料，逐字节不改。新增补充报告明确原报告的来源描述错误，不能追改旧摘要或掩盖59项差异。
2. 从同一固定提交通过 `git cat-file --batch` 提取所需原始字节，逐文件记录Git object/blob摘要、实际运行目录摘要和大小；运行前及结束后对照。可复用原212项清单中的路径，但不能复用其换行转换后的摘要作为Git摘要。禁止使用浮动主树或未核对的archive充当目标输入。
3. 在新的隔离目录、新的输出位置重用原来未改的检查脚本：精确缺行反例、4个相关模块的70项回归、26项独立检查。只为本次已发现的输入表示差异做一次有界补证，不重复更早整套浏览器/合同/坐标矩阵。脚本需要输出参数即可原样使用；若实际参数限制必须解释，不能静默改期望值或删除失败用例。
4. 比较原始PGM字节、发布包的资源hash/尺寸/搬运消费和真实导入位置；同时给出新输入与原archive表示差异，不把两次运行成绩混为一次。
5. 记录全部实际命令、stdout/stderr、退出码、失败和自有子进程结束。若有确定产品差异，保留最小反例并停；无差异则补充限定的OFFLINE_R3结论。整个A04真实R01～R06和S01仍BLOCKED。

禁止产品、依赖、state、旧报告/证据修改；禁止浏览器、网络、平台、profile、凭据、登录、OCR、模型或书籍动作。不复测题22，不联系执行者、B或其他任务，不提交、推送或集成。原先未执行的Node/junction/配置极限压力检查仍如实保留。

## 交付

只新增 `docs/tasks/A04-coordinate-R3-raw-bytes-review-report.md` 和 `docs/evidence/A04/review/coordinate-R3-raw-bytes/`。补充报告、清单及旧355项+原清单自身保存核对齐全后结束。主调度收到冻结补充后才决定有限接受与集成，不将本次补证扩成产品返工或新研发阶段。

本地集成还有一项明确边界：主树尚无 `source/usense`，整分支合并还会带入尚未接受的browser/session/collector/真实坐标代码；本轮不做整分支合并。补充报告无需设计拆包或实现集成方案。
