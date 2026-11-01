# A25 当前五题保存材料与计划顺序最小修正

当前正式接受的40个GET绑定书46007447第二课时印刷1–5题，历史全局17–21，当前native18–22。五稳定node/info与第一课时17题不重合；实际父目录仍为原第1课时目录，不移动节点。当前源闭环由协调根保存，本交付不重复采集、OCR或历史套件。

五题候选、人工看图审校、图像绑定和逐题计划位于私有目录 `D:/1800/.local/stages/a25-lesson2-expansion-20261023/post-manual-login-source/five-candidates-v2`。`targets.json` SHA256为 `eb3b29c28c80650674f7df24e523dcc7c05e27b6713eda78dec92910b074d792`。各题使用当前annotations返回的既有图像URL与rect身份，无上传、增删框或迁目录。第1、5题既有图像包含原文和图示；第2–4题使用既有图示框。历史JPEG像素仅与当前URL、页索引和框坐标绑定，不宣称新下载或远端像素新鲜度，图URL本轮未发起HTTP检查。

第1、4题仅改question；第2、3、5题改question及answer。第3题在原有question/answer框下补入缺失文字及答案4；第2题答案清理为D，第5题去掉答案开头杂点并保留原解答。正确的第1题答案、第2题choice和第4题答案保持原值。所有目录、全框、题框、info字段和未改OCR区保留；只允许既有写入器规定的目标info更新时间推进。

在实际五计划上发现批处理入口误用排序键的`core.write_new`落盘，原生缺失区对象顺序被改变，五份计划均在写入器校验中以`OCR_ABSENCE_NOT_PROVEN`拒绝。最小修正仅在`tools/run_usense_reviewed_batch.py`增加保序、独占创建、flush/fsync与落盘后`validate_plan`的`write_plan`，用于plan.json；通用报告序列化和包内运行时代码不变。新增一个测试覆盖五计划保序往返及拒绝覆盖。初始私有构建脚本误预期更晚的`PLAN_TAMPERED`而断言失败，另一个Python命令引号错误均保留；原未完成目录没有重写。

有限验证：五实际计划经该落盘函数往返并全部通过真实writer.validate_inputs；新增测试1/1通过；整批5题`--preflight-only`通过。原始输出和进程记录在私有`five-plan-validation`，`validation.json` SHA256为 `48169bd82711fbab23a3cf4fc5d2d5906e96cb964bd2dc5c08cd296c52812c61`。账本为空，网络0、浏览器0、保存0。包内implementation仍为 `5ddfe19c4cb0f2b98555c927a1d205f1165ab23ecac981896627445e29f3c2c8`。

实际执行命令由私有checkpoint给出，须由根绑定新的唯一写入authority并由同一正式独立及根验收本候选和最小差异。依次每题新鲜读取、一次commit POST、释放writer、不同进程/新context独立读取并完整比较；首个异常停止，后继NOT_RUN，不重发。当前实际保存与独立回读均NOT_RUN。sole1800-a保持PAUSED，旧失败、UNKNOWN和耗尽额度不变。
