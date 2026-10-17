# A03 P2-R7 产品只读 codec

实现位于 [annotation.contracts.a03_bridge](../../../src/annotation/contracts/a03_bridge/__init__.py)，交付状态 **REVIEW**。它只实现 A 内部 STATIC_INSPECTION；不会生成 CURRENT/PRE/写入资格。既有 contracts 默认分发不变。

```python
from annotation.contracts.a03_bridge import (
    select_static_codec, open_static_context, validate_static_bundle,
)

selection = select_static_codec()
context = open_static_context(asset_root="explicit-assets", selection=selection)
snapshot = validate_static_bundle(bundle, context=context)
copy_of_complete_bundle = snapshot.model_dump()
```

BridgeSelection 是无 __dict__ 的冻结描述，所有 pins/版本均为不可变元组；提供 selection 时校验具体类型及全部字段。BridgeContext 仅含 selection 和解析后的显式资源根。ValidatedA03Bundle 存 canonical JSON bytes、canonical_sha256、selection 及冻结的 resources(path/raw_sha256)；data 是深层只读视图，model_dump() 每次返回完整独立副本。它不代表持续文件锁、真实 PRE run 或执行凭据。

[迁移对应表](migration-map.json) 记录 R2 Package、R3 正式 EvidenceRecord 闭包和 R5 上下文/target 规则的产品位置。没有 exec、AST 加载、examples fallback、oracle/session/conversion 执行。精确 Schema/API/profile 和新的只读角色记录随 wheel 内置；原 profile 的 STATIC_UNIMPLEMENTED/implementation_authorized=false 原字节不变。

[七个产品夹具](../../../tests/fixtures/a03/P2-R7-readonly-codec/index.json) 的业务 bundle 与原 raw Git 字节相同；散布资源只按原逻辑路径物化。全局 hash 负控仍含原始损坏字节及不匹配声明，没有在物化中修好。

实际验证：七个新入口场景均在指定层返回/拒绝；角色/pins、未知版本、非有限数、深层快照隔离、路径拒绝通过。首次符号链接测试因 Windows 1314 跳过，随后仅对这一项加入目录联接备用方式并补测通过，产品代码没有修后重跑。原 C01 70 项通过。离线 wheel 在仓库外、清除 PYTHONPATH 后实际导入并运行正包与 target 负控通过；9 个内置数据文件的 raw pins 一致。

供后续复现，当前交付阶段不再运行：

```powershell
Set-Location C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800
$env:PYTHONPATH = 'src'
python -B -m unittest discover -s tests -p test_a03_r7_readonly_codec.py -v
# 只核对归档和保全，不执行产品或测试。
python -X utf8 -B docs/evidence/A03/execution/P2-R7-readonly-codec/archive.py --check
```

实际原始流/拒绝路径、wheel、仓库外 __file__、全部 pins 与进程释放见 [交付报告](../../../docs/tasks/A03-P2-R7-readonly-codec-delivery.md)。A03 原生恢复、R17、I01 及 B/公共合同采用均未释放；字段重置专项仍 NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION。
