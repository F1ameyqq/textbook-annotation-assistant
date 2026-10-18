# A06 F01 第二、最终候选差量

续派基线 `761d9afed8b9d3d33851ad3d79b0bee7c294089d`；调度工作流
`aab6a34214ae6b25ff784425e680c8ef4abdcea0`。原 [README](README.md)、配方和证据保留为首候选记录。
本次只补固定14个 stage 的 `payload.result.kind/schema_version` 独立版本门，位置在 wrapper 校验后、
result_ref 核对前。未知结果版本返回 UNSUPPORTED_VERSION，错 kind 返回 UNSUPPORTED_KIND，均为 VERSION 层并定位结果字段。
`pipeline.stages[].result_version_check` 给出精确 kind/version、校验位置及 `FIXED_STAGE_DIAGNOSTIC_ONLY`。
它不授予当前顶层版本支持，当前 E0.3/G0.7/Check0.7 及 archive/0.6 规则均不变。

第二冻结提交、实际结果和限制见 [第二最终执行报告](../../docs/tasks/A06-second-final-execution-report.md)。
仍为 REVIEW，必须独立验收。第二冻结后失败即停止，无第三候选。

独立复现时先从报告指定提交的 raw Git bytes 导出自己的代码；使用本机既有依赖，不安装、不执行 B 代码。
`$repo` 为该导出根，`$package` 为原固定 ZIP（SHA和长度见原 README）；输出目录须全新。

```powershell
$env:GIT_NO_LAZY_FETCH = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
python "$repo/examples/a06/make_stage_result_variant.py" $package 'D:/new-local-output/f01-variant'
python "$repo/examples/a06/verify_second_final.py" $package 'D:/new-local-output/f01-variant/recipe.json' 'D:/new-local-output/f01-run'
```

配方只生成一个 TEST_VARIANT：非最终 `inline_apply` stage 结果版本改为
`b-inline-apply-stage-trial/9.9`，重封必要 wrapper/pipeline/manifest及外层文件绑定。
目标结果 payload 和身份不变，其他13项 stage result 与当前 E/G/Check 原字节不变；配方自身先做静态核对。
driver 仅运行原 ZIP HOLD 与这个结果层未知版本完整入口各一次，不运行旧四例全集或 C01 消费者。
冻结前的窄检查只运行 `test_a06_stage_results.py`，覆盖已观察14组、一个未知版本和一个错 kind。
已有坏资源、陈旧 Check、顶层/历史版本及公共消费者的独立结果由固定第一验收报告承接。

历史缺失引用仍保留 UNRESOLVED_HISTORY_REFERENCE、UNCONFIRMED_REQUIREDNESS、optional=null；
business_acceptance/c01_execution_eligible仍false。只读诊断不代表双方映射、内容、平台、完整语义闭包或联合业务验收。
