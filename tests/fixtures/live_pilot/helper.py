"""New A11 synthetic fixture construction and disk-backed fake transport. ZERO platform I/O."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys

from annotation.contracts import artifact_ref, policy_ref, seal_artifact, seal_policy
from annotation.runtime.storage.common import digest

HERE = Path(__file__).parent
MARKER = "A11_SYNTHETIC_OFFLINE_ONLY"


def build_fixture():
    page = b"P5\n100 100\n255\n" + bytes([255]) * 10000
    proof = b"A11 synthetic offline test evidence. No platform observation.\n"
    (HERE / "page.pgm").write_bytes(page)
    (HERE / "proof.txt").write_bytes(proof)
    sha = hashlib.sha256(page).hexdigest()
    policy = seal_policy({"policy_id": "a11-offline-policy", "revision": 1,
        "confirmation_status": "SYNTHETIC_ASSUMPTION", "option_grouping": "SEPARATE",
        "role_mapping": {"stem": "Q", "option": "W", "answer": "A", "explanation": "E", "shared_material": "Q"},
        "source_notes": ["OFFLINE: 项目交接说明 R01/R02 ordinary options W; not joint live adoption"],
        "frame_save_status": "SYNTHETIC", "ocr_status": "SYNTHETIC", "applicability": "SYNTHETIC_ONLY"})
    def artifact(kind, identity, payload, dependencies=()):
        return seal_artifact({"schema_version": "1.0.0-a-proposal", "artifact_id": identity,
            "revision": 1, "kind": kind, "run_id": "a11-new-offline-suite", "book_id": "46007447",
            "scope_id": "a11-offline-scope", "input_refs": [artifact_ref(d) for d in dependencies],
            "producer": {"module": "a11-fixture", "implementation_version": "1", "config_version": "offline",
                "policy_versions": [policy_ref(policy)], "model_version": None, "prompt_version": None,
                "evidence_mode": "SYNTHETIC"}, "created_at": "2026-10-19T00:00:00Z", "payload": payload})
    image = {"asset_id": "a11-page", "width": 100, "height": 100, "sha256": sha}
    source = artifact("SourceBundle", "a11-source", {"assets": [dict(image, path="page.pgm",
        media_type="image/x-portable-graymap", source_label=MARKER, provenance="SYNTHETIC")],
        "directories": [{"directory_id": "source-dir", "parent_id": None, "label": "OFFLINE"}],
        "pages_expected": ["a11-page"], "pages_acquired": ["a11-page"],
        "external_page_mappings": [{"asset_id": "a11-page", "directory_id": "source-dir", "external_page": "1",
            "mapping_status": "CONFIRMED", "evidence_refs": ["a11-proof"]}], "history": [],
        "scope_manifest": ["a11-new-alpha", "a11-new-beta"], "scope_manifest_basis": MARKER, "metadata_page_count": 1})
    regions, fragments, questions, relations = [], [], [], []
    for n, qid in enumerate(source["payload"]["scope_manifest"]):
        ids = []
        for index, role in enumerate(("stem", "option", "option", "option", "option", "answer")):
            rid, fid = qid + "-r" + str(index), qid + "-f" + str(index)
            ids.append(fid)
            regions.append({"region_id": rid, "box": {"image": image, "bbox": [float(n*40), float(index*10), float(n*40+30), float(index*10+8)]},
                "crop_transform": {"scale_x": 1.0, "scale_y": 1.0, "offset_x": 0.0, "offset_y": 0.0,
                    "rotation_degrees": 0.0, "padding": [0.0]*4, "processed_width": 100, "processed_height": 100, "invertible": True},
                "content_type": "text", "text": ["OFFLINE: 1 + 1 = ?", "A. 1", "B. 2", "C. 3", "D. 4", "B"][index],
                "source": "SYNTHETIC", "evidence_refs": ["a11-proof"], "printed_number_candidates": [], "certainty": "CONFIRMED"})
            fragments.append({"fragment_id": fid, "region_ids": [rid], "role": role, "content_type": "text", "reading_order": index})
        questions.append({"question_id": qid, "directory_id": "source-dir", "question_type": "ordinary_choice",
            "fragment_ids": ids[:5], "parent_question_id": None, "shared_fragment_ids": [], "cross_page": False,
            "external_refs": {"printed_number": str(n+70), "platform_question_id": None, "platform_order": None}})
        relations.append({"relation_id": qid+"-answer", "question_id": qid, "candidate_fragment_ids": [ids[5]],
            "selected_fragment_ids": [ids[5]], "status": "SELECTED", "evidence_refs": ["a11-proof"]})
    evidence = artifact("EvidenceBundle", "a11-evidence", {"source": artifact_ref(source), "regions": regions,
        "coverage_clues": [{"clue_id": "a11-clue", "box": {"image": image, "bbox": [0.0,0.0,100.0,100.0]},
            "source": "SYNTHETIC", "disposition": "ASSIGNED", "region_ids": [r["region_id"] for r in regions],
            "reason": MARKER, "evidence_refs": ["a11-proof"]}]}, [source])
    graph = artifact("QuestionGraph", "a11-graph", {"source": artifact_ref(source), "evidence": artifact_ref(evidence),
        "questions": questions, "fragments": fragments, "answer_relations": relations, "identity_notes": MARKER}, [source,evidence])
    bindings = {"a11-page": dict(image, resource_id="offline-resource-1", viewer_page=1, source_page=0, save_page=0,
                                 evidence_refs=["a11-proof"])}
    target = {"directories": ["target-a", "target-b"], "questions": [
        {"platform_question_id": "old-a", "directory_id": "target-a", "platform_order": 2},
        {"platform_question_id": "old-b", "directory_id": "target-b", "platform_order": 9}],
        "frames": [{"platform_frame_id": "old-rect", "platform_question_id": "old-a",
                    "box": {"image": image, "bbox": [0.0,80.0,20.0,90.0]}, "platform_role": "Q", "platform_type": "text"}]}
    observation = {"book_id": "46007447", "platform_version": "a11-fake-v1", "complete": True,
        "read_status": "OK", "submission_status": "NOT_SUBMITTED", "source_bindings": bindings,
        "origin": "FAKE_BACKEND_READ", "phase": "baseline", "source_ref": "offline-read-1", "read_sequence": 1,
        "session_id": "offline-session-1", "directory_details": [
            {"directory_id": "target-a", "parent_id": None, "label": "old A", "sibling_order": 0},
            {"directory_id": "target-b", "parent_id": None, "label": "old B", "sibling_order": 1}],
        "view": {"target": target, "internal_bindings": {}, "frame_projections": {"old-rect": {"old": True}},
            "question_content": {"old-a": {"status": "AVAILABLE", "question_type": "free_response", "parts": [{"text": "old A"}]},
                                 "old-b": {"status": "AVAILABLE", "question_type": "free_response", "parts": [{"text": "old B"}]}}}}
    snap = artifact("PlatformSnapshot", "a11-initial-snapshot", {"target_id": "a11-offline-target", "platform_version": "a11-fake-v1",
        "observed_at": "2026-10-19T00:00:00Z", "observed_version": "1", "observed_hash": digest(observation),
        "authorized_scope_id": "a11-offline-scope", "directories": target["directories"], "questions": target["questions"],
        "frames": [{k:v for k,v in target["frames"][0].items() if k != "platform_type"}],
        "capabilities": [{"name": n, "status": "VERIFIED", "platform_version": "a11-fake-v1", "evidence_refs": ["a11-proof"]}
                         for n in ("frame_readback", "content_readback", "same_session_handoff")], "evidence_refs": ["a11-proof"]}, [source])
    pre = artifact("CheckReport", "a11-precheck", {"stage": "PRE_APPLY", "subject": artifact_ref(graph),
        "graph": artifact_ref(graph), "policy": policy_ref(policy), "snapshot": None, "receipt": None,
        "coverage": {"scope_id": "a11-offline-scope", "pages_expected": ["a11-page"], "pages_checked": ["a11-page"],
                     "clue_ids": ["a11-clue"], "unassigned_region_ids": []},
        "checks": [{"check_id": n, "outcome": "PASS", "evidence_refs": ["a11-proof"], "reason": MARKER}
                   for n in ("source_integrity", "structure", "answer_matching", "coverage", "policy")],
        "issues": [], "decision": "PASS", "reason": MARKER}, [graph])
    bundle = {"format_version": "c01-exchange-1", "evidence": [{"evidence_id": "a11-proof",
        "resource": {"path": "proof.txt", "sha256": hashlib.sha256(proof).hexdigest(), "media_type": "text/plain"},
        "description": MARKER, "mode": "SYNTHETIC"}], "policies": [policy], "artifacts": [source,evidence,graph,snap,pre]}
    # Fixture construction performs model parsing/sealing only, not runtime execution.
    from annotation.contracts.models import ExchangeBundle
    from annotation.quality.live_pilot import question_facts
    model = ExchangeBundle.model_validate(bundle)
    mg = next(a for a in model.artifacts if a.kind == "QuestionGraph")
    facts = [question_facts(model, mg, q, model.policies[0], bindings) for q in mg.payload.questions]
    request = {"fixture_marker": MARKER, "bundle": bundle, "bindings": bindings, "directory_map": {"source-dir": "target-a"},
        "refs": {"graph": artifact_ref(graph), "precheck": artifact_ref(pre), "snapshot": artifact_ref(snap), "policy": policy_ref(policy)},
        "observation": observation, "approval": {"purpose": "OFFLINE_A11_TEST_ONLY", "book_id": "46007447",
            "operations": ["CREATE_FRAMES"], "per_question_send_limit": 1, "batch_send_limit": 2,
            "policy": policy_ref(policy), "evidence_refs": ["a11-proof"], "starts_at": "2026-01-01T00:00:00Z",
            "ends_at": "2099-01-01T00:00:00Z", "questions": [{"question_id": f["question_id"], "input_hash": digest(f),
                "approved_parts": f["parts"], "answer_relation": f["relations"][0]} for f in facts]}}
    (HERE / "request.json").write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "a05-history.json").write_text(json.dumps({"marker": MARKER, "historical_shape_only": True,
        "code": 0, "ocr_submissions": [], "question_order": 22, "content": None}), encoding="utf-8")


def request():
    return json.loads((HERE / "request.json").read_text(encoding="utf-8"))


def reseal(req):
    """Rebind a negative fixture so hash validity cannot hide a semantic failure."""
    replacements = []
    def rewrite(value):
        for old, new in replacements:
            if value == old: return copy.deepcopy(new)
        if isinstance(value, dict): return {k:rewrite(v) for k,v in value.items()}
        if isinstance(value, list): return [rewrite(v) for v in value]
        return value
    for i, policy in enumerate(req["bundle"]["policies"]):
        old = policy_ref(policy)
        new = seal_policy(policy)
        req["bundle"]["policies"][i] = new
        replacements.append((old, policy_ref(new)))
    for i, artifact in enumerate(req["bundle"]["artifacts"]):
        old = artifact_ref(artifact)
        new = seal_artifact(rewrite(artifact))
        req["bundle"]["artifacts"][i] = new
        replacements.append((old, artifact_ref(new)))
    req.update(rewrite(req))
    return req


def case_root(name):
    root = Path(os.environ["A11_CASE_ROOT"]) / name
    root.mkdir(parents=True, exist_ok=False)
    return root


def process_event(value):
    path = Path(os.environ["A11_PROCESS_LOG"])
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


class FakeTransport:
    offline = True
    def __init__(self, root, initial, behavior="normal"):
        self.root, self.behavior = Path(root), behavior
        self.root.mkdir(parents=True, exist_ok=True)
        self.file = self.root / "fake-backend.json"
        if not self.file.exists():
            self._save({"initial": copy.deepcopy(initial), "new": [], "sequence": initial["read_sequence"],
                        "session": 1, "closed": False, "sends": 0})

    def _load(self):
        return json.loads(self.file.read_text(encoding="utf-8"))

    def _save(self, data):
        self.file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def send_once(self, command):
        from annotation.delivery.live_pilot.usense import validate_offline_command
        validate_offline_command(command)
        data = self._load()
        data["sends"] += 1
        self._save(data)
        pid = "fake-created-" + str(data["sends"])
        rectangles = []
        for i, frame in enumerate(command["frames"]):
            rectangles.append({"rect_id": pid+"-rect-"+str(i), "image": frame["box"]["image"],
                "coordinates": frame["box"]["bbox"], "role": frame["platform_role"], "kind": frame["platform_type"],
                "fragment": frame["fragment_id"], "region": frame["region_id"], "ordinal": i})
        data["new"].append({"id": pid, "internal": command["question_id"], "directory": command["directory_id"],
            "order": command["insert_after_order"]+1, "rectangles": rectangles,
            "content": {"status": "AVAILABLE", "question_type": "ordinary_choice", "parts": copy.deepcopy(command["approved_parts"])}})
        if self.behavior == "partial":
            data["new"][-1]["rectangles"].pop()
        if self.behavior.startswith("text_"):
            content = data["new"][-1]["content"]
            if self.behavior == "text_pending": content["status"] = "PENDING"
            elif self.behavior == "text_order": content["parts"][1:3] = content["parts"][1:3][::-1]
            elif self.behavior == "text_answer": content["parts"][-1]["text"] = "A"
            else: content["parts"][0]["text"] = "OFFLINE: 1 - 1 = ?"
        self._save(data)
        if self.behavior == "response_loss": raise TimeoutError("synthetic response lost")
        if self.behavior == "http_only": return {"http_status": 200}
        return {"namespace": MARKER, "business_code": 0, "operation": "inserted",
                "platform_question_id": pid, "append_at_global_end": True}

    def observe(self, phase):
        if self.behavior == "get_timeout" and phase == "get": raise TimeoutError("synthetic GET")
        data = self._load()
        predecessor = "offline-session-" + str(data["session"])
        if data["closed"] or phase == "reopen":
            data["session"] += 1
            data["closed"] = False
        data["sequence"] += 1
        self._save(data)
        obs = copy.deepcopy(data["initial"])
        obs.update(phase=phase, read_sequence=data["sequence"], source_ref="offline-read-"+str(data["sequence"]),
                   session_id="offline-session-"+str(data["session"]))
        if phase == "reopen":
            obs.update(predecessor_session_id=predecessor, released_predecessor=True)
        view = obs["view"]
        for item in data["new"]:
            pid = item["id"]
            view["internal_bindings"][item["internal"]] = pid
            view["target"]["questions"].append({"platform_question_id": pid, "directory_id": item["directory"], "platform_order": item["order"]})
            view["question_content"][pid] = copy.deepcopy(item["content"])
            for raw in sorted(item["rectangles"], key=lambda r:r["ordinal"]):
                box = {"image": raw["image"], "bbox": raw["coordinates"]}
                view["target"]["frames"].append({"platform_frame_id": raw["rect_id"], "platform_question_id": pid,
                    "box": box, "platform_role": raw["role"], "platform_type": raw["kind"]})
                view["frame_projections"][raw["rect_id"]] = {"fragment_id": raw["fragment"], "region_id": raw["region"],
                    "box": box, "platform_role": raw["role"], "platform_type": raw["kind"]}
        if self.behavior == "prewrite_drift" and phase == "prewrite": obs["directory_details"][0]["label"] = "drift"
        if phase in ("get", "refresh", "reopen", "reconcile"):
            if self.behavior == "truncated": obs["complete"] = False
            if self.behavior == "plan_copy": obs["origin"] = "EXPECTED_PROJECTION"
            if self.behavior == "old_frame": view["target"]["frames"][0]["platform_role"] = "A"
            if self.behavior == "old_text": view["question_content"]["old-a"]["parts"][0]["text"] = "changed"
            if self.behavior == "old_directory": obs["directory_details"][0]["label"] = "changed"
            if self.behavior == "old_order": view["target"]["questions"][0]["platform_order"] = 3
            if self.behavior == "same_reopen" and phase == "reopen": obs["session_id"] = predecessor
        return obs

    def close(self):
        data = self._load()
        data["closed"] = True
        self._save(data)
        if self.behavior == "close_error": raise OSError("synthetic close failure")
        return {"released": True, "owned_fake_session_closed": True, "platform_calls": 0}


def worker():
    from annotation.runtime.live_pilot.journal import Journal
    from annotation.runtime.live_pilot.runner import apply
    root, point = Path(sys.argv[2]), sys.argv[3]
    req = request()
    transport = FakeTransport(root / "backend", req["observation"])
    def fault(current):
        if current == point:
            os._exit(73)
    try:
        result = apply(req, HERE, Journal(root / "journal", offline=True), transport, fault=fault)
        print(json.dumps({"pid": os.getpid(), "result": result}))
    except Exception as exc:
        print(json.dumps({"pid": os.getpid(), "blocked": getattr(exc, "code", type(exc).__name__)}))
        raise SystemExit(2)


if __name__ == "__main__":
    if sys.argv[1] == "build": build_fixture()
    elif sys.argv[1] == "worker": worker()
