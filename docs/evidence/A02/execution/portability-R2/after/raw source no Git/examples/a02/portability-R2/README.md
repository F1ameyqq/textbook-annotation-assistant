# A02 portability-R2：无 Git 身份探测

R2 唯一既有改动是 `examples/a02/R1/identity.py`：Git 无法启动，或核实 top-level 后 HEAD 查询失败/为空时，
`git_identity` 返回 `checkout_commit=null` 与明确 unknown；只有 top-level 与源码根一致且取得 HEAD 才返回 verified。
`source_binding` 未改，缺外部 Git 身份、blob 查询失败或源码字节不等仍失败关闭，不能返回成功绑定。

作者回归（现有 Python/Pydantic，无新依赖）：

```powershell
$env:PYTHONPATH = "$PWD\src"
python -B -m unittest discover -s tests -p 'test_a02_portability_r2.py' -v
```

新增 10 项包含真实独立 Python 子进程：新 raw 副本且 PATH 只有一个空目录，子进程实测 `shutil.which('git')=null`；
身份探测应退出 0 并 UNKNOWN，需要 Git 的 binding 应退出 1 且不输出 result。首次启动失败、第二次启动丢失、
第二次非零/拒绝执行、空 HEAD、错误 top-level、blob 查询失效和字节不等另以有限模拟故障测试，不冒充真实无 Git。

冻结提交的完整受影响验证（所有输出路径必须不存在）：

```powershell
python -B examples/a02/portability-R2/verify.py --repo "$PWD" `
  --commit <R2补丁完整SHA> --output "$env:TEMP/a02-portability-r2-after-new"
```

复现器以显式提交导出必要源码/测试/小型样例的原始 Git 字节，不复制历史归档。实际子进程 argv、cwd、PATH、
Git 可执行路径/null、退出码、真实 identity/annotation/test 导入和 SHA256 保存在每个 command/stdout/stderr 文件。
raw 源码根不含 `.git`，即使处于本任务仓库下也不得继承父 HEAD。有 Git 对照另验证真实 checkout 和外部 blob binding。
62 项受影响 A02 discovery 在有/无 Git 两个环境运行；不运行 C01、登录或几何矩阵，不跳过/吞掉测试失败。

修前使用 `--commit 38aca9dcc8d027409b95193e9cc142c2336b76d3 --before --output <新目录>`，
此模式只验证原缺陷：无 Git 两入口预期退出 1、有 Git 两入口退出 0，结果不能称为功能接受。
binding 的无 Git 非零是明确拒绝，不会包装成 verified。第二次调用缺失为单独模拟测试，报告明确区分证据层级。

本轮没有 A01 全组合入口的实现或复验，不改变原 A02 R1 接受/集成记录，也不释放 A01/A04。
SYNTHETIC/SIMULATED 边界、内容 PENDING、提交 NOT_SUBMITTED、N1/N2、A03 恢复公共接缝均保持原范围。
全部离线，平台、浏览器、网络、凭据、OCR、模型调用为 0；交付仅 REVIEW。
