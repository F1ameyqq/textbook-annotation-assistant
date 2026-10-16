# 46007447：只读来源读取与连接恢复

日期：2026-10-16（Asia/Shanghai）。详细实测摘要见 `evaluation/book-46007447-readonly.json`。

## 本轮如何恢复

原 CUA/Edge 控制通道持续超时；没有声称修复该通道。经用户明确要求尝试其他方式，改用本机已运行的 Kimi Browser Extension / WebBridge。
守护进程和扩展已连接，但旧会话没有标签页。使用独立会话 `B-side-readonly-46007447`，正常打开网站后读取成功。
不启动新调试端口，不修改代理、证书设置或登录凭证。用户的原页面不刷新。

协议以 [官方工具说明](https://github.com/MoonshotAI/kimi-code/blob/main/plugins/official/kimi-webbridge/skills/kimi-webbridge/SKILL.md) 为准：

1. 检查 `kimi-webbridge status`、当前任务的 `list_tabs`；daemon 就绪不等于会话已有页面。
2. 首次 `navigate` 正确指定 task session 和网站 URL；后续使用同一 session，以免操作另一组标签页。
3. `snapshot` 取得实际网址及元素引用，只点击选书、已有题目和读取/导出入口。
4. 在正常选书前启动 `network` 观察，收集已发生的站点 GET 的响应 body；不保存 requestHeaders/authorization/Cookie。
5. Windows 请求体必须使用 UTF-8 临时 JSON 文件和 curl.exe --data-binary，不能把中文 JSON 直接拼入命令行。
6. 本次版本的旧 `fetch` action 不可用；不要继续按旧 land_data.py 的调用方式重试。直接不带应用授权头的 OCR GET 返回 401，不提取 token 补头。
7. “更多操作”为悬停菜单；等待最新 snapshot 出现 menuitem 后，正常点击“导出试卷试题”。本次 GET 成功取得 JSONL。
8. 保存原图摘要、尺寸、真实页面映射、读取范围和未核准状态；完成后停止自己的 network 观察。

正常读取不使用目录编辑、插题、清理脏数据、识别、保存或提交入口。状态不明的输入动作不能盲目重发。

## 本次实际取得

- 平台报告 214 页，目录有 8 个根、121 个目录组、22 个题目节点；不是全书采集完成。
- 68 条历史框：question 35 / answer 24 / choice 9；全部 verified=0。
- 查看器页 10/11/12/14/173 分别返回资源索引 9/10/11/13/172，取得 5 张原图并检查全部 68 框边界，未发现越界。
- 这五页的机器预标注 blocks 均为空。几何合法不代表内容、题答或标注粒度正确。
- OCR 任务摘要有 19 条：18 SUCCESS、1 PARTIAL_FAILED；平台题序 7/19/22 没有返回任务记录，不能据此断言状态。
- 正常“导出试卷试题”返回 19 行 JSONL，含题干/选项/答案/解析。导出 tixu 连续 1..19，不能直接等同平台 order_in_level；逐条映射仍待核准。
- 第 4 题历史状态 PARTIAL_FAILED，原因“部分图片识别失败”。原答案图为 13，导出答案为 1:3；具体失败图片仍未知。
- 第 4、17 题各有两个答案框，作为待复核信号，不自动删除、合并或当作真值。

## 给 A/B 的交接

用户侧已有局部来源包，含便携 `b-source-trial/0.1` 清单、5 张原图、目录、历史框、任务摘要、19 行原始 JSONL 和 SHA-256 清单。
该包尚未作为正式 SourceBundle 合同实现，也未自动上传原始数据到仓库。A 可据包核准来源和导出身份；B 的离线输入加载器已校验这 5 个资产。

后续必须分别验证：平台题身份、印刷题号、导出 tixu 的关系；图像/公式内容；跨框和跨页组合；独立整页覆盖。
第 4 题可作为“平台任务结束或导出成功，内容仍不可靠”的真实回归线索。历史数据与独立留出真值保持区分。
