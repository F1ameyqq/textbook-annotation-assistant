/* Self-contained UI protocol checks. Injected JavaScript-only data, no content
 * gold, browser, optional package, network or model. Optional argv[2] selects
 * an exported repository. */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const assert = require("assert");
const repo = path.resolve(process.argv[2] || path.join(__dirname, ".."));
const html = fs.readFileSync(path.join(repo, "src/annotation/recognition/review_ui.html"), "utf8");
const source = fs.readFileSync(path.join(repo, "src/annotation/recognition/review_ui.js"), "utf8");
const ids = new Set([...html.matchAll(/id="([^"]+)"/g)].map((m) => m[1]));
assert.deepStrictEqual([...new Set([...source.matchAll(/\$\("([^"]+)"\)/g)].map((m) => m[1]))].filter((id) => !ids.has(id)), []);
assert(!source.includes("innerHTML"));

class Element {
  constructor(tag = "div") {
    this.tagName = tag; this.children = []; this.attrs = {}; this.listeners = {};
    this.value = ""; this.hidden = false; this.disabled = false; this.isConnected = true;
    this.checked = false; this._text = ""; this.className = ""; this.classList = { toggle() {} };
  }
  set textContent(value) { this._text = String(value); this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent || "").join(""); }
  append(...values) { this.children.push(...values); }
  replaceChildren(...values) { this._text = ""; this.children = values; if (this.tagName === "select") this.value = ""; }
  addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
  setAttribute(key, value) { this.attrs[key] = value; }
  removeAttribute(key) { delete this.attrs[key]; }
  focus() {}
  select() { this.selectionStart = 0; this.selectionEnd = this.value.length; }
  showModal() { this.open = true; }
  close() { this.open = false; }
  dispatch(name) { for (const fn of this.listeners[name] || []) fn({ target: this, preventDefault() {} }); }
}
const elements = new Map([...ids].map((id) => [id, new Element()]));
elements.get("issue-scope").value = "answer";
const sidebars = new Map();
const document = {
  getElementById: (id) => elements.get(id), createElement: (tag) => new Element(tag),
  createElementNS: (_, tag) => new Element(tag),
  createTextNode: (text) => { const value = new Element("#text"); value.textContent = text; return value; },
  createDocumentFragment: () => new Element("#fragment"),
  querySelector: (selector) => { if (!sidebars.has(selector)) sidebars.set(selector, new Element()); return sidebars.get(selector); },
  addEventListener() {}, title: ""
};
const bundle = { artifact_id: "injected-fixed-bundle", revision: 2, content_hash: "injected-source-hash" };
function group(index, id, latex) {
  const choices = [
    { candidate_id: id + "-raw", kind: "WHOLE_MODEL_OBSERVATION", latex, parse_supported: true, origin: { raw: "injected original" }, complete_model_call: true },
    { candidate_id: id + "-same", kind: "DERIVED_ROLE_COMPOSITION", latex, parse_supported: true, origin: { numerator: "n", denominator: "d" }, complete_model_call: false },
    { candidate_id: id + "-unknown", kind: "WHOLE_MODEL_OBSERVATION", latex: "\\unknown{<img onerror=x>}", parse_supported: false, origin: { raw: "unknown and unchanged" }, complete_model_call: true }
  ];
  // 342 injected distinct candidate IDs across two groups, deliberately repeated
  // text. This tests untruncated access, not the real corpus candidate census.
  for (let i = 3; i < 171; i++) choices.push({ candidate_id: id + "-duplicate-" + i,
    kind: i % 2 ? "WHOLE_MODEL_OBSERVATION" : "DERIVED_ROLE_COMPOSITION", latex, parse_supported: true,
    origin: { injected_duplicate_index: i }, complete_model_call: Boolean(i % 2) });
  return { bundle_ref: { ...bundle }, row_id: "injected-source-row", run_index: index, fraction_id: id,
    source_bbox: [20, 10, 40, 30], matching_candidate_ids: [id + "-raw", id + "-same"], default_candidate_id: id + "-raw",
    decision: "HOLD", transcription_verified: false, choices };
}
const first = group(1, "F5", "a"), second = group(3, "F9", "b");
const region = { key: "r", kind: "REGION", role: "answer", asset_id: "source", bbox: [0, 0, 100, 40],
  source_text: "injected original fragments", text: "body a tail b", source_fragment_ids: ["f1"],
  runs: [{ format: "plain", text: "body " }, { format: "latex", text: "a", math_preview: { raw_latex: "a", supported: false } },
    { format: "plain", text: " tail " }, { format: "latex", text: "b", math_preview: { raw_latex: "b", supported: false } }], region_candidates: [first, second] };
const fragment = { key: "f", kind: "FRAGMENT", role: "answer", asset_id: "source", bbox: [0, 45, 100, 60],
  source_text: "𝑥+a", text: "old mixed", source_fragment_ids: ["f2"], runs: [{ format: "plain", text: "old " },
    { format: "latex", text: "mixed", math_preview: { raw_latex: "mixed", supported: false } }],
  candidates: [{ candidate_id: "inline-c", call_id: "inline-call", unit_id: "inline-unit", raw_latex: "a^2", parse_supported: true }] };
const sourceRisks = Array.from({ length: 50 }, (_, i) => ({ code: "INJECTED_SOURCE_RISK_" + i, row_id: "row-" + (i % 3),
  slot_ids: ["slot-" + i], threshold: [180, 190, 200, 210][i % 4], detail: { raw: "<img onerror=never-executed>", uncovered_pixels: i + 1 } }));
const state = {
  schema_version: "b-content-review-state-trial/0.1", head: "head1", book_id: "injected-ui", scope_id: "two-sections", plan_revision: 1,
  graph_ref: { artifact_id: "g" }, quality_ref: { artifact_id: "q" }, csrf_token: "token", region_catalog_available: true,
  counts: { questions: 1, answers: 2, issues: 127, unassigned: 19 }, assets: [{ asset_id: "source", width: 100, height: 100, sha256: "injected" }],
  author: { kind: "MODEL_DRAFT", id: "ui-test", note: "Injected UI-only fixture, not model execution or transcription gold" },
  answers: [{ answer_id: "a1", printed_number: "16", section_path: ["Section 1"], text: "body a tail b", explanation_text: "", figures: [],
    issue_ids: ["i0"], question_candidates: [], blocks: [region, fragment],
    region_draft_risks: [{ bundle_ref: bundle, source: { asset_id: "source", source_sha256: "injected" }, risks: sourceRisks, decision: "HOLD", transcription_verified: false }] },
    { answer_id: "a2", printed_number: "16", section_path: ["Section 2"], text: "other", explanation_text: "", figures: [], issue_ids: [], question_candidates: [], blocks: [] }],
  issues: Array.from({ length: 127 }, (_, i) => ({ issue_id: "i" + i, code: "INJECTED_EXISTING_CHECK_FINDING", severity: "REVIEW" })),
  history: [{ head: "head1", parent_head: null, plan_ref: { revision: 1 }, author: { kind: "MODEL_DRAFT", id: "test" }, summary: "initial" }],
  decision: "HOLD", complete: false, transcription_verified: false, business_acceptance: false, platform_actions: []
};
const frozen = JSON.stringify(state), calls = [];
let mode = "conflict";
const context = { document, URLSearchParams, Map, Set, WeakMap, Array, Object, String, Number, Boolean, JSON, Math, Error,
  setTimeout: () => 0, clearTimeout() {}, fetch: async (url, options) => {
    calls.push({ url, options });
    if (mode === "conflict") return { ok: false, status: 409, json: async () => ({ ok: false, error: { code: "STALE_HEAD", message: "injected stale head" } }) };
    const next = JSON.parse(frozen); next.head = url === "/api/restore" ? "head3" : "head2"; next.plan_revision = url === "/api/restore" ? 3 : 2;
    next.history.push({ head: "head2", parent_head: "head1", plan_ref: { revision: 2 }, author: next.author, summary: "saved" });
    if (next.head === "head3") next.history.push({ head: "head3", parent_head: "head2", plan_ref: { revision: 3 }, author: next.author, summary: "restored" });
    return { ok: true, status: 200, json: async () => ({ ok: true, state: next }) };
  } };
context.globalThis = context;
const instrumented = source.replace(/  refresh\(\);\r?\n\}\)\(\);\s*$/,
  "  globalThis.ui={applyState,changeFor,saveCurrent,resetBlock,applyRegionChoice,regionTopologyMatches,loadSourceImage,askRestore,restore,drafts:()=>drafts};\n})();");
assert.notStrictEqual(instrumented, source); vm.runInNewContext(instrumented, context);
const ui = context.ui;
const find = (root, predicate) => { if (predicate(root)) return root; for (const child of root.children || []) { const result = find(child, predicate); if (result) return result; } return null; };
const all = (root, predicate) => { const values = predicate(root) ? [root] : []; for (const child of root.children || []) values.push(...all(child, predicate)); return values; };
const runNode = (draft, index) => find(draft.editor, (n) => n.className === "run-editors").children[index];
const runText = (draft, index) => find(runNode(draft, index), (n) => n.tagName === "textarea");
ui.applyState(state);
assert.strictEqual(elements.get("export-region-catalog").hidden, false);
const old = JSON.parse(frozen); delete old.region_catalog_available; delete old.answers[0].region_draft_risks; ui.applyState(old);
assert.strictEqual(elements.get("export-region-catalog").hidden, true); assert.strictEqual(elements.get("region-draft-risks").hidden, true);
ui.applyState(state);
const riskDisplay = elements.get("region-draft-risks").textContent;
assert(riskDisplay.includes("自动草稿来源风险 · 50 项")); assert(riskDisplay.includes("不计入当前检查问题数"));
assert.strictEqual(elements.get("issue-total").textContent, "127");
assert.strictEqual(all(elements.get("region-draft-risks"), (n) => n.className === "region-source-risk").length, 50);
assert(riskDisplay.includes('"uncovered_pixels": 50'));

// Existing FRAGMENT selection remains bound to original Unicode code points.
const fd = ui.drafts().get("f"); assert.strictEqual(ui.changeFor(fd), null);
const original = find(fd.card, (n) => n.className === "source-text"); original.selectionStart = 0; original.selectionEnd = 2; original.dispatch("select");
assert.deepStrictEqual(Array.from(fd.sourceSpan), [0, 1]);
find(fd.card, (n) => n.tagName === "button" && n.textContent === "用于原文选区").dispatch("click");
assert.deepStrictEqual(Array.from(ui.changeFor(fd).fragment_span), [0, 1]); ui.resetBlock(fd);

let draft = ui.drafts().get("r"); assert.strictEqual(ui.changeFor(draft), null); assert.strictEqual(draft.regionSelections.size, 0);
assert.strictEqual(all(draft.editor, (n) => n.className === "region-choice-select")[0].children.length, 172);
ui.applyRegionChoice(draft, first, first.choices[1]); assert.strictEqual(draft.runs[1].text, "a"); assert(ui.changeFor(draft));
assert.deepStrictEqual(JSON.parse(JSON.stringify(ui.changeFor(draft).region_selections[0])), { bundle_ref: bundle, row_id: "injected-source-row", run_index: 1, fraction_id: "F5", candidate_id: "F5-same" });
ui.applyRegionChoice(draft, second, second.choices[0]);
runText(draft, 0).value = "edited body "; runText(draft, 0).dispatch("input"); assert.strictEqual(draft.regionSelections.size, 2);
runText(draft, 1).value = "manual a"; runText(draft, 1).dispatch("input"); assert(!draft.regionSelections.has(1)); assert(draft.regionSelections.has(3));
assert.strictEqual(elements.get("region-draft-risks").textContent, riskDisplay, "Editing/choosing cannot clear source risks");
assert.strictEqual(elements.get("issue-total").textContent, "127");
all(draft.editor, (n) => n.tagName === "button" && n.textContent === "↓")[0].dispatch("click");
assert.strictEqual(draft.regionMappingEnabled, false); assert.strictEqual(draft.regionSelections.size, 0); assert(!ui.regionTopologyMatches(draft));
assert.strictEqual(all(draft.editor, (n) => n.className === "region-readonly-catalog").length, 1);
assert(all(draft.editor, (n) => n.tagName === "button" && n.textContent === "用于此公式").every((n) => n.disabled));
ui.applyRegionChoice(draft, first, first.choices[0]); assert.strictEqual(draft.regionSelections.size, 0);
ui.resetBlock(draft); assert.strictEqual(ui.changeFor(draft), null); assert.strictEqual(draft.regionMappingEnabled, true);
ui.applyRegionChoice(draft, first, first.choices[0]);
const format = find(runNode(draft, 1), (n) => n.className === "editor-format"); format.value = "plain"; format.dispatch("change");
assert.strictEqual(draft.regionSelections.size, 0); assert.strictEqual(draft.regionMappingEnabled, false); ui.resetBlock(draft);
find(draft.editor, (n) => n.tagName === "button" && n.textContent === "＋ 添加文字段").dispatch("click");
all(draft.editor, (n) => n.tagName === "button" && n.textContent === "删除").at(-1).dispatch("click");
assert.strictEqual(draft.runs.length, 4); assert.strictEqual(ui.changeFor(draft), null); assert.strictEqual(draft.regionMappingEnabled, false); assert.strictEqual(draft.resetButton.hidden, false);
ui.resetBlock(draft); ui.applyRegionChoice(draft, first, first.choices[2]);
assert.strictEqual(draft.runs[1].text, "\\unknown{<img onerror=x>}");
assert(all(draft.editor, (n) => n.className === "region-choice-raw").some((n) => n.textContent === "\\unknown{<img onerror=x>}"));
assert.strictEqual(JSON.stringify(state), frozen, "Frozen source/catalog cannot mutate");

// A failed image load offers one explicit retry of the same strict source URL.
const imageUrls = [], image = { set src(value) { imageUrls.push(value); }, removeAttribute(name) { assert.strictEqual(name, "src"); } };
const imageError = new Element(); ui.loadSourceImage(image, "source", [1.2, 2.4, 40.1, 30.1], imageError);
image.onerror(); assert.strictEqual(imageUrls.length, 1); assert.strictEqual(imageError.children[1].textContent, "重试读取"); imageError.children[1].dispatch("click");
assert.strictEqual(imageUrls.length, 2); assert.strictEqual(imageUrls[0], imageUrls[1]); image.onload(); assert.strictEqual(imageError.hidden, true);

(async () => {
  assert.strictEqual(await ui.saveCurrent(), false); assert(draft.regionSelections.has(1)); assert.strictEqual(elements.get("save-button").disabled, false);
  mode = "success"; assert.strictEqual(await ui.saveCurrent(), true); assert.strictEqual(calls.length, 2);
  const sent = JSON.parse(calls[1].options.body);
  assert.strictEqual(sent.answer_id, "a1"); assert.strictEqual(sent.changes.length, 1); assert.strictEqual(sent.changes[0].key, "r");
  assert.strictEqual(sent.changes[0].runs[1].text, "\\unknown{<img onerror=x>}"); assert.strictEqual(sent.changes[0].region_selections[0].candidate_id, "F5-unknown");
  assert.strictEqual(sent.author.kind, "MODEL_DRAFT"); assert.strictEqual(calls[1].options.headers["X-Review-Token"], "token");
  assert.strictEqual(elements.get("region-draft-risks").textContent, riskDisplay); assert.strictEqual(elements.get("issue-total").textContent, "127");
  assert.strictEqual(elements.get("undo-save").disabled, false);
  ui.askRestore("head1"); await ui.restore(); assert.strictEqual(calls.length, 3); assert.strictEqual(calls[2].url, "/api/restore");
  assert.deepStrictEqual(JSON.parse(calls[2].options.body), { expected_head: "head2", revision_head: "head1", author: state.author });
  assert.strictEqual(elements.get("region-draft-risks").textContent, riskDisplay); assert.strictEqual(JSON.stringify(state), frozen);

  // A restore confirmation is not modal: new edits must be checked again at
  // confirmation time, with a second explicit restore after save or discard.
  const click = async (id) => {
    for (const listener of elements.get(id).listeners.click || []) await listener({ target: elements.get(id), preventDefault() {} });
    await new Promise((resolve) => setImmediate(resolve));
  };
  const restoreReady = () => {
    const next = JSON.parse(frozen); next.head = "head2"; next.plan_revision = 2;
    next.history.push({ head: "head2", parent_head: "head1", plan_ref: { revision: 2 }, author: next.author, summary: "saved" });
    ui.applyState(next); ui.askRestore("head1");
    assert.strictEqual(elements.get("history-confirm").hidden, false);
    assert.strictEqual(elements.get("navigation-guard").hidden, true);
    return ui.drafts().get("r");
  };
  let before = calls.length;
  let protectedDraft = restoreReady();
  ui.applyRegionChoice(protectedDraft, first, first.choices[1]); // Same text, new provenance is still dirty.
  await click("history-confirm-yes");
  assert.strictEqual(calls.length, before, "Dirty confirmation must not POST restore");
  assert.strictEqual(elements.get("navigation-guard").hidden, false);
  assert.strictEqual(elements.get("history-confirm").hidden, true);
  assert(ui.changeFor(protectedDraft));
  await click("guard-cancel");
  assert.strictEqual(elements.get("navigation-guard").hidden, true);
  assert(ui.changeFor(protectedDraft), "Stay here must retain the pending candidate");
  await ui.restore(); assert.strictEqual(calls.length, before, "Dismissed confirmation cannot restore later");

  protectedDraft = restoreReady();
  ui.applyRegionChoice(protectedDraft, first, first.choices[2]);
  await click("history-confirm-yes"); await click("guard-discard");
  assert.strictEqual(calls.length, before, "Discard may reopen confirmation, never auto-restore");
  assert.strictEqual(ui.changeFor(ui.drafts().get("r")), null);
  assert.strictEqual(elements.get("history-confirm").hidden, false);
  await click("history-confirm-yes");
  assert.strictEqual(calls.length, before + 1); assert.strictEqual(calls.at(-1).url, "/api/restore");

  before = calls.length; protectedDraft = restoreReady();
  runText(protectedDraft, 0).value = "edited after restore confirmation "; runText(protectedDraft, 0).dispatch("input");
  await click("history-confirm-yes");
  assert.strictEqual(calls.length, before); assert.strictEqual(elements.get("navigation-guard").hidden, false);
  mode = "conflict"; await click("guard-save");
  assert.strictEqual(calls.length, before + 1); assert.strictEqual(calls.at(-1).url, "/api/save");
  assert(ui.changeFor(protectedDraft), "Failed guarded save must retain unsaved text");
  assert.strictEqual(elements.get("navigation-guard").hidden, false);
  assert.strictEqual(elements.get("history-confirm").hidden, true);
  mode = "success"; await click("guard-save");
  assert.strictEqual(calls.length, before + 2); assert.strictEqual(calls.at(-1).url, "/api/save");
  assert.strictEqual(JSON.parse(calls.at(-1).options.body).changes[0].runs[0].text, "edited after restore confirmation ");
  assert.strictEqual(elements.get("navigation-guard").hidden, true);
  assert.strictEqual(elements.get("history-confirm").hidden, false, "Saved edits require a new explicit restore confirmation");
  assert.strictEqual(ui.changeFor(ui.drafts().get("r")), null);
  await click("history-confirm-yes");
  assert.strictEqual(calls.length, before + 3); assert.strictEqual(calls.at(-1).url, "/api/restore");
  assert.strictEqual(elements.get("region-draft-risks").textContent, riskDisplay);
  assert.strictEqual(elements.get("issue-total").textContent, "127");
  assert.strictEqual(JSON.stringify(state), frozen);
  console.log("PASS: literal DOM IDs; optional export/risks; 342 injected candidates; unchanged/default not selected; exact same-text provenance; body edit preserves/target edit clears; topology locks/reset; unknown raw safe; FRAGMENT codepoints; 50 source risks separate from 127 check findings and retained through edit/save/restore; manual image retry; CAS failure retains draft; current-only save; exact historical restore; confirmation-time dirty guard with stay/discard/save/failure and explicit reconfirmation; no source/catalog mutation.");
})().catch((error) => { console.error(error); process.exitCode = 1; });
