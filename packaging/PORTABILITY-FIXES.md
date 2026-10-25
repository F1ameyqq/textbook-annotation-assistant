# 可移植性修复：让只读平台访问在另一台机器上成立

在 B 机器（Windows + Edge + Clash 代理 + Python 3.11）上，把 a30 的只读
平台访问从"能启动但取不到数"修到 **`status: NATIVE_GETS_CAPTURED`**。

## 实测结果

```json
{ "status": "NATIVE_GETS_CAPTURED",
  "captures": {
    "directory": {"status": 200, "bytes": 15538},
    "frames":    {"status": 200, "bytes": 94596},
    "source":    {"status": 200}
  },
  "save_attempts": 0,
  "release": {"context_created": true, "context_closed": true,
              "context_runtime_release_confirmed": true} }
```

`tls-probe.json`：`status=EXACT_LEAF_CONFIRMED`，`probe_stack=OPENSSL_CLI`，
`leaf_sha256=52d86421…e3941`（与 `core.py` 的 `APPROVED_CERT_DER` 完全一致）。

## 修复一：profile 必须放在可写目录

**现象**

```
[pid][err] CreateFile ...\Crashpad\throttle_store.dat: 拒绝访问。 (0x5)
[pid][err] Lock file can not be created! Error code: 5
BrowserType.launch_persistent_context: Failed to create a ProcessSingleton
```

**原因**：交接来的 profile 位于 `D:\1800\.local\browser-profiles\...`，
该目录在本机只读（连创建文件都被拒）。Edge 需要写锁文件与 Crashpad。

**做法**：把 profile 放到工作区内可写路径，并保证其同级目录存在
`usense-existing-ledger`（`transport.py` 的硬性要求）：

```
<workspace>/browser-profiles/
├── work-default/            ← 登录用 profile（Edge 可写）
└── usense-existing-ledger/  ← 必须是同级目录，不能用空账本代替
```

登录时用同一个 profile 启动 Edge，登录态会落到该 profile。

## 修复二：显式配置代理

**现象**：`Page.evaluate: TypeError: Failed to fetch`（`phase=GET_directory`）

**原因**：Playwright 默认加 `--no-proxy-server`，绕过系统代理。
本机需要经 `127.0.0.1:7897`（Clash）访问平台；直连会被重置或拿到不匹配证书。

**做法**：在 `settings.json` 写 `proxy_server`：

```json
{ "proxy_server": "http://127.0.0.1:7897" }
```

`transport.validate_transport` 只接受**无凭据的回环地址**，
所以必须是 `http://127.0.0.1:<port>` 形式。

## 修复三：TLS 预检的 OpenSSL 回退（代码改动）

**现象**

```
ssl.SSLEOFError: [SSL: UNEXPECTED_EOF_WHILE_READING]
  at transport.py -- context.wrap_socket(sock, server_hostname="www.usense.com")
```

**原因**：部分网络出口按 TLS 指纹中断 Python `ssl` 握手；
同一路径下 `openssl s_client` 能正常握手并取到叶子证书。

**改动**（`src/annotation/runtime/usense_live/transport.py`）：

1. 新增 `openssl_leaf_certificate(binding, proxy)`：用 OpenSSL CLI 取叶子证书 DER
2. 把 `context.wrap_socket(...)` 包进 `try/except ssl.SSLError`，
   捕获后改走 OpenSSL 回退，并在证据里记 `probe_stack`

**校验强度不变**：回退取得的证书仍需满足

```python
require(evidence["leaf_sha256"] == setting["leaf_der_sha256"],
        "APPROVED_CERTIFICATE_CHANGED")
```

即必须与 `core.py` 中钉定的 `APPROVED_CERT_DER` 完全一致才放行。
`--ignore-certificate-errors-spki-list` 也只豁免该 SPKI，不放开整站校验。

## 未改动、未放宽的部分

- `tls.mode` 仍由 `--approved-known-certificate` 决定，STRICT 时不做任何豁免
- 请求策略仍逐条比对 `allowed_get`，被重定向即 abort
- 只读捕获仍要求 `save_attempts == 0`
- 不引入环境变量/WinINET/PAC 自动代理发现

## 复现步骤

```powershell
# 1. 绑定本机 Python
python packaging/patch_runtime.py --app . --python C:\Path\To\python.exe

# 2. 首次配置：可写 profile + 启用平台 + 批准已知证书
python tools/customer.py --workspace <ws> setup `
  --existing-profile <ws>\browser-profiles\work-default `
  --enable-platform --approved-known-certificate

# 3. 写代理（setup 无该参数，直接改 settings.json）
#    "proxy_server": "http://127.0.0.1:7897"

# 4. 只用该 profile 登录一次平台，然后关闭 Edge（释放 profile 锁）

# 5. 只读读取
python tools/customer.py --workspace <ws> platform `
  --book 46007447 --directory <目录ID>
```
