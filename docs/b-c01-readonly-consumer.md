# 固定A24 C01只读消费

入口 `tools/consume_b_c01_readonly.py` 只调用原A24 `annotation.contracts.load_bundle(..., verify_assets=True)`，随后将完整 `model_dump(mode='json')` 与输入bundle进行类型敏感的规范JSON比较，数组顺序保留。它不转换私有候选、不引入新的内容schema、不调用planner/target/runtime dispatch，也不表示A所有者或真人已验收。

当前固定A提交为 `c5aefbc8e995c410b3babf74a251f05a7724a1c2`。主仓记录的A08/A09 `edf12596`较早；其C01/geometry消费闭包与A24的50份文件字节相同，但原 `consume_q16_reading_a.py` 还调用写死Q16/3阅读任务的校验器，不能直接供第二课时九题使用。

## 固定源码与pin

pin在 `tests/fixtures/book46007447/a24-c01-readonly-pins-20261023.json`，仅列 `annotation`包标记、`contracts/`和`geometry/`50份文件，没有runtime/delivery/target源码。来源为已有固定A24包的未改baseline：

`handoffs/b/a24/a24-offline-replay-20261022-v2-final.zip`，SHA256 `c4ad1b298dd34a8b0a5ec8706a3514fefe19d9a33582cd27fa826ef1a94ec89e`。

将其中 `a24-offline-replay/baseline/<pin成员路径>` 的原字节保留到自选源码目录。不要执行包内replay/runtime，不必复制完整A树。源码文件逐一与pin长度/SHA核对，pin文件自身SHA由调用者显式传入。该pin曾逐项对照固定c5提交Git blob；若A发布新版本，先审查新闭包/差异后另出pin，不直接更改提交号或放宽检查。

## 参数化入口

```powershell
$c01Python = '<已有Python3解释器>'
$c01Source = '<仅含固定50份源码的目录>'
$c01Pins = '<仓库>/tests/fixtures/book46007447/a24-c01-readonly-pins-20261023.json'
$c01PinsSha = (Get-FileHash -LiteralPath $c01Pins -Algorithm SHA256).Hash.ToLower()
& $c01Python -B -X utf8 tools/consume_b_c01_readonly.py --a-source $c01Source --pins $c01Pins --pins-sha256 $c01PinsSha --bundle '<第二课时C01包>/bundle.json' --expected-questions 9 --out '<尚不存在的私有完整读回.json>'
```

所有输入/输出路径均为必填参数；没有个人目录或profile默认值。可从任意cwd调用该工具的绝对路径。固定格式仍为 `c01-exchange-1`、artifact schema `1.0.0-a-proposal`。只有全部验证通过才独占创建读回文件，`full_object`保存整个读回，不只保存题数或投影。不要把含题文的读回提交到公共Git。

脚本在导入消费者前阻断网络/子进程入口和delivery/runtime/target等模块导入。该限制服务于纯合同读取，不是OS级沙箱。

## 已验证与待核范围

固定Q16 v2包（SHA `4725523ec499a3074b268b12f0282ca795c13ddd98e97350078a50db89f7dc93`）实际读取四任务/26片段、资源字节校验及完整对象比较通过。四任务假充九题、私有候选schema假充C01、篡改资源字节均实际拒绝。第二课时九题必须消费其真实最终包，不能拿四任务结果或合成fixture替代。

B01准备Source/Evidence和原图来源，B02准备九题QuestionGraph/片段/配答及同号变式隔离，B03准备PRE_APPLY检查与独立来源/覆盖口径。原始OCR、图/公式、null/unknown及修订来源通过原C01的证据资源或旁文件保留；未经确认的身份、关系、政策和覆盖不得为通过解析而升级。完整C01对象相等仍不代替源稿到C01的语义对应核验或人工内容正确性。
