"""The one bounded, legally resealed image-as-text semantic counterexample."""
import copy

from annotation.contracts import artifact_ref, seal_artifact, validate_bundle


def image_as_text(bundle, root):
    data = bundle.model_dump(mode="json")
    replacements, artifacts = [], []

    def rebind(value):
        if isinstance(value, dict):
            for old, new in replacements:
                if value == old:
                    return copy.deepcopy(new)
            return {k: rebind(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rebind(v) for v in value]
        return value

    for old in data["artifacts"]:
        new = rebind(old)
        if new["kind"] == "EvidenceBundle":
            new["payload"]["regions"][0]["content_type"] = "text"
        if new["kind"] == "QuestionGraph":
            new["payload"]["fragments"][0]["content_type"] = "text"
        new = seal_artifact(new)
        replacements.append((artifact_ref(old), artifact_ref(new)))
        artifacts.append(new)
    data["artifacts"] = artifacts
    return validate_bundle(data, asset_root=root)
