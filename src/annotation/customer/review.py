"""Customer job adapter for the existing source-visible B review server/UI."""
from __future__ import annotations

import copy
import io
from pathlib import Path

from .prepare import candidate_hash, preparation_status, utcnow
from .source import verify_sources
from .store import Hold, digest

CONFIRMABLE = {"IMAGE_TRANSCRIPTION_AND_FIGURES_REVIEW", "FIGURE_OR_FORMULA_REVIEW", "ANSWER_BOUNDARY_UNRESOLVED"}


class CustomerReviewWorkspace:
    def __init__(self, store, identity):
        self.store, self.identity = store, identity

    def _load(self):
        job, head = self.store.job(self.identity)
        verify_sources(job["pages"])
        return job, head

    def state(self):
        job, head = self._load()
        answers, issues = [], []
        for index, issue in enumerate(job["issues"]):
            issues.append({**issue, "issue_id": "global-" + str(index), "severity": "ERROR"})
        for candidate in job["candidates"]:
            linked = []
            for code in candidate["issues"]:
                iid = candidate["key"] + "-" + code
                issues.append({"code": code, "issue_id": iid, "severity": "REVIEW", "scope_id": candidate["key"]})
                linked.append(iid)
            blocks = []
            for zone, text in candidate["zones"].items():
                frames = [f for f in candidate["frames"] if f["zone"] == zone]
                frame = frames[0] if frames else candidate["frames"][0]
                blocks.append({"key": candidate["key"] + ":" + zone, "kind": "FRAGMENT", "role": zone,
                    "asset_id": frame["asset_id"], "bbox": frame["bbox"], "text": text,
                    "source_text": candidate.get("original_zones", candidate["zones"]).get(zone, ""),
                    "runs": [{"format": "plain", "text": text}], "candidates": [], "source_fragment_ids": []})
            answers.append({"answer_id": candidate["key"], "printed_number": candidate["printed_number"],
                "section_path": candidate["section_path"], "text": candidate["zones"]["answer"],
                "explanation_text": candidate["zones"].get("analysis", ""), "blocks": blocks,
                "figures": [{"region_id": "source-" + str(i), "asset_id": f["asset_id"], "bbox": f["bbox"], "role": f["zone"]}
                            for i, f in enumerate(candidate["frames"])],
                "issue_ids": linked, "question_candidates": [{"question_id": candidate["question_id"],
                    "printed_number": candidate["printed_number"], "section_path": candidate["section_path"],
                    "text": candidate["zones"]["question"]}], "content_status": candidate["content_status"]})
        # These are the existing UI's immutable draft/recognition boundary,
        # not the separate customer review receipt or platform acceptance.
        return {"schema_version": "b-content-review-state-trial/0.1", "head": head,
            "book_id": job["book_id"], "scope_id": job["lesson"], "plan_revision": job["revision"],
            "author": {"kind": "HUMAN_DRAFT", "id": "local-customer", "note": "对照原始材料核对"},
            "counts": {"questions": len(answers), "answers": len(answers), "issues": len(issues), "unassigned": len(job["issues"])},
            "assets": [{"asset_id": p["asset_id"], "width": p.get("width", 1), "height": p.get("height", 1), "sha256": p["raw_sha256"]}
                       for p in job["pages"]], "answers": answers, "issues": issues, "history": [],
            "decision": "HOLD", "complete": False, "transcription_verified": False,
            "business_acceptance": False, "platform_actions": [],
            "customer": {"job_status": job["status"], "can_confirm": True,
                         "message": job.get("last_message", "核对题干、选项、答案及来源框后确认；缺材料或结构错误仍会阻断。"),
                         "metrics": job["metrics"], "platform_status": job["platform_status"]}}

    def source_png(self, aid, bbox=None):
        from PIL import Image, ImageDraw, ImageFont
        job, _ = self._load()
        page = next((p for p in job["pages"] if p["asset_id"] == aid), None)
        if page is None:
            raise Hold("来源页不属于本任务。")
        if page["kind"] == "image":
            with Image.open(page["raw_path"]) as original:
                image = original.convert("RGB")
        else:
            image = Image.new("RGB", (page["width"], page["height"]), "white")
            font_path = Path("C:/Windows/Fonts/msyh.ttc")
            font = ImageFont.truetype(str(font_path), 20) if font_path.exists() else ImageFont.load_default()
            draw = ImageDraw.Draw(image)
            for index, line in enumerate(page["text"].splitlines()):
                draw.text((20, 20 + index * 30), line, font=font, fill="black")
        if bbox is not None:
            from annotation.recognition.baseline import valid_bbox
            if not valid_bbox(bbox, *image.size) or any(type(x) is not int for x in bbox):
                raise Hold("来源裁片范围无效。")
            image = image.crop(tuple(bbox))
        output = io.BytesIO(); image.save(output, format="PNG")
        return output.getvalue()

    def _target(self, job, request, head):
        from annotation.recognition.content_review import ReviewConflict
        if request.get("expected_head") != head:
            raise ReviewConflict("任务已更新，请刷新后再操作。")
        candidate = next((q for q in job["candidates"] if q["key"] == request.get("answer_id")), None)
        if candidate is None:
            raise Hold("没有找到所选题目。")
        return candidate

    def save(self, request):
        job, head = self._load()
        with self.store.book_lock(job["book_id"]):
            job, head = self._load()
            candidate = self._target(job, request, head)
            changes = request.get("changes")
            if not isinstance(changes, list) or not changes:
                raise Hold("没有可保存的修改。")
            candidate.setdefault("original_zones", copy.deepcopy(candidate["zones"]))
            seen = set()
            for change in changes:
                if set(change) != {"key", "text", "format"} or change["format"] != "plain":
                    raise Hold("本入口保存完整文字；公式候选的结构编辑需保留原有区域审校流程。")
                prefix = candidate["key"] + ":"
                if not isinstance(change["key"], str) or not change["key"].startswith(prefix):
                    raise Hold("编辑块不属于当前题目。")
                zone = change["key"][len(prefix):]
                text = change["text"]
                if zone not in candidate["zones"] or zone in seen or not isinstance(text, str) or not text.strip() or len(text) > 100000:
                    raise Hold("编辑块为空、重复或超出范围。")
                candidate["zones"][zone] = text; seen.add(zone)
            candidate["review"] = None
            candidate["content_status"] = "NEEDS_REVIEW"
            if "EDITED_CONTENT_REVIEW" not in candidate["issues"]:
                candidate["issues"].append("EDITED_CONTENT_REVIEW")
            candidate["content_hash"] = candidate_hash(candidate)
            job["revision"] += 1; job["metrics"]["review_actions"] += 1
            job["status"] = preparation_status(job)
            self.store.save_job(job, head, "CUSTOMER_EDIT")
        return self.state()

    def confirm(self, request):
        job, head = self._load()
        with self.store.book_lock(job["book_id"]):
            job, head = self._load()
            candidate = self._target(job, request, head)
            if request.get("source_checked") is not True or request.get("content_checked") is not True:
                raise Hold("请对照原图核对完整内容及来源框。")
            blocking = set(candidate["issues"]) - CONFIRMABLE - {"EDITED_CONTENT_REVIEW"}
            if blocking or job["issues"]:
                raise Hold("仍有缺材料、配答或结构问题；内容确认不能消除这些问题。请补充正确范围后重新准备，已有识别缓存会复用。")
            if any(not text.strip() for text in candidate["zones"].values()):
                raise Hold("题干或答案为空。")
            # Re-run semantic structural checks after an edit, not only before.
            from annotation.recognition.policy import option_set_valid, choice_answer_valid
            import re
            if "choice" in candidate["zones"]:
                labels = re.findall(r"^\s*([A-G])[.．、]", candidate["zones"]["choice"], re.M)
                if not option_set_valid(labels) or not choice_answer_valid(candidate["zones"]["answer"], labels):
                    raise Hold("选项或答案结构仍不完整。")
            candidate["review"] = {"kind": "CUSTOMER_SOURCE_REVIEW", "at": utcnow(),
                "content_hash": candidate_hash(candidate), "previous_head": head,
                "source_checked": True, "content_checked": True}
            candidate["issues"] = []
            candidate["content_status"] = "READY_CUSTOMER_REVIEWED"
            job["revision"] += 1; job["metrics"]["review_actions"] += 1
            job["status"] = preparation_status(job)
            self.store.save_job(job, head, "CUSTOMER_CONFIRM")
        return self.state()

    def documents(self):
        job, _ = self._load()
        return {"plan": job}

    def restore(self, request):
        raise Hold("原版本保存在本地历史中；本入口不自动恢复已确认或已执行内容。")

    def region_catalog(self):
        raise Hold("本任务没有公式区域候选目录。")
