# A18 固定当前前端只读适配独立预检

结论 **ACCEPTED_OFFLINE_ONLY**，`acceptance_basis=BOUNDED_READONLY_PREFLIGHT`。本结论仅支持调度对本固定 A18 产品绑定一次有界只读观测，不证明认证、书源库存、原图、正文/schema、真实浏览器/native行为、保存或生产资格。本验收已释放；没有创建决定、activation或live。

## 固定版本及输入

- 基线 `5aec24575a0e1621f4f22680da3beba581e6cec2`；产品 `45174e312ad23af349b3345be23eadb7f6a5e498`；final `a1dae2efb49f39700194f912bf4ce8404950699b`。
- 产品workflow `bb163ba162f32857202b6a068e9fc050ed4ad9f4`；本次复核派发workflow `dbb3122383e5138fb1be8d053bf956c32928f970`。
- 候选SHA256 `c0f7ea30ee5a3484544524b5e8c609125113a474d901bd24fc600529509ae8e8`；正式执行 `01a15954-3ca1-76a3-a984-13229a985976`；正式独立 `01a15954-997c-7af2-9645-a4e2c2b25e76`。
- 本次任务SHA256 `f77bee32246b848121b9657fa5a0a4b894e6670ad5c6db23dfc5f25552af11cd`；调度输入清单SHA256 `f9c9c1b40f691fceaaf94d5d8f1d0bee9086303dcf4dbb3f3f0f521725c4f2c1`。
- 只用 `D:/1800-worktrees/a18-independent-fixed` 的67份固定raw；先后核长度/SHA全部匹配。候选22依赖、作者59交付成员及清单SHA也分别核实。作者`release.json`声明离线未建真实资源并冻结，本验收不访问活动作者目录。
- 全基线31599成员仅四获准产品修改、30374旧evidence保全及0删除，引用本次调度已完成的原mode/type/blob核证和固定`product-preservation.json`；本验收没有另做全历史Git扫描，也不声称由新suite证明全历史保全。

## 实际新差量与有限控制

使用CPython3.9，以新独立`review_runner.py`载入固定新测试模块。候选测试工具原输出路径保持不动；独立runner只写本输出目录，并使用纯内存selector/事件循环，封锁socket连接、urlopen、Popen、真实native加载、profile binding及occupancy。没有启动launcher、产品子进程或旧suite。

| 检查 | 实际结果 | 证据与含义 |
|---|---|---|
| 新A18差量 | 20/20，937ms，0FAIL/ERROR/SKIP | `delta-result.json`、`stderr.txt`：双层拒绝/顺序、硬停、版本单次/并发、混合16/17预算、拒绝异常、被拒响应、晚到fatal、回调结清、A18绑定。 |
| C1 | PASS | 实际候选22成员核证；真实固定报告模板与gate的19个scope字段一致；仅内存构造有效文件值，逐字段改报告且重算hash后仍拒绝，证明语义绑定而非只测digest。 |
| C2 | PASS | 重复同URL版本请求的native networkId关联；第一次预留一次，重复failRequest，若被拒请求出现响应即停止，0正文提取。 |
| C3 | PASS | close期间被拒版本响应进入最终ERROR/退出2；所有后继NOT_RUN，body/schema UNKNOWN，production_ready/write_eligible=false。均为fake对象、内存保存。 |
| C4 | PASS | 安装前主框身份缺失/有parent时不启用Fetch；原主框身份改变进入停止。所有CDP/context方法为fake。 |
| 4独立控制合计 | 4/4，219ms，0FAIL/ERROR/SKIP | `delta-result.json`的`independent_records`；没有用真实activation或路径落盘。 |
| 固定输入与源码 | PASS | `fixed-input-source-audit.json`：67raw/22依赖/59作者成员在差量后全部匹配；Script 3065996字节、SHA及24标记offset一致，并核了包含函数的实际调用关系。 |

具体P0–P7检查索引见`checks.json`。测试不是通用回归；旧30/34/11及其他旧suite运行0，历史NOT_RUN保持，没有将作者首run失败重标通过。没有借旧suite计数扩大本轮证明范围。

## 安全及事实结论

未知同源非API GET XHR/Fetch仍在两个屏障拒绝发送；只有原主框、原站规范HTTPS、无redirect且原唯一分类PATH_BLOCKED的窄分支允许拒绝后继续。protected/API、已知六GET参数/书ID错误、样题、登录、未知写方法、导航/第二导航、其他origin、身份缺失及WS等仍停止。共享预算在await前记账，CDN/未知同源/重复版本总16事件、双层各计一次；第17次仍拒绝并fatal。

精确版本静态GET只接受`/qieti/version.json`及唯一原样13位正十进制`t`，Fetch/XHR，各层首个保守预留且native发送预留最多1，后继拒绝并扣共享预算。版本变化的reload仍被第二主导航守卫阻止。代码依据为单一已捕获Script的端点offset3064125、fetch3064330，且已核mount后fEt→ED(initialize)→uEt、Date.now、no-store、JSON及reload分支。该证据不证明A17实际被拒XHR就是此路径。

六GET的已声明wrapper/参数在相关片段得到支持；未取得必须修正的新参数依据，因此六GET保持原样。未知响应schema、实际触发条件及OSS本地构造分支不能变成新API/manifest资格。wy正文GET和E6e保存POST仅静态接线线索。新诊断未知path只留不可逆hash、已知路由只给安全模板，query值和未知参数名不输出；对应敏感哨兵负例通过。

A18 candidate/scope/run_id/workflow/executor/决定/报告/activation/输出及version1/共享16绑定核实；旧A17 activation及篡改字段拒绝。正式机器报告按固定模板填写，canonical报告路径由调度归档使用，本验收只写隔离输出。

## 保留限制与释放

- 仅有限内存fake transport及静态字节证明；实际context/native交互、认证/目录/框库存/两原图/正文和schema仍待唯一真实轮。库存不能从历史或脚本推断；sample0、自动schema=false、body/schema UNKNOWN、production_ready/write_eligible=false，原R02未修保持。
- 作者首次Windows asyncio socketpair离线守卫失败及原始runs/raw-checkout全部保留。正确拒绝/ERROR且原始原因完整的细微报告归因残留按既定实践记录限制，不额外制造阻断；未关闭旧A17/其他阶段的UNKNOWN或失败。
- launcher自身OS创建/退出身份、旧计时差、辅助发送总数等历史UNKNOWN保持。本验收未启动launcher，不据离线命令结束宣称真实资源释放能力已获新平台验证。
- 用户同类专用context临时TLS持续许可保持；调度仍需固定A18自己决定与activation，限1轮/1context/1主导航/900秒含释放，六GET及viewer14/173两原图各最多一次，精确版本静态GET至多1。原session/static范围保持，总HTTP不混称8或9次。不重复问TLS，不自行激活。
- 0真实browser/network/profile/credentials/native/occupancy/login/business，0产品子进程/Job/handle，0B或外部联系人消息。没有进程kill/清锁/换profile/重放Q22/书级提交；其他三例HOLD。

`release.json`记录本轮命令已结束、无持有的真实会话或占用。所有固定输入在运行后再次核证未改；新输出raw清单`sha256-manifest.json`排除且仅排除自身，供调度归档和绑定。无产品修订、根JSON更新或集成操作。
