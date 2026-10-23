# B03 第二课时 C01 独立检查

独立质量线只读取本地冻结内容。三个入口分别做安全解包、固定未改写 A24 C01 消费和 B03 来源内容检查，不修改公共合同，不操作网站/profile，不调用平台运行时或 OCR。

```powershell
python -I tools/safe_extract_b_content.py --archive fixed.zip --sha256 ZIP_SHA256 --destination fresh-package --out extraction.json
python -I tools/consume_fixed_a24_c01_b.py --a-source fixed-a24-source --pins fixed-c01-pins.json --bundle fresh-package/delivery/bundle.json --out a24-readback.json
python -I tools/audit_lesson_c01_b.py --delivery fresh-package/delivery --oracle evaluation/b03-lesson2-independent-source-oracle.json --options evaluation/b03-lesson2-independent-option-regions.json --out content-review.json
```

固定 A24 提交为 `c5aefbc8e995c410b3babf74a251f05a7724a1c2`。消费入口要求固定 pins 文件的原始摘要，逐一重核50份合同/几何源码后，调用原 `annotation.contracts.load_bundle(..., verify_assets=True)`，比较完整对象。依赖本机 Pydantic；来源图像与裁片检查另需 Pillow，不安装或下载依赖。私有来源预期由本线直接读固定原图后手工记录，含题序、数学关系、选项和来源摘要；协调 review 只作被检输入，不能代替独立预期。原文与原图不随此代码提交。

本线实际读取的第二版目录中，九题题答与来源匹配，含9条已确认关系、43个活动语义片段、46个来源区域及逐像素裁片、10组配图和8个未填题空。Q2/Q6/Q7各四个独立选项，原三组合框保留为非活动诊断。已单独核对12框与固定原图；Q7顶部扩展以完整原始字形为据，不要求仍被旧合框包住。`EXCLUDED/UNASSIGNED` clue 不得携带已分配 region_ids。

15个实际目录故障样例全部被固定 C01 消费或本线来源检查拒绝。缺裁片和若干重新签摘要的错误正文可以满足 C01 的有限结构检查，因此另核侧文件资源、片段完整性、源图像素及来源语义。正常结构并不代表来源内容正确。这些有限检查不构成通用识别准确率或全书覆盖证据。

安全解包另跑正常对照及七个拒绝样例，包括路径越界、Windows盘符、反斜杠、链接、大小写重复成员和已有输出目录。解包检查只证明安全落盘；最终 ZIP 仍须实际解到新目录，检查 manifest、所有资源并运行其重放入口。目录检查通过不能代替尚未取得的最终容器验证。

B 内容通过、C01 PRE_APPLY 的平台政策提示、A所有者接收和独立人工确认分别记录。缺少人工签字不单独阻断已核对的正常九题内容。没有网站/平台/整章验收结论；CI 合成回归与当前真实内容包检查分开报告。

最终 `82faa8…` ZIP已实际新目录解包与包内重放，通过116清单成员、54文件原字节重建及固定A24读回。正式范围见[独立最终报告](reviews/b03-independent-lesson2-c01-20261024.md)。

本批限定题序、数值、配答与12个选项坐标预期已脱敏固定在 `evaluation/b03-lesson2-independent-*.json`，不含个人路径、服务器身份或原始响应。包内重放之后可执行：

```powershell
python -I tools/replay_b03_negative_cases.py --package fresh-package --oracle evaluation/b03-lesson2-independent-source-oracle.json --options evaluation/b03-lesson2-independent-option-regions.json --out independent-negative-cases.json
```

该入口不导入生产者构造器，以固定包正常对照为起点，实际运行15个故障副本；陈旧CheckReport使用可复现的陈旧subject引用，实际旧版混包另已检查。

脱敏独立预期和选项文件按固定JSON内容摘要核对，保留类型与值，避免Git换行转换影响复现；原图、ZIP和原始选项审校原件仍按原始字节SHA固定。
