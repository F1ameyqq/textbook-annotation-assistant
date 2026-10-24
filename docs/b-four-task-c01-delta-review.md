# Q16与阅读三任务C01差量核对入口

本线仅做离线合同读取和来源关系核对。固定A24 `c5aefbc8e995c410b3babf74a251f05a7724a1c2`；无writer、浏览器、profile、planner、target或dispatch。不重复已完成的九题发布，也不推送。

## 已完成的准备

历史Q16/阅读v2包实际新进程完整消费通过，bundle SHA256 `95488a276535a7bee7094238b02c6b41574e37df19d7b946830c6c07f9a824d6`，规范完整对象SHA256 `674f7270f3aa1064e018099699b9caa3772d7f38d78608658d1af99220f38d8f`。4任务、26片段、37证据区域；独立来源/映射186项通过，包括37切图原图像素比对。后续指定最终v3已实际消费并收口，结果见本文末。

历史语义身份为独立Q16 `q-457f1973a1426d29587d5752`，阅读任务 `task-f76ca3153a12aea40b7d481b`、`task-0a662336bef0b2eaec440a6b`、`task-b8a3d034281fd685a5509780`。三个阅读任务各自引用相同8个shared_material片段；Q16没有共享阅读材料。题页分别viewer15/viewer13，答案viewer173；原图摘要固定。

旧包四配答为UNRESOLVED。一次明确标记为局部内存试验的原A24校验已确认：四artifact同ID升revision2，重封全部引用后，四关系可表达为SELECTED，原题/共享片段字段完整保留。不改公共合同，没有写出或接受真实新版包；旧质量审核及原始证据未升级。

旧`verify_q16_reading_b.py`把UNRESOLVED、历史review/basis SHA和18项旧人工pending写死，不适合新模型来源复核的SELECTED交付。新入口仍调用现有固定消费者，仅在成功后独立核对差量，旧规则未放宽或替换公共合同。

## 两阶段命令

路径全部显式传入，没有个人目录默认值。prepare要求已有真实固定A24完整读回receipt，并将整个bundle、全部JSON旁文件和期望身份冻结为有摘要的基线；compare只在新包已有具体路径后调用。

```text
python -B -X utf8 tools/review_four_task_c01_b.py prepare --receipt <历史完整读回.json> --delivery <历史delivery目录> --out <新建基线目录>

python -B -X utf8 tools/review_four_task_c01_b.py compare --prepared <历史四任务已冻结基线目录> --new-delivery <新四任务delivery目录> --new-bundle-sha256 <内容线公布的固定bundle原字节SHA256> --label-source-manifest --a-source <固定50源码目录> --pins <固定pin.json> --pins-sha256 <pin原字节SHA256> --consumer <consume_b_c01_readonly.py路径> --out <新结果目录>
```

若来源成员明确重命名了本地实体，可加`--identity-map <局部映射.json>`，只接受显式question_ids/fragment_ids/asset_ids/blank_ids映射，不按印刷号或数组位置猜同一题。该配置仅为本地核对参数，不是新的内容交换合同。

## 差量及拒绝口径

先由原A24完整读取并核资源，再保存完整对象读回。其后逐项核四身份、8共享片段、3任务共享引用、独立Q16题页、4条SELECTED本题答案、原图摘要、6个未填blank、11公式slot、所有绑定runs与区域文字、全部切图SHA和原图像素。旧三阅读task不借用Q16答案。

完整差量列出所有bundle及JSON旁文件的字段增加/删除/值变更；数组按序、标量按类型比较，保留额外字段。分别记录每类artifact原/新ID、revision、content_hash：允许新不可变artifact ID，旧ID内容有变时必须升revision；不强迫生产者采用某一种发布命名。

合同读取拒绝时记录`REAL_NEW_PACKAGE_CONTRACT_REJECTED`，无成功读回。合同通过而语义/来源核对有差异时记录`REAL_NEW_A24_READ_MAPPING_REVIEW_REQUIRED`，列明具体失败，不把“可解析”升级为内容通过。全部核对通过才记录本线消费/映射通过；仍不代A所有者、独立真人、平台或章节覆盖验收。

在具体新包路径到位前，本轮停留在准备完成，不轮询目录、不重跑旧CI。

## Q16三小问标签的定点修订

QA发现原书（1）（2）（3）未进C01文字/runs；根要求仅补回这三项，其余内容、公式、答案、空白与几何不变。准备时未读可变v3目录；收到固定SHA后才实际消费。

实际生产者已提供从原v2逐项列出before/after、完整runs、来源bbox及PNG/RGB SHA的三条source_text_changes，故最终采用`--label-source-manifest`直接核对不可变历史v2，不再读取已废弃的73cddd中间稿。三处标签是唯一正文/runs变化；先前已授权的四SELECTED、本地目录分离及B来源确认另做精确核对，不混称正文变化。新bundle SHA必须显式传入且消费前后均核值。

`verify_q16_label_delta_b.py`精确接受三个前缀：q16-task1→（1）、q16-task2→（2）、q16-task3→（3）。三处均须在C01 region.text、delivery绑定runs和current-review绑定的source_text_changes中一致，且新region.text严格等于标签+旧文字。实际版只在首个plain run内补前缀；其余runs字段/顺序逐字一致。所有旧basis、proof、题答映射、公式slot和阅读答案完整对象不变。

所有三标签变化的完整路径、原图box和裁片摘要均输出。来源确认模式将37个certainty改为CONFIRMED、四条关系改为本题全部候选SELECTED及显式本地目录路由分别验证；全部区域除certainty/指定三标签外必须完整相等，全部绑定除三前缀外必须完整相等。公式、答案、空白、几何、proof、原图不在豁免内。完整原新bundle和全部JSON旁文件的220项字段差量另行保留，发布封装、政策/检查说明及审核元数据没有被藏掉或混称正文不变。

若已有实际消费的相邻四SELECTED冻结包，也保留`--label-baseline <prepared目录> --label-baseline-manifest-sha256 <固定SHA>`的严格相邻版本模式；不能用未固定或废弃草稿替代它。两个label模式互斥且必须选一个。

## 指定最终ZIP的实际独审结果

唯一容器为生产者`B-46007447-Q16-reading-C01-v3-20261024-final.zip`，SHA256 `1362c7582bacce796b518bdf12e421537ef69be768da39bed99209777a46d2fd`，6,266,082字节、119成员。独立安全新目录解包，118清单成员逐一核长度/SHA；包内50源码与本线固定A24字节相同。

固定bundle SHA256 `ed656b23e1c343a2d11d09f6006bb22ddb90fbe64120d75f38facdd154c17f38`；完整对象规范SHA256 `a1d3311dd56a5ca8f7825f93e6b039c8c10602fda25dc05bc0a92fe027160282`。原A24完整对象读回通过，4任务、26片段、37区域/切图、8共享片段由3阅读任务共用，独立Q16没有混入阅读共享材料；4条本题SELECTED关系、6个null空白、11公式slot保全。

224项独立映射、来源、精确标签及摘要核对通过；220项完整字段差量已保留。三裁片已目视核原书标签。针对实际固定输入的缺标签、额外正文、公式变动、填空污染、几何移动、Q16错目录及第四条标签记录7类局部内存变异均被拒绝，不将变异夹具当新C01交付。

指定最终ZIP已新目录包内fresh replay：50个交付文件逐字节重建一致，固定A24完整读回对象一致。原v2 ZIP与本线固定原件逐字节相同，46个旧delivery成员分别原位复用或保留到history/v2，全字节相等。没有重封装其它包或推送。

B内容已就绪、问题为空。PRE_APPLY仍HOLD，仅保留正式policy采纳与整页/全章目标覆盖未确立；A所有者、真人和平台验收分别保留未声明。平台请求、writer、dispatch与新OCR均为0。
