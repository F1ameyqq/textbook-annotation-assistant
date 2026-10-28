# A24 离线重放包 v1 独立静态 HOLD

## 结论

`HOLD_V1_REPLACED_BEFORE_EXECUTION`

旧 ZIP 已固定证据，但在静态门发现阻断项后即停止。未解包、未重建、未运行其 21 项测试，不能沿用作者包内旧回执，也不会把 `21b4e9f…` 标为通过。待 v2 到达后必须从 ZIP 身份开始全新验收。

## v1 固定身份

- ZIP：`a24-offline-replay-20261022.zip`
- 字节数：`2034114`
- SHA-256：`21b4e9f22910469c0af9592de944a919e0c0ac8895bd7b2d8c8fbdf895bb8435`
- ZIP 成员：532；展开总字节：9,639,706；CRC 全量检查通过。
- root manifest SHA-256：`324d8fd79a82fec325f96571daf8582db506c51b9eabc52ffdf2d97320bc638f`
- root manifest 声明排除自身 531 项，ZIP 实际排除自身也是 531 项。

## 阻断项

1. **测试组错误**：七项组指向 `tests/a24_bootstrap_exclusion/test_integration.py`，本轮要求的是 `tests/a24_controlled_capture/test_integration.py`。
2. **测试树未绑定**：`test` 命令不先调用 `verify_package()`，也不按 `effective-manifest.json` 核对 `--tree`。因此任意或被篡改树也可能生成“21 项通过”回执。
3. **root manifest 可缺省**：`verify_package()` 仅在文件存在时校验；对可移交包而言根清单应为必需输入。
4. **Windows 路径门不足**：`safe_relative()` 先用 `PurePosixPath`，再转为 Windows `Path`；未拒绝反斜杠、盘符/UNC、ADS 冒号、保留设备名、尾随点空格、Unicode/大小写规范化冲突和文件/目录前缀冲突。
5. **真实 I/O 门不完整**：`MemoryPolicy` 只阻止 asyncio selector FD，runner 只 patch 部分 socket、`Popen` 和 `urlopen`；没有文件系统根限制，也未覆盖所有进程/网络入口。包内含历史 authority 文件，策略没有明确拒绝测试读取/复用它们。
6. **失败证据不足**：回执只保留 failure/error 数量，不保留测试 ID、错误文本或 traceback，失败时无法独立定位。

## 已确认但不能抵消阻断的事实

- ZIP 内 baseline 恰有 522 项，overlay 恰有 3 项，effective manifest 声明 523 项。
- 原 baseline manifest SHA-256 为既定 `a927a201988a277520275509791401e00cc45fdd9edcde140056bf85060633a9`。
- 三个覆盖文件的 SHA 与此前独立接受的 owner、current-body fixture 和四项 book snapshot 测试一致。
- README 保留 `CURRENT_SCHEMA_UNBOUND` 与 HOLD，不声称真实平台验证。

上述仅是静态事实。因为 v1 未执行重放，不能形成 offline replay PASS；v2 任何字节变化都必须重新做 ZIP 安全门、实际重建、覆盖/篡改拒绝和正确的 7+10+4 测试。
