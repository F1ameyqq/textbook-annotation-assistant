# A01 R2：冻结交付与独立复验交接

日期：2026-10-17。状态：REVIEW。仅交付指定三类来源一致性修复；未接受、未集成、未释放 A04。

被验提交 `c3aff9598b6705ab4122062615a13ae3774698b2`；实现 `63ac5a184798326d629a43d1dfed25fa73a1a27e`；R2 基线 `03c1af41a134945c406a52a48e3d4f6f0da33eb2`；原 base/workflow `39341c98d73c354d639f3beeb55429f55d0e9be5`。源工作树 `C:/Users/ASUS/.codex/worktrees/a01-source-geometry/1800`。

目标提交内 `docs/tasks/A01-rework-R2-report.md` SHA256 为 `3aeaaf40e55163541921ec5915995cc9d01b878bb6843f76fb9f048d5dba8d50`；最终归档清单 SHA256 为 `ed4aee2d5aaf4b71f5eee6c60c90c0b58c1672a4803507bb03d1056c00000576`。执行对话已完成、声明冻结且工作树干净；未打开浏览器/profile，待释放会话 0。

依据 [原独立验收](A01-independent-review.md)、[R2 有界任务](A01-rework-R2.md)、[R1 REWORK 报告](A01-review-R1-report.md)及[主调度反例复现](../evidence/A01/coordinator/R2/coordinator-check.json)。来源实现 `a01-static-1-r2`；合同保持 `1.0.0-a-proposal`，B 未确认。

交付前检通过：88 个变更路径在允许范围；实现至交付只新增报告/manifest；87 项清单磁盘与 Git 原始 blob 摘要相同；886 个受保全旧文件、31 份原输入、7 份主目录只读输入和 29 个新包文件核对通过。geometry SHA256 保持 `3b707579cd586887da3b5125048b17c5baf548010fccf6cb21cc386baddaacf0`。这些是版本和字节前检，不是功能验收。

## 输出与隔离

- 原验收对话继续，只写新报告 `D:/1800/docs/tasks/A01-review-R2-report.md`、新目录 `D:/1800/docs/evidence/A01/review-R2/`；不覆盖任何旧证据。
- 从确切提交导出原始 Git blob，固定并记录导入路径。可将隔离源码放本任务 `.local/stages/A01-review-R2/`，但来源输出及测试 TMP/TEMP 必须是独占普通临时目录，不放受保护 `.local`。不用浮动工作树或其他 editable 安装。
- 零平台、浏览器、网络、凭据、OCR、模型。不得改实现、公共合同、根依赖、调度状态、A02/A03/A04 或自行集成。

## 本轮必要核查

1. 复现作者最短命令及 R2 新包消费者、搬运、A01/C01 回归。作者自报 40 通过/1 文件 symlink 权限跳过、70 C01 通过、原16例通过、R2九例通过必须独立确认。不要运行会覆盖旧证据的原脚本，所有输出使用新目录。
2. 从已冻结 R1 正式四个输入独立复放，并构造可搬运邻近反例，证明先通过公共资产/摘要校验，再在来源边界定位拒绝：selected/acquired/missing/outside 分区、响应 image URL 两处书籍标识及 source index、观察索引路径与保留输入清单摘要。
3. 保留合法非零缺页、空 outside、源索引0/上界和正常旧格式/两书旧包，不能把修复简化为拒绝所有缺页或只接受新包。额外检查重叠、遗漏、重复及 bool/float 越界，URL 主机文本不能误作来源归属认证，查看器映射不能硬编码偏移。
4. geometry 和旧失败/报告/样例逐字节保全。R1 的630项几何矩阵已有证据，可在确认模块/条件不变后引用原结果；若未重跑必须明确说明，不记为 R2 新通过。R1 旧测试仅生成器版本断言可调整，不允许降低旧反例期望。
5. S01 公共完整性资格、D01 根 Pillow 依赖、N15 非认证标签及文件 symlink 跳过仍保留；没有全书分母或来源 coverage PASS。来源内部一致性不证明外部真实性或实时平台状态。

给出确切提交、实际命令/模块位置/退出码、每个指定修复及新增邻近场景的结果。若有缺口，保存最小输入并给有界 REWORK/BLOCKED；不得自行扩修。完整 SHA256 清单包括报告、脚本、输入、输出、原始日志及自身排除说明。旧证据保留，主调度复现与集成后才能释放 A04。
