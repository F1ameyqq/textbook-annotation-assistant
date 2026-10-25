# 封装层：让 a30 在另一台 Windows 机器上跑起来

本目录不含 A 的产品代码——它基于 `codex/handoff-a30-20261024-union20`，
只补**运行时绑定**和**自检脚本**，解决"换机器就跑不起来"的问题。

## 为什么需要这一层

A 的 `runtime/customer-runtimes.json` 记录的是**他本机的绝对路径**：

```
D:\1800\.local\stages\a30-customer-independent-20261024\runtime-support\
    venv-customer-py312\Scripts\python.exe
```

交接包按文档说明不含 venv（`environment/` 只有依赖清单）。
所以在任何另一台机器上，`START_CUSTOMER.cmd` 都会直接报：

```
Configured local runtime is missing. Preserve the existing workspace.
```

## 三步恢复

```powershell
# 1) 取代码（本分支已含 A 的完整产品树）
git clone --branch b-side/packaged-runtime-win64 ^
  https://github.com/F1ameyqq/textbook-annotation-assistant.git a30

# 2) 重新绑定本机 Python（自动算 byte_hash 并校验）
python packaging/patch_runtime.py --app . --python "C:\Path\To\python.exe"

# 3) 自检
python packaging/verify_runtime.py --app .
python packaging/smoke_import.py --app .
```

通过后双击 `START_CUSTOMER.cmd`，或：

```powershell
python tools/customer.py --workspace <工作区目录>
```

## 实测记录（B 机器，2026-10-25）

| 项 | 结果 |
|---|---|
| Python | 3.11.8（A 原文档要求 3.12，实测 **3.11 完全兼容**） |
| 模块导入 | **110 / 110 通过**（customer 32 · recognition 52 · runtime 24 · prebox 3） |
| `packaged_runtime()` 校验 | 通过 |
| Tkinter GUI | 启动成功，窗口「教辅 · 材料准备与生产」 |
| `prepare` 实跑 | 2 页 → 6 题候选（Q11–Q16），**0.48 秒**，`NEEDS_REVIEW` |
| 识别来源 | `HISTORICAL_CACHE_NO_NEW_OCR`（命中历史缓存，0 次新 OCR） |
| 复核页面 | `http://127.0.0.1:<port>` HTTP 200，标题「教辅 · 离线内容复核」 |

依赖版本差异（本机 vs A 的 constraints）：

```
numpy      2.3.5    (A 要求 2.0.2)
opencv     4.10.0   (A 要求 4.11.0.86)
Pillow     12.2.0   (A 要求 11.3.0)
onnxruntime 1.25.1  (完全一致)
```

版本更高但未触发兼容问题。

## 已知缺口（不伪装）

| 缺口 | 影响 |
|---|---|
| `rapid_latex_ocr` 未安装 | **公式推理不可用**；已在绑定里标 `formula_inference_activated: false` |
| 平台登录态不在包内 | 读/写 usense 前必须由有权用户在本机登录 |
| 全书 OCR 库不在包内 | 整书盘点需要该库或全书页面图 |
| PyInstaller 打包未做 | 目前仍需本机有 Python + 4 个依赖 |

## 不含什么

- 不含任何凭据、Cookie、浏览器 profile
- 不含书籍原图与私有快照（体积与版权原因）
- 不含 `usense-existing-ledger`（旧题账本必须来自原环境，不能用空账本代替）
