# A24 历史原件保全候选 v1：独立复验

## 结论

`PASS_BOUNDED_HISTORICAL_PRESERVATION_WITH_MINIMAL_FIX_NATURAL_CODEC_OPEN`

内容候选的方向成立：它新增的是一个与 current-schema codec、写入准入完全分离的历史旁路保全层。经独立复现并补上两个小缺口后，真实19条历史 JSONL 可以逐字节重建，映射账本始终保持 canonical ID 未绑定、无自动选择、`write_allowed=false`。

这个 PASS 只覆盖历史原件旁路保全，不代表 natural codec 已无损、不代表当前19/22分母成立，也不代表内容人工验收或平台保存完成。

## 输入与实际应用

- 用户声明 B 基线：`16b2c6b`。本环境只有无 `.git` 的 `source-readiness-v2` 抽取树，且没有 `D:/1800`，因此 commit 对象无法在本机复核；不能把它写成已验证事实。
- 固定内容补丁：15,895 bytes，SHA-256 `d9ade078140df02a7da3473e3031cc7c801474b17dba5c0d1561cd04d1c73bdf`。
- 独立副本中 `git apply --check --whitespace=error-all` 退出0，实际 `git apply` 退出0。
- 补丁仅新增 `historical_preservation.py` 与其聚焦测试；现有 `wire.py` 前后 SHA 均为 `64885d7ac5d91d5351231a803ffeab4badb1b55528057a6abde1c03ac6131116`。
- 历史原件：11,625 bytes，SHA-256 `02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c`。

原始抽取树内的归档校验器退出1，因为目录没有 Git 对象且缺根 `manifest.json`；这是抽取形态限制，不是候选产品失败。

## 独立首轮发现与最小修补

作者原5项测试全部通过，退出0。但新增反例复现了两个真实缺口：

1. 高精度小数会进入 Python `float` 并舍入，`1e309` 会成为 infinity；原始字节仍在，但解析值/指纹口径不能再称全值精确。
2. `@dataclass(frozen=True)` 只冻结属性重新赋值；内部 `_value` 仍是可变 dict。外部可改写它，使后续 `full_records()` 变化而原 content fingerprint 不变。

独立最小补丁 [a24-historical-preservation-independent-minimal-fix-20261022.patch](C:/Users/LIHAOYANG/Documents/Codex/2026-10-17/chapter1-quality-sol56/outputs/a24-historical-preservation-independent-minimal-fix-20261022.patch) 完成三件事：

- 当前真实原件只有小整数与字符串/数组，因此对任何 JSON float 保守 fail-closed，错误码为 `HISTORICAL_JSON_NUMBER`；不对未知数字格式作有损泛化。
- 删除持久可变 `_value`，每次从冻结的 `record_bytes` 重新严格解析。
- 增加数值拒绝与内部值不可变两项回归。

该补丁3,601 bytes，SHA-256 `2c562a87d2f9a927aa577dd0354173df47abfe629a1859d090fb19126bafea15`；对原内容候选 `git apply --check --whitespace=error-all` 退出0。

主审正式采用的直接集成件是 [adopted-v2 组合补丁](C:/Users/LIHAOYANG/Documents/Codex/2026-10-17/chapter1-content-sol56/outputs/a24-historical-preservation-20261022/a24-historical-preservation-adopted-v2.patch)：16,928 bytes，SHA-256 `524467067bc0f33d976e8dd1c41a46bc45809d0a863d3c65266f3cf6ac02d820`。它可直接应用到未变的 `source-readiness-v2`，不需要先应用内容 v1；独立新副本中 apply-check 与实际 apply 均退出0，产出的两个文件 SHA 与最终复验候选完全一致。

质量侧保留的 [组合补丁镜像](C:/Users/LIHAOYANG/Documents/Codex/2026-10-17/chapter1-quality-sol56/outputs/a24-historical-preservation-combined-final-20261022.patch) SHA 为 `1d37397099edf16363772a54ae56d7a8431faf7081ec8c5669769545543d1312`。两份 patch 的序列化字节不同，但实际应用后的两个源码文件逐字节一致；正式集成应使用上述 adopted-v2，而不是叠加两份。

本轮采用“所有 JSON float token 均拒绝”的收窄版本。Decimal 方案保留为未采用实验，不声明两个变体兼容，也不继续扩展未知 JSON 数值范围。

直接应用与复验命令如下；`$tree` 必须指向一份新的、未应用内容 v1 的 `source-readiness-v2` 副本：

```powershell
$tree = '<fresh-copy-of-source-readiness-v2>'
$patch = 'C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-content-sol56\outputs\a24-historical-preservation-20261022\a24-historical-preservation-adopted-v2.patch'
$raw = 'C:\Users\LIHAOYANG\Documents\Codex\2026-10-16\ni\work\a24-takeover-20261022\historical-download-export-20261022\46007447_paper_questions.jsonl'
$python = 'C:\Users\LIHAOYANG\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'

git -C $tree apply --check --whitespace=error-all $patch
git -C $tree apply --whitespace=error-all $patch

$env:PYTHONDONTWRITEBYTECODE = '1'
$env:A24_HISTORICAL_EXPORT_PATH = $raw
$env:PYTHONPATH = "$tree\src"
& $python -m unittest discover -s "$tree\tests\a24_historical_preservation" -p 'test_historical_preservation.py' -v
& $python 'C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\tools\a24_historical_preservation_independent_tests.py' -v
& $python -m unittest discover -s "$tree\tests\a24_schema_readiness" -p 'test_schema_readiness.py' -v
```

## 最终复验结果

| 范围 | 结果 | 退出码 |
|---|---:|---:|
| 候选聚焦测试（含2项最小修补回归） | 7/7 PASS | 0 |
| 独立原件/负例测试 | 6/6 PASS | 0 |
| 相关 schema-readiness 回归 | 14/14 PASS | 0 |
| 合计 | 27 PASS，0 FAIL，0 ERROR | 全部0 |

真实19条核查确认：整文件与逐行字节可重建；记录顺序、19个字段的顺序、字符串、HTML/TeX、选项列表顺序、空字符串、空列表和 unknown extra 均保持；错 SHA、字节篡改、嵌套重复 JSON key 均 fail-closed，错误字符串不包含测试正文哨兵。

## 身份账本与公共输出

- [公开保全清单](C:/Users/LIHAOYANG/Documents/Codex/2026-10-17/chapter1-content-sol56/outputs/a24-historical-preservation-20261022/a24-historical-original-preservation-manifest-20261022.json)，SHA-256 `47b4917e909abaa690d2cc7f80574369c905b6de001136f8e469edc131f22293`。
- [公开身份候选账本](C:/Users/LIHAOYANG/Documents/Codex/2026-10-17/chapter1-content-sol56/outputs/a24-historical-preservation-20261022/a24-historical-identity-candidates-20261022.json)，SHA-256 `1905f6367813ed714a18fc0a8bf0153b8f33a814c2a53fe1ae0608a2e3cc2276`。

两份公开对象与独立重生成结果完全一致。保全清单19条，身份账本19条；全部 `canonical_question_id=null`、`selected_candidate=null`，状态为 `HOLD_CANONICAL_ID_UNBOUND`，两者均 `write_allowed=false`。公开记录只含字段名、字节引用和摘要，不含题文、答案、账号或原始业务值。

`tixu`、DOM data-key、行号与内容 fingerprint 只作为本地候选证据，均未升级 canonical ID。多对多候选只进入 `HOLD_AMBIGUOUS_LOCAL_MAPPING`，没有 first-match 自动选择；19与22也没有被用于推分母。

## natural codec 仍然 OPEN

旁路层没有修改 `decode_natural_export`，所以不能说 codec 缺口已修复。独立合成反例仍显示：

- natural codec 会拒绝重复 JSON key，但错误类型为普通 `ValueError`；
- 输入含 unknown extra 时可以准入，但输出只留 `raw_record_hash`，不保留 extra 原值；
- 在合成 qualification/inventory 下，把字符串形式的 `tixu`、DOM key、行号或内容 hash 映射为 `platform_question_id` 仍可被接受。

因此 current natural codec 的全 raw/extra 无损保全、权威身份来源和 current catalog/state binding 继续 OPEN。历史旁路 PASS 不能替代它。

## 项目四层短评

- 工程模拟：最小修补后27项相关检查全通过，证明本地历史原件保全与拒绝门可工作；不证明真实平台完整性。
- 实际数据：2026-10-16历史19条原件已字节固定；current fresh 导出、完整分母、canonical ID 与 frame/catalog/state binding 未取得。
- 内容验收：既有显式校正只有限定接受记录；本次未做人类最终内容批准，也未证明历史19条五区完整。
- 平台保存：save、refresh、独立 reopen 均为 `NOT_RUN`，没有平台回执或签收。

共享树没有源文件修改，也没有 commit。首轮基线测试曾生成20个 `.pyc` 和10个缓存目录，已精确清理并确认归零；之后观察到另有13个时间较晚、归属不明的缓存文件，未擅自删除。浏览器、网络和付费模型调用均为0。
