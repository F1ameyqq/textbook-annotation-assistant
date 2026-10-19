"""Construct and reseal three new local inputs; no suite, plan, runtime or transport call."""
import copy
import hashlib
import json
from pathlib import Path

from annotation.contracts import artifact_ref, policy_ref, seal_artifact
from annotation.contracts.models import ExchangeBundle
from annotation.quality.live_pilot import question_facts
from annotation.runtime.storage.common import digest

HERE = Path(__file__).parent
BASE = HERE.parent


def write(path, data):
    raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def reseal(req):
    replacements = []
    def rewrite(value):
        for old, new in replacements:
            if value == old:
                return copy.deepcopy(new)
        if isinstance(value, dict):
            return {k: rewrite(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rewrite(v) for v in value]
        return value
    for i, artifact in enumerate(req["bundle"]["artifacts"]):
        old = artifact_ref(artifact)
        new = seal_artifact(rewrite(artifact))
        req["bundle"]["artifacts"][i] = new
        replacements.append((old, artifact_ref(new)))
    req.update(rewrite(req))


def build(name, first_classification, answer):
    req = json.loads((BASE / "request.json").read_bytes())
    evidence = next(a for a in req["bundle"]["artifacts"] if a["kind"] == "EvidenceBundle")
    next(r for r in evidence["payload"]["regions"] if r["region_id"] == "a11-new-alpha-r5")["text"] = answer
    source = next(a for a in req["bundle"]["artifacts"] if a["kind"] == "SourceBundle")
    model = ExchangeBundle.model_validate(req["bundle"])
    graph = next(a for a in model.artifacts if a.kind == "QuestionGraph")
    qualifications = []
    for question, classification in zip(graph.payload.questions, (first_classification, "SINGLE_CHOICE")):
        fact = question_facts(model, graph, question, model.policies[0], req["bindings"])
        suffix = question.question_id.rsplit("-", 1)[-1]
        filename = name + "-" + suffix + "-classification.json"
        data = {"schema": "a11-choice-classification-1", "marker": "A11_REVIEW_DELTA_SYNTHETIC_OFFLINE_ONLY",
                "book_id": "46007447", "question_id": question.question_id,
                "source_frames_hash": digest(fact["frames"]), "source_parts_hash": digest(fact["parts"]),
                "classification": classification,
                "basis": "Explicit synthetic source classification for the fixed offline delta; no real human/platform finding"}
        resource = {"path": "review_delta/" + filename, "sha256": write(HERE / filename, data), "media_type": "application/json"}
        source["payload"]["history"].append({"resource": resource, "quality": "REVIEWED",
            "reason": "Synthetic reviewed classification fixture; NOT a real source or platform qualification"})
        qualifications.append({"resource": resource, "classification": classification})
    reseal(req)
    model = ExchangeBundle.model_validate(req["bundle"])
    graph = next(a for a in model.artifacts if a.kind == "QuestionGraph")
    for question, entry, qualification in zip(graph.payload.questions, req["approval"]["questions"], qualifications):
        fact = question_facts(model, graph, question, model.policies[0], req["bindings"])
        entry.update(input_hash=digest(fact), approved_parts=fact["parts"], answer_relation=fact["relations"][0],
                     choice_qualification=qualification)
    write(HERE / (name + ".json"), req)


if __name__ == "__main__":
    build("valid", "SINGLE_CHOICE", "B")
    build("multiple-answer", "SINGLE_CHOICE", "BC")
    build("explicit-multiple", "MULTIPLE_CHOICE", "B")
