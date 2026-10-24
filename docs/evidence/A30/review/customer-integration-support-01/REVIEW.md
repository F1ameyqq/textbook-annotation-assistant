# A30 客户图题与多段来源支持候选独立审查

结论：**ACCEPTED_OFFLINE_CUSTOMER_FIGURE_SOURCE_REVIEW_SUPPORT_ONLY**。

指定独立审查`01a16bf6-f61d-7f40-a4cc-2f1201f2ece3`接受本次固定支持候选的有限语义。06的“明确引用题图但没有来源图，普通内容确认仍给READY”具体REWORK，在此候选的状态、确认及生产前门槛中已关闭。原06失败记录保留；这不是最终09/formula合并版本或最终客户包的接受，`CUSTOMER_READY=false`。

## 固定输入

固定目录：`D:/1800/.local/stages/a30-customer-independent-20261024/customer-integration-support`。

独立隔离：`D:/1800-private/a30-customer-integration-support-independent-20261024-01/input`。

| 对象 | SHA-256 |
| --- | --- |
| source-manifest | `84a7ce611d679e3a51bf3891b64d56f6e3c3ec86460f8f92ce8621bbcdead5f8` |
| artifact-manifest | `1abb021936468b9f7ab61041edfc2564c9530125cdf9d036f2adcc9439ab0a2e` |
| fixed-result | `ea409e1005852605e4cbdd5b78303a6c5a8af9126f5f42167b5bfdc2e348d05d` |
| MERGE-INSTRUCTIONS | `8cf77c6723d9e8468a928e15968accd0a3908d18672304f56f6ca9d70dbebce8` |
| 仅图门槛合入09的patch | `205953e9f75c897508ac702defe6c0b05ea080b720f20688f42aa2563d3967be` |
| 从06合入review/UI的patch | `39dd6cfc52c2fb8791a1c3898ba3670f5dc057ec24ffcfa8b82c7eea83e226ab` |

262个固定成员已独立隔离并逐件核验；根侧262个raw副本也全部匹配。source分母220。相对07：7个文件改变、5个新增、208个原成员不变，无删除。仅从冻结对象读取，无活动作者树、真实workspace、profile或ledger访问。

## 接受的行为

缺图要求同时取当前分区文字、首次编辑前保留的`original_zones`、有效原graph片段及手动配答原文。明确图引用必须有对应题/选项或答/解析类别的图片来源绑定；图片必须具有匹配的原始哈希、尺寸、原始像素坐标和有效bbox，并经过来源确认。程序proposal本身不算确认。`BLOCKER`不属于普通内容确认可消除的集合。

`state`重算后展示`NEEDS_REVIEW`；`confirm`在保存READY之前重算；`produce`在建立transport或save intent之前重算。因此旧READY/no-issues字段或删去编辑文字中的图引用，均不能替代原来源图绑定。`quality.assess`和`native_plan.make_plan`也增加图门槛；native计划在没有graph参数时仍检查当前/原文字与平台来源绑定。接收的是已实现的明确图引用谓词，不是对所有自然语言暗示、全部图片内容和全部图数量的通用识别承诺。

图框proposal只从已有OCR行、不可变原图像素，以及有观察证据的题/栏/小节边界产生，不调用OCR或模型。开放续页、边界缺失等状态继续显式保留。低置信、触边或范围不确定的proposal不能直接确认；客户可在原页手动调整，再通过原`bind_region`入口明确确认。proposal路径和普通路径继续受当前head、来源页/角色、bbox、其他题区域不相交、当前平台状态等既有检查约束。绑定后仍需内容复核，LOW与公式UNKNOWN等质量信息保留。

多段来源按原graph片段次序展示，不重新按x/y排序；同一frame的非连续片段不会越过中间来源段强行合并。整区编辑不伪装成逐段编辑映射；重复、遗漏或无法匹配的来源引用保留明确issue。投影对象不修改candidate、graph或evidence，不产生READY，也不生成可自动应用的TeX候选。

## 新独立验证

新增4项Python检查及1项受控JS函数检查全部PASS，相关命令退出码均为0。见独立目录的`independent-python-result.json`、`independent-js-result.json`和原始命令/stdout/stderr。

1. 全新合成图题通过普通编辑入口删除可见“见图”文字；首次原文仍保留。普通确认仍HOLD，失败确认不改变head，状态仍NEEDS_REVIEW。
2. 新生成几何图触及已观察范围边界，程序产生LOW proposal；携proposal_id直接绑定被拒绝且head不变。随后以明确手动调整范围走普通bind_region成功，图缺失门槛解除但仍NEEDS_REVIEW，LOW置信与公式UNKNOWN质量原值保留。
3. 构造新READY候选，其图片声称已来源确认但sha256与来源页不同；正常produce在transport构造和save intent之前HOLD，二者均0。
4. 新三段源序列对应frame索引0/1/0，按原graph保留顺序及三个独立段；整区编辑维持无逐段映射。另一个无效来源引用同时保留缺失引用和遗漏graph片段的issue，不猜测对应关系。
5. 不开浏览器的JS函数环境验证LOW proposal即使勾选也不发请求；手动重画清除旧确认；明确重新勾选后仅生成一个普通`/api/bind-region`请求，使用当前head/asset，且不带旧proposal_id。

上述Python使用独立目录内新建Store与新合成图片；JS的图片、DOM及请求均为受控对象。没有旧OCR、旧浏览器UI、旧成功、旧实际或作者2个示例的重跑。没有网络、模型、浏览器、真实客户workspace或平台操作。绑定成功只证明程序路径及客户声明记录，不代表真实客户已审阅，也不证明图的数学内容。

## 06保留与09合并边界

06的`tools/customer.py`、客户启动文档及`orphan_groups.py`原字节一致。06 GUI-only部署入口及原workspace绑定模板继续有效；deployment manifest声明的8件与先前独立隔离06支持文件逐字节相同，未运行packager或启动命令。客户日常GUI不要求开发授权JSON。候选app内历史INNER START_CUSTOMER.cmd不是最终客户入口；最终包根入口必须由已保留模板渲染并传入原workspace。

review/UI增量patch在内存中精确应用到固定06，结果与此候选两文件逐字相同，06未归属段落支持保留。图门槛patch在内存中可精确应用到09的production/native_plan/quality；只改变produce、make_plan、assess所需门槛。其余函数AST保持一致，包括09正常reconcile、send_window_bounds、compare_readback、固定选择及逐计划node/info/rect范围保护。该patch不包含retained_readback.py。没有写出或执行合并产品。

**不得用此候选的完整07基底native_plan.py或production.py覆盖09。** 正式作者仍须保留09完整恢复/时间政策、06 GUI/orphan功能及作者公式worker/UI增量，只合指定门槛hunk，再冻结最终union提交有限实版本核验。本次内存静态合并检查不替代最终union审查。

`formula_roi_cache.py`仅为未连接的接口参考；所有源码无该模块import。此次未审查它的worker接线、推理、UI集成或迁移行为，未调用任何公式模型。公式worker仍属另一修改范围。

## 结论范围

06缺图falseREADY具体缺陷仅在本固定支持候选层关闭。原06正式报告及其反例保留：`D:/1800/docs/evidence/A30/review/customer-delivery-06/REVIEW.md`，SHA-256 `b058178e7087d5f66a1c78cc2c3ee15114f5c7bb24181073bf7662613e3b1f62`。

最终09/formula合并、最终包、真实客户输入运行、真实图绑定与平台保存、全课/全章/全书完成均NOT_RUN/未接受。此审查不改变并行09实际续跑、Q1原UNKNOWN/已耗尽授权或任何真实账本，不授权重发。`CUSTOMER_READY=false`，`1800-a PAUSED`。
