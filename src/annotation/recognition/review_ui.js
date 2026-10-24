/* Local draft review. Source strings enter the DOM only as text or form values. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const MATH_NS = "http://www.w3.org/1998/Math/MathML";
  const roleLabel = (role) => ({question: "题干", choice: "选项", answer: "答案", analysis: "解析", explanation: "解析"}[role] || "正文 / 答案");
  const authorLabels = { MODEL_DRAFT: "模型草稿", HUMAN_DRAFT: "人工草稿 · 未核准", SYNTHETIC_TEST: "合成测试草稿" };
  const ruleLabels = {
    CONTENT_REGION_REBUILD_DRAFT_UNVERIFIED: "来源区域重建的文字仍待逐字核对",
    CONTENT_REGION_SOURCE_GEOMETRY_DRAFT_UNVERIFIED: "来源裁边记录仍待人工核对",
    CONTENT_REVISION_DRAFT_UNVERIFIED: "当前正文含未核准的草稿修订",
    CONTENT_EDIT_DRAFT_UNVERIFIED: "显式文字编辑仍待核对",
    CONTENT_INLINE_SELECTION_DRAFT_UNVERIFIED: "所选模型候选仍待核对",
    CONTENT_RAW_WRAP_DRAFT_UNVERIFIED: "原文跨行连接仍待核对",
    CONTENT_SELECTED_FORMULA_CLOSURE_CONFLICT: "所选公式与原文连接处存在冲突",
    CONTENT_SELECTED_FORMULA_SYNTAX_UNSUPPORTED: "所选公式含暂不支持的语法",
    INLINE_CONTENT_TRANSCRIPTION_UNVERIFIED: "行内文字与数学候选未核准",
    INLINE_FORMULA_SYNTAX_UNSUPPORTED: "公式候选含暂不支持的语法",
    INLINE_FORMULA_SOURCE_WRAP_CLOSURE_CONFLICT: "模型公式与原文闭合位置存在冲突",
    BUSINESS_REVIEW_REQUIRED: "仍需要独立的内容复核",
    ANSWER_BOUNDARY_UNRESOLVED: "答案结束边界仍待确认",
    ANSWER_VALUE_MISMATCH: "答案数值与参考不一致",
    CONTINUATION_DEVELOPMENT_TRANSCRIPTION_DISAGREEMENT: "续页原文与开发参考存在转写差异",
    ANSWER_UNASSIGNED_SOURCE: "存在尚未归属的来源文字"
  };
  let state = null;
  let csrfToken = "";
  let currentAnswerId = null;
  let drafts = new Map();
  let busy = false;
  let pendingNavigation = null;
  let restoreHead = null;
  let dialogSource = null;
  const previewRequests = new WeakMap();

  function node(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined && text !== null) element.textContent = String(text);
    return element;
  }
  function button(text, callback, className = "") {
    const element = node("button", className, text);
    element.type = "button";
    element.addEventListener("click", callback);
    return element;
  }
  function formatBox(bbox) { return Array.isArray(bbox) ? bbox.join(", ") : "未提供范围"; }
  function pathText(path) { return Array.isArray(path) ? path.join(" / ") : "未提供章节"; }
  function shortId(value, length = 18) { return typeof value === "string" && value.length > length ? value.slice(0, length) + "…" : String(value ?? "—"); }
  function currentAnswer() { return state?.answers.find((answer) => answer.answer_id === currentAnswerId); }
  function rawRuns(runs) { return (runs || []).map((run) => ({ format: run.format, text: run.text })); }
  function runsEqual(left, right) { return JSON.stringify(rawRuns(left)) === JSON.stringify(rawRuns(right)); }

  async function request(path, body) {
    const options = { method: body === undefined ? "GET" : "POST", cache: "no-store", credentials: "same-origin", redirect: "error" };
    if (body !== undefined) {
      options.headers = { "Content-Type": "application/json", "X-Review-Token": csrfToken };
      options.body = JSON.stringify(body);
    }
    const response = await fetch(path, options);
    let value;
    try { value = await response.json(); }
    catch (_) { throw new Error("服务器未返回有效的复核数据，请检查本地服务状态。"); }
    if (!response.ok || value.ok === false) {
      const error = new Error(value.error?.message || "本地请求失败。");
      error.code = value.error?.code;
      error.status = response.status;
      throw error;
    }
    return value;
  }
  function feedback(message, isError = false) {
    const element = $("feedback");
    element.textContent = message;
    element.classList.toggle("error", isError);
    element.hidden = !message;
  }
  function showError(error, prefix = "操作未完成") {
    const stale = error.status === 409 ? " 当前草稿仍保留在页面中；请刷新并核对最新版本后再保存。" : "";
    feedback(prefix + "：" + error.message + stale, true);
  }
  function setBusy(value) {
    busy = value;
    $("review-content").inert = value;
    document.querySelector(".answer-sidebar").inert = value;
    const inspection = document.querySelector(".inspection-sidebar");
    inspection.inert = value;
    inspection.setAttribute("aria-busy", String(value));
    $("refresh-button").disabled = value;
    $("guard-save").disabled = value;
    $("guard-discard").disabled = value;
    $("guard-cancel").disabled = value;
    $("history-confirm-yes").disabled = value;
    if (state) {
      updateAnswerArrows();
      const history = state.history || [];
      const current = history.find((entry) => entry.head === state.head);
      $("undo-save").disabled = value || !current?.parent_head || !history.some((entry) => entry.head === current.parent_head);
    }
    updateDirtyState();
  }
  function changeFor(draft) {
    const block = draft.block;
    if (block.kind === "REGION") {
      const selections = [...draft.regionSelections.values()].sort((left, right) => left.run_index - right.run_index);
      if (runsEqual(block.runs, draft.runs) && !selections.length) return null;
      const change = { key: block.key, runs: rawRuns(draft.runs) };
      if (selections.length) change.region_selections = selections.map((selection) => ({ ...selection, bundle_ref: { ...selection.bundle_ref } }));
      return change;
    }
    if (draft.candidate) return { key: block.key, ...draft.candidate };
    if (draft.text === block.text && draft.format === draft.initialFormat) return null;
    return { key: block.key, text: draft.text, format: draft.format };
  }
  function dirtyDrafts() { return [...drafts.values()].filter((draft) => changeFor(draft) !== null); }
  function updateDirtyState() {
    const dirty = dirtyDrafts();
    $("dirty-label").textContent = dirty.length ? dirty.length + " 个编辑块尚未保存" : "没有未保存更改";
    $("save-hint").textContent = busy ? "正在校验来源、保存新版本并重检…" : "只保存当前答案中改变的编辑块；原始 OCR 和图片保持来源记录。";
    $("save-button").disabled = busy || dirty.length === 0;
    $("discard-button").disabled = busy || dirty.length === 0;
    for (const draft of drafts.values()) {
      const changed = changeFor(draft) !== null;
      draft.card?.classList.toggle("dirty", changed);
      if (draft.dirtyBadge) draft.dirtyBadge.hidden = !changed;
      if (draft.resetButton) draft.resetButton.hidden = !changed && !(draft.block.kind === "REGION" && !draft.regionMappingEnabled);
    }
    document.title = (dirty.length ? "● " : "") + "教辅 · 离线内容复核";
  }
  function cancelNavigation() {
    pendingNavigation = null;
    $("navigation-guard").hidden = true;
  }
  function guarded(action, label) {
    if (busy) return;
    if (!dirtyDrafts().length) { action(); return; }
    pendingNavigation = action;
    $("guard-message").textContent = "当前答案有未保存更改。" + label;
    $("navigation-guard").hidden = false;
    $("guard-cancel").focus();
  }
  function getAuthor() {
    const author = { kind: $("author-kind").value, id: $("author-id").value, note: $("author-note").value };
    if (!author.id.trim()) { $("author-id").focus(); throw new Error("请填写本次草稿作者标识。"); }
    if (!author.note.trim()) { $("author-note").focus(); throw new Error("请填写本次草稿说明。"); }
    return author;
  }

  function applyState(next, preferredAnswer = currentAnswerId) {
    if (!next || next.schema_version !== "b-content-review-state-trial/0.1" || !Array.isArray(next.answers) || !Array.isArray(next.issues)) throw new Error("工作区状态格式不受此界面支持。");
    if (next.decision !== "HOLD" || next.complete !== false || next.transcription_verified !== false || next.business_acceptance !== false || !Array.isArray(next.platform_actions) || next.platform_actions.length) throw new Error("工作区返回了不符合草稿边界的状态。");
    state = next;
    $("customer-confirm").hidden = !next.customer?.can_confirm;
    $("customer-status").textContent = next.customer ? next.customer.job_status + " · " + next.customer.message : "";
    $("customer-source-checked").checked = false;
    $("customer-content-checked").checked = false;
    $("customer-structure-checked").checked = false;
    if (typeof next.csrf_token === "string") csrfToken = next.csrf_token;
    currentAnswerId = next.answers.some((answer) => answer.answer_id === preferredAnswer) ? preferredAnswer : next.answers[0]?.answer_id ?? null;
    $("book-label").textContent = "书籍 " + next.book_id + " · " + next.scope_id;
    $("revision-label").textContent = "计划 v" + next.plan_revision + " · " + shortId(next.head);
    $("revision-label").title = "当前冻结版本：" + next.head + "\n图谱：" + (next.graph_ref?.artifact_id || "—") + "\n质检：" + (next.quality_ref?.artifact_id || "—");
    $("workspace-counts").textContent = (next.counts?.questions ?? "—") + " 题 · " + (next.counts?.answers ?? next.answers.length) + " 答案候选 · " + next.issues.length + " 问题 · " + (next.counts?.unassigned ?? "—") + " 未归属来源";
    $("issue-total").textContent = String(next.issues.length);
    $("export-region-catalog").hidden = next.region_catalog_available !== true;
    $("author-kind").value = next.author?.kind || "MODEL_DRAFT";
    $("author-id").value = next.author?.id || "";
    $("author-note").value = next.author?.note || "";
    const oldSection = $("section-filter").value;
    $("section-filter").replaceChildren();
    const all = node("option", "", "全部范围"); all.value = ""; $("section-filter").append(all);
    const sections = new Map();
    for (const answer of next.answers) sections.set(JSON.stringify(answer.section_path), pathText(answer.section_path));
    for (const [value, label] of sections) { const option = node("option", "", label); option.value = value; $("section-filter").append(option); }
    if (sections.has(oldSection)) $("section-filter").value = oldSection;
    $("loading-state").hidden = true;
    $("review-content").hidden = !currentAnswerId;
    $("save-bar").hidden = !currentAnswerId;
    cancelNavigation();
    renderNavigation(); renderAnswer(); renderHistory();
  }
  async function refresh() {
    setBusy(true);
    try { const value = await request("/api/state"); applyState(value.state || value); feedback("已读取当前冻结版本。来源检查和语法预览仍不表示内容核准。"); }
    catch (error) { showError(error, "无法读取工作区"); }
    finally { setBusy(false); }
  }
  $("customer-confirm-button").addEventListener("click", async () => {
    if (busy || !state?.customer || !currentAnswerId) return;
    if (dirtyDrafts().length) { feedback("请先保存编辑，再对照原图确认。", true); return; }
    setBusy(true);
    try {
      const value = await request("/api/confirm", {expected_head: state.head, answer_id: currentAnswerId,
        source_checked: $("customer-source-checked").checked, content_checked: $("customer-content-checked").checked,
        structure_checked: $("customer-structure-checked").checked,author:getAuthor()});
      applyState(value.state);
      feedback("已记录本题客户核对。平台保存与独立读回仍分别记录。");
    } catch (error) { showError(error, "内容尚不能确认"); }
    finally { setBusy(false); }
  });
  $("customer-formula-batch-button").addEventListener("click",async()=>{
    if(busy||!state?.customer)return;
    if(dirtyDrafts().length){feedback("请先保存当前文字编辑，再准备本课公式候选。",true);return;}
    setBusy(true);feedback("正在准备本课明确区域的公式候选；中文混排区域会保留给原图审校…");
    try{const value=await request("/api/formula-batch",{expected_head:state.head,author:getAuthor()});applyState(value.state);
      const report=state.customer.formula_batch_result;feedback(report?.status==="NO_CLEAR_REGIONS"?"没有待准备的明确数学行，请对照原图审校混排区域。":"本课公式候选已保留，请逐项检查后放入草稿；内容尚未确认。");}
    catch(error){showError(error,"本次公式准备已停止，已有结果及失败记录保留，后继未运行");}
    finally{setBusy(false);}
  });
  async function saveCurrent(afterSave) {
    if (busy) return false;
    const changed = dirtyDrafts();
    if (!changed.length) { if (afterSave) afterSave(); return true; }
    let author;
    try {
      author = getAuthor();
      for (const draft of changed) {
        if (draft.block.kind === "REGION" && (!draft.runs.length || draft.runs.some((run) => !run.text || !["plain", "latex"].includes(run.format)))) throw new Error("每个区域文字段都需要非空内容与明确格式；可删除空文字段。");
        if (draft.block.kind === "FRAGMENT" && !draft.candidate && (!draft.text || !["plain", "latex"].includes(draft.format))) throw new Error("请为改变的原文片段填写非空内容，并明确选择纯文本或 LaTeX 格式。");
      }
    } catch (error) { showError(error, "尚不能保存"); return false; }
    const requestBody = { expected_head: state.head, answer_id: currentAnswerId, changes: changed.map(changeFor), author };
    const oldHead = state.head;
    setBusy(true); feedback("正在核对来源和版本，保存后将重新生成当前质检…");
    try {
      const value = await request("/api/save", requestBody);
      applyState(value.state);
      feedback(state.head === oldHead ? "内容未改变，保留当前版本。" : "已保存计划 v" + state.plan_revision + " 并重检。当前仍为未核准草稿。" );
      setBusy(false);
      if (afterSave) afterSave();
      return true;
    } catch (error) { showError(error, "保存失败，未显示为已保存"); return false; }
    finally { setBusy(false); }
  }

  function filteredAnswers() {
    const query = $("answer-search").value.trim().toLocaleLowerCase();
    const section = $("section-filter").value;
    return (state?.answers || []).filter((answer) => (!section || JSON.stringify(answer.section_path) === section)
      && (!$("only-issues").checked || answer.issue_ids?.length)
      && (!query || [answer.printed_number, pathText(answer.section_path), answer.answer_id, answer.text, answer.explanation_text].join(" ").toLocaleLowerCase().includes(query)));
  }
  function selectAnswer(answerId) {
    if (answerId === currentAnswerId) return;
    guarded(() => { currentAnswerId = answerId; cancelNavigation(); renderNavigation(); renderAnswer(); }, "切换答案前，请保存或放弃这些编辑。");
  }
  function renderNavigation() {
    if (!state) return;
    const answers = filteredAnswers();
    $("answer-total").textContent = answers.length + " / " + state.answers.length;
    $("answer-list").replaceChildren();
    $("answer-empty").hidden = answers.length !== 0;
    for (const answer of answers) {
      const item = button("", () => selectAnswer(answer.answer_id), "answer-item" + (answer.answer_id === currentAnswerId ? " active" : ""));
      if (answer.answer_id === currentAnswerId) item.setAttribute("aria-current", "true");
      const top = node("span", "answer-item-top"); top.append(node("strong", "", "第 " + answer.printed_number + " 题"));
      top.append(node("span", "issue-count", answer.issue_ids?.length ? answer.issue_ids.length + " 项" : "未关联问题"));
      item.append(top, node("span", "section-path", pathText(answer.section_path)));
      item.title = pathText(answer.section_path) + "\n" + answer.answer_id;
      $("answer-list").append(item);
    }
    updateAnswerArrows();
  }
  function updateAnswerArrows() {
    const answers = filteredAnswers(); const index = answers.findIndex((answer) => answer.answer_id === currentAnswerId);
    $("previous-answer").disabled = busy || index <= 0;
    $("next-answer").disabled = busy || !answers.length || index === answers.length - 1;
  }
  function moveAnswer(offset) {
    const answers = filteredAnswers(); const index = answers.findIndex((answer) => answer.answer_id === currentAnswerId);
    const answer = answers[index < 0 ? 0 : index + offset];
    if (answer) selectAnswer(answer.answer_id);
  }
  function renderAnswer() {
    $("customer-source-checked").checked = false;
    $("customer-content-checked").checked = false;
    drafts = new Map();
    const answer = currentAnswer();
    if (!answer) { $("block-editors").replaceChildren(); renderIssues(); updateDirtyState(); return; }
    $("answer-title").textContent = "第 " + answer.printed_number + " 题 · 答案候选";
    $("answer-section").textContent = pathText(answer.section_path);
    $("answer-identity").textContent = answer.answer_id;
    renderRegionDraftRisks(answer); renderQuestions(answer); renderSources(answer); renderActive(answer); renderUnassigned(answer); renderRegionBinding(answer);
    $("block-editors").replaceChildren();
    $("no-editable-blocks").hidden = (answer.blocks || []).length !== 0;
    $("region-candidate-help").hidden = !(answer.blocks || []).some((block) => block.kind === "REGION" && block.region_candidates?.length);
    for (const [index, block] of (answer.blocks || []).entries()) $("block-editors").append(renderBlock(block, index));
    renderIssues(); updateAnswerArrows(); updateDirtyState();
  }
  function renderUnassigned(answer) {
    const parent = $("customer-unassigned"); parent.replaceChildren();
    const lines = (state.customer?.unassigned_sources || []).filter(line => JSON.stringify(line.location?.section_path) === JSON.stringify(answer.section_path));
    parent.hidden = !lines.length;
    if (!lines.length) return;
    parent.append(node("h4", "", "未归属答案来源"), node("p", "muted small", "对照整页核对题号、公式和完整内容。可按连续段落整组关联，也可保留逐行选择；分组不会推断题号或核准答案。"));
    const checks = [];
    async function assignSources(lineIds, groupId = null) {
      if (busy || dirtyDrafts().length) { feedback("请先保存当前编辑。", true); return; }
      setBusy(true);
      try {
        const payload = {expected_head:state.head, answer_id:currentAnswerId,
          line_ids:lineIds, source_checked:$("customer-source-checked").checked};
        if (groupId !== null) payload.group_id = groupId;
        const value = await request("/api/assign", payload);
        applyState(value.state); feedback("已按原始来源建立配答；公式、内容及原图完整性仍须核对后确认。");
      } catch (error) { showError(error, "来源尚不能关联"); }
      finally { setBusy(false); }
    }
    const available = new Set(lines.map(line => line.line_id));
    const groups = (state.customer?.unassigned_groups || []).filter(group =>
      JSON.stringify(group.location?.section_path) === JSON.stringify(answer.section_path) &&
      group.line_ids.every(id => available.has(id)));
    for (const group of groups) {
      const row = node("div", "customer-orphan-group");
      row.append(node("h4", "", "连续段落 · " + group.line_ids.length + " 条原始来源"),
        node("p", "muted small", "同页、同栏和同范围的连续来源；未识别的原图内容仍可能缺失，公式阅读顺序未经核对。"));
      const view = node("button", "", "查看段落来源"); view.type = "button";
      view.addEventListener("click", () => showSource(group.asset_id, group.bbox, "未归属段落 · 请结合整页核对"));
      const assignGroup = node("button", "", "整段关联为本题答案并重检"); assignGroup.type = "button";
      assignGroup.addEventListener("click", () => assignSources([...group.line_ids], group.group_id));
      const controls = node("div", "button-row"); controls.append(view, assignGroup); row.append(controls); parent.append(row);
    }
    for (const line of lines) {
      const row = node("div", "button-row"), label = node("label", "check-label");
      const input = node("input"); input.type = "checkbox"; checks.push({input, line});
      label.append(input, document.createTextNode(line.text));
      const view = node("button", "", "查看来源"); view.type = "button";
      view.addEventListener("click", () => showSource(line.asset_id, line.bbox, "未归属答案原文"));
      row.append(label, view); parent.append(row);
    }
    const assign = node("button", "", "关联所选来源为本题答案并重检"); assign.type = "button";
    assign.addEventListener("click", () => assignSources(checks.filter(row => row.input.checked).map(row => row.line.line_id)));
    parent.append(assign);
  }
  function renderQuestions(answer) {
    const parent = $("question-candidates"); parent.replaceChildren();
    const candidates = answer.question_candidates || [];
    if (!candidates.length) { parent.append(node("p", "muted small", "当前范围没有关联题目候选；不会据此新增配答。")); return; }
    const details = node("details"); details.append(node("summary", "", "关联题目候选（只读） · " + candidates.length));
    for (const question of candidates) {
      const item = node("div", "question-candidate");
      item.append(node("h4", "", "第 " + question.printed_number + " 题"), node("p", "muted small", pathText(question.section_path)), node("pre", "", question.text || "未提供题目文字"), node("p", "mono muted small", question.question_id));
      details.append(item);
    }
    parent.append(details);
  }
  function renderRegionDraftRisks(answer) {
    const parent = $("region-draft-risks"); parent.replaceChildren();
    const bundles = Array.isArray(answer.region_draft_risks) ? answer.region_draft_risks : [];
    parent.hidden = !bundles.length;
    if (!bundles.length) return;
    const total = bundles.reduce((count, bundle) => count + (Array.isArray(bundle.risks) ? bundle.risks.length : 0), 0);
    const details = node("details");
    details.append(node("summary", "", "自动草稿来源风险 · " + total + " 项"));
    const content = node("div", "region-draft-risk-content");
    content.append(node("p", "region-draft-risk-note", "保留补读时的来源风险，不计入当前检查问题数；编辑或选择不会自动消除。像素记账闭合也不表示文字已完整识别。"));
    for (const [index, bundle] of bundles.entries()) {
      const risks = Array.isArray(bundle.risks) ? bundle.risks : [];
      const section = node("div", "region-risk-bundle");
      section.append(node("h4", "", "来源资料 " + (index + 1) + (bundle.source?.asset_id ? " · " + bundle.source.asset_id : "") + " · " + risks.length + " 项（未核准）"));
      const source = node("details", "region-risk-source");
      source.append(node("summary", "", "查看冻结来源记录"), node("pre", "", JSON.stringify({ bundle_ref: bundle.bundle_ref, source: bundle.source,
        decision: bundle.decision, transcription_verified: bundle.transcription_verified }, null, 2))); section.append(source);
      for (const risk of risks) {
        const item = node("details", "region-source-risk");
        item.append(node("summary", "mono", risk.code || "来源风险"));
        const labels = [];
        if (risk.row_id !== undefined && risk.row_id !== null) labels.push("行：" + risk.row_id);
        if (risk.slot_id !== undefined && risk.slot_id !== null) labels.push("位置：" + risk.slot_id);
        if (Array.isArray(risk.slot_ids)) labels.push("位置：" + risk.slot_ids.join("、"));
        if (risk.threshold !== undefined && risk.threshold !== null) labels.push("阈值：" + risk.threshold);
        if (labels.length) item.append(node("p", "region-risk-meta mono", labels.join("\n")));
        item.append(node("pre", "", JSON.stringify(risk, null, 2))); section.append(item);
      }
      if (!risks.length) section.append(node("p", "muted small", "此来源资料没有声明额外来源风险；这不表示内容已核准。"));
      content.append(section);
    }
    details.append(content); parent.append(details);
  }
  function renderActive(answer) {
    const parent = $("active-overview"); parent.replaceChildren();
    for (const [label, value] of [["当前正文 / 答案", answer.text], ["当前解析", answer.explanation_text]]) {
      const column = node("div", "active-column"); column.append(node("h4", "", label), node("pre", "", value || "当前未提供内容")); parent.append(column);
    }
  }

  function sourceBox(assetId, bbox) {
    if (!bbox) return null;
    const asset = state.assets.find((item) => item.asset_id === assetId);
    if (!asset || !Array.isArray(bbox) || bbox.length !== 4 || bbox.some((value) => typeof value !== "number" || !Number.isFinite(value))) throw new Error("该来源范围缺少有效几何信息。");
    const box = [Math.max(0, Math.floor(bbox[0])), Math.max(0, Math.floor(bbox[1])), Math.min(asset.width, Math.ceil(bbox[2])), Math.min(asset.height, Math.ceil(bbox[3]))];
    if (box[0] >= box[2] || box[1] >= box[3]) throw new Error("该来源范围为空或超出原图。");
    return box;
  }
  function sourceUrl(assetId, bbox) {
    const parameters = new URLSearchParams({ asset_id: assetId });
    const box = sourceBox(assetId, bbox);
    if (box) parameters.set("bbox", box.join(","));
    return "/api/source?" + parameters.toString();
  }
  function loadSourceImage(image, assetId, bbox, errorElement) {
    const showFailure = (message) => {
      if (!errorElement) return;
      const retry = button("重试读取", () => {
        errorElement.replaceChildren(node("span", "", "正在重新读取来源图像…"));
        image.removeAttribute("src");
        loadSourceImage(image, assetId, bbox, errorElement);
      }, "small-button");
      errorElement.replaceChildren(node("span", "", message + " "), retry);
      errorElement.hidden = false;
    };
    image.onload = () => { if (errorElement) { errorElement.hidden = true; errorElement.replaceChildren(); } };
    image.onerror = () => showFailure("来源图像无法读取。请检查本地来源或其字节是否改变。");
    try { image.src = sourceUrl(assetId, bbox); }
    catch (error) { showFailure(error.message); }
  }
  function showSource(assetId, bbox, label) {
    dialogSource = { assetId, bbox, label };
    $("source-dialog-title").textContent = label || "来源图像";
    $("source-dialog-meta").textContent = assetId + (bbox ? " · 原图范围 [" + formatBox(bbox) + "]" : " · 完整来源页");
    $("source-full-page").disabled = !bbox;
    $("source-dialog-error").hidden = true;
    loadSourceImage($("source-dialog-image"), assetId, bbox, $("source-dialog-error"));
    $("source-dialog-image").alt = (label || "来源图像") + " · " + assetId;
    if (!$("source-dialog").open) $("source-dialog").showModal();
  }
  function sourceCard(assetId, bbox, title) {
    const card = node("div", "source-card");
    const open = button("", () => showSource(assetId, bbox, title)); open.setAttribute("aria-label", "放大查看" + title);
    const image = node("img"); image.loading = "lazy"; image.alt = title + " · " + assetId; open.append(image);
    const content = node("div", "source-card-body"); content.append(node("p", "", title), node("p", "mono muted", assetId));
    const actions = node("div", "button-row"); actions.append(button("放大", () => showSource(assetId, bbox, title)));
    if (bbox) actions.append(button("整页", () => showSource(assetId, null, assetId + " · 整页")));
    content.append(actions);
    const error = node("p", "source-error"); error.hidden = true; content.append(error); loadSourceImage(image, assetId, bbox, error);
    card.append(open, content); return card;
  }
  function renderSources(answer) {
    const assetIds = [...new Set([...(answer.blocks || []).map(block => block.asset_id), ...(answer.figures || []).map(figure => figure.asset_id),
      ...(answer.reading_answer_candidates||[]).flatMap(candidate=>candidate.windows.map(window=>window.asset_id))])];
    const host = $("source-overview"); host.replaceChildren();
    host.style.flexWrap="wrap";host.style.alignItems="flex-start";
    const projection = answer.source_projection;
    if (projection?.status === "SOURCE_MAPPING_UNAVAILABLE") {
      host.append(node("p", "source-error", "来源分段映射暂不可用；原编辑内容与来源页保留，不能把未知对应关系当作已核准。"));
    }
    for (const zone of projection?.zones || []) {
      host.append(node("h4", "", roleLabel(zone.zone) + " · 按原始组题顺序的来源"));
      if (zone.edit_mapping !== "EXACT_SOURCE_TEXT" || zone.issues?.length) {
        host.append(node("p", "muted small", "当前完整分区文字没有逐段编辑映射；下方仅显示原始来源，编辑区保持整区编辑，不猜测文字属于哪一个框。"));
      }
      for (const segment of zone.segments || []) {
        const card = sourceCard(segment.asset_id, segment.preview_bbox,
          roleLabel(zone.zone) + " · 来源段 " + (segment.order + 1));
        card.append(node("pre", "", segment.source_text || "此段没有可核准文字"));
        if (segment.formula_hints?.length) {
          const hints = node("details"); hints.append(node("summary", "", "已有公式结构观察 · 未核准"),
            node("p", "muted small", "这些是已有分子、分母或行内来源观察，不是可直接应用的公式候选。"),
            node("pre", "", JSON.stringify(segment.formula_hints, null, 2))); card.append(hints);
        }
        host.append(card);
      }
      if (!zone.segments?.length) host.append(node("p", "muted small", "此分区尚无可可靠对应的来源段；保留完整编辑区和来源页。"));
    }
    for(const candidate of answer.reading_answer_candidates||[]){
      host.append(node("h4","","阅读答案待选素材 · 第（"+candidate.printed_number+"）题"),
        node("p","muted small","以下是共享原页上下文，题号片段仅用于定位，尚未配答或确认；请结合完整原图核对公式和分母。"),
        node("pre","",candidate.anchor_excerpt));
      for(const window of candidate.windows){
        const card=sourceCard(window.asset_id,window.bbox,"共享答案原页 · 待核对");card.style.flexBasis="100%";
        card.firstElementChild.style.height="auto";
        const image=card.querySelector("img");image.style.height="auto";image.style.maxHeight="520px";
        host.append(card);
      }
      const original=node("details");original.append(node("summary","","查看共享上下文的原识别行"),
        node("pre","",candidate.source_rows.map(row=>row.text).join("\n")));host.append(original);
    }
    for (const id of assetIds) host.append(sourceCard(id, null, "来源整页"));
    const images = (answer.figures || []).filter(figure => figure.content_type === "image");
    for (const [index, figure] of images.entries()) host.append(sourceCard(figure.asset_id, figure.bbox,
      figure.graphic_option_label?("选项 "+figure.graphic_option_label+(figure.source_checked?" · 已核对来源":" · 来源待核对")):
      figure.referenced_figure_id?("题干图 "+(index+1)+(figure.source_checked?" · 已核对来源":" · 来源待核对")):"已绑定题图 " + (index + 1) + " · " + roleLabel(figure.role)));
    for(const child of host.children)if(!child.classList.contains("source-card")){child.style.flexBasis="100%";child.style.minWidth="0";}
    $("source-overview-count").textContent = assetIds.length + " 来源页 · " + images.length + " 图片来源框";
    if (!assetIds.length && !projection?.zones?.length) host.append(node("p", "muted small", "该答案没有可显示的来源范围。"));
  }

  function renderRegionBinding(answer) {
    $("customer-region").hidden = !state.customer?.region_binding;
    const host=$("customer-region-editor");host.replaceChildren();
    if (!state.customer?.region_binding) return;
    const assetSelect=node("select"),zoneSelect=node("select"),canvas=node("canvas"),note=node("p","muted");
    const proposals=answer.figure_discovery?.proposals||[];
    const ids=[...new Set([...(answer.figures||[]).map(f=>f.asset_id),...proposals.map(p=>p.asset_id)])];
    for(const id of ids){const o=node("option","",id);o.value=id;assetSelect.append(o);}
    for(const block of answer.blocks||[]){const o=node("option","",roleLabel(block.role));o.value=block.role;zoneSelect.append(o);}
    canvas.style.cssText="max-width:100%;height:auto;touch-action:none;cursor:crosshair;border:1px solid #9ab";
    const bindingAnswerId=currentAnswerId,bindingHead=state.head;
    let picture=null,start=null,box=null,generation=0,loaded=null,boxBinding=null,replacement=null,textReplacement=null;
    const textBounds=node("div","text-source-bounds"),edgeInputs=[];
    const readEdges=()=>{
      if(!picture)return null;const values=edgeInputs.map(input=>Number(input.value));
      if(edgeInputs.some(input=>input.value.trim()==="")||values.some(value=>!Number.isInteger(value))
        ||values[0]<0||values[1]<0||values[2]>picture.naturalWidth||values[3]>picture.naturalHeight
        ||values[0]>=values[2]||values[1]>=values[3])return null;
      return values;
    };
    textBounds.append(node("p","muted","精确调整文字边界（原图像素，可用键盘上下键微调 1 像素）"));
    for(const [index,name] of ["左边界","上边界","右边界","下边界"].entries()){
      const field=node("input"),fieldLabel=node("label","check-label");field.type="number";field.step="1";field.min="0";
      fieldLabel.append(document.createTextNode("文字来源"+name),field);textBounds.append(fieldLabel);edgeInputs.push(field);
      field.addEventListener("input",()=>{
        if(!textReplacement)return;checked.checked=false;if(!ready())return;const values=readEdges();
        if(!values){box=null;boxBinding=null;paint();refreshConflicts();note.textContent="边界无效，请填写原页内有宽度和高度的整数范围，再核对完整性。";return;}
        const sx=canvas.width/picture.naturalWidth,sy=canvas.height/picture.naturalHeight;
        box=[values[0]*sx,values[1]*sy,values[2]*sx,values[3]*sy];boxBinding={...loaded,sourceBBox:values};
        paint();refreshConflicts();note.textContent="边界已按原图像素更新，请核对全部文字后再保存。";
      });
    }
    const showEdges=()=>{const values=chosenBox();if(values)edgeInputs.forEach((input,index)=>{input.value=String(values[index]);});};
    const conflictsHost=node("div","source-overlap-review");let transferChoices=[];
    const chosenBox=()=>{if(!picture||!box)return null;const sx=picture.naturalWidth/canvas.width,sy=picture.naturalHeight/canvas.height;
      return boxBinding?.sourceBBox?[...boxBinding.sourceBBox]:[Math.floor(box[0]*sx),Math.floor(box[1]*sy),Math.ceil(box[2]*sx),Math.ceil(box[3]*sy)];};
    const refreshConflicts=()=>{
      conflictsHost.replaceChildren();transferChoices=[];const selected=chosenBox();if(!selected||!loaded)return;
      const hits=(state.customer?.source_occupancy||[]).filter(item=>item.owner_key!==bindingAnswerId&&item.asset_id===loaded.assetId
        &&Math.max(item.bbox[0],selected[0])<Math.min(item.bbox[2],selected[2])&&Math.max(item.bbox[1],selected[1])<Math.min(item.bbox[3],selected[3]));
      if(hits.length)conflictsHost.append(node("p","source-proof-note","所选图内有其他题已认领的来源。只有确为本图文字、被原题误归时才逐项勾选；题号、已保存题或无法映射的范围不能移交。移交不改正文，原题必须回去核对并保存完整文字，再重新确认双方。"));
      for(const item of hits){const row=node("div","source-overlap-row"),within=selected[0]<=item.bbox[0]&&selected[1]<=item.bbox[1]&&selected[2]>=item.bbox[2]&&selected[3]>=item.bbox[3];
        const fragmentWithin=!item.fragment_bbox||(selected[0]<=item.fragment_bbox[0]&&selected[1]<=item.fragment_bbox[1]&&selected[2]>=item.fragment_bbox[2]&&selected[3]>=item.fragment_bbox[3]);
        if(!textReplacement&&item.can_transfer&&within&&fragmentWithin){const input=node("input");input.type="checkbox";const choice={input,item};transferChoices.push(choice);
          const label=node("label","check-label");label.append(input,document.createTextNode("这是本图文字，原第"+item.printed_number+"题误归："+(item.text||"")));row.append(label);
        }else row.append(node("p","source-error","第"+item.printed_number+"题的受保护来源与图相交，请调整范围或保留异常。"));
        row.append(button("查看这段原始来源",()=>showSource(item.asset_id,item.bbox,"原第"+item.printed_number+"题来源 · 只读"),"link-button small-button"));conflictsHost.append(row);
      }
    };
    const current=()=>host.contains(canvas)&&currentAnswerId===bindingAnswerId&&state.head===bindingHead;
    const ready=()=>current()&&picture&&loaded&&loaded.generation===generation&&loaded.assetId===assetSelect.value;
    const paint=()=>{const ctx=canvas.getContext("2d");if(!picture)return;ctx.drawImage(picture,0,0,canvas.width,canvas.height);if(box){ctx.strokeStyle="#d23d25";ctx.lineWidth=2;ctx.strokeRect(box[0],box[1],box[2]-box[0],box[3]-box[1]);}};
    const point=e=>{const r=canvas.getBoundingClientRect();return [Math.max(0,Math.min(canvas.width,(e.clientX-r.left)*canvas.width/r.width)),Math.max(0,Math.min(canvas.height,(e.clientY-r.top)*canvas.height/r.height))];};
    const load=(preset=null)=>{
      const requestGeneration=++generation,assetId=assetSelect.value;
      replacement=preset?.replace_region_id||null;textReplacement=preset?.replace_text_region_id||null;
      textBounds.hidden=!textReplacement;
      zoneSelect.disabled=Boolean(replacement||textReplacement);assetSelect.disabled=Boolean(textReplacement);
      save.textContent=textReplacement?"保存文字来源范围":"绑定所选题图";
      labelText.textContent=textReplacement?"调整后仍完整包含本段文字，未包含其他题目":"所选区域是本题原图，范围完整";
      box=null;start=null;picture=null;loaded=null;boxBinding=null;checked.checked=false;save.disabled=true;conflictsHost.replaceChildren();transferChoices=[];
      canvas.getContext("2d").clearRect(0,0,canvas.width,canvas.height);note.textContent="正在读取来源原页…";
      const observed=state.assets.find(asset=>asset.asset_id===assetId);
      if(preset&&(!observed||preset.asset_id!==assetId||preset.source_sha256!==observed.sha256)){note.textContent="题图候选来源已变化，请刷新后重新核对。";return;}
      const image=new Image();
      const isCurrent=()=>current()&&requestGeneration===generation&&assetSelect.value===assetId;
      image.onload=()=>{
        if(!isCurrent())return;
        if(!image.naturalWidth||!image.naturalHeight){note.textContent="来源图片尺寸无效。";return;}
        if(preset&&(image.naturalWidth!==preset.source_dimensions[0]||image.naturalHeight!==preset.source_dimensions[1])){note.textContent="题图候选与原页尺寸不同，停止关联。";return;}
        picture=image;loaded={assetId,generation:requestGeneration};canvas.width=Math.min(680,image.naturalWidth);
        canvas.height=Math.round(image.naturalHeight*canvas.width/image.naturalWidth);
        if(preset){const sx=canvas.width/image.naturalWidth,sy=canvas.height/image.naturalHeight;
          box=[preset.bbox[0]*sx,preset.bbox[1]*sy,preset.bbox[2]*sx,preset.bbox[3]*sy];
          boxBinding={...loaded,proposalId:preset.proposal_id,sourceBBox:[...preset.bbox],needsAdjustment:!preset.can_confirm_extent_without_adjustment};
          note.textContent=textReplacement?"可收窄空白；补齐框外遗漏符号须使用已固定审校清单的完整题区，保留最初文字框并避开其他来源。请核对全部文字。":boxBinding.needsAdjustment?"程序发现了低置信范围，请在原页调整后核对；不能直接确认完整图。":"程序已提出范围，请对照整页核对完整性，再勾选确认。";
        }else note.textContent="程序尚未提出可用范围时，可在原页框选题图。";
        paint();refreshConflicts();showEdges();save.disabled=false;
      };
      image.onerror=()=>{if(isCurrent())note.textContent="无法读取来源原页。";};image.src=sourceUrl(assetId,null);
    };
    assetSelect.addEventListener("change",()=>load());
    zoneSelect.addEventListener("change",()=>{checked.checked=false;refreshConflicts();});
    canvas.addEventListener("pointerdown",e=>{if(!ready())return;start=point(e);box=null;boxBinding={...loaded};checked.checked=false;conflictsHost.replaceChildren();transferChoices=[];canvas.setPointerCapture(e.pointerId);});
    canvas.addEventListener("pointermove",e=>{if(!start||!ready()||boxBinding?.generation!==generation)return;const p=point(e);box=[Math.min(start[0],p[0]),Math.min(start[1],p[1]),Math.max(start[0],p[0]),Math.max(start[1],p[1])];paint();});
    canvas.addEventListener("pointerup",()=>{start=null;refreshConflicts();showEdges();note.textContent=textReplacement?"请核对文字及遗漏符号完整，新增范围没有占用其他来源；保存后需重新确认本题。":box?"已框选，请核对是否完整包含题图且没有其他题目。":"请拖动框选题图。";});
    const checked=node("input");checked.type="checkbox";const label=node("label","check-label"),labelText=document.createTextNode("所选区域是本题原图，范围完整");label.append(checked,labelText);
    const save=button("绑定所选题图",async()=>{
      if(busy||dirtyDrafts().length||!ready()||!box||!checked.checked||boxBinding?.generation!==loaded.generation||boxBinding?.assetId!==loaded.assetId){feedback("请先保存文字编辑，再框选并核对题图。",true);return;}
      const selected=chosenBox(),bbox=textReplacement?readEdges():selected;
      if(textReplacement&&(!bbox||bbox.some((value,index)=>value!==selected[index]))){checked.checked=false;feedback("当前文字边界无效或已改变，请重新调整并核对完整性。",true);return;}
      if(boxBinding.needsAdjustment){feedback("此候选范围仍需在原页调整，不能直接视为完整题图。",true);return;}
      const sourceTransfers=transferChoices.filter(choice=>choice.input.checked).map(({item})=>({owner_key:item.owner_key,frame_index:item.frame_index,fragment_id:item.fragment_id}));
      setBusy(true);try{const payload={expected_head:bindingHead,answer_id:bindingAnswerId,asset_id:loaded.assetId,zone:zoneSelect.value,bbox,source_checked:true};if(textReplacement){payload.replace_text_region_id=textReplacement;payload.text_complete_checked=true;payload.expand_complete_source=true;}else{if(replacement)payload.replace_region_id=replacement;if(sourceTransfers.length)payload.source_transfers=sourceTransfers;if(boxBinding.proposalId)payload.proposal_id=boxBinding.proposalId;}const value=await request("/api/bind-region",payload);applyState(value.state);feedback(textReplacement?"文字来源边界已调整，原框和识别记录已保留。请重新核对并确认本题。":sourceTransfers.length?"题图及已核对的误归来源已绑定。请回原题核对并保存完整文字，再重新确认双方。":replacement?"题图范围已调整，原范围仍保留在记录中。请核对新图后重新确认本题。":"题图已绑定原始像素范围，请再确认本题内容。");}catch(error){showError(error,textReplacement?"文字来源范围未保存":"题图未绑定");}finally{setBusy(false);}
    });
    const proposed=node("div","customer-figure-proposals");
    if(answer.platform_status==="NOT_RUN")for(const [index,figure] of (answer.figures||[]).filter(f=>f.content_type==="image").entries()){
      const row=node("div","button-row");row.append(node("span","",figure.graphic_option_label?("选项 "+figure.graphic_option_label+(figure.source_checked?" · 已核对来源":" · 来源待核对")):
        figure.referenced_figure_id?("题干图 "+(index+1)+(figure.source_checked?" · 已核对来源":" · 来源待核对")):"已绑定题图 "+(index+1)));
      row.append(button("调整这张题图的范围",()=>{if(busy||dirtyDrafts().length){feedback("请先保存当前文字编辑。",true);return;}
        const asset=state.assets.find(a=>a.asset_id===figure.asset_id);if(!asset){feedback("来源页已变化，请刷新。",true);return;}
        assetSelect.value=figure.asset_id;zoneSelect.value=figure.role;load({...figure,zone:figure.role,source_sha256:asset.sha256,
          source_dimensions:[asset.width,asset.height],replace_region_id:figure.region_id,can_confirm_extent_without_adjustment:false});}));proposed.append(row);
    }
    if(answer.platform_status==="NOT_RUN")for(const [index,figure] of (answer.figures||[]).filter(f=>f.content_type==="text").entries()){
      const row=node("div","button-row");row.append(node("span","","文字来源 "+(index+1)+" · "+roleLabel(figure.role)));
      row.append(button("调整这段文字的来源范围",()=>{if(busy||dirtyDrafts().length){feedback("请先保存当前文字编辑。",true);return;}
        const asset=state.assets.find(a=>a.asset_id===figure.asset_id);if(!asset){feedback("来源页已变化，请刷新。",true);return;}
        assetSelect.value=figure.asset_id;zoneSelect.value=figure.role;load({...figure,zone:figure.role,source_sha256:asset.sha256,
          source_dimensions:[asset.width,asset.height],replace_text_region_id:figure.region_id,can_confirm_extent_without_adjustment:false});}));proposed.append(row);
    }
    if(answer.source_reassignment_pending_zones?.length)proposed.append(node("p","source-error","本题有误归的图内文字来源已移交。请核对并保存完整的"+answer.source_reassignment_pending_zones.map(roleLabel).join("、")+"，再重新确认本题；来源移交没有自动修改正文。"));
    if(answer.figure_requirements?.length)proposed.append(node("p","source-error","本题明确引用题图，必须先完成来源题图绑定；内容确认不能代替这一步。"));
    for(const proposal of proposals){
      const row=node("div","button-row");row.append(node("span","",proposal.option_label?("选项 "+proposal.option_label+(proposal.confidence==="LOW"?" · 重裁提案待调整":" · 原图范围待确认")):proposal.confidence==="LOW"?"题图线索 · 范围待调整":"程序提出的题图范围 · 待确认"));
      row.append(button("查看并使用这个范围",()=>{if(busy||dirtyDrafts().length){feedback("请先保存当前文字编辑。",true);return;}assetSelect.value=proposal.asset_id;zoneSelect.value=proposal.zone;load(proposal);}));proposed.append(row);
    }
    if(answer.figure_discovery?.issues?.length&&!proposals.length)proposed.append(node("p","muted small","题图范围仍无法可靠自动确定；来源映射、题号或分栏边界的未知状态继续保留，请在原页核对。"));
    host.append(proposed,assetSelect,zoneSelect,canvas,note,textBounds,conflictsHost,label,save);if(ids.length)load();
  }

  function renderBlock(block, index) {
    const sourceZone=currentAnswer()?.source_projection?.zones?.find(zone=>zone.zone===block.role);
    const multipleSources=(sourceZone?.segments?.length||0)>1;
    const initialRuns = rawRuns(block.runs);
    const formats = new Set(initialRuns.map((run) => run.format));
    const initialFormat = formats.size === 1 ? initialRuns[0].format : "";
    const draft = { block, runs: initialRuns, text: block.text || "", format: initialFormat, initialFormat, candidate: null,
      sourceSpan: [0, Array.from(block.source_text || "").length], sourceExplicitSelection: false,
      regionSelections: new Map(), regionMappingEnabled: true, regionBrowsing: new Map(), regionOpenGroups: new Set(), regionWidgets: [] };
    drafts.set(block.key, draft);
    const card = node("article", "block-card"); draft.card = card;
    const heading = node("div", "block-heading");
    const title = node("div", "block-title"); title.append(node("span", "", (index + 1) + ". " + roleLabel(block.role)), node("span", "kind-badge", block.kind === "REGION" ? "来源区域重建" : "原文片段"));
    draft.dirtyBadge = node("span", "dirty-badge", "未保存"); draft.dirtyBadge.hidden = true; title.append(draft.dirtyBadge);
    draft.resetButton = button("撤销此处编辑", () => resetBlock(draft), "small-button"); draft.resetButton.hidden = true;
    heading.append(title, draft.resetButton); card.append(heading);
    const compare = node("div", "block-compare"); const source = node("div", "source-column"); const editor = node("div", "draft-column");
    const sourceHeading = node("div", "column-heading"); sourceHeading.append(node("h4", "", "原始来源文字 · 只读"), button(multipleSources?"查看上方全部来源段":"查看图像", () => multipleSources?$("source-overview").scrollIntoView({block:"start"}):showSource(block.asset_id, block.bbox, roleLabel(block.role) + " · 来源区域"), "link-button small-button")); source.append(sourceHeading);
    const original = node("textarea", "source-text"); original.readOnly = true; original.spellcheck = false;
    original.value = block.source_text || ""; original.rows = Math.min(8, Math.max(3, (block.source_text || "").split("\n").length + 1));
    original.setAttribute("aria-label", roleLabel(block.role) + "原始来源文字，第 " + (index + 1) + " 块");
    original.placeholder = "无原 OCR 字串；仍绑定来源图像区域。"; source.append(original);
    source.append(node("p", "source-coordinates mono", block.asset_id + " · [" + formatBox(block.bbox) + "]"));
    if (block.source_geometry_revisions?.length) {
      const geometry = node("details", "source-geometry");
      geometry.append(node("summary", "", "来源裁边记录 · 未核准"));
      geometry.append(node("p", "source-proof-note", "已核对原图和被裁掉的像素。未检出深色像素不代表裁切或文字已获人工核准；本页仅编辑文字。"));
      for (const revision of block.source_geometry_revisions) {
        geometry.append(node("p", "source-coordinates mono", "原范围 [" + formatBox(revision.original_bbox) + "] → 当前范围 [" + formatBox(revision.revised_bbox) + "]"));
        geometry.append(button("查看裁边前原图", () => showSource(block.asset_id, revision.original_bbox, "裁边前的原始范围"), "link-button small-button"));
      }
      source.append(geometry);
    }
    if (block.kind === "FRAGMENT") {
      const spanControl = node("div", "span-control"); const span = node("span"); draft.spanLabel = span;
      const updateSelection = () => {
        const start = original.selectionStart; const end = original.selectionEnd;
        draft.sourceExplicitSelection = end > start;
        draft.sourceSpan = end > start ? [Array.from(original.value.slice(0, start)).length, Array.from(original.value.slice(0, end)).length] : [0, Array.from(original.value).length];
        updateSpanLabel(draft);
      };
      original.addEventListener("select", updateSelection); original.addEventListener("keyup", updateSelection); original.addEventListener("pointerup", updateSelection);
      const all = button("整段原文", () => { original.focus(); original.select(); updateSelection(); }, "link-button small-button");
      spanControl.append(span, all); source.append(spanControl); updateSpanLabel(draft);
      source.append(node("p", "source-proof-note", "候选替换只使用此原文选区；区间按 Unicode 码点计算，与右侧当前草稿的位置不同。"));
    } else source.append(node("p", "source-proof-note", "来源几何与原片段不可在此修改。空原 OCR 不等于没有像素来源；区域转写仍是未核准草稿。"));
    if(multipleSources)source.append(node("p","muted small","此完整分区有多段来源，按上方原始顺序核对；当前整区编辑不会被分配到单个来源框。"));
    const crop = node("img", "source-crop"); crop.loading = "lazy"; crop.alt = "第 " + (index + 1) + " 块的原图来源区域";
    crop.tabIndex = 0; crop.setAttribute("role", "button"); crop.addEventListener("click", () => showSource(block.asset_id, block.bbox, "第 " + (index + 1) + " 块来源"));
    crop.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); crop.click(); } });
    const cropError = node("p", "source-error"); cropError.hidden = true; if(!multipleSources){source.append(crop, cropError); loadSourceImage(crop, block.asset_id, block.bbox, cropError);}
    draft.editor = editor;
    compare.append(source, editor); card.append(compare);
    renderDraftEditor(draft);
    if (block.kind === "FRAGMENT" && block.candidates?.length) card.append(renderCandidates(draft));
    if (state.customer && block.kind === "FRAGMENT") card.append(renderCustomerFormulas(draft));
    return card;
  }
  function renderCustomerFormulas(draft) {
    const answer=currentAnswer(),host=node("div","customer-formulas");
    const proposals=(answer.formula_regions?.regions||[]).filter(item=>item.zone===draft.block.role);
    const observations=answer.formula_observations||[];
    if (!proposals.length) return host;
    const details=node("details");details.append(node("summary","","原图中的公式候选（"+proposals.length+" 个区域）"),
      node("p","muted small","逐个对照原图核对范围；中文混排可拖动选择公式。识别结果需检查后放入右侧当前草稿，再保存和确认。"));host.append(details);
    for(const [index,proposal] of proposals.entries()) {
      const row=node("details","formula-region");row.append(node("summary","","区域 "+(index+1)+(proposal.recognition_blocked?" · 已有识别记录，请查看原记录或人工核对":proposal.boundary_review_required?" · 与相邻题目或分区重叠，请调整边界":proposal.uncertainty==="MIXED_TEXT_COARSE_REGION"?" · 中文混排，核对公式范围":" · 核对来源")));
      if(proposal.recognition_blocked) row.append(node("p","warning",proposal.manual_resolution_required?"此区域的失败记录永久保留，不再识别；请对照原图人工修正文字。修复后的程序只继续原批次尚未调用的区域。":"此区域已有原始识别候选，请使用已保留的记录，不再调用模型。"));
      if(proposal.boundary_review_required) row.append(node("p","warning","此区域已退出自动批次。请在下方原图中拖动，选择不与相邻题目或分区重叠的公式范围，再勾选核对并识别。"));
      const retained=observations.filter(item=>item.proposal_id===proposal.proposal_id);
      const answerId=currentAnswerId,head=state.head,bounds=proposal.adjustment_bounds||proposal.bbox;
      const canvas=node("canvas"),note=node("p","muted small"),checked=node("input"),label=node("label","check-label");
      checked.type="checkbox";label.append(checked,document.createTextNode("已对照原图核对公式范围"));
      canvas.style.cssText="max-width:100%;height:auto;touch-action:none;cursor:crosshair;border:1px solid #9ab";
      canvas.setAttribute("aria-label","公式区域 "+(index+1)+" 的来源与可调整范围");
      let picture=null,start=null,box=[...proposal.bbox],loaded=false;
      const current=()=>host.isConnected&&currentAnswerId===answerId&&state.head===head;
      const paint=()=>{if(!picture)return;const ctx=canvas.getContext("2d"),sx=canvas.width/(bounds[2]-bounds[0]),sy=canvas.height/(bounds[3]-bounds[1]);
        ctx.drawImage(picture,0,0,canvas.width,canvas.height);ctx.strokeStyle="#c23824";ctx.lineWidth=2;
        ctx.strokeRect((box[0]-bounds[0])*sx,(box[1]-bounds[1])*sy,(box[2]-box[0])*sx,(box[3]-box[1])*sy);};
      const point=e=>{const r=canvas.getBoundingClientRect();return [Math.max(bounds[0],Math.min(bounds[2],bounds[0]+(e.clientX-r.left)/r.width*(bounds[2]-bounds[0]))),
        Math.max(bounds[1],Math.min(bounds[3],bounds[1]+(e.clientY-r.top)/r.height*(bounds[3]-bounds[1])))];};
      row.addEventListener("toggle",()=>{if(!row.open||loaded)return;loaded=true;const image=new Image();note.textContent="正在读取原图…";
        image.onload=()=>{if(!current())return;if(image.naturalWidth!==bounds[2]-bounds[0]||image.naturalHeight!==bounds[3]-bounds[1]){note.textContent="来源区域尺寸已变化，请刷新。";return;}
          picture=image;canvas.width=Math.min(800,Math.max(400,image.naturalWidth));canvas.height=Math.round(image.naturalHeight*canvas.width/image.naturalWidth);paint();note.textContent="红框是当前公式范围，可在图中拖动重新框选。";};
        image.onerror=()=>{if(current())note.textContent="来源图片未能读取。";};image.src=sourceUrl(proposal.asset_id,bounds);});
      canvas.addEventListener("pointerdown",e=>{if(!picture||busy||!current()||retained.length)return;start=point(e);checked.checked=false;canvas.setPointerCapture(e.pointerId);});
      canvas.addEventListener("pointermove",e=>{if(!start||!current())return;const p=point(e);box=[Math.floor(Math.min(start[0],p[0])),Math.floor(Math.min(start[1],p[1])),Math.ceil(Math.max(start[0],p[0])),Math.ceil(Math.max(start[1],p[1]))];paint();});
      canvas.addEventListener("pointerup",()=>{start=null;});
      const recognize=button("识别当前公式区域",async()=>{
        if(proposal.recognition_blocked){feedback("此范围已有识别记录，不换裁剪重跑；请使用原记录或人工修正。",true);return;}
        if(busy||!current()||!picture||!checked.checked||box[0]>=box[2]||box[1]>=box[3]){feedback("请先在原图核对有效的公式范围。",true);return;}
        if(dirtyDrafts().length){feedback("请先保存当前文字编辑，再识别下一处公式。",true);return;}
        if(proposal.boundary_review_required && (box.every((value,i)=>value===proposal.bbox[i]) || (proposal.boundary_conflicts||[]).some(peer=>Math.max(box[0],peer.bbox[0])<Math.min(box[2],peer.bbox[2]) && Math.max(box[1],peer.bbox[1])<Math.min(box[3],peer.bbox[3])))) {
          feedback("请先在原图中调整为不与相邻题目或分区重叠的公式范围。",true);return;
        }
        setBusy(true);feedback("正在本机识别此区域，结果会保留供核对…");
        try{const value=await request("/api/formula",{expected_head:head,answer_id:answerId,proposal_id:proposal.proposal_id,
          adjusted_bbox:box,source_checked:true,author:getAuthor()});applyState(value.state);feedback("公式候选已保留，请核对后放入草稿。");}
        catch(error){showError(error,"公式识别未完成，原记录已保留");}finally{setBusy(false);}
      });
      if(answer.platform_status!=="NOT_RUN") {recognize.disabled=true;note.textContent="此题已有平台处理记录，保留现有内容。";}
      if(proposal.recognition_blocked) {recognize.disabled=true;recognize.textContent="保留原记录，不再识别";}
      if(retained.length) {recognize.disabled=true;recognize.textContent="已有公式记录";box=[...retained[0].candidate.source_bbox];}
      row.append(canvas,note,label,recognize);
      for(const record of retained){
        const raw=record.candidate.raw_latex, candidate=node("div","formula-candidate");
        candidate.append(node("pre","",raw),node("p","muted small","本地识别原始候选 · 仍待逐字核对"));
        candidate.append(button("放入当前草稿选区",()=>{
          if(busy||!current()||answer.platform_status!=="NOT_RUN")return;
          const textarea=draft.editor.querySelector("textarea.draft-text");if(!textarea)return;
          const a=textarea.selectionStart,b=textarea.selectionEnd;
          draft.text=textarea.value.slice(0,a)+"$"+raw+"$"+textarea.value.slice(b);draft.format="plain";draft.candidate=null;
          renderDraftEditor(draft);updateDirtyState();feedback("候选已放入当前草稿选区，请对照原图检查后保存。");
        },"small-button"));row.append(candidate);
      }
      details.append(row);
    }
    return host;
  }
  function updateSpanLabel(draft) {
    draft.spanLabel.textContent = (draft.sourceExplicitSelection ? "已选原文" : "默认整段") + " [" + draft.sourceSpan.join(", ") + ") · " + (draft.sourceSpan[1] - draft.sourceSpan[0]) + " 码点";
  }
  function resetBlock(draft) {
    draft.runs = rawRuns(draft.block.runs); draft.text = draft.block.text || ""; draft.format = draft.initialFormat; draft.candidate = null;
    draft.regionSelections.clear(); draft.regionMappingEnabled = true; draft.regionBrowsing.clear(); draft.regionOpenGroups.clear();
    renderDraftEditor(draft); updateDirtyState();
  }
  function invalidateRegionMapping(draft) {
    draft.regionSelections.clear(); draft.regionMappingEnabled = false;
    draft.regionBrowsing.clear(); draft.regionOpenGroups.clear();
  }
  function clearRegionChoice(draft, index) {
    draft.regionSelections.delete(index);
    for (const update of draft.regionWidgets) update();
  }
  function formatSelect(value, mixed = false) {
    const select = node("select", "editor-format");
    if (mixed) { const option = node("option", "", "混排 · 编辑时选格式"); option.value = ""; select.append(option); }
    for (const [code, text] of [["plain", "纯文本"], ["latex", "LaTeX 公式"]]) { const option = node("option", "", text); option.value = code; select.append(option); }
    select.value = value; select.setAttribute("aria-label", "文字格式"); return select;
  }
  function renderDraftEditor(draft) {
    const parent = draft.editor; parent.replaceChildren();
    draft.regionWidgets = [];
    const heading = node("div", "column-heading"); heading.append(node("h4", "", draft.block.kind === "REGION" ? "当前区域草稿 · 可编辑文字段" : "当前完整片段 · 显式编辑")); parent.append(heading);
    if (draft.block.kind === "REGION") {
      const groups = Array.isArray(draft.block.region_candidates) ? draft.block.region_candidates : [];
      if (groups.length && !draft.regionMappingEnabled) parent.append(node("p", "region-mapping-warning", "文字段的数量、顺序或格式已调整，公式候选的定位已暂停。可撤销此处编辑恢复原映射；保存后只有服务端能重新对应来源时才会提供候选。"));
      const editors = node("div", "run-editors"); parent.append(editors);
      for (const [index, run] of draft.runs.entries()) {
        const row = node("div", "run-editor"); const controls = node("div", "run-controls");
        const format = formatSelect(run.format); controls.append(node("span", "run-label", "文字段 " + (index + 1)), format);
        const actions = node("div", "button-row");
        const up = button("↑", () => { invalidateRegionMapping(draft); [draft.runs[index - 1], draft.runs[index]] = [draft.runs[index], draft.runs[index - 1]]; renderDraftEditor(draft); updateDirtyState(); }, "small-button"); up.disabled = index === 0; up.setAttribute("aria-label", "上移文字段 " + (index + 1));
        const down = button("↓", () => { invalidateRegionMapping(draft); [draft.runs[index + 1], draft.runs[index]] = [draft.runs[index], draft.runs[index + 1]]; renderDraftEditor(draft); updateDirtyState(); }, "small-button"); down.disabled = index === draft.runs.length - 1; down.setAttribute("aria-label", "下移文字段 " + (index + 1));
        const remove = button("删除", () => { invalidateRegionMapping(draft); draft.runs.splice(index, 1); renderDraftEditor(draft); updateDirtyState(); }, "small-button"); remove.setAttribute("aria-label", "删除文字段 " + (index + 1)); actions.append(up, down, remove); controls.append(actions);
        const text = node("textarea"); text.value = run.text; text.spellcheck = false; text.rows = Math.min(7, Math.max(2, run.text.split("\n").length + Math.floor(run.text.length / 85)));
        text.setAttribute("aria-label", "文字段 " + (index + 1) + " 的原样草稿内容");
        row.append(controls, text); editors.append(row);
        format.addEventListener("change", () => { run.format = format.value; invalidateRegionMapping(draft); renderDraftEditor(draft); updateDirtyState(); });
        text.addEventListener("input", () => { run.text = text.value; clearRegionChoice(draft, index); updateDirtyState(); renderDraftPreview(draft); });
        if (draft.regionMappingEnabled && run.format === "latex") {
          for (const group of groups.filter((item) => item.run_index === index)) row.append(renderRegionChoiceGroup(draft, group, true));
        }
      }
      parent.append(button("＋ 添加文字段", () => { invalidateRegionMapping(draft); draft.runs.push({ format: "plain", text: "" }); renderDraftEditor(draft); updateDirtyState(); }, "small-button"));
      if (groups.length && !draft.regionMappingEnabled) {
        const catalog = node("details", "region-readonly-catalog"); catalog.append(node("summary", "", "原始公式候选目录 · 仅供查看"));
        for (const group of groups) catalog.append(renderRegionChoiceGroup(draft, group, false));
        parent.append(catalog);
      }
    } else {
      const format = formatSelect(draft.format, draft.initialFormat === ""); parent.append(format);
      if (draft.initialFormat === "") parent.append(node("p", "source-proof-note", "当前片段含混排文字段。未编辑时保持原样；整段修改时需明确选择一种格式。"));
      if (draft.candidate) {
        const selected = node("div", "candidate-selected");
        selected.append(node("p", "", "待保存候选 · 原文码点 [" + draft.candidate.fragment_span.join(", ") + ")"), node("pre", "", draft.selectedRaw || ""), node("p", "", "保存后重建当前文字；此处不猜测已有修订的字符位置。"), button("取消候选选择", () => { draft.candidate = null; renderDraftEditor(draft); updateDirtyState(); }, "small-button")); parent.append(selected);
      }
      const text = node("textarea", "draft-text"); text.value = draft.text; text.spellcheck = false;
      text.rows = Math.min(10, Math.max(4, draft.text.split("\n").length + Math.floor(draft.text.length / 85)));
      text.setAttribute("aria-label", "当前片段完整草稿"); text.readOnly = Boolean(draft.candidate); format.disabled = Boolean(draft.candidate);
      text.addEventListener("input", () => { draft.text = text.value; draft.candidate = null; updateDirtyState(); renderDraftPreview(draft); });
      format.addEventListener("change", () => { draft.format = format.value; draft.candidate = null; updateDirtyState(); renderDraftPreview(draft); }); parent.append(text);
    }
    const previewTitle = node("div", "preview-title"); previewTitle.append(node("span", "", "显示预览"), node("span", "", "语法支持 ≠ 转写正确")); parent.append(previewTitle);
    draft.preview = node("div", "run-preview"); draft.preview.setAttribute("aria-label", "当前草稿显示预览"); parent.append(draft.preview);
    renderDraftPreview(draft);
  }
  function regionGroupKey(group) {
    return JSON.stringify([group.bundle_ref, group.row_id, group.run_index, group.fraction_id]);
  }
  function regionKindLabel(choice) {
    if (choice.kind === "WHOLE_MODEL_OBSERVATION") return "整式原始观察";
    if (choice.kind === "DERIVED_ROLE_COMPOSITION") return "分量派生组合";
    return "来源候选";
  }
  function regionTopologyMatches(draft) {
    return draft.regionMappingEnabled && draft.runs.length === draft.block.runs.length
      && draft.runs.every((run, index) => run.format === draft.block.runs[index].format);
  }
  function applyRegionChoice(draft, group, choice) {
    if (busy) return;
    if (!regionTopologyMatches(draft) || !Number.isInteger(group.run_index) || !draft.runs[group.run_index]
        || draft.runs[group.run_index].format !== "latex" || !(group.choices || []).includes(choice)) {
      feedback("此公式的来源位置已不能对应。请撤销此处编辑，或保存后重新核对服务端提供的候选。", true);
      return;
    }
    const selection = { bundle_ref: { ...group.bundle_ref }, row_id: group.row_id, run_index: group.run_index,
      fraction_id: group.fraction_id, candidate_id: choice.candidate_id };
    draft.runs[group.run_index].text = choice.latex;
    draft.runs[group.run_index].format = "latex";
    draft.regionSelections.set(group.run_index, selection);
    draft.regionBrowsing.set(regionGroupKey(group), choice.candidate_id);
    draft.regionOpenGroups.add(regionGroupKey(group));
    renderDraftEditor(draft); updateDirtyState();
  }
  function renderRegionChoiceGroup(draft, group, mapped) {
    const key = regionGroupKey(group);
    const choices = Array.isArray(group.choices) ? group.choices : [];
    const wholeCount = choices.filter((choice) => choice.kind === "WHOLE_MODEL_OBSERVATION").length;
    const composedCount = choices.filter((choice) => choice.kind === "DERIVED_ROLE_COMPOSITION").length;
    const details = node("details", "region-formula-candidates");
    details.open = draft.regionOpenGroups.has(key);
    details.addEventListener("toggle", () => {
      if (details.open) draft.regionOpenGroups.add(key); else draft.regionOpenGroups.delete(key);
    });
    details.append(node("summary", "", (mapped ? "此公式的来源候选" : "原文字段 " + (group.run_index + 1) + " 的候选") + " · " + choices.length + " 条"));
    const body = node("div", "region-choice-body");
    const status = node("p", "region-choice-status"); body.append(status);
    body.append(node("p", "muted small", "整式原始观察 " + wholeCount + " 条 · 分量派生组合 " + composedCount + " 条。相同文字的不同来源也分别保留，全部未核准。"));
    const source = node("div", "region-choice-source");
    source.append(button("核对公式原图", () => showSource(draft.block.asset_id, group.source_bbox, "公式来源区域"), "small-button"), node("span", "mono muted", "[" + formatBox(group.source_bbox) + "]")); body.append(source);
    const filters = node("div", "region-choice-filters");
    const kindLabel = node("label", "field", "候选类型"); const kind = node("select");
    for (const [value, label] of [["", "全部来源"], ["WHOLE_MODEL_OBSERVATION", "整式原始观察"], ["DERIVED_ROLE_COMPOSITION", "分量派生组合"]]) {
      const option = node("option", "", label); option.value = value; kind.append(option);
    }
    kindLabel.append(kind); filters.append(kindLabel);
    const choiceLabel = node("label", "field", "查看候选（不会自动应用）"); const chooser = node("select", "region-choice-select"); choiceLabel.append(chooser); filters.append(choiceLabel); body.append(filters);
    const choiceCount = node("p", "muted small"); body.append(choiceCount);
    const preview = node("div", "region-choice-preview"); body.append(preview);
    const actions = node("div", "button-row");
    const apply = button("用于此公式", () => {
      const choice = choices.find((item) => item.candidate_id === chooser.value);
      if (choice) applyRegionChoice(draft, group, choice);
    }, "small-button");
    const clear = button("保留文字，改为显式编辑", () => {
      draft.regionSelections.delete(group.run_index); renderDraftEditor(draft); updateDirtyState();
    }, "link-button small-button"); actions.append(apply, clear); body.append(actions);
    function updateStatus() {
      const pending = draft.regionSelections.get(group.run_index);
      const ours = pending && pending.fraction_id === group.fraction_id && pending.row_id === group.row_id
        && JSON.stringify(pending.bundle_ref) === JSON.stringify(group.bundle_ref);
      const current = draft.runs[group.run_index];
      const matches = mapped && current?.format === "latex" ? choices.filter((choice) => choice.latex === current.text).length : 0;
      if (!mapped || !regionTopologyMatches(draft)) status.textContent = "位置映射已暂停。可查看原始候选与来源图，不能应用到当前文字段。";
      else if (ours) status.textContent = "已选择，待保存 · " + regionKindLabel(choices.find((choice) => choice.candidate_id === pending.candidate_id) || {}) + "。保存将记录原始来源引用，仍未核准。";
      else status.textContent = matches ? "当前文字与 " + matches + " 条候选相同；尚未为本次编辑选择来源，也不代表内容正确。" : "当前文字未与这些候选完全相同；选择前请先核对来源。";
      status.classList.toggle("pending", Boolean(ours));
      clear.hidden = !ours;
      apply.disabled = busy || !mapped || !regionTopologyMatches(draft) || !chooser.value;
    }
    function renderChosen() {
      preview.replaceChildren();
      const choice = choices.find((item) => item.candidate_id === chooser.value);
      if (!choice) {
        preview.append(node("p", "muted small", "从列表选择一条，查看完整原始 LaTeX 和来源；点击“用于此公式”后才改变草稿。"));
        updateStatus(); return;
      }
      draft.regionBrowsing.set(key, choice.candidate_id);
      preview.append(node("span", "region-choice-kind", regionKindLabel(choice)), node("p", "source-proof-note", choice.complete_model_call === true ? "来自一次完整公式模型观察，文字仍可能有误。" : "由分子、分母等观察派生组合，不是一次整式模型输出；所有原分量来源保留。"));
      preview.append(node("pre", "region-choice-raw", choice.latex));
      const math = node("div", "run-preview region-choice-math"); preview.append(math);
      if (choice.parse_supported === true) mathPreview(math, choice.latex, null);
      else rawMath(math, choice.latex, "含暂不支持的语法；完整原文仍可查看和显式选择，不自动清理。");
      const provenance = node("details", "region-choice-provenance");
      provenance.append(node("summary", "", "查看原始来源记录"), node("pre", "", JSON.stringify({ bundle_ref: group.bundle_ref, row_id: group.row_id,
        fraction_id: group.fraction_id, candidate_id: choice.candidate_id, kind: choice.kind, source_bbox: group.source_bbox,
        complete_model_call: choice.complete_model_call, origin: choice.origin }, null, 2)));
      preview.append(provenance); updateStatus();
    }
    function renderOptions() {
      const previous = chooser.value || draft.regionBrowsing.get(key);
      chooser.replaceChildren();
      const empty = node("option", "", "请选择一条候选查看"); empty.value = ""; chooser.append(empty);
      const visible = choices.filter((choice) => !kind.value || choice.kind === kind.value);
      for (const choice of visible) {
        const index = choices.indexOf(choice) + 1;
        const codepoints = Array.from(choice.latex);
        const snippet = codepoints.slice(0, 75).join("") + (codepoints.length > 75 ? "…" : "");
        const option = node("option", "", index + ". " + regionKindLabel(choice) + " · " + snippet + (choice.candidate_id === group.default_candidate_id ? " · 初始草稿来源" : ""));
        option.value = choice.candidate_id; chooser.append(option);
      }
      if (visible.some((choice) => choice.candidate_id === previous)) chooser.value = previous;
      choiceCount.textContent = "显示 " + visible.length + " / " + choices.length + " 条；同文不同来源不合并。";
      renderChosen();
    }
    kind.addEventListener("change", renderOptions); chooser.addEventListener("change", renderChosen);
    draft.regionWidgets.push(updateStatus);
    details.append(body); renderOptions(); return details;
  }
  function renderCandidates(draft) {
    const details = node("details", "candidates"); details.append(node("summary", "", "模型原始候选 · " + draft.block.candidates.length + " 条（未核准）"));
    const list = node("div", "candidate-list");
    for (const candidate of draft.block.candidates) {
      const card = node("div", "candidate-card"); const top = node("div", "candidate-top");
      const id = node("span", "candidate-id", candidate.candidate_id); id.title = candidate.candidate_id;
      top.append(id, node("span", "", candidate.parse_supported ? "语法可预览 · 未核准" : "未知语法 · 原文保留"));
      const select = button("用于原文选区", () => {
        if (busy) return;
        if (!draft.block.source_text || draft.sourceSpan[0] >= draft.sourceSpan[1]) { feedback("没有可替换的原文码点区间。", true); return; }
        draft.candidate = { candidate_id: candidate.candidate_id, call_id: candidate.call_id, unit_id: candidate.unit_id, fragment_span: [...draft.sourceSpan] };
        draft.selectedRaw = candidate.raw_latex;
        renderDraftEditor(draft); updateDirtyState();
      }, "small-button");
      card.append(top, node("pre", "", candidate.raw_latex), select); list.append(card);
    }
    details.append(list); return details;
  }

  const mathValues = { "\\cdot": "·", "\\times": "×", "\\div": "÷", "\\leq": "≤", "\\geq": "≥", "\\neq": "≠", "\\approx": "≈", "\\because": "∵", "\\therefore": "∴", "\\pi": "π", "\\alpha": "α", "\\beta": "β", "\\gamma": "γ", "\\theta": "θ", "\\ell": "ℓ" };
  function mathNode(tag, children = [], text) {
    const element = document.createElementNS(MATH_NS, tag);
    if (text !== undefined) element.textContent = text;
    for (const child of children) element.append(child);
    return element;
  }
  function astNode(ast, depth = 0) {
    if (!ast || typeof ast !== "object" || depth > 40) throw new Error("Unsupported math tree");
    const child = (value) => astNode(value, depth + 1);
    switch (ast.type) {
      case "sequence": if (!Array.isArray(ast.items) || !ast.items.length) throw new Error("Empty math sequence"); return mathNode("mrow", ast.items.map(child));
      case "number": case "symbol": case "operator": {
        if (typeof ast.value !== "string") throw new Error("Missing math value");
        const text = mathValues[ast.value] || ast.value;
        if (text.startsWith("\\")) throw new Error("Unknown math command");
        return mathNode(ast.type === "number" ? "mn" : ast.type === "operator" ? "mo" : "mi", [], text);
      }
      case "fraction": return mathNode("mfrac", [child(ast.numerator), child(ast.denominator)]);
      case "power": return mathNode("msup", [child(ast.base), child(ast.exponent)]);
      case "subscript": return mathNode("msub", [child(ast.base), child(ast.index)]);
      case "radical": return ast.index ? mathNode("mroot", [child(ast.radicand), child(ast.index.type === "group" && ast.index.delimiters === "[]" ? ast.index.body : ast.index)]) : mathNode("msqrt", [child(ast.radicand)]);
      case "group": {
        const delimiters = ast.delimiters;
        if (delimiters === "{}") return child(ast.body);
        if (delimiters !== "()" && delimiters !== "[]") throw new Error("Unknown math group");
        return mathNode("mrow", [mathNode("mo", [], delimiters[0]), child(ast.body), mathNode("mo", [], delimiters[1])]);
      }
      case "styled": {
        const styles = { "\\mathrm": "normal", "\\mathbf": "bold", "\\mathit": "italic", "\\text": "normal" };
        if (!styles[ast.style]) throw new Error("Unknown math style");
        const row = mathNode("mstyle", [child(ast.body)]); row.setAttribute("mathvariant", styles[ast.style]); return row;
      }
      default: throw new Error("Unsupported math node");
    }
  }
  function rawMath(target, text, reason) {
    target.replaceChildren(node("code", "math-raw", text));
    target.append(node("span", "math-warning", reason || "语法暂不支持；完整保留原 LaTeX，未作自动修正。"));
  }
  function showMath(target, text, preview) {
    if (!preview || preview.supported !== true || !preview.normalized_ast) { rawMath(target, text); return; }
    try {
      const ast = preview.normalized_ast;
      const parts = ast.type === "sequence" ? ast.items : [ast];
      const content = document.createDocumentFragment();
      for (const [index, part] of parts.entries()) {
        const span = node("span", "math-piece"); const math = mathNode("math", [astNode(part)]); math.setAttribute("aria-label", "数学草稿预览"); span.append(math); content.append(span);
        if (index < parts.length - 1) content.append(document.createTextNode("\u200b"));
      }
      target.replaceChildren(content);
    } catch (_) { rawMath(target, text, "该语法树暂不能完整显示；保留整段原 LaTeX。" ); }
  }
  function mathPreview(target, text, existing) {
    if (existing?.raw_latex === text) { showMath(target, text, existing); return; }
    rawMath(target, text, text ? "正在生成语法预览…" : "空文字段需填写内容或删除。" );
    if (!text) return;
    const previous = previewRequests.get(target); if (previous) clearTimeout(previous.timer);
    const ticket = { timer: null }; previewRequests.set(target, ticket);
    ticket.timer = setTimeout(async () => {
      if (!target.isConnected || previewRequests.get(target) !== ticket) return;
      try {
        const value = await request("/api/preview", { text });
        if (target.isConnected && previewRequests.get(target) === ticket) showMath(target, text, value.preview);
      } catch (_) { if (target.isConnected && previewRequests.get(target) === ticket) rawMath(target, text, "预览暂不可用；原 LaTeX 保持完整，可继续核对来源。" ); }
    }, 300);
  }
  function renderDraftPreview(draft) {
    if (!draft.preview) return;
    draft.preview.replaceChildren();
    if (draft.candidate) { rawMath(draft.preview, draft.selectedRaw || "", "待保存原始候选；尚未覆盖当前正文。" ); return; }
    let runs;
    if (draft.block.kind === "REGION") runs = draft.runs;
    else if (draft.text === draft.block.text && draft.format === draft.initialFormat) runs = draft.block.runs || [{ format: "plain", text: draft.text }];
    else runs = [{ format: draft.format || "plain", text: draft.text }];
    runs.forEach((run, index) => {
      const span = node("span", run.format === "latex" ? "latex-preview" : "plain-preview"); draft.preview.append(span);
      if (run.format === "latex") {
        const original = draft.block.runs?.[index];
        mathPreview(span, run.text, original?.text === run.text && original.format === run.format ? original.math_preview : null);
      } else span.textContent = run.text;
    });
  }

  function linkedAnswers(issueId) { return state.answers.filter((answer) => (answer.issue_ids || []).includes(issueId)); }
  function renderIssues() {
    if (!state) return;
    const answer = currentAnswer(); const scope = $("issue-scope").value; const query = $("issue-search").value.trim().toLocaleLowerCase();
    const issues = state.issues.filter((issue) => (scope === "all" || scope === "answer" && (answer?.issue_ids || []).includes(issue.issue_id) || scope === "global" && !linkedAnswers(issue.issue_id).length)
      && (!query || JSON.stringify(issue).toLocaleLowerCase().includes(query) || (ruleLabels[issue.code] || "").includes(query)));
    $("issue-scope-note").textContent = "显示 " + issues.length + " / " + state.issues.length + " 项当前问题。问题数量不代表转写准确率。";
    const parent = $("issue-list"); parent.replaceChildren();
    if (!issues.length) { parent.append(node("p", "empty-note", scope === "answer" ? "当前答案未关联到符合筛选的问题。请同时查看全局队列；这不表示内容已核准。" : "没有符合筛选的问题。")); return; }
    for (const issue of issues) {
      const card = node("article", "issue-card"); const top = node("div", "issue-meta");
      top.append(node("span", issue.severity === "ERROR" ? "severity-error" : "severity-review", issue.severity === "ERROR" ? "阻塞 / ERROR" : "待复核 / " + (issue.severity || "REVIEW")));
      const links = linkedAnswers(issue.issue_id); top.append(node("span", "muted", links.length ? "关联 " + links.length + " 答案" : "全局 / 未定位"));
      card.append(top, node("h4", "", ruleLabels[issue.code] || "当前检查提示"), node("p", "rule-code mono", issue.code));
      if (links.length && !links.some((item) => item.answer_id === currentAnswerId)) card.append(button("定位第 " + links[0].printed_number + " 题", () => selectAnswer(links[0].answer_id), "link-button small-button"));
      const details = node("details"); details.append(node("summary", "", "查看完整来源与检查记录"), node("pre", "", JSON.stringify(issue, null, 2))); card.append(details); parent.append(card);
    }
  }
  function renderHistory() {
    const history = state.history || []; const current = history.find((entry) => entry.head === state.head);
    const parentExists = current?.parent_head && history.some((entry) => entry.head === current.parent_head);
    $("undo-save").disabled = busy || !parentExists;
    $("undo-save").onclick = () => askRestore(current.parent_head);
    $("history-confirm").hidden = true; restoreHead = null;
    const parent = $("history-list"); parent.replaceChildren();
    for (const entry of [...history].reverse()) {
      const isCurrent = entry.head === state.head; const card = node("article", "history-card" + (isCurrent ? " current" : ""));
      const top = node("div", "history-top"); top.append(node("span", "", "计划 v" + (entry.plan_ref?.revision ?? "—")), node("span", "", isCurrent ? "当前版本" : "历史快照")); card.append(top);
      card.append(node("p", "mono", shortId(entry.head, 30)), node("p", "", (authorLabels[entry.author?.kind] || "草稿") + " · " + (entry.author?.id || "未提供作者")));
      if (entry.created_at) card.append(node("p", "", entry.created_at));
      if (entry.summary !== undefined) card.append(node("pre", "", typeof entry.summary === "string" ? entry.summary : JSON.stringify(entry.summary, null, 2)));
      if (!isCurrent) card.append(button("恢复此快照为新版本", () => askRestore(entry.head), "small-button"));
      parent.append(card);
    }
    if (!history.length) parent.append(node("p", "empty-note", "工作区暂未提供版本记录。"));
  }
  function askRestore(head) {
    if (busy || head === state.head || !state.history.some((entry) => entry.head === head)) return;
    guarded(() => {
      restoreHead = head;
      $("history-confirm-message").textContent = "将快照 " + shortId(head) + " 的操作恢复为新版本。当前版本与原始来源仍保留。请先填写本次草稿作者。";
      $("history-confirm").hidden = false; $("history-confirm-yes").focus();
    }, "恢复历史前，请保存或放弃这些编辑。");
  }
  async function restore() {
    if (busy || !restoreHead) return;
    if (dirtyDrafts().length) {
      const targetHead = restoreHead;
      restoreHead = null;
      $("history-confirm").hidden = true;
      guarded(() => askRestore(targetHead), "恢复历史前，请保存或放弃这些编辑；随后需再次确认恢复。");
      return;
    }
    let author;
    try { author = getAuthor(); } catch (error) { showError(error, "尚不能恢复"); return; }
    const body = { expected_head: state.head, revision_head: restoreHead, author };
    setBusy(true);
    try { const value = await request("/api/restore", body); applyState(value.state); feedback("已创建恢复版本 v" + state.plan_revision + " 并重检，原有历史仍保留。草稿仍未核准。" ); }
    catch (error) { showError(error, "历史恢复失败"); }
    finally { setBusy(false); }
  }
  function showInspection(panel) {
    for (const name of ["issues", "history"]) {
      const selected = name === panel; $(name + "-tab").setAttribute("aria-selected", String(selected)); $(name + "-tab").tabIndex = selected ? 0 : -1; $(name + "-panel").hidden = !selected;
    }
  }

  $("refresh-button").addEventListener("click", () => guarded(refresh, "刷新前，请保存或放弃这些编辑。"));
  $("save-button").addEventListener("click", () => saveCurrent());
  $("discard-button").addEventListener("click", () => guarded(() => { cancelNavigation(); renderAnswer(); feedback("编辑器已恢复为当前保存版本，历史记录仍保留。" ); }, "可在下方放弃当前未保存编辑。"));
  $("guard-cancel").addEventListener("click", cancelNavigation);
  $("guard-discard").addEventListener("click", () => { const action = pendingNavigation; cancelNavigation(); renderAnswer(); if (action) action(); });
  $("guard-save").addEventListener("click", () => { const action = pendingNavigation; saveCurrent(() => { cancelNavigation(); if (action) action(); }); });
  $("answer-search").addEventListener("input", renderNavigation); $("section-filter").addEventListener("change", renderNavigation); $("only-issues").addEventListener("change", renderNavigation);
  $("previous-answer").addEventListener("click", () => moveAnswer(-1)); $("next-answer").addEventListener("click", () => moveAnswer(1));
  $("issue-scope").addEventListener("change", renderIssues); $("issue-search").addEventListener("input", renderIssues);
  $("issues-tab").addEventListener("click", () => showInspection("issues")); $("history-tab").addEventListener("click", () => showInspection("history"));
  for (const name of ["issues", "history"]) $(name + "-tab").addEventListener("keydown", (event) => { if (["ArrowLeft", "ArrowRight"].includes(event.key)) { event.preventDefault(); const other = name === "issues" ? "history" : "issues"; showInspection(other); $(other + "-tab").focus(); } });
  $("history-confirm-yes").addEventListener("click", restore); $("history-confirm-no").addEventListener("click", () => { restoreHead = null; $("history-confirm").hidden = true; });
  $("source-close").addEventListener("click", () => $("source-dialog").close());
  $("source-fit").addEventListener("change", () => $("source-dialog-scroll").classList.toggle("actual-size", !$("source-fit").checked));
  $("source-full-page").addEventListener("click", () => { if (dialogSource) showSource(dialogSource.assetId, null, dialogSource.assetId + " · 整页"); });
  document.addEventListener("keydown", (event) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") { event.preventDefault(); if (!$("source-dialog").open) saveCurrent(); } });
  refresh();
})();
