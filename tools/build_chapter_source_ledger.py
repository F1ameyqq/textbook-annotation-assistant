"""Turn the fixed parsed archive into a chapter acquisition ledger, not a census.

Only observed directory membership is joined by exact node ID. Printed question
numbers, page offsets and absent children never establish identity/completeness.
No browser, model, HTTP request or platform write is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path


BOOK = "46007447"
ROOT_ID = "dir-1792063578574-ug3232apl"
REFLECTION_ID = "dir-1792063578574-iv9ig1hci"
STATE_SHA256 = "640aaabe023c1e96e24ac3b1b002c8b9e7c045ed7b075a8777377a8ae9ba5775"
STATE_BYTES = 232913


def require(condition, code):
    if not condition:
        raise ValueError(code)


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def build_ledger(state, root_id=ROOT_ID, reflection_id=REFLECTION_ID):
    target = state["target"]
    require(target.get("book_id") == BOOK, "WRONG_BOOK")
    tree = target.get("raw_directory_tree_projection")
    require(isinstance(tree, list), "ARCHIVED_TREE_REQUIRED")
    nodes, parents = {}, {}

    def index(node, parent):
        require(isinstance(node, dict) and isinstance(node.get("id"), str), "TREE_NODE_SCHEMA")
        key = node["id"]
        require(key not in nodes, "DUPLICATE_TREE_NODE_ID")
        nodes[key], parents[key] = node, parent
        children = node.get("children", [])
        require(isinstance(children, list), "TREE_CHILDREN_SCHEMA")
        for child in children:
            index(child, key)

    for node in tree:
        index(node, None)
    require(root_id in nodes and nodes[root_id].get("isQuestion") is not True, "CHAPTER_ROOT_MISSING")
    rows = target.get("questions")
    require(isinstance(rows, list), "ARCHIVED_QUESTIONS_REQUIRED")
    question_rows = {}
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get("id"), str), "QUESTION_ROW_SCHEMA")
        require(row["id"] not in question_rows, "DUPLICATE_QUESTION_ROW_ID")
        question_rows[row["id"]] = row
    sections = []

    def visit(node, path):
        require(node.get("isQuestion") is not True, "EXPECTED_DIRECTORY")
        label = node.get("label")
        require(isinstance(label, str), "DIRECTORY_LABEL_SCHEMA")
        path = path + [label]
        children = node.get("children", [])
        directories = [n for n in children if n.get("isQuestion") is not True]
        questions = [n for n in children if n.get("isQuestion") is True]
        question_observations = []
        for question in questions:
            row = question_rows.get(question["id"])
            if row is not None:
                require(row.get("directory_id") == node["id"], "DIRECTORY_MEMBERSHIP_CONFLICT")
            content = row.get("content", {}) if row is not None else {}
            frames = row.get("frames", []) if row is not None else []
            require(isinstance(frames, list), "FRAMES_SCHEMA")
            question_observations.append({
                "directory_node_id_candidate": question["id"],
                "visible_label": question.get("label"),
                "raw_order_in_level": question.get("order_in_level"),
                "printed_question_number": None,
                "canonical_question_id": None,
                "archived_content_status": content.get("status", "UNOBSERVED"),
                "archived_content_reason": content.get("reason", "UNOBSERVED"),
                "frame_count_observed": len(frames),
                "frame_page_observations": [
                    {"zone": frame.get("type"), "page_index": frame.get("page_index")}
                    for frame in frames],
                "full_body_coverage_proven": False,
            })
        status = ("OBSERVED_DIRECTORY_CONTAINER" if directories else
                  "PARTIAL_QUESTION_NODES_OBSERVED" if questions else
                  "QUESTION_MEMBERSHIP_UNOBSERVED_NOT_PROVEN_EMPTY")
        sections.append({
            "directory_node_id_candidate": node["id"], "parent_id_candidate": parents[node["id"]],
            "path": path, "directory_children_observed": len(directories),
            "question_node_count_observed": len(questions),
            "questions": question_observations, "status": status,
            "question_denominator": None, "page_range": None,
            "source_range_complete": False,
        })
        for child in directories:
            visit(child, path)

    visit(nodes[root_id], [])
    section_index = {row["directory_node_id_candidate"]: row for row in sections}
    require(reflection_id in section_index, "REFLECTION_DIRECTORY_MISSING")
    leaves = [row for row in sections if row["directory_children_observed"] == 0]
    prioritized = sorted(leaves, key=lambda row: row["directory_node_id_candidate"] != reflection_id)
    queue = [{
        "priority": index, "directory_node_id_candidate": row["directory_node_id_candidate"],
        "path": row["path"],
        "needs": ["CURRENT_DIRECTORY_MEMBERSHIP", "QUESTION_PAGE_RANGE_AND_ORIGINALS",
                  "ANSWER_PAGE_RANGE_AND_ORIGINALS", "PRINTED_TO_NODE_IDENTITY_EVIDENCE"],
    } for index, row in enumerate(prioritized, 1)]
    reflected = section_index[reflection_id]
    same_label = [q["directory_node_id_candidate"] for row in sections for q in row["questions"]
                  if q["visible_label"] == "9" and row["directory_node_id_candidate"] != reflection_id]
    return {
        "schema": "46007447-chapter-source-acquisition-ledger/1",
        "source_classification": "FIXED_PARSED_ARCHIVE_NOT_FRESH_COMPLETE_DIRECTORY",
        "book_id": BOOK, "chapter_root_id_candidate": root_id,
        "scope": "OBSERVED_SUBTREE_ONLY", "source_range_complete": False,
        "chapter_question_denominator": None, "chapter_page_denominator": None,
        "observed": {"directory_nodes": len(sections), "leaf_directories": len(leaves),
                     "question_nodes": sum(row["question_node_count_observed"] for row in sections),
                     "leaf_directories_without_observed_question_nodes": sum(
                         row["question_node_count_observed"] == 0 for row in leaves)},
        "sections": sections,
        "q9_reflection": {
            "directory_node_id_candidate": reflection_id, "path": reflected["path"],
            "question_id": None, "question_page": None,
            "status": "ANSWER_EVIDENCE_ONLY_QUESTION_SOURCE_NOT_BOUND",
            "other_directory_label_9_ids_rejected_as_substitutes": same_label,
        },
        "acquisition_queue": queue,
        "authentication_or_account_root_fields_exported": False,
        "canonical_ids_proven": False, "platform_use_allowed": False,
    }


def render(ledger):
    labels = {"OBSERVED_DIRECTORY_CONTAINER": "目录容器，子分支分别核查",
              "PARTIAL_QUESTION_NODES_OBSERVED": "仅见部分题节点，正文/范围未完整取得",
              "QUESTION_MEMBERSHIP_UNOBSERVED_NOT_PROVEN_EMPTY": "题成员未取得，不能判为空"}
    lines = ["# 第一章来源采集账本（归档观察）", "",
             "此表只列已观察目录；空children不等于空章节，22个节点不等于第一章题量。",
             "题页/答页范围和完整分母仍未知；先采反思分支，禁止拿其他分支同号9替代。", "",
             "|目录路径|已观察题节点|当前覆盖状态|", "|---|---:|---|"]
    for row in ledger["sections"]:
        path = " / ".join(row["path"]).replace("|", "\\|")
        lines.append(f"|{path}|{row['question_node_count_observed']}|{labels[row['status']]}|")
    return "\n".join(lines) + "\n"


def run(state_path, output):
    raw = Path(state_path).read_bytes()
    require(len(raw) == STATE_BYTES and hashlib.sha256(raw).hexdigest() == STATE_SHA256,
            "ARCHIVED_STATE_HASH_MISMATCH")
    state = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_json)
    ledger = build_ledger(state)
    ledger["source"] = {"bytes": len(raw), "sha256": STATE_SHA256}
    output = Path(output)
    require(not output.exists(), "OUTPUT_EXISTS")
    output.mkdir(parents=True)
    (output / "chapter-source-ledger.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (output / "chapter-source-ledger.md").write_text(render(ledger), encoding="utf-8", newline="\n")
    return ledger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archived-state", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    ledger = run(args.archived_state, args.out)
    print(json.dumps({"status": "PARTIAL_ACQUISITION_LEDGER_CREATED", "observed": ledger["observed"],
                      "chapter_question_denominator": None, "platform_use_allowed": False}))


if __name__ == "__main__":
    main()
