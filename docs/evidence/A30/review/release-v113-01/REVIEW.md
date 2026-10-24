# A30 v1.1.3 本机包及普通入口有限独立审查

结论：**ACCEPTED_OFFLINE_CURRENT_MACHINE_V113_PACKAGE_BYTES_AND_ORDINARY_ENTRY_ONLY**。

接受当前固定包的源码/ZIP字节对应、普通根入口静态接线、说明和声明缓存边界。没有发现本有限增量的阻塞项。实际根 START 启动、认证恢复和业务完成尚未由本审查证明；CUSTOMER_READY=false。

固定输入：

- ZIP `D:/1800/.local/releases/A30-v1.1.3-customer-local-win64.zip`：2711918字节，SHA-256 `b8044d97d17f51790dd5faa92147db88e3b96533bacbe79d4973448c5b727dba`。
- release-manifest `95ece106ff41ad6752e6d7d0c23b57bbf9e800e24d8e8cc88182d5ddd0690a43`。
- accepted18 source manifest `4bbb88831bc13d581b8e102a580d05c7a14356d6b1783b56fc602d12b4bad45a`，原有限UI/生产接受保持原范围。
- support artifact-manifest `cb01b51a6f5cb464d902f41779b6292cbc50b554129149f95e8ac05b08238a74`；fixed-result `0309ecde5c483cd2ab0360ee3d260c0c60d5da369306805c15b87233c69481a3`；candidate-build sidecar `7bb620ee8553301825d7d3238eef8fdceef5370f58a27b113b68e0912e809260`。
- 私有审查目录 `D:/1800-private/a30-release-v113-independent-20261024-01`。290个原送审输入加1份精确hash绑定的固定root18接受回执，共291个；最终全部重核。

逐字节接收确认：包内246源码成员精确等于独立保存的accepted18，未混入其他app文件；release目录258文件与ZIP258条目一一相同。ZIP唯一外层目录 `A30-v1.1.3-customer-local-win64/`，排序、大小写唯一、相对路径、无穿越/反斜线/符号链接检查通过。相对v110只有已接受产品差异、四个新增测试与版本/状态/说明元数据；无删除。未重新执行产品测试或中间版本。

新增四组静态检查PASS：

1. 打包器、PACK-FINAL.ps1及五项精确缓存叶允许清单与v110已接受原字节相同。9项支持输入hash匹配，255项初始打包文件保持原字节；finalizer只新增候选状态/缓存边界并重写该新包自有清单。固定打包/finalizer执行记录均exit0，build-result与ZIP外candidate-build逐字节一致。package-record里的zip=NOT_CREATED是旧阶段记录，不覆盖或冒充后续ZIP结果。
2. 根 START_CUSTOMER.cmd、app/tools/customer.py、app/runtime/customer-runtimes.json 与v110原字节相同；两依赖锁和CLI参考亦相同。runtime-reference只有解释性product_runtime_binding文字变化，所有外部运行时路径/身份引用不变。START与START_HERE可由固定模板、版本、源码hash和三项交付值精确还原，无未填写占位。原workspace显式绑定、缺失即停止、无替代workspace回退；customer-deployment只内存合并运行时的既有静态结论复用。
3. 11份本书缓存和BOOK-DATA-CACHE-BOUNDARY原字节与v110完全相同，无新增缓存叶；复用此前有限检查：15份JSON（含5份嵌套JSON）与嵌套JPG类型等。没有重扫旧成功，也没有将其提升为全面秘密保证。整个包排除settings/state/credentials/cookies及profile/ledger实际目录；不额外复制原workspace/profile/ledger。源码内文件路径字面量或来源历史引用不等于复制其外部内容，本轮未打开这些外部对象。
4. accepted18 formal manifest和固定root回执hash/范围一致，原非UI生产范围保持独立。候选状态、build及最终sidecar模板都保留CUSTOMER_READY=false、4题已接受/12题待生产、全16未完成、START NOT_RUN；公式执行记录不提升为内容批准。401/零保存声明与已独立接受f450固定失败一致。包中“账本对账中/PENDING”是构建时状态；已完成的f450有限失败审查由后续单独回执补充，不涂改固定ZIP，也不把当前状态解释为可重启f450。

普通一页说明加入官方页面用户自行登录、保留原目录、不交密码、不清数据或放宽证书；401停止后回原任务、不盲目重发，UNKNOWN保存只读对账。新增原图1像素微调和最初边界内回调说明对应accepted18，保存后必须重新核对确认。实际开启该入口、操作登录按钮、访问profile或平台均未发生于本审查。

这仍是依赖本机既有双venv/基础Python、四模型、Edge、原workspace/profile/ledger的本书数据包，不是跨机即用发行包。外部依赖当前可用性未重验。启动说明不是新业务授权，候选状态也不是额外程序锁。后续若执行只读普通START观察，应另冻结真实入口、原任务/既有结果展示及退出释放原件供实际审查；不能用本离线接受替代该证据。登录完成也不能证明后续保存。

本次产品/打包器导入或运行、GUI、OCR、模型、浏览器、平台、新登录/授权、旧测试与旧扫描重播均0。没有新审查助手错误。原v110助手错误、17 REWORK、f450 HTTP401/1耗尽0剩余、1147及其他历史FAIL/UNKNOWN、旧9/4成功不变。完整16生产/导出/显示和客户总时间/干预尚未成立；1800-a PAUSED。
