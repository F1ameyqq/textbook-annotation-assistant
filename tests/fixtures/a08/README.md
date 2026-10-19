# A08 有限变体配方

输入为调度登记的固定 ZIP，不复制或修改原件。`tests/test_a08_reception.py` 冻结 `mutate` 与 `repack`，记录每个变体 bytes/SHA、命令、退出码及实际门。

R0 原件一次；R1 schema/kind 两变体；R2 资源坏摘要一次；R3 同号跨章节 Q4 配答一次；R4 给 Q9 造题一次；R5 资产别名/未知 viewer 填值两变体；R6 删除 Q9 后页呈现区/Q16 一个 LaTeX run 两变体；R7 Q1 审批及 30 项排除/外加批准两变体。共 8 组，1 正向结构接收、11 拒绝。

每个负例单独从原件生成。除 R2 故意损坏之外，更新 standalone case、batch、stage receipt 的 batch SHA 和内外 manifest 的 SHA/bytes，使目标检查层可达。R6 的预期是固定结构库存门，不能称为新公式/续接语义判断。

ZIP 重新封装的摘要不等于固定输入，产品最终固定字节门仍关闭；负例无法成为新业务案例。临时副本只在本任务 `examples/a08/` 新目录中产生；全通过后删除该新目录，失败则保留首次现场。
