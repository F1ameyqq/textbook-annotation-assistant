"""Seal review-only staged raw blobs, or verify the committed review manifest."""
import argparse
import json
from pathlib import Path
from review_checks import REPO, OUT, CANDIDATE, DELIVERY, WORKFLOW, digest, blobs, git, tree

MANIFEST = "docs/evidence/A07/review/review-raw-git-manifest.json"
REPORT = "docs/tasks/A07-Q1-review-report.md"

def allowed(path):
    return path == REPORT or path.startswith("docs/evidence/A07/review/")

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("phase",choices=("prepare","verify"))
    args = parser.parse_args()
    if args.phase == "prepare":
        assert git("rev-parse","HEAD").decode().strip() == CANDIDATE
        changes = git("diff","--cached","--name-status","HEAD").decode().splitlines()
        assert changes and all(row.startswith("A\t") and allowed(row[2:]) for row in changes)
        members = []
        for entry in git("ls-files","--stage","-z","--",REPORT,"docs/evidence/A07/review/").split(b"\0"):
            if not entry: continue
            fields,path = entry.split(b"\t",1); mode,oid,stage = fields.decode().split()
            path = path.decode("utf-8")
            assert stage == "0" and mode == "100644" and allowed(path) and path != MANIFEST
            members.append({"path":path,"blob_oid":oid,"mode":mode})
        members.sort(key=lambda item:item["path"])
        raw = blobs(list(dict.fromkeys(m["blob_oid"] for m in members)))
        for member in members:
            data = raw[member["blob_oid"]]
            member.update(bytes=len(data),sha256=digest(data))
        manifest = {"review_parent_product_commit":CANDIDATE,"reviewed_delivery_commit":DELIVERY,
            "workflow_commit":WORKFLOW,"review_delivery_identity":"commit containing this manifest and the review report; exact SHA in final handoff",
            "basis":"raw staged Git blobs via cat-file --batch; verified against final commit after sealing",
            "self_excluded_path":MANIFEST,"members_count":len(members),"total_bytes":sum(m["bytes"] for m in members),"members":members}
        dest = REPO/MANIFEST
        assert not dest.exists()
        dest.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"members":len(members),"bytes":manifest["total_bytes"],"manifest_sha256":digest(dest.read_bytes())}))
    else:
        commit = git("rev-parse","HEAD").decode().strip()
        current,base = tree(commit),tree(CANDIDATE)
        assert all(current.get(p) == spec for p,spec in base.items())
        added = set(current)-set(base)
        assert all(map(allowed,added))
        raw_manifest = git("show",commit+":"+MANIFEST)
        manifest = json.loads(raw_manifest)
        assert {m["path"] for m in manifest["members"]} == added-{MANIFEST}
        raw = blobs(list(dict.fromkeys(m["blob_oid"] for m in manifest["members"])))
        for member in manifest["members"]:
            value = raw[member["blob_oid"]]
            assert current[member["path"]][2] == member["blob_oid"]
            assert len(value) == member["bytes"] and digest(value) == member["sha256"]
        assert len(manifest["members"]) == manifest["members_count"]
        assert sum(m["bytes"] for m in manifest["members"]) == manifest["total_bytes"]
        report = REPO/REPORT
        import re
        links = re.findall(r'\]\(([^)]+)\)',report.read_text(encoding="utf-8"))
        assert all((report.parent/link.split("#")[0]).resolve().exists() for link in links if "://" not in link)
        print(json.dumps({"result":"PASS","review_commit":commit,"review_tree":git("rev-parse",commit+"^{tree}").decode().strip(),
            "members":manifest["members_count"],"bytes":manifest["total_bytes"],"added_paths_including_manifest":len(added),
            "all_candidate_paths_preserved":True,"report_sha256":digest(git("show",commit+":"+REPORT)),
            "manifest_sha256":digest(raw_manifest),"report_links_checked":len(links)}))

if __name__ == "__main__":
    main()
