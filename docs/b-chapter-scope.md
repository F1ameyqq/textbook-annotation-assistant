# B 侧完整章节范围入口（本地试行）

`tools/prepare_chapter_scope_b.py` 将章节的预期页/资产清单与实际收到的本地图像逐项对账，生成既有离线流水线可读的 `b-source-trial/0.1` 来源描述符和缺口报告。它不读取网站、不运行识别模型、不造题目、答案或人工 gold。

## 输入格式

```json
{
  "schema_version": "b-chapter-scope-input/0.1",
  "book_id": "46007447",
  "scope_id": "chapter-identifier",
  "chapter_id": "chapter-identifier",
  "inventory_frozen": true,
  "pages": [
    {"page_id": "printed-page-12", "page_order": 0, "required_asset_ids": ["page12-front"]},
    {"page_id": "printed-page-13", "page_order": 1, "required_asset_ids": ["page13"]}
  ],
  "assets": [
    {"asset_id": "page12-front", "page_id": "printed-page-12", "path": "images/page12.png",
     "sha256": "<64 lowercase hex digits>", "width": 1200, "height": 1700},
    {"asset_id": "page13", "page_id": "printed-page-13", "path": "images/page13.png",
     "sha256": "<64 lowercase hex digits>", "width": 1200, "height": 1700}
  ]
}
```

`pages` 是冻结的章节分母；每页列出必须收到的全部源资产。一个物理页可对应多个资产（例如分片），但每个资产 ID 必须唯一且归属一个预期页。`required_asset_ids` 按该页内的实际阅读顺序排列；输出先按 `page_order`，再按此有序列表，不能用资产名称排序代替分片顺序。`path` 相对清单所在目录。为使生成的 B 来源描述符可直接使用，`--out` 必须是包含这些图像的目录；报告会把目录之外的图像列为 `ASSET_OUTSIDE_OUTPUT_ROOT`。页面身份应使用调用方已有的稳定标识，不要从观察到的局部题号推测。

## 运行

```powershell
python tools/prepare_chapter_scope_b.py --scope path/to/chapter-scope.json --out path/to/source-root
```

产物为 `source-root/source-descriptor.json` 和 `source-root/chapter-scope-report.json`。清单未冻结、缺页/资产、重复身份、页资产归属冲突、源文件缺失、SHA 或解码尺寸不符时，范围状态为 `PARTIAL`，逐项缺口保留。此时可继续收集材料或对已收到部分做离线工作，但不能称为完整章节。

经对账后得到 `DECLARED_COMPLETE_SOURCE_INVENTORY`，只表示所声明的冻结库存与当前本地文件吻合。它仍不是章节业务验收：题目/答案/共享材料的目录清点、身份映射、内容复核、异常处理回执及独立验收仍需完成，报告中的业务决定始终为 `HOLD`，`business_acceptance` 和 `transcription_verified` 始终为 false。
报告把调用方的 `inventory_frozen` 记录为 `inventory_frozen_claim`，并始终令 `independent_denominator_verified: false`；单凭自报清单无法证实整章分母。

## 独立质量复现后的收紧（2026-10-17）

同一实际路径或相同文件 SHA 被声明为多个资产时报告 `ALIASED_SOURCE_ASSET`，不再计作完整来源库存；真实重复空白页等情况也需先独立解决身份歧义。章节交付门禁同时拒绝同资产/同字节别名页及题答页角色冲突。当前单角色格式不支持把同一页拆成多个身份来表达混合内容。

章节门禁的 `checks.binding` 必须绑定当前 manifest 和候选内容，旧的 `PASS + 0` 自报检查不再足以得到机器 PASS。绑定字段为 `manifest_sha256` 与 `candidate_content_sha256`，对完整 manifest、去掉 `checks`/`human_review` 的 candidate 分别作 canonical JSON SHA-256（UTF-8、键排序、紧凑分隔符、`ensure_ascii=false`）；`--contract` 给出当前要求。内容/来源/身份或 manifest 改动后旧绑定失效，必须实际重检再出具新记录。绑定只是内容一致性证明，不认证检查作者或人工核对；G2 恒为 HOLD。缺失/不全的人工声明也明确列为机器 PARTIAL，不能借此签发人工验收。

G07/Check07 适配器现在重新计算两份 payload 的摘要并校验精确图谱引用，拒绝重复答案 ID、悬空或格式错误的候选关系及重复 JSON 键。合成输入须按真实格式提供摘要；正常真实固定输入仍投影 34 题/66 答及 127 未决项，不补造章节身份。

## 与现有流水线的关系

现有 `tools/run_pipeline_b.py` 接收一个 source manifest，其中 `assets` 可包含多个图像；批处理按资产记录恢复、缓存与失效，并以 source/scope 身份隔离运行。用生成的 `source-descriptor.json` 作为 `--source`，还须按这些资产准备现有 `--context` 和 `--review` 输入，再指定持久 `--workdir`。14 阶段内容修订链还需要显式提供其相应 recovery/continuation/inline/content-revision 输入；章节入口没有合成这些输入。具体停止阶段、恢复和依赖失效由现有 pipeline 管理。增加页面或修正原资产 SHA 会改变来源输入身份，受影响的阶段应按既有依赖键重检。

当前仓库中的 `46007447` 固定来源仍只有五张被记录的整页和第六资产的前缀裁片；章节页数、目录和完整页资产仍未知。现有 14 阶段真实记录与该固定局部来源，不构成完整章节 manifest。没有真实章节来源及独立清单时，本入口只能产生 `PARTIAL/HOLD`。此工具的 schema 仍是 B 内部试行格式，公共合同草案未冻结，A 侧消费者未验收。
