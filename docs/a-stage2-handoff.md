# A 侧第二阶段交接：固定接收入口与当前进展

2026-10-18。分支 `codex/a-stage2-handoff`，以已发布阶段一 `a15301ef3532aca25dcd527aae1c680c1e220e9f` 为父。产品及所选历史记录来自本地固定提交 `817e6d73b939ba33db5c8050d987f1c7f2095dfa`，通过原 Git bytes 选择性纳入。本分支没有合并 B 或架构分支的新提交。

**现在可以使用 A06 读取指定 B 包并得到只读 HOLD / 拒绝回执。真实单题进入 A 计划和模拟执行仍待双方确认。** [进展架构图](handoff/a-stage2/progress-architecture.html) 展示这两个不同边界。

## 发布内容

| 范围 | 本次交付 | 状态与限制 |
|---|---|---|
| A06 | `annotation.source.b_handoff` API / CLI、固定消费者和窄测试 | 已独立验收、调度接受及本地集成；固定包只读范围 |
| 公共合同 | 完整 `src/`、schema / profile / pins 与 `pyproject.toml` | C01 公共接口保持；A03 内部格式不等于 B 共同格式 |
| A03-R1 | 持久化、恢复、UNKNOWN 对账源码与有限接受记录 | 原有限离线范围已集成；没有发布活库或迁移流程 |
| I01-A | N/E/U 固定输入、输入摘要检查、历史结果记录 | 正常 / 目标漂移 / UNKNOWN 后新进程对账三条 synthetic 路径；不等于真实 B 正向路径 |
| D01 | Pillow 依赖声明及历史有限接受说明 | 原 Windows CPython 3.9.13 证据；本次没有重新做 wheel / 清洁安装验收 |

[精确成员与 SHA 清单](handoff/a-stage2/manifest.json) 绑定所有新增来源。完整 `src/` 一起发布，是因为当前公共入口依赖恢复模块及其包内数据；没有仅复制入口文件。

## 获取与环境

在独立目录克隆此分支，或在已有仓库抓取后建立独立工作目录；不要覆盖当前 B 工作目录。可用如下方式获取：

```powershell
git clone --branch codex/a-stage2-handoff --single-branch https://github.com/F1ameyqq/textbook-annotation-assistant.git a-stage2-handoff
cd a-stage2-handoff
git rev-parse HEAD
$repo = (Get-Location).Path
$env:PYTHONPATH = "$repo/src"
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
```

沿用验证环境 CPython 3.9.13、`pydantic==2.12.5`、`Pillow==11.3.0`。以下入口采用源码模式；不是当前完整 wheel 安装的承诺。`pyproject.toml` 是原接受版本，未为发布修改产品配置；已有 bridge/native package-data 声明不能代替对 recovery schema 的完整 wheel 打包验证。

发布层 `.gitattributes` 保护源码原字节，避免 Windows 换行转换导致 native pins 拒绝。出现摘要不符应核对检出字节，不修改 pins。

## A06 固定 B 包入口

输入由调用方提供原包 `B-46007447-Q16-offline-HOLD-2026-10-17.zip`；本分支不重复上传 B 的 ZIP 或生成变体。

```text
ZIP SHA256 b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d
manifest SHA256 3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f
```

```powershell
$package = 'D:/path/to/B-46007447-Q16-offline-HOLD-2026-10-17.zip'
python "$repo/examples/a06/consume.py" $package --sha256 b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d --manifest-sha256 3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f
# 公共 CLI 的参数与消费者相同：
python -m annotation.source.b_handoff --help
```

```python
from annotation.source.b_handoff import receive_package, HandoffError, version_policy
received = receive_package(package_path, expected_sha256=zip_sha256,
                           expected_manifest_sha256=manifest_sha256)
receipt = received.receipt
```

退出 0 仅表示只读诊断完成，`decision=HOLD`；拒绝退出 2，提供 `code/path/layer`。`business_acceptance=false`、`c01_execution_eligible=false`。不执行包内脚本、B 生产者或 SQL。

| 当前格式或位置 | 处理 |
|---|---|
| E 0.3 / G 0.7 / Check 0.7 | 仅已固定 run 的只读 HOLD |
| G / Check 0.4、0.5，精确绑定历史引用 | ARCHIVE_ONLY |
| 0.4、0.5 冒充当前顶层 | 拒绝 |
| 0.6 | 缺完整正样例，明确拒绝 |
| 未注册版本 / kind | 明确拒绝 |
| 14 个已观察 stage 的结果 kind/schema | 单独核对，仅历史诊断，不升级顶层资格 |

历史引用必要性仍为 `UNCONFIRMED_REQUIREDNESS`，缺引用仍为 `UNRESOLVED_HISTORY_REFERENCE`，`optional=null`。不得把 READY/DONE 当作 PASS。

`examples/a06/README.md`、`SECOND_FINAL.md` 及 `verify*` 保留冻结时记录；其中 REVIEW 为历史状态。当前状态以本文和[接受摘要](handoff/a-stage2/acceptance-summary.md)为准。当前接收入口为 `consume.py` / 公共 API / CLI，不要求重新运行冻结验收驱动。

## 公共合同和固定消费者

公共版本仍为 `1.0.0-a-proposal` / `c01-exchange-1`，共同语义仍待 B 确认。

```python
from annotation.contracts import load_bundle, validate_bundle, schema, ContractError
bundle = load_bundle('path/to/input.json', verify_assets=True)
```

阶段一已有三种固定 C01 样例在本分支保留：

```powershell
python "$repo/examples/contracts/consume.py" "$repo/tests/fixtures/contracts/normal"
python "$repo/examples/contracts/consume.py" "$repo/tests/fixtures/contracts/exception"
python "$repo/examples/contracts/consume.py" "$repo/tests/fixtures/contracts/unknown"
```

这三个入口读取静态数据，不向模拟或真实平台 dispatch。版本与额外语义约束见[合同说明](contracts-v1.md)及[实现说明](contracts-implementation-v1.md)。

## 补充离线材料与复现边界

`tests/fixtures/i01/{N,E,U}` 是原三路径输入；完整 24 个固定输入及 identity 保留。下面仅核对 Git 中的输入摘要，不运行业务，不创建数据库，也不证明业务通过：

```powershell
$candidate = git rev-parse HEAD
python "$repo/examples/i01/check_freeze.py" --candidate $candidate --output 'D:/new-output/i01-inputs-check.json'
```

原 I01 运行候选为 `be68b8d7c645de556d601458d1d493258f063721`，其 HEAD 与产品守卫不变。阶段二 HEAD 不可替代它。A03/R1 的成功业务与旧 pending 状态不重跑、不迁移；本次不带其旧驱动、数据库和失败全集。

`docs/handoff/a-stage2/records/*.txt` 是原记录的逐字节副本，扩展名标明档案文本。其原始深层路径、提交号与链接仅是来源线索；未承诺这些 Git 对象或全部大证据在本分支可达。特别是 final review manifest 的 155 个成员只有明确选中的记录随包发布，不能把 manifest 当作完整证据包。

## 发布检查与下一步

[发布检查](handoff/a-stage2/publication-checks.json)记录异目录源码导入、包内 pins、CLI 帮助及 C01 静态消费者；不增加 A06 完整接收调用、不运行 A03/I01 业务、不安装依赖。[图检查](handoff/a-stage2/diagram-checks.json)记录架构图的生成检查。

下一步请共同确认[字段映射、执行准入和真实单题](b-minimal-integration-confirmation-2026-10-18.md)，再固定“一道真实 B 题目 → A 计划 → 模拟回执”的 A 侧任务。A04 真实平台 R01–R06/S01 仍 BLOCKED；A05 题22只证明过去单个保存/重开，不能重放。

本次发布不修改 B/main/架构/第一阶段分支，不发送 B 消息，不表示 B 已读取或接受。
