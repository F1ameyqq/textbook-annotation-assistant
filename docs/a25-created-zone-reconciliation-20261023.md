# A25 首次创建区对象键序的有限对账与剩余两题

原唯一五题批次已在native20（印刷3题）严格回读失败时停止：3次提交均有精确成功原回执，native18/19完整匹配，native20仅question/answer的data对象键序不一致，native21/22为NOT_RUN。原批次1/0、原失败、第三未决intent和前两accepted标记不改。202实际原件固定清单SHA256为`a72cc4a6d4f63c6eb2d3e5393ad031d38a9fb12d2d97cbf81771871dcd131eae`。

新增纯函数`reconcile_first_created_zone_key_order`单独对账：先保留原严格比较，仅在本计划确实从absent创建的区、expected键序为`rect_ids,ocr_result,success`、actual键序为`success,ocr_result,rect_ids`时，逐字段用原`json_same`证明字段集、类型、全部值、嵌套对象序及数组序相同，再重排私有expected副本。完整快照再次严格比较，仍只沿用原单字段单调时间戳政策。原plan、after和after hash不改；全局`json_same`、`differences`、`validate_plan`、prewrite、原严格compare入口、发送器及revision均不放宽。私有比较函数增加可选expected副本参数，原入口使用默认原计划expected。

现有第三题12原始回读、writer发送前12原响应、精确回执、双层一次POST、不同PID/context、writer退出后所有读回时刻、释放、源页/目录/全框、原失败产物和未决intent逐一绑定。六字段全部类型和值与原计划相同，两处新建data键序是唯一差异。完整对账产物`third-reconciliation.json`位于私有`post-manual-login-source/created-zone-reconciliation`，SHA256为`3895f347d8f5eeb328e070ec830a9d1be73e0d939f452f51712a2729f6cba0f9`。它不是`acceptance.json`，不充当revision predecessor，不写accepted标记，不赋予补发权限；正式与根接受后如需账本收口，由根另派发。

新增边界3项测试及16个反例控制通过：保留文本（含空白）、类型、字段集、未知字段、数组顺序、其他对象顺序、时间戳及既有区的严格性。隔离模式fixture导入首次失败及原测试文件、原stderr保留；仅修正测试导入后运行新的边界，未重跑旧套件或OCR。

剩余manifest只含印刷4/5、native21/22，SHA256为`769ea9b78906f689776613942799581966a9a0e690e62cc1af8e43117988f6c7`。复用原已审候选/计划及完整来源引用，均`previous_acceptance=null`，自身稳定分支为空；非空账本中的前三题原文件全部保持。两计划与原五题包中的对应计划逐字段、类型和对象序完全相同，保序落盘后通过本次纯batch.prepare。原基线仅用于未触及的21/22及共享目录/框/源，实际每题仍须writer新鲜读取12GET后才可发一次POST。

具体2题命令在私有`remaining-two/save-readback-plan.json`，要求根另绑定独立新authority（最多2POST、2reader、4context/4TLS probe/48JSON GET、900秒整批监管），原五题批次不恢复。当前新增平台动作0、账本改动0；sole1800-a保持PAUSED。
