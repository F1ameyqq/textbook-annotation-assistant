# 固定 Q1：当前验收与历史证据

## 当前有效结果

`ACCEPTED_FIXED_Q1_OFFLINE_ROLE_CORRECTED`，A07-F01 已关闭并本地集成。范围仅固定 Q1 的 A 侧离线模拟，最终角色 `Q/W/W/W/W/A`。四选项角色变化，六框内容、原图、坐标、身份、顺序不变。

| 身份 | 固定值 |
|---|---|
| B 输入提交 | `ef6ba4dd083e7fd5378e80123b2b038dd11d7052` |
| B 原 ZIP SHA256 | `b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d` |
| Q1 旁文件 ZIP SHA256 | `3039645ca69c2604f542c479cb180049604788a3ca28ffac1b5063dee533afac` |
| 获验产品候选 | `3d22524ff626fc7b0376b7312be6fe75f2e73aab` |
| 作者固定交付 | `6f8f1d6fa4c8db9678738673a54fa862df9a666e` |
| 独立固定交付 | `71bf89251a3225a7e0defe5fc6feb84d0628dd85` |
| 调度接受 | `4abed4ad823e2c499a6e273374a30a42941dfed6` |
| 本地集成 | `0a0b3ed5ae044706b633ff767f1b7bd6211a9039` |
| 独立回执 | `a07-receipt-a07-f01-review-1`，revision 1 |
| 回执 C01 摘要 | `6eef5b12bbc20b61f3d1cbb37f28fce4f184e6c72416c5edcf50f4d0e9b2325f` |
| 独立实际读回文件 SHA256 | `5c1b51f0c5fd01c65876fe9904f08664f0598887a4614f4411b9e8619d7d0cd0` |

本表的历史提交用于身份追溯，不承诺其全部 Git 祖先在发布分支可达；清单保全的是相应原始文件及 Git blob。

## 修复后证据

- [作者报告](../../tasks/A07-F01-execution-report.md)与[58成员清单](../../evidence/A07/F01/execution/delivery-raw-manifest.json)。
- [独立报告](../../tasks/A07-F01-review-report.md)与[55成员清单](../../evidence/A07/F01/review/raw-git-manifest.json)。
- [角色门对照](../../evidence/A07/F01/review/archive-delta-review.json)及[调度逐框比对](../../evidence/coordinator/a07-f01-20261018/review-recorded-delta.json)。
- [调度接受](../../tasks/A07-F01-coordinator-acceptance.md)、[释放与范围记录](../../evidence/coordinator/a07-f01-20261018/release-and-scope-notes.json)、[本地集成](../../tasks/A07-F01-local-integration.md)和[集成静态检查](../../evidence/coordinator/a07-f01-20261018/integration-check.json)。

作者与独立本轮各1次正常尝试/1dispatch/1成功，各2次零写入角色门核对、1次原 CLI 自带重放拒绝；没有追加运行。新独立计划、实际 frame 和 projection 都是正确角色，读回零差异。调度仅核对归档，不新增正常业务。

## 必须保留的旧记录

[原角色缺口发现](../../tasks/A07-Q1-role-mapping-finding.md)、[旧独立报告](../../tasks/A07-Q1-review-report.md)、[旧独立回执](../../evidence/A07/review/candidate-1/normal/run/receipt.json)、[旧实际读回](../../evidence/A07/review/candidate-1/normal/run/assets/readback.json)和旧作者/独立清单均按原字节保留。旧 Q/Q/Q/Q/Q/A 与当时 PASS 只记录历史结果，不能作为当前角色符合性的依据。

[旧作者清单](../../evidence/A07/execution/delivery-raw-git-manifest.json)绑定旧产品；其中 reader.py 与 quality/q1_offline.py 正是本次改变的两条源码。发布清单将这两条旧成员指向 [旧 reader 原字节快照](history/reader.py.txt)和[旧 quality 原字节快照](history/q1_offline.py.txt)，不改旧清单，也不假称旧摘要对应新源码。其他历史成员可按原路径核对。

所有历史任务单、脚本、机器日志中的本机路径及旧状态属于当时的审计元数据，不能照其历史指令重新开工。当前有效入口是[本次交接说明](../../a07-q1-handoff.md)。归档读取和完整性校验不授予新的模拟、平台或发布权限。
