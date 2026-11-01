# 一条命令运行A24只读适配与读回

2026-10-22，Asia/Shanghai；B输入 `d3b753d`。本轮直接交可运行入口，不要求手工重建A24或叠加历史补丁。网站无写入。

在仓库根目录，使用已有Python及Pydantic/Pillow依赖运行：

```powershell
python tools/run_a24_readonly_trial.py --sample-46007447 --input "$env:USERPROFILE/Downloads/46007447_paper_questions.jsonl" --out data/runs/a24-trial-001
```

`--sample-46007447`固定的是**10月16日历史原件**（11,625字节/SHA `02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c`）；文件不匹配立即拒绝。加 `--line 1`只处理原文件第一行，不将行号当平台题ID。输出目录应为新目录；私有正文保存在本机，不推送。

- `private/records.full.jsonl`：原始选中行字节。
- `private/records.adapted.json`：question/option/answer原值及全部extra字段、字段顺序、空值状态。
- `public-summary.json`：不含题文的来源、字段状态、摘要及可选预检诊断。
- `readback-receipt.json`：磁盘读回摘要；canonical ID仍null、write_allowed=false。

当前实际有界验证：主会话最终v3的6项测试通过；经打包入口实际运行全部19条及第1行，各exit0。独立标准库读取重建原值/extra/字段顺序均一致。质量成员独立确认成功路径与失败路径；首版precheck校验过晚会留下两份无回执文件，v3已移到输出创建前并新增失败不落盘回归。测试不是当前平台或人工验收。

代码包只含114份A24源文件及清单，463,903字节，SHA `8921ec742e5830ce9184dabfde2d563e00c54314f06ee815241e7df77a2e2d6b`；不含依赖安装器、私有输入、账号或浏览器状态。启动器验证代码包与逐文件摘要，隔离A/B的Python命名空间，不需要Git、不下载模型、不调用平台。

本轮A24两文件增量另附[可审查补丁](../handoffs/b/a24/a24-readonly-trial-v3-20261022.patch)，基于上一轮527文件树；包内已集成，无需手动应用。

要处理另一个本机JSONL，去掉sample参数，按 `--help`显式提供source-type、预期SHA/字节数。`CURRENT_RAW_RECORD`只是调用方对**输入JSONL**的分类，fresh_capture_proven仍false，不证明服务器来源、内容正确或稳定身份；图像转写须保留MODEL_VISUAL_DRAFT来源，不能冒充服务器原文。

当前9项导出预检错误已与原DOM逐条对照：choice/question/answer各3项，涉及可见importShitiID 1/2/7/19/22；底层值保持UNOBSERVED，不按同号连接历史记录。网页控制受阻后的v4未读到正文；用户随后手动打开第1题，团队另取新证据，不能用历史首行替代当前首题验收。

本轮代码、版本、实跑及证据摘要见[机器记录](../evaluation/a24-readonly-trial-runtime-20261022.json)。20:00前的首题目标仍按当前真实来源、内容/身份关联及只读/离线核对计，网站保存未获授权、未执行。
