"""Portable sealed mutations for the bounded R2 source consistency checks."""
import hashlib
import json
import shutil
from pathlib import Path

from annotation.contracts import seal_artifact


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Package:
    def __init__(self,base,destination):
        shutil.copytree(base,destination)
        self.folder = Path(destination)
        self.data = read(self.folder/"exchange.json")

    @property
    def source(self):
        return self.data["artifacts"][0]

    def resource(self,relative,value):
        path = self.folder/relative
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        for item in self.data["evidence"]+self.source["payload"]["history"]:
            if item["resource"]["path"] == relative:
                item["resource"]["sha256"] = digest
        return digest

    def sidecar(self,relative,mutate):
        value = read(self.folder/relative)
        mutate(value)
        self.resource(relative,value)

    def page_url(self,mutate):
        relative = "history/00-independent-source-page14.json"
        value = read(self.folder/relative)
        mutate(value["data"]["pages"][0])
        digest = self.resource(relative,value)
        def keep_bytes_consistent(integrity):
            rows = [r for r in integrity["inputs"] if r["archive_path"].endswith("/independent-source-page14.json")]
            assert len(rows) == 1
            rows[0]["before_sha256"] = rows[0]["after_sha256"] = digest
        self.sidecar("input-integrity.json",keep_bytes_consistent)

    def select_missing(self,indices):
        """Declare unacquired intent IDs, never fabricate assets/digests/images."""
        provenance = read(self.folder/"provenance.json")
        acquired = {m["source_index"] for m in provenance["mappings"]}
        selected = acquired|set(indices)
        provenance["selected_source_indices"] = sorted(selected)
        provenance["selected_missing_source_indices"] = list(indices)
        provenance["outside_selected_scope_unacquired_indices"] = [i for i in range(provenance["metadata_page_count"]) if i not in selected]
        self.resource("provenance.json",provenance)
        payload = self.source["payload"]
        payload["pages_expected"] = payload["pages_acquired"]+[
            "expected-"+self.source["book_id"]+"-source-"+str(i) for i in indices]
        self.source["producer"].update(evidence_mode="SYNTHETIC",config_version="a01-r2-declared-missing-test")

    def seal(self):
        self.data["artifacts"][0] = seal_artifact(self.source)
        path = self.folder/"exchange.json"
        path.write_text(json.dumps(self.data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        return path


PRIMARY = ("P01","N14","P02","P03","P04")


def mutated(base,destination,case):
    package = Package(base,destination)
    if case == "P01":
        package.sidecar("provenance.json",lambda p:p.update(selected_missing_source_indices=[7]))
    elif case == "N14":
        package.sidecar("provenance.json",lambda p:p["outside_selected_scope_unacquired_indices"].append(7))
    elif case == "P02":
        package.page_url(lambda p:p.update(image=p["image"].replace("46007447","46006966")))
    elif case == "P03":
        package.page_url(lambda p:p.update(image=p["image"].replace("_page_13.jpg","_page_172.jpg")))
    elif case == "P04":
        package.sidecar("provenance.json",lambda p:p["observation"]["observation_index_source"].update(sha256="0"*64))
    else:
        raise ValueError("unknown R2 case")
    return package.seal()
