/* Local draft review. Source strings enter the DOM only as text or form values. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const MATH_NS = "http://www.w3.org/1998/Math/MathML";
  const roleLabel = (role) => role === "explanation" ? "解析" : "正文 / 答案";
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
    drafts = new Map();
    const answer = currentAnswer();
    if (!answer) { $("block-editors").replaceChildren(); renderIssues(); updateDirtyState(); return; }
    $("answer-title").textContent = "第 " + answer.printed_number + " 题 · 答案候选";
    $("answer-section").textContent = pathText(answer.section_path);
    $("answer-identity").textContent = answer.answer_id;
    renderRegionDraftRisks(answer); renderQuestions(answer); renderSources(answer); renderActive(answer);
    $("block-editors").replaceChildren();
    $("no-editable-blocks").hidden = (answer.blocks || []).length !== 0;
    $("region-candidate-help").hidden = !(answer.blocks || []).some((block) => block.kind === "REGION" && block.region_candidates?.length);
    for (const [index, block] of (answer.blocks || []).entries()) $("block-editors").append(renderBlock(block, index));
    renderIssues(); updateAnswerArrows(); updateDirtyState();
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
    const assetIds = [...new Set([...(answer.blocks || []).map((block) => block.asset_id), ...(answer.figures || []).map((figure) => figure.asset_id)])];
    $("source-overview").replaceChildren();
    for (const id of assetIds) $("source-overview").append(sourceCard(id, null, "来源页"));
    for (const [index, figure] of (answer.figures || []).entries()) $("source-overview").append(sourceCard(figure.asset_id, figure.bbox, "图形 " + (index + 1) + " · " + roleLabel(figure.role)));
    $("source-overview-count").textContent = assetIds.length + " 来源页 · " + (answer.figures || []).length + " 图形";
    if (!assetIds.length) $("source-overview").append(node("p", "muted small", "该答案没有可显示的来源范围。"));
  }

  function renderBlock(block, index) {
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
    const sourceHeading = node("div", "column-heading"); sourceHeading.append(node("h4", "", "原始来源文字 · 只读"), button("查看图像", () => showSource(block.asset_id, block.bbox, roleLabel(block.role) + " · 来源区域"), "link-button small-button")); source.append(sourceHeading);
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
    const crop = node("img", "source-crop"); crop.loading = "lazy"; crop.alt = "第 " + (index + 1) + " 块的原图来源区域";
    crop.tabIndex = 0; crop.setAttribute("role", "button"); crop.addEventListener("click", () => showSource(block.asset_id, block.bbox, "第 " + (index + 1) + " 块来源"));
    crop.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); crop.click(); } });
    const cropError = node("p", "source-error"); cropError.hidden = true; source.append(crop, cropError); loadSourceImage(crop, block.asset_id, block.bbox, cropError);
    draft.editor = editor;
    compare.append(source, editor); card.append(compare);
    renderDraftEditor(draft);
    if (block.kind === "FRAGMENT" && block.candidates?.length) card.append(renderCandidates(draft));
    return card;
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
