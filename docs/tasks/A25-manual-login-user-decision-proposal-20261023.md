# A25 原专用配置一次手动登录：具体待决定方案

当前事实：新 Python3.12/OpenSSL3.5.8 已在实际采集中通过原精确证书检查并启动浏览器；首个目录 GET 返回 HTTP401、正文0字节。准确 token/session 原因仍未知，当前登录状态未通过业务请求验证。五题尚未保存。

推荐操作：在原专用 Edge 配置中打开 https://www.usense.com/qieti/login，由用户在浏览器内填写并点击登录一次。无需把密码发到聊天。使用现有已固定的 `MANUAL_LOGIN_ONLY` 入口；不新增自动填写实现，不读取本机凭据配置，不导出账号、密码、Cookie或token。

批准/用户准备好之后，根建立本方案唯一新 authority、配置和运行输出，原profile独占检查后启动。1个可见context、固定登录页、最多1次用户操作的官方登录POST、最长900秒。沿用固定主机和已核验的原leaf/SPKI限制，证书改变即停；不扩大到其他站点，不换profile，不清锁，不改代理。首次未知/守卫失败/超时停止，不自动重试。配置生成与登录进程均由既有Windows Job监督器持有并核释放。

凭据输入和点击只由用户执行。程序只记录登录响应HTTP状态、同站页面转换及释放；这些不等同独立业务认证成功。登录进程退出释放后，由根绑定一次独立新context读取原书第二课时五题的40GET当前源；成功后继续身份、来源和内容审校、五题串行真实保存与各自独立读回。原失败轮及诊断记录不重开，1800-a保持PAUSED。

配置命令的固定参数列表（决定后才创建新授权、配置及运行窗口）：

```json
[
  "D:/1800/.local/stages/a25-lesson2-expansion-20261023/runtime-py312/venv/Scripts/python.exe",
  "-I",
  "-B",
  "C:/Users/ASUS/.codex/worktrees/b-latest-20261023/1800/tools/run_usense_live.py",
  "configure",
  "--login",
  "--profile",
  "D:/1800/.local/browser-profiles/937cbc0b7541861c7c68",
  "--output-root",
  "D:/1800/.local/stages/a25-lesson2-expansion-20261023/manual-auth-recovery/runs",
  "--config",
  "D:/1800/.local/stages/a25-lesson2-expansion-20261023/manual-auth-recovery/configs/login-01.json",
  "--coordinator",
  "01a166c5-f93f-76e3-baf4-a3545ccddebd",
  "--executor",
  "01a166e7-cfd7-7da2-a76e-bcb612b9646b",
  "--reviewer",
  "01a166e8-3f23-7192-a560-4724adca74b1",
  "--authorization-reference",
  "D:/1800/.local/stages/a25-lesson2-expansion-20261023/manual-auth-recovery/authority.json",
  "--tls-approval-reference",
  "D:/1800/docs/approvals/A17-excluded-static-user-decision.json",
  "--seconds",
  "900"
]
```

随后同一解释器执行 `-I -B <上述入口> login --config <上述login-01.json> --sha256 <该次configure产生的摘要>`，监督进程上限按配置到期与清理余量绑定。此文档为可执行方案，不是已发生登录或当前激活。

当前等待原因：原 A25 任务第13行规定“当前未授权新登录、读取用户名密码配置、切换 profile、清锁或书级送审”；且手动登录需要用户当前能够操作可见页面。此次仅请求打开原配置并由用户登录一次，后续测试继续按已明确的五题目标推进。
