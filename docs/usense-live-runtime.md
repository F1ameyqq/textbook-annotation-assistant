# 书籍 46007447 的真实读取与登录入口

运行入口为 `python -m annotation.runtime.usense_live`。需要 Windows、Python 3.9+、Python Playwright 和已安装的 Microsoft Edge。项目代码需要已安装，或将仓库 `src` 加到 Python 模块路径。模块没有本机绝对路径、账户、密码、Cookie 或令牌配置。

也可使用仓库入口 `python tools/run_usense_live.py`，它根据脚本所在目录加载同仓库的 `src`，无需设置 `PYTHONPATH`。可从任意工作目录用此脚本的绝对路径调用。选择已经具备 Playwright 的 Python 环境；入口不会下载依赖。`doctor`、`configure` 和离线验证不启动浏览器。实际登录、采集和写入需要 Windows 上可用的 Edge 与兼容的 Playwright（需支持 `route_web_socket`；已实测版本为 1.64.0）。

```powershell
python tools/run_usense_live.py --help
python tools/run_usense_live.py doctor
python tools/run_usense_live.py capture --config C:/project/private/configs/read-3-5.json --sha256 <配置摘要>
python tools/run_usense_live.py --writer --help
```

`--writer`（或首个子命令 `writer`）明确进入单独的写入模块；须先将审查后的 `writer.py` 和 `update.py` 合入同一个包。可用参数由 writer 的 `--help` 列出。它不会把 capture 配置解释为写授权：真实写入还需要审校后的 plan、绑定哈希、原始 baseline、全局 intent ledger 及当前写入授权引用。每次只处理一题；收据成功之后仍须另进程读回比较。应在所有模块集成完成后生成新配置；运行期间改动包内 Python 文件会使实现哈希校验失败。

`doctor` 只检查依赖和已有配置，不启动浏览器；检查成功不等于登录有效或平台读写完成。业务写入由独立 writer 实现，本包的 capture 不能 POST。

## 准备配置

先准备项目专用浏览器目录、输出目录和配置目录。下面的路径、执行者和审核者由调用者填写：

```powershell
python -m annotation.runtime.usense_live configure --profile C:/project/private/browser --output-root C:/project/private/runs --config C:/project/private/configs/read-3-5.json --coordinator coordinator-id --executor executor-id --reviewer reviewer-id --authorization-reference current-user-request --orders 3 4 5 --pages 10 173
```

命令返回配置 SHA256。配置绑定当前操作者、profile 目录身份、书籍、精确 GET 列表、代码摘要和最多 15 分钟的运行窗口。它不生成或伪造历史 A24 授权。每个运行目录只能创建一次，结果不明时不自动重试。

默认保持严格 TLS。只有用户明确批准当前证书例外时，才传 `--tls-approval-reference <实际批准记录引用>`；该参数只启用代码中固定的 www.usense.com 证书及 SPKI。程序先通过 TLS 握手校验原证书 DER 摘要，再让 Chromium 对固定公钥应用例外，`ignore_https_errors` 始终为 false。证书改变会停止，不能自动更新 pin。

## 首次登录

使用独立配置和可见窗口：

```powershell
python -m annotation.runtime.usense_live configure --login --profile C:/project/private/browser --output-root C:/project/private/runs --config C:/project/private/configs/login.json --coordinator coordinator-id --executor executor-id --reviewer reviewer-id --authorization-reference current-user-request
python -m annotation.runtime.usense_live login --config C:/project/private/configs/login.json --sha256 <上一步摘要>
```

用户在可见 Edge 中输入密码并登录。程序不填写、读取或输出密码和令牌；只允许一次原生登录 POST，不允许业务写入。返回的 `LOGIN_HTTP200_NAVIGATION_OBSERVED` 只是登录请求返回及页面跳转证据，后续 capture 才验证业务会话。

## 读取第 3—5 题

```powershell
python -m annotation.runtime.usense_live capture --config C:/project/private/configs/read-3-5.json --sha256 <配置摘要>
```

每题读取现有框、题目信息和题干、选项、答案、解析、知识点五区；同批还读取目录和全框。`--pages` 指定已观察的来源页，`--source` 可读取来源元数据。每批最多 6 题、8 个来源页，第 1 课时可分批执行，不会自动扩大题目范围。

输出 `directory.json`、`frames.json`、`q3_annotations.json`、`q3_info.json`、`q3_question.json` 等原始响应文件，附 `capture-summary.json` 中的长度、SHA256、HTTP 状态及每层请求次数。响应使用 fetch arrayBuffer 保存 HTTP 实体字节（浏览器已处理传输压缩），不经过文本解码再编码；原始键序、空值和未知字段得到保留。每个响应还须满足实际已观察的 `code: 0` 业务格式。

采集器使用同源惰性 HTML 避免前端自动发整书请求。这份文档是本地生成的，不能称真实页面渲染。原生 API GET 仍经过 context route 和 CDP Fetch 双层保护，每层恰好一次；原网页内认证令牌只在浏览器中用于认证，不返回 Python、不写日志。业务 POST、WebSocket、重定向及未列明请求均阻断。

## 释放和验收边界

浏览器以 offline 模式启动并清理其恢复页，安装保护后才联网。单 GET 有 20 秒终止器，Python 等待也有上限。context、runtime 及回调清理写入 `release.json`；该记录不会冒充自身 OS 进程退出证明，外层执行器负责进程退出或 Job 容器核查。

`NATIVE_GETS_CAPTURED` 表示当前批次 GET 得到并保存，不表示 OCR 正确、保存成功、独立读回通过或整书送审。写入后独立读回应使用新配置、新运行目录和新的读取进程。旧会话、旧模板和配置不能复用来绕过 UNKNOWN 状态。

当前自动标注流程复用平台已有题框及其稳定身份，只将来源和审校记录绑定的文本交给更新计划；这个入口没有自动建框、删框或猜测目录结构的能力。OCR 输出必须对应实际来源页、来源文件哈希、明确审校记录以及审校文本的 UTF-8 SHA256，OCR 成功不能代替审校通过。先对指定普通单选逐题完成“采集 → OCR → 审校 → 一次更新 → 独立读回”，再按批准范围推进第 1 课时。3—5 题通过不能直接宣称整课时或整章完成。

离线验证：`python -m unittest discover -s tests/usense_live -p "test_*.py"`。测试覆盖错误目标、配置变动、单次发送限制、禁止额外写入、部分启动清理、三题批次端点完整性以及原始字节保全。合成测试不产生真实平台请求。
