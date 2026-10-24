# A30 source-r1：有限只读取源分支接受

2026-10-24；独立方 `01a16bf6-f61d-7f40-a4cc-2f1201f2ece3`。

**结论：ACCEPTED_OFFLINE_SOURCE_ONLY。** 这份固定只读取源代码及计划可交根协调绑定其自身一次实际取源，不需要等待无关内容/写入修订。当前实际取源 `NOT_RUN`、模板 `activated=false`、`CUSTOMER_READY=false`；A30 v1 的数字答案及内容/写入链 `REWORK` 不变。

固定形式是 `8ac7be97c104c4cc57004de691ba21e5d4b92b33` 上的 **RAW_SNAPSHOT_WITH_UNCOMMITTED_R1_DELTA**，不是新 Git 提交。作者清单 SHA-256 `f76335e21e70825edbf660964bfd4532db5ac762f7c9ca888944d18cee6e6494`；根索引 `e15da9b5bbdb9ba09c37b09b96682ced0815d912d224dae579df1293ac41d337`。独立核对 179 源、6 证据及全部本次输入，初始隔离 193 件与根索引相符，另接收根冻结的目录来源记录 1 件，共关联 194 件；未读取作者活动树。

## 本次接受的精确范围

- 从固定原始目录、全书题框及 source 响应执行 `catalog → scope_plan`，通过普通目录路径选择唯一末级目录，得到与交付完全相同的计划。计划未使用候选、答案、题框人工清单或接受标记作为客户输入。
- 书 `46007447`，目录 `dir-1792063578574-g0n3ulsni`；题页 `[14,15]`、答页 `[173,174]`；API 集合恰为目录、题框、source 和四个 page GET，共 7；原图最多 4 GET。既有节点仅作来源线索，`existing_node_replay=false`、`source_scope_complete=false`。
- 执行只调用 `acquire`，不调用 `prepare_acquired`、识别、保存、登录或导出。一次 `_capture(pages=...)` 复用既有受控 context/native 双层 GET 边界；原图来自该轮返回的本书官方页面 URL，拒绝错页号、外域、query/fragment 和重定向；原始响应和图片字节保存在独立输出中。
- `source-plan` SHA `d5cb17e0bf3767118b61e623c49095887ab05078ca6d62f2b8159f15e1e03593`，settings SHA `03430187c38355c67298feccd3a0462053ac1c5a83a1103f977cd12d0891f94a`。入口重新核 source 清单、计划、settings、目标、限制和当前专用 profile 目录指纹；DIRECT 与既有 exact-leaf/SPKI 常量匹配。未读取 profile 文件或凭据。
- 根新 authority 的窗口最多 900 秒；在 Store/transport 前独占写入并 fsync 一次性消耗文件，已有文件即拒绝再次启动。业务 API 和图片请求读取剩余窗口；缓存只能复用相同计划/URL 键及校验相符的原件，失败/未知不自动重试。真实耗时与当前缓存/登录有效性待实际结果记实。
- 受控浏览器 child 仍由字节相同的 A29 Windows Job holder 管理；只有 OS 释放及 context/runtime 释放均已证明才消费结果。原图 response 通过上下文管理关闭。实际输出须在整个固定包之外，保持 holder 既有包边界；不把本次入口的离线接受当作实际释放证明。

## 独立验证

仅执行 4 项新增有限检查，**4/4 PASS**：

1. 用固定真实目录/题框/source 重建精确计划，核 7 个 GET、exact-cert 常量及原 A29 holder 原始哈希。
2. 实际运行本包入口消费未激活模板，退出 2、明确 `EXPLICIT_ACTIVATION_REQUIRED`，未构造 Store/profile/browser 资源。
3. 独立合成 OS 释放缺证记录，验证退出 0 仍被 transport 拒绝。
4. 独立合成 context 释放缺证摘要，验证采集状态即使为成功仍被拒绝。

后两项是离线反例，不是实际资源释放或平台实测。作者 9 项和全部旧矩阵未复跑；原作者期望异常类型错误及后续记录原样保留。本次真实浏览器/网络/OCR/公式/模型/保存/登录调用均 0，没有消耗任何平台实际轮次。

独立证据目录：`D:/1800-private/a30-source-independent-20261024-r1/`；`result.json` 为机器结论，`review-manifest.json` 绑定检查脚本、原始输出和报告。复制包内的公式、组题、审校、保存、导出等其他增量只作为冻结依赖保留，**不随本分支接受**。此前成功九题不重存，`1800-a` 暂停保持；未修改根 JSON、AGENTS 或产品。
