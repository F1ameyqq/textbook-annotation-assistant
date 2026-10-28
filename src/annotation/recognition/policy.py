"""Offline semantic candidates from the confirmed annotation requirements.

Platform shortcut mapping belongs to delivery; this module emits no actions.
Shared-material and visible-blank facts must come from evidence, not assumed
merely because a mathematical question has numbered subparts.
"""
import re


def classify(text, option_labels, answer=None, *, shared_material=False, visible_blank=False):
    if shared_material:
        return {"question_type": "combination", "option_role": "stem", "selection_mode": None}
    if option_labels:
        letters = re.sub(r"\s+", "", answer or "")
        multi = "多选" in text or bool(re.fullmatch(r"[A-G]{2,}", letters))
        seven = set(option_labels) == set("ABCDEFG") and (visible_blank or bool(re.search(r"_{2,}|（\s*）|\(\s*\)|□|\[\s*\]", text)))
        return {"question_type": "choice", "option_role": "option",
                "selection_mode": "multiple" if multi else "single" if re.fullmatch(r"[A-G]", letters) else "UNKNOWN",
                "seven_to_five_candidate": seven}
    blank = visible_blank or bool(re.search(r"_{2,}|（\s*）|\(\s*\)|□|\[\s*\]", text))
    return {"question_type": "fill_blank" if blank else "open_response", "option_role": None, "selection_mode": None}


def choice_answer_valid(value, labels):
    letters = re.sub(r"\s+", "", value)
    return bool(re.fullmatch(r"[A-G]+", letters)) and len(set(letters)) == len(letters) and set(letters) <= set(labels)


def option_set_valid(labels):
    # The confirmed scope uses A-D or A-G. Unknown pools require review rather
    # than manufacturing absent options or treating every set as A-D.
    return sorted(labels) in [list("ABCD"), list("ABCDEFG")]
