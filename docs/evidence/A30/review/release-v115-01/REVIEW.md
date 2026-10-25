# A30 v1.1.5 本机阶段包独立验收

结论：**ACCEPTED_OFFLINE_CUSTOMER_PACKAGE_V115_CANDIDATE**。只接受精确ZIP/发布树/源码/普通入口/说明及固定打包报告；不接受首次START或业务actual成果，customer_ready=false，1800-a保持PAUSED。

ZIP SHA256 `d3abd4e5670fe82a103aad14b3f69774b92944da5bca74ff6853aff223805bf3`，2741285字节；release manifest `66c811ba5497b7134aad143a668db4988170808d5b744c09e83632d3a7e05f77`。源码为已接受02 `0095d385936969fe45e38b092e0095ab60465e41f54b37acbe076b8f37601d6f`；固定报告manifest `1531cdc360150a8700e8a74d623b85c344ba6f00398c246a82be80a6547c15f1`。

## 独立核验

- 266文件=254 app源码+12个根元数据/锁文件；release manifest除自身覆盖265。ZIP、发布树与全新私有隔离副本逐文件sha/bytes相同，app集合和字节精确匹配已接受source-manifest，无未声明代码。
- 单一根目录；路径穿越/绝对路径/Windows危险文件名、重复、大小写冲突、符号链接和加密检查通过。唯一声明二进制为既有嵌套识别ZIP，6成员安全。无额外私密capture、workspace DB/blob、profile、authority、可执行二进制。
- 精确声明的本书缓存仍在包内，这是本机书籍专用交付，不是无用户数据的通用发行。有限JSON/编码JSON/嵌套档案检查无凭据、auth字段、JWT或私钥命中；236个base64 JSON对象已解析。没有泛化为万能secret扫描保证。
- START与已接受v1.1.4字节相同，只进入普通customer-deployment GUI；环境、入口、原DB/settings缺失即停止。默认不自动登录/生产/识别，不默认忽略证书。普通恢复由共享程序从本机材料处理，客户不填技术JSON/IDs，不依赖agent逐课工程准备。
- 新副本上有限导入store/production/retained_upgrade及--help通过；阻止Store、GUI、SQLite、子进程、网络及原workspace/profile读取的守卫无命中；副本266文件哈希前后不变。没有运行START、GUI、浏览器、模型或业务。
- 后送打包报告13成员及manifest自身核sha/bytes并隔离复制；22个冻结准备成员、plan/builder和3条源码接受pin闭合。ZIP/报告/源码的身份对应一致。此前包检查未重跑，也没有大回归。

## 时点和未证范围

包内带日期的准备快照正确保留：本课11已接受；Q12原UNKNOWN/原reconcile FAILED、待保留恢复；13—16现存待采纳、来源UNKNOWN；全16导出/展示NOT_RUN，客户总工时/人工NOT_MEASURED。61历史审校事件不是客户人工数，旧九题是另一保留范围。

协调最新消息说明唯一0POST actual（授权前缀78a99d28）已在开发对话执行。这是外部正在运行状态的协调声明，本评审未观察、运行或接受它。打包报告内actual未激活/未运行文字是较早冻结构建时点事实，不用它声称当前平台actual仍未激活；也不为此改写包内快照。全程不读取真实workspace或浮动actual输出。

首次新包普通START、窗口就绪/本次自身释放、固定实际恢复/采纳/全16原生导出和显示、最终customer-ready均未接受。实际独立接受后应以外置sidecar绑定本ZIP hash和最终成果，旧ZIP保持原样。包依赖已有本机runtime/base/models/Edge/profile/workspace；跨机器、任意书范围及整章整书未验证。

同模型家族、独立新会话，使用共享本机环境；不是外部或异模型独立。源码02已披露的评审中间摘要RAW_UNAVAILABLE限制仍保留，审包没有改写它。本轮产品/包检查没有新增失败或跳过项，未跑层如上逐项列明。
