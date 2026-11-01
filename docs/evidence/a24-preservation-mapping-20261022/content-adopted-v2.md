# A24 历史原件保全：采用版 v2

## 结论

**PASS_BOUNDED_HISTORICAL_PRESERVATION_WITH_MINIMAL_FIX / NATURAL_CODEC_OPEN / HOLD**

本轮正式采用质量成员已独立验证的收窄版本：

- 历史原件 raw bytes、完整记录、未知字段、空值、HTML/TeX 和 option 顺序均保留；
- JSON 浮点一律显式拒绝为 `HISTORICAL_JSON_NUMBER`；
- 真实 19 条不含 JSON float，因此不受该收窄影响；
- 记录值每次从冻结 `record_bytes` 重新解析，不持有可变内部 dict；
- canonical ID 继续为 null，多对多候选不自动选择；
- 现有 natural/complete codec 和准入门均未修改。

当前仍为 `write_allowed=false`。旁路历史保全 PASS 不代表 current natural codec 的 raw/extra 保全已修复。

## 正式组合补丁

`C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-content-sol56\outputs\a24-historical-preservation-20261022\a24-historical-preservation-adopted-v2.patch`

- 16928 bytes
- SHA-256 `524467067bc0f33d976e8dd1c41a46bc45809d0a863d3c65266f3cf6ac02d820`
- 对 `source-readiness-v2` 的 `git apply --check --whitespace=error-all`：退出码 0
- 只新增两个文件，不修改已有源码

采用版文件：

- `historical_preservation.py`：8823 bytes，SHA-256 `636707c2fec0889627220657ef7099ea2a135ce8263165a2987e14e9d40ccf27`
- `test_historical_preservation.py`：7529 bytes，SHA-256 `295263cc873af9e247edf79d26c6793c5ffb621305631cf448d293228dbac380`

组合来源：

- 原 v1 内容补丁：SHA-256 `d9ade078140df02a7da3473e3031cc7c801474b17dba5c0d1561cd04d1c73bdf`
- 质量最小修补：SHA-256 `2c562a87d2f9a927aa577dd0354173df47abfe629a1859d090fb19126bafea15`

## 数值边界

冻结 v1 的实际 probe 复现：

- 长小数进入 Python float 后变为 `1.2345678901234567`；
- `1e309` 变为 infinity；
- 后续内容指纹计算抛出 `ValueError`。

采用版不尝试扩展通用精确数值模型，而是对任何 JSON float token fail-closed：

- 普通小数 → `HISTORICAL_JSON_NUMBER`
- 指数形式 → `HISTORICAL_JSON_NUMBER`
- NaN/Infinity → 继续由 `HISTORICAL_JSON_NONFINITE` 拒绝
- JSON integer 继续精确保留

这样不影响实际 19 条：其数字只有整数 `tixu=1…19`。

## 实际验证

### 内容成员同字节复跑

采用版聚焦测试：

- 7/7 PASS
- `Ran 7 tests in 0.041s`
- 退出码 0

包括：

- 真实 19 条逐字节、逐记录往返；
- 全字段顺序、记录顺序、字符串、HTML/TeX、option 顺序、空值和 unknown extra；
- 错 SHA、字节篡改、重复 JSON key；
- 浮点/指数拒绝；
- 内部值不可变；
- identity 伪装拒绝；
- 多对多候选 HOLD 且不选择。

### 质量成员独立复验

独立报告：

`C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-quality-sol56\outputs\a24-historical-preservation-independent-review-20261022.md`

- 报告 SHA-256 `ace734f899e2c9065cbd4e3590ed3963f313e0fda8d1b30b83a7eb7170cbba94`
- 机器回执 SHA-256 `5c56ab48e2eae18c2667e94e7d85ef4bfe5a35ab84f75d09ed63ad2bcc99d157`
- 候选 7/7 PASS
- 独立负例 6/6 PASS
- schema-readiness 14/14 PASS
- 合计 27 PASS，0 FAIL，0 ERROR，全部退出码 0

## 公开清单与身份账本

采用版继续使用经质量成员独立重生成并确认对象一致的 v1 公开输出：

- `a24-historical-original-preservation-manifest-20261022.json`
  - SHA-256 `47b4917e909abaa690d2cc7f80574369c905b6de001136f8e469edc131f22293`
- `a24-historical-identity-candidates-20261022.json`
  - SHA-256 `1905f6367813ed714a18fc0a8bf0153b8f33a814c2a53fe1ae0608a2e3cc2276`

19 条全部：

- `canonical_question_id=null`
- `selected_candidate=null`
- `HOLD_LOCAL_CANDIDATES_ONLY`
- `write_allowed=false`

公开对象只含字段名、逐行字节引用、哈希、行号和证据类型，不含题文、答案、选项值或账号。

## 未采用实验

内容成员的 Decimal 变体保留但不采用：

- `a24-historical-preservation-v2.patch`
  - SHA-256 `0b1763048682b408767ca32c2449eff677d6edf16094102245cd741291c9cff0`
- `a24-historical-preservation-numeric-probe-v2.json`
  - SHA-256 `6930fc0687da2825134e8fc162c843f74fa4d87b7b456f9000baa3436fbeec98`

这些文件仅记录实验路径，不应与正式组合补丁叠加或替代采用版。

## 保留边界

1. 旁路保全层 PASS；现有 natural codec 的 raw extra 原值保留仍 OPEN。
2. natural codec 在合成 qualification 下仍可能接受把 `tixu`、DOM key、行号或内容 hash 投影成题 ID；权威身份来源仍 OPEN。
3. 当前 fresh export、完整 catalog/state binding、canonical question/frame/rect ID 均未取得。
4. 不把历史 19 或 DOM 22 当分母。
5. reparse 防护声明只覆盖实际检查的叶文件，不声明其所有父路径均已防护。
6. save、refresh、独立 reopen 仍 NOT_RUN；不构成平台验收。
