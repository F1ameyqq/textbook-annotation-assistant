# A30 02 固定代码与 launcher 独立评审

结论：**ACCEPTED_OFFLINE_CODE_AND_PACKAGE**。仅接受02固定源码、冻结launcher及构建证据引用闭包。actual未授权，customer_ready=false，1800-a保持PAUSED。01的REWORK与原失败不改写。

固定输入：产品manifest `0095d385936969fe45e38b092e0095ab60465e41f54b37acbe076b8f37601d6f`；launcher `dc6677df5ef20e9b217298a7a57c0edb251202c3045b7e4957e3fde38551229d`；构建 `21c33d7b3ad585e4e9054ad4c6e662dba29de6a3b0a9a8ad278acad97ecabc9b`。新补充任务 `1a299874…` 与原统一合同 `0fefc092…` 共同适用。

## 01阻断的关闭

Store.complete_retained_recovery在同一SQLite事务内发布原save的CAS、恢复COMPLETE、job head和event。独立真实副本控制在原save更新前、恢复终态更新后、job更新后及event插入后注入SQL失败，另测save CAS miss：原save仍UNKNOWN、原job/head/events和失败reconcile不变，新恢复为FAILED_NO_RETRY，重复动作拒绝。成功时save/recovery共用一个COMPLETE接受ref，候选、job和唯一新增event一致；旧UNKNOWN blob/历史头/events可追溯。没有用交换finish/resolve顺序代替事务。

## 必要验证

- 产品254源码、155证据及report共410声明成员，launcher7声明成员逐一sha/bytes核对；完整隔离副本字节一致。相对01为4改、1增、0删，249个旧源码字节不变。旧01未重写。
- 30项受影响测试独立重跑通过：26项retained/adopt/atomic/existing-fill，加3项已修正夹具和1项未失败普通reconcile回归。原断言未弱化。
- 13项独立真实工作区副本控制通过：成功/重复、原CAS及更晚提交回滚、缺失/篡改/歧义/已有intent/缺失failed row/冻结scope变更拒绝、普通CLI。transport构造0、平台调用0。GUI回调静态确认使用同一共享程序路径；没有打开GUI窗口。
- 17个不同的独立语义控制完成。默认None与Union20比较结果逐字段相等；仅精确四尾节点剪除，三绑定/重复/错node/order/time/窗口内/额外第五题均Hold，full after digest仍完整。Q15候选顺序命中，rect集合相同但顺序错误及正文变化Hold；同序existing-fill输出与Union20相同。
- 四个实际保留尾节点的order/created_at机械进入scope。结构合法的39/40题序交换及创建时间变化，在采纳前Hold。真实四题ADOPT-only副本得到4条CustomerCurrentExistingRead/v1、16条副本接受，save begin/POST均0，旧12个ref保留。这不是平台本次保存或真实全16完成。
- 构建43新成员及12外部pin全部核验/隔离。11,176复用原件均核其冻结01成员声明与实际字节；4个作者副本用base+delta复原SQL/接受链/历史结果。未重跑旧213239成员大矩阵或旧成功/OCR/模型。
- 只读preflight退出0、READONLY_BINDING_PREFLIGHT_PASS、platform_calls=0、activated=false。原工作区11,176文件在副本测试和preflight前后字节一致。没有原工作区Store、live目录创建或profile文件读取；只对专用profile目录做既定元数据stat。

## 评审工具问题和限制

保留1次评审夹具错误：题序交换后未同步目录排列，先被validate_current拒绝；修正夹具后新鲜题序绑定控制通过。辅助脚本输出名替换又未命中，导致一份未冻结phase-A摘要被最终摘要覆盖；原预期sha `6cee8c74a60ab119b1f8d89ea4e7a1430ba9a9f90b67febda0676e2d30fc9bb4` 保留，但原始字节/耗时未恢复。第一阶段11个控制对象仍在最终结果内。最终摘要18条记录含1个重复，按17个不同控制统计。见raw/helper-correction-ledger.json；不冒称中间原件逐字节保留。这些问题未改产品、构建、01固定证据或真实现场。

本评审是同模型家族的独立新会话，使用共享本机runtime/文件系统，不是外部或异模型评审。旧132/10、大矩阵、GUI视觉实操、真实actual、完整16原生导出/展示和阶段ZIP/客户启动未在本轮重跑或接受。所有新实际上限和spent历史保持，Q13—16原来源归因UNKNOWN。

协调独立接收后仍须另绑一条新的精确0POST authority。代码/launcher接受不自动激活实际，也不等于阶段客户就绪。

## 最终证据资格补充

丢失项明确记为 **RAW_UNAVAILABLE**：首次phase-A的raw/semantic-controls-summary.json，原预期sha为6cee8c74a60ab119b1f8d89ea4e7a1430ba9a9f90b67febda0676e2d30fc9bb4。覆盖发生在首次independent_semantic_controls_r1.py的finally写出时；现存文件元数据为北京时间2026-10-25 16:17:15.2024934（这不是独立执行事件时刻证明）。已观察的stdout/工具输出不含完整丢失字节，原序列化字节/耗时未恢复；没有为冒充原件重跑测试。

本接受不依赖丢失字节、该sha作为已核原件、或丢失耗时。事务和现场关键证明以现存real-controls原日志/结果、nominal-success、前后索引及preflight为依据；语义证明以现存续接原输出中保留的11个前段结果对象和6个新控制、执行脚本/静态对比及30项定向测试原日志为依据。前段结果对象存续不等于完整原始中间摘要恢复。本范围内未发现因此缺失的关键证明；原actual和客户阶段仍未接受。完整现存文件sha清单及哪些结论不依赖丢失项见raw/raw-unavailable-qualification.json和decision.evidence_limitations。此前未冻结decision/REVIEW草稿原字节另存before-evidence-clarification文件，最终manifest将同时列明。
