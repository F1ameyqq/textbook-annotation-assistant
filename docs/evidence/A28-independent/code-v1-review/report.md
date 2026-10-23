# A28 固定代码与生产launcher独立验收

结论：`REWORK`。固定提交 `48cbd114e59713d50438a478174b0b9396eee523` 存在一个阻断性身份反例：新题读回复用包内已证明存在的旧题info_id时，仍被判为接受。当前固定版本不能据此派发真实四题生产。先前四题内容及14张远端裁片接受结论不变；未执行平台操作，也没有发生已知线上数据损坏。

## R1：新题info_id可复用已接受旧题身份

位置：[lesson_insert.py:394](D:/1800/.local/stages/a28-independent-20261023/code-v1-review/workspace/src/annotation/runtime/usense_live/lesson_insert.py:394)，以及 [lesson_batch.py:140](D:/1800/.local/stages/a28-independent-20261023/code-v1-review/workspace/src/annotation/runtime/usense_live/lesson_batch.py:140)、[lesson_batch.py:202](D:/1800/.local/stages/a28-independent-20261023/code-v1-review/workspace/src/annotation/runtime/usense_live/lesson_batch.py:202)。

比较器只要求新info_id不等于唯一旧尾题 `TAIL_INFO`。批入口的 `accepted_info_ids` 从空集合开始，只排除本轮此前插入题的info_id，没有排除既有旧题身份。

独立控制使用本包冻结的实际13响应写前快照和已经接受的Q6候选，构造明确标记为合成的保存后响应及回执。正常新node/info、正确尾题顺移、完整框和内容保全的对照通过。随后仅替换 `q23_info.data.id` 为固定 `q22_info.json` 中的 `2110708481181396993`，其原件SHA256为 `f6490f9cc64ff0244a071958fc6b5a899853ef6cb3de6157f465235063c0751a`。这是A25已接受旧Q5/native22的info身份，不是一个新info。

反例返回 `ok=true`、`status=ACCEPTED_A28_INSERT_PRESERVATION`、`differences=[]`。它会将已存在的info身份当作新增Q6身份，无法排除旧题info被复用/覆盖。该问题发生在实际接受门，不是题号显示差异，也不涉及要求全书末尾追加。完整批入口没有补上这项拒绝；其首题空集合检查也会通过。

最小修正应把既有固定证据能证明的旧info身份纳入明确的保留集合，在新题身份接受前拒绝与其碰撞，并与本轮先前新题去重共同覆盖。至少应拒绝本反例的已知旧Q5身份；用已有固定身份材料绑定，不要求重做旧题内容/OCR或恢复旧额度。保留本反例及原失败结果。修正冻结后复核正常新身份和本反例，并核验受影响的批入口；无需重跑已通过的无关检查。

## 固定范围与完成检查

根索引SHA256 `02bf8bc293d38a7ffbc0c57499c7196ad95f21ba69d6d4e3c56076d525211758`；fixed-delivery SHA256 `dfc14eb0b86bc4a03f0f21e7c784a444d0137b60cf9c104d9cdffcf5d1cbf27f`；raw manifest SHA256 `67db3aee2ede4ee51dfd04bf70dee0cd094b238b33233025b90ea2c4c01ca52c`。208个根固定原件已核长度/SHA256并隔离；31个Git原始blob重算Git对象身份并核对指定commit的tree，恢复到独立源码目录。未读活动作者工作区。

与已接受A27基线比较，产品范围为两个新模块、两个新测试文件、插入writer和批入口修改及说明文档；`release.py` 与已接受基线逐字节相同。静态确认新writer调用 `close_framework` / `run_owned_writer`，已增加的释放/入口检查通过。

新增40项作者检查在独立隔离源码中全部获得通过记录，拆为首次35项通过及helper纠正后其余5项通过；没有重跑此前35项或任何历史套件。首次审查器将标准库Windows asyncio的本地socketpair误认外部连接，在第36项的测试setup阶段触发1个helper错误，后4项当次NOT_RUN；原stderr及伴随未完整初始化loop的析构异常保留。纠正仅允许标准库 `socket.py/_fallback_socketpair` 对127.0.0.1的内部通信，业务网络、子进程及活动profile/作者目录读取仍被拒绝。其余5项含被阻setup的那1项，0产品失败。另一次只读路径命令以错误cwd定位launcher失败，后续rg使组合shell退出0；此为辅助读取错误，不将该退出码当作launcher检查通过，随后从确切隔离路径读取。

独立控制结果为1个正常对照PASS、1个身份拒绝反例FAIL。发现首个语义失败后，余下独立连续运行、实际候选预检重演和launcher动态控制均标记NOT_RUN；未为了补齐计数继续测试。作者4个真实候选preflight原件和40/40原检查原件均已冻结接收，但不代替这个独立失败。

## 尚未释放的生产层

静态读到的入口顺序为四题逐题writer后新reader；读回20/27/34/41 GET，加每题writer前13 GET，合计174业务GET。launcher绑定4writers、4readers、8contexts、4POST、900秒、0login/0retry，并要求固定commit/manifest、原profile指纹、原ledger和一次性输出目录。此预算和launcher的静态绑定记录没有因代码反例获得正式整体接受，生产资格保持REWORK。

原正常题/框保全、锚点22的官方插入、后续顺移及已有五题复用范围保持，不要求全书max append。真实新node/frame、实际保存、fresh reader、9/9课时交付和原生导出仍未由本轮证明。独立方无网络/浏览器/平台操作，不改根JSON/AGENTS/产品/旧ledger/旧失败，不发B消息，未变更1800-a。

固定结果见 [机器结果](result.json)、[身份反例](identity-control.json)、[输入清单](intake.json)、[新增检查首轮](new-suite-process.json)、[新增检查余项](remaining-suite-process.json) 和 [报告清单](report-manifest.json)。反例原始plan、两个after、回执与比较结果只保存在独立私有目录。
