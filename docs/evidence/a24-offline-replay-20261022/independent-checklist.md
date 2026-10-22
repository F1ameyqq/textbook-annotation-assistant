# A24 可移交离线重建重放包：独立验收清单

适用范围：只审查和重放待交 ZIP；禁止浏览器、平台请求、live owner 启动、共享 B 仓库修改或 push。所有解包、重建和测试只进入本质量工作区的新目录。

## 1. 收件与 ZIP 安全门

- [ ] 记录 ZIP 的绝对路径、字节数、SHA-256；只读保留原 ZIP。
- [ ] 先枚举 central directory，不直接解包；拒绝加密成员、损坏 CRC、非普通文件/目录、symlink、reparse/special-file 标志。
- [ ] 对每个成员同时做 POSIX 与 Windows 规范化；拒绝绝对路径、盘符、UNC、`..`、空段、NUL、ADS 冒号、反斜杠混淆、尾随点/空格、Windows 保留设备名。
- [ ] 拒绝原名重复、大小写不敏感重复、Unicode/分隔符规范化后冲突、文件与目录前缀冲突。
- [ ] 核对成员数、单文件大小、总展开大小和压缩比；异常膨胀立即停止。
- [ ] 只有所有静态门通过后，才在一个事先不存在的专用目录中逐成员独占创建；不得覆盖任何已有文件。

## 2. 基线 522 与原 manifest 绑定

- [ ] 原 manifest 自身格式、记录唯一性和声明哈希可验证；路径集合无重复/冲突。
- [ ] 基线恰好重建 manifest 声明的 522 个成员；不得把 ZIP 目录项、脚本、覆盖层或报告混入 522 分母。
- [ ] 每个基线成员逐项核对相对路径、字节数、SHA-256；无缺失、无额外、无内容漂移。
- [ ] 原 manifest 的来源身份（选定 A 发布/既定 manifest hash）与此前冻结证据一致；仅“有 522 个文件”不能通过。

## 3. 三覆盖文件与 effective manifest

- [ ] 覆盖清单必须恰好声明 3 个文件，并给出目标路径、基线 SHA（若为替换）、覆盖 SHA/长度和来源说明。
- [ ] 每个覆盖字节必须与已接受的独立产物或作者交付哈希一致；CRLF/LF 若造成差异，必须同时报告原始字节哈希与规范化比较，不能静默归一化。
- [ ] 覆盖目标只能落在重建树内；拒绝任意额外删除、移动、未声明新增或第四处修改。
- [ ] effective 路径集合必须严格等于“基线路径集合 − 被替换路径 + 已声明新增路径”；逐项复算 effective 长度/SHA。
- [ ] effective manifest 必须由实际重建结果验证，不能由覆盖声明自证；manifest 自身不得列入被验证源码分母，除非格式明确这样定义。

## 4. 只新目录、绝不覆盖

- [ ] 分别使用全新的 `extract/`、`baseline/`、`effective/`、`test-output/`；任何目标已存在即停止。
- [ ] 重建脚本不得写入 ZIP 所在目录、固定 A/B 仓库、作者工作区、用户 profile、TEMP 之外的隐式位置。
- [ ] 重放前后对共享 B 仓库和固定 A 发布做只读哈希/状态快照；不得修改、提交或 push。
- [ ] 重复执行必须因已存在目标而拒绝，或由调用方指定另一个全新目录；不得原地覆盖更新。

## 5. 离线脚本、MemoryPolicy 与权限边界

- [ ] 先静态检查脚本：不得启动浏览器、Windows 原生 viewer、live owner、HTTP/client、socket、DNS、上传、登录、刷新或平台请求。
- [ ] 不得读取或复用历史 authority/activation/owner JSON、cookie、token、浏览器 profile、会话目录或私有 live capture；离线测试只允许自带 synthetic fixture。
- [ ] `MemoryPolicy`/等价 guard 必须让任何真实文件外部 I/O、网络、进程/浏览器启动尝试 fail-closed；只放行重放根目录、bundled Python 和明确测试所需的内存/临时路径。
- [ ] 运行时记录进程命令、cwd、Python 路径、TEMP/TMP、环境中影响导入/网络的关键项；使用规定 bundled Python 与 canonical long TEMP。
- [ ] 若脚本需要不在 ZIP/系统现有环境中的依赖、下载或安装，立即停止，不补装。

## 6. 实际重放与有限合成回归

- [ ] 实际从 ZIP 在新目录完成：安全解包 → 522 基线验证 → 3 覆盖应用 → effective manifest 验证；不能只读脚本或报告。
- [ ] 仅运行约定的三组有限合成回归：7 项 controlled capture、10 项 current-body gate、4 项 book snapshot，共 21 项。
- [ ] 每组记录发现/运行/通过/失败/错误数、精确命令和退出码；不得用旧回执代替本次运行。
- [ ] 4 项 book snapshot 必须包含第三 GET 失败负例：前两份保留、后续不发、无 POST、adapter/写资格不解锁。
- [ ] 不运行旧大型套件；若任一有限测试触发真实 I/O、live authority 或工作区外写入，立即终止整次重放并保留失败证据。

## 7. 文案与最终判定

- [ ] 包内报告、机器回执和脚本输出必须保留 `CURRENT_SCHEMA_UNBOUND`、`write_allowed=false`、`successors=NOT_RUN` 与总体 HOLD 边界。
- [ ] 不得把合成 PASS 描述成真实 schema、完整旧题分母、网站保存效果、独立 reopen、人工或官方验收。
- [ ] 没有真实 book/directory/fullframes/natural_export 时，最终结论最多为：`PASS_OFFLINE_REPLAY_ONLY_LIVE_HOLD`。

## 立即停止条件

出现任一项即停止，不继续解包或执行：路径逃逸/规范化冲突、symlink/special member、清单不一致、覆盖数或目标不符、已有目标将被覆盖、脚本含 live/browser/network/authority 复用、依赖下载要求、工作区外写入、任何真实平台 I/O、HOLD 文案被提升为 VERIFIED/ACCEPTED。
