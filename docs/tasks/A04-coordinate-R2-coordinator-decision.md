# A04 coordinate-R2 主调度复核：REWORK

2026-10-17（Asia/Shanghai）。冻结交付 `76898657e76ac2db071327e90c6ca5031d17571f` 的离线修复不接受、不集成；整个A04仍BLOCKED。

主调度核对[独立报告](A04-coordinate-R2-review-report.md)及333项清单，报告SHA256 `78ea0975444d3fbc278adf97944cfab3b2392e569f2d4d928abc01fb9eb545dc`，清单SHA256 `85dd149c08e055b3b8dcb4f380cd72cca1957a935edc219ee8da3b557f9a5567`。完成的验收对话和冻结释放记录显示35个自有工作进程结束；该记录不表示授权profile当前空闲。

新建35文件的原始Git字节隔离输入，重跑一个最小反例：37×29 PNG仅含1行像素，公共CLI仍退出0、生成最终包、公共loader接受。复现wrapper退出1表示缺陷确认，不是环境失败；[结果和命令](../evidence/A04/coordinator/coordinate-R2-review/checks.json)。没有重跑整套测试、访问平台或调用模型。

第一次预检发现复验临时checkout有33个仅CRLF/LF差异，未进入产品执行即退出。该临时目录没有非换行差异；复验归档自身清单仍有效。主调度另建确切字节输入后同样重现，不覆盖复验文件或把原临时checkout称为原始字节一致；[首次失败保留](../evidence/A04/coordinator/coordinate-R2-review/preflight-attempt-01.json)。

原24字节PNG、截断JPEG/PGM和状态声明修复的有限结果保留。新的缺行反例说明仅调用Pillow verify/load不足以闭合原图完整性；不以其他测试通过抵消该必需条件。后续一次有界[coordinate-R3返修](A04-coordinate-R3-rework.md)仅处理这个缺口，之后仍需独立复验。真实六项及I01依赖未释放，本地归档未推送。
