# A30 Union18 边界修复有限独立审查

结论：**ACCEPTED_OFFLINE_UNION18_TEXT_BOUNDARY_PRECISION_AND_INITIAL_BOUNDS_REPAIR_ONLY**。

固定18 manifest `4bbb88831bc13d581b8e102a580d05c7a14356d6b1783b56fc602d12b4bad45a`，report `e64713f4634979b90deb0a65a99ace61ff2d099663223bceb63e6c2023ce20b4`。接收输入沿用生产审查私有冻结副本 `D:/1800-private/a30-full16-v62-launch02-independent-20261024-01/input/union18`，本次最终按清单逐字节重新核对；没有读取活跃作者源码。

17→18 仅 `src/annotation/recognition/review_ui.js` 改动并新增一个作者检查；全部 Python 原字节相同。14 已接受框收窄/未保存题限制/来源历史/失效确认/普通UI绑定矩阵按字节复用，不重跑。17 当时因空输入反例 first-error-stop 而未验的原框回调后端和定位信息，本次作为新增差异检查完成。

新增独立四组通过：

1. UI使用14实际普通adapter生成的纯合成state，而不是作者的手工UI状态。四坐标分别清空、空格、小数、负值、零宽/零高、越页、NaN、Infinity 共13个无效输入，均清除完整性勾选并清空旧框，重新勾选仍发送0。绕过input事件直接修改输入框，空值与不同有效bbox各被保存时重新核验拒绝。恢复有效1像素变更后，未重勾选发送0，重勾选后只发送1个模拟请求，bbox/head/answer/source-region身份精确。共16情况通过；真实HTTP/浏览器/模型/平台0。
2. 新合成三题31/32/33，book872541、760×980新图片。Q32答案最初[60,310,430,360]→收窄[60,315,430,355]→回调[60,313,430,358]，允许在最初范围内恢复；两层原框历史逐项保留、正文/来源/识别和其余两题不变，确认失效；确认前纯计划拒绝，重新确认后计划使用新框。
3. 扩出最初边界拒绝。原始历史中的asset、source hash、fragment ids、content_type四种不一致均拒绝，head/SQLite保持该次尝试前的原字节；未触及原14已经接受的旧矩阵。
4. 新合成旧框重叠案例，纯计划报错精确包含第32题、答案、来源页89、来源框2、返回本题审校；原重叠判断不变。生产审查另用AST证明native_plan只改报错内容。

原17 FAIL与报告完整保留，仅固定18关闭该反例。旧v59 Q7冲突由独立的v62/launch03范围接受关闭，不能将本UI结论当作实际保存或客户交付成功。未执行实际GUI/model/OCR/platform、未修改真实workspace或settings、未重播成功保存或消耗旧authority。

初次后端合成夹具在准备确认时被现有答案识别规则拦截：答案以 New 开头，不符合未修改的 semantic_value 首字符规则，得到 UNASSIGNED_ANSWER_OCR_LINE / ANSWER_MISSING_OR_AMBIGUOUS。原失败和后继NOT_RUN保留；仅将新建r1夹具前缀改为 Answer，原产品字节未动，随后三组新增后端检查通过。另一次猜测测试文件名的读取失败保留于helper分类，不构成产品测试。

全客户包需基于18重构建并另外核验实际启动；本次没有做该动作。CUSTOMER_READY=false，1800-a PAUSED。已接受的 v62非UI生产/launch03 有限范围继续有效，本UI审查本身不激活新实际授权。
