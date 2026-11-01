# A27 R1：Windows 等价 profile 路径占用检查

在原候选 `23591811be71f9598c07c09b6a25a2a5fb066db0` 上作同一任务最小修订，正式独立复验待根派发。原候选的独立结论为 `REWORK_PROFILE_EXCLUSIVITY_GATE`，不能因其他有限检查通过改称已接受；原23591811、固定输出、root-frozen和全部原失败保持不变。

固定独立结果 SHA256 `16d2e26e92d09437eda81fe1d4af6c92eab26b428992420cefabd2e173c13971`；精确 witness SHA256 `616fd5b65ed843a4446bd0651696281c9d766cccebccd5bb273f8eaf22fe5824`。其中 OS samefile=true 的 `parent\.\profile` 被旧字符串包含检查误判为未占用，两次观察后确实分派 configure/capture。本执行先在原产品实际恢复入口复现同一 FAIL，原输出单独保留。

产品仅改 `tools/run_usense_postsave_readback.py` 的占用识别：用 Windows `CommandLineToArgvW` 解析引号/反斜杠和 `user-data-dir` 参数，释放解析缓冲区；然后读取目录元数据，比较 `st_dev/st_ino`，不读目录内容。这样 `.`、`..`、分隔符/大小写、带空格引号、扩展本地路径等实际指向同目录的形式无法被文本差异绕过。重复参数、空值、相对路径、非目录或无法取确切目录身份一律停止。显式 UNC/非本地盘路径在 stat 前拒绝，不由进程参数触发 UNC 查找。无 data-dir 的子进程仍通过完整 OS 枚举与所属浏览器行共同观察，未删除前后两次检查。

只有确为不同现存目录的参数才可放行；相同文本前缀但不同目录不会再被误挡。首次观察发现等价占用时，在 spent、输出目录、configure/capture 前拒绝；第二次发现时保留已消费状态及 configure 记录，capture NOT_RUN。没有增加重试、写操作、ledger 修补、旧预算恢复或新的真实权限。

新增8项（含等价形式和拒绝反例）通过；必要受影响2项通过。另用指定 witness 的原命令行/合成目录原件核得 `RECOVERY_PROFILE_IN_USE`，并把其已核 `\.\` 构造绑定到新合成实际恢复入口，分派0、spent0。独立原件5份逐hash冻结，原 REWORK/两次matched0/configure+capture 事实保留，不改原 witness。

本修订保留一次新增夹具 FAIL：手写带末尾反斜杠的引号串把末尾引号变成字面字符，产品已保守拒绝为 identity UNKNOWN，而夹具误期待 IN_USE。只将该夹具换为 Windows `subprocess.list2cmdline` 正确转义，原脚本/输出及后继 NOT_RUN 保留；未放松产品解析。旧20/9/194和真实成功实测均未重跑，未扩大到其他产品修订。

所有输出使用新目录 `D:/1800/.local/stages/a27-batch-stability-20261023/r1-profile-equivalence/`；最终commit、Git raw依赖及清单摘要由新固定交付给出。没有启动Edge、查询真实进程、访问真实profile/ledger、请求平台或OCR，未改A26/根源码state/自动化，sole1800-a按任务保持PAUSED。目录身份检查只在合成目录实测；真实运行仍NOT_RUN，等待同一独立对新冻结候选复验。
