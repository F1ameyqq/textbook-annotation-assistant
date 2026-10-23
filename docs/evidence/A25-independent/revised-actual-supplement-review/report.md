# A25 完整实际归档：有限静态补充验收

补充结论：`ACCEPTED_STATIC_SUPPLEMENT_ONLY`。保留已接受的 `ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY`；本次不增加根因、当前来源、保存或新实际轮授权。审查完成并释放。

完整交付 final `b864f413c8bf971153afcefcb78f9621b70ba95f`；产品仍为 `afc9d761294203e7cfb8086a82f1a7fdd8724372`，launch `fef3638d5793347a2b70f21108f6c03ee7856bbc`。Git raw 清单 SHA256 `1634a45f71f7ce9c9feeabc81d3b3f0f641df12715fd337ff80a47e1fb3e3ebc`。

独立核验并隔离了71项：34 actual、30 source、6 supplement、1 supervisor；另从确切 final Git blob 核对6份公开交付。源码与前次已验30份相同，launch到final仅文档/evaluation变化。原21份raw的哈希全部包含，完整actual按哈希增加12项；旧checkpoint `1b1a98a1…` 和前次6报告+self清单成员未改。原件索引见 `intake.json`、`raw-manifest.json`。没有读取作者活动目录。

## 新材料的有限结论

| 新材料 | 核对结果及适用边界 |
| --- | --- |
| configure、config-binding、启动前观察 | configure进程exit0；217-byte stdout绑定已验8338-byte配置及相同SHA256，声明platform_ready=false、save_authority_created=false。独立记录中的40 JSON、原native18—22、印刷1—5、历史17—21、900秒及传输与既有绑定一致；启动前观察记录无锁/匹配进程。configure自身持有PID32296/56076已signaled、Job0、句柄关闭，与实际capture的PID52748/20684分开，不混计实际进程数量。 |
| 两次准备helper错误 | 保留的作者观察记录为两个exit1：预建evidence目录导致New-Item错误，以及预建configs目录导致WinError183。记录明确声明配置程序/实际轮未启动、budget_spent=0；原helper stdout/stderr未分别捕获，来源指向聊天工具响应。本次接受该诚实观察记录，不能将其当独立原始进程输出或补造缺失流，也不替换首次实际TLS错误或改变1/0。 |
| error-location、运行库原件、local-call-path-audit | 固定运行记录标示Python3.9.13/OpenSSL1.1.1n；ssl.py及_ssl.pyd原bytes/大小/哈希吻合。只读源码显示1310行调用`self._sslobj.do_handshake()`；产品静态AST显示76行wrap_socket只传socket和server_hostname，53/67行请求/响应头open对应原件均存在。没有确定的缺失本地路径可据此修复；不证明运行库完整健康或排除原生库/系统内部行为。未导入或执行复制的库。 |
| 现有代理日志摘录及监听元数据 | 仅一行292 bytes，SHA256 `ffa8b8e0aac6a428fa1e868c856213b99c752ed3988f2c0cd655da0ee2b86604`，时间13:12:14、目标www.usense.com:443、进程标签python.exe、规则GeoIP(cn)、出站DIRECT。该行有本地端口65085，但没有PID；本次探测未记录本地端口，故不能绑定到本次socket。13:22的监听者观察晚于实际轮，不能证明过去PID归属。只接受目标/时间窗口内匹配记录；它不证明TLS断链原因、远端中断或缺文件，也不证明直连已修复。 |
| 作者完整报告和evaluation | 与固定checkpoint、21份已验原件及本次新增材料相容：CONNECT响应200、TLS_HANDSHAKE内FileNotFoundError errno2、未取得leaf、无具体缺失文件名、根因UNKNOWN、业务0、browser/runtime未创建、1/0、save0、五题及ledger后继NOT_RUN。作者交付中的pending/formal_acceptance=false保留冻结时点，不覆盖后来本独立及根对checkpoint的有限接受。 |

日志搜索元数据限定到对应日期、13:11—13:13（Asia/Shanghai）/05:11—05:13 UTC及唯一目标，原搜索exit0、stderr0，只保留匹配行，没有整份日志。验收者未重新搜索当前日志、查询监听者、读取订阅/控制配置或访问网络；本次只能评价冻结摘录的范围，不能保证未记录事件不存在。

根转述用户直接确认B首课时成功来自另一电脑/环境。本次将其作为当前协调背景，未复查或联系B，也不从B成功推定本机环境、入口、代理或TLS已合格。

## 保留状态与执行记录

既有实际结论不变：本次authority `9a6bed2d-3025-4dec-b719-6c7762476134` spent1/remaining0、retry=false，业务响应0、save0；缺失文件路径和根因仍UNKNOWN。第二课时印刷1—5的当前node/info/实际父目录/来源尚未取得，候选、计划、账本初始化、保存、新进程读回及导出均NOT_RUN。没有产品改动、新测试、平台/网络/模型/OCR动作或新激活。

本次只运行输入拷贝/哈希与静态一致性helper。`intake.py` exit0；首版`verify.py`在Python3.9解析PowerShell七位小数秒时ValueError/exit1，后继语义检查未运行；原脚本与工具文本观察保存在`helper-first-failure.json`。新增`verify_v2.py`仅为时间比较截断到Python3.9支持的微秒精度，原时间戳文件不改，exit0。未重跑产品、已接受检查或实际轮。此helper修正不改变事实或通过改原件消除失败。

公开机器结论为`result.json`，固定交付哈希为`review-files.sha256`；私有隔离为 `D:/1800/.local/stages/a25-independent-20261023/revised-actual-supplement-review-20261023/`。原报告保持原bytes；未改根JSON/AGENTS/index、作者或原证据，不发送其他聊天/B消息，不自动开展后继工作。
