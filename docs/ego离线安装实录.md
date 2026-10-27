# ego lite 离线安装（crx3）· 本机实录与一个脚本缺陷

> 2026-10-28 00:37–00:50 ｜ 本机 Windows ｜ 安装包 `ego-0.6.1.13-x64.crx3`（286,365,034 B）
> 方法来源：A 仓 `F1ameyqq/getaway-to-goal` 的 `install/install_ego.ps1` + `install/extract_crx.py`

## 一、结论

**装成功了，但 A 的安装脚本漏了一个文件。** 补上后 ego-browser 可正常启动（`0.6.1.13 / chromium 156.0.8078.48 / node v24.22.1`）。

## 二、脚本缺陷（已修，建议 A 侧同步）

| 项 | 内容 |
|---|---|
| 现象 | 装完后 `ego-browser --version` 正常，但一执行脚本就报 `Failed to start ego lite: cannot find the app for ...\ego-browser.exe` |
| 根因 | 载荷结构是 `Chrome-bin/ego.exe`（**上一层**）+ `Chrome-bin/0.6.1.13/...`（831 个文件）。<br>脚本 `$srcDir = @(Get-ChildItem $binRoot -Directory)[0]` 只取了 `0.6.1.13/` 这个子目录，**`Chrome-bin/ego.exe` 从未被复制**。 |
| 佐证 | A 侧自述"831 vs 832，唯一差异是 Installer\setup.exe"——实际差异是 `ego.exe`，不是 setup.exe |
| 修法 | 把 `Chrome-bin/ego.exe` 复制到 `%LOCALAPPDATA%\Citro Labs\ego lite\Application\<ver>\ego.exe` |
| 建议给 A 的补丁 | 在 install_ego.ps1 的 "[3/5] 复制" 之后加：`Copy-Item (Join-Path $binRoot 'ego.exe') (Join-Path $dest 'ego.exe') -Force` |

## 三、本机安装后的位置

```
%LOCALAPPDATA%\Citro Labs\ego lite\Application\0.6.1.13\   ← 831 + ego.exe
~/.local/share/ego/active_version_dir    → junction 指向上面的版本目录
~/.local/share/ego/ego-skills            → junction 指向 .../ego-skills/ego-browser
用户 PATH 已追加 ~/.local/share/ego/active_version_dir
```

## 四、装完还差的两步（人类操作，agent 做不了）

1. **Onboarding**：首次运行会弹 setup 窗口，按提示走完（本机已弹出）
2. **登录平台 + 过证书页**：平台证书过期，首次访问要点「继续前往」

做完之后跑自检：

```powershell
cd C:\Users\LIHAOYANG\Desktop\_pub\a_tools
$env:CHECK_QPAGE="34"; $env:CHECK_APAGE="175"
.\run_ego.ps1 -Js .\check_env.mjs -Out "$env:TEMP\check.txt" -TimeoutSec 300
# 期望输出 CHECK_ENV_OK
```

## 五、复现命令（完整）

```powershell
# 1) 解 crx3 → 7z
python -I extract_crx.py "ego-0.6.1.13-x64.crx3" payload.7z
# 2) 7z → 文件树
tar -xf payload.7z -C unpacked
# 3) 官方安装
.\install_ego.ps1 -Crx "...\ego-0.6.1.13-x64.crx3"
# 4) 补漏掉的 ego.exe（本文件第二节）
Copy-Item .\unpacked\Chrome-bin\ego.exe "$env:LOCALAPPDATA\Citro Labs\ego lite\Application\0.6.1.13\ego.exe"
```

## 六、注意

- 解包临时占用约 1.4GB（`mini_installer` 645MB + payload 637MB），装完要清
- `tar` 必须用 **Windows 自带的 bsdtar**（PowerShell 里调用），Git-bash 的 GNU tar 不认 7z
- 安装脚本会改**用户 PATH**，需要新开终端才生效
