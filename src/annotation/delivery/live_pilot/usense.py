"""Narrow transport contract. Real text/upload/readback codec is deliberately closed."""
from typing import Protocol

from annotation.quality.live_pilot import PilotError, require


class Transport(Protocol):
    offline: bool
    def observe(self, phase: str): ...
    def send_once(self, payload): ...
    def close(self): ...


class UsenseTransport:
    """No browser/client is constructed and supplied labels never open real sending."""
    offline = False
    missing = ("CURRENT_JOINT_POLICY_PROOF", "CURRENT_COMPLETE_TARGET", "VERIFIED_TEXT_WIRE_CODEC",
               "VERIFIED_CONTENT_READBACK_CODEC", "CROP_UPLOAD_AND_W_ROLE_PROFILE",
               "NEW_EXACT_BUSINESS_MANIFEST", "EXCLUSIVE_SESSION_EVIDENCE")

    def __init__(self, session=None, wire_profile=None):
        self._session = session  # Kept opaque; never inspected, invoked, closed or logged.

    def observe(self, phase):
        raise PilotError("LIVE_READBACK_CODEC_UNAVAILABLE")

    def build_commit(self, *args, **kwargs):
        raise PilotError("LIVE_TEXT_WIRE_UNVERIFIED")

    def send_once(self, payload):
        raise PilotError("LIVE_TEXT_WIRE_UNVERIFIED")

    def close(self):
        return {"released": True, "session_created": False, "platform_calls": 0}


def build_offline_command(plan):
    require(plan["mode"] == "OFFLINE", "OFFLINE_ONLY")
    return {"namespace": "A11_SYNTHETIC_OFFLINE_ONLY", "operation": "CREATE_FRAMES",
            "book_id": "46007447", "question_id": plan["action"]["target"]["question_id"],
            "directory_id": plan["action"]["expected_after"]["directory_id"],
            "insert_after_order": plan["insert_after_order"], "frames": plan["frames"],
            "approved_parts": plan["approved_parts"], "deletes": [], "uploads": [],
            "submit": False, "ocr": False}


def validate_offline_command(command):
    require(set(command) == {"namespace", "operation", "book_id", "question_id", "directory_id",
        "insert_after_order", "frames", "approved_parts", "deletes", "uploads", "submit", "ocr"},
        "UNAUTHORIZED_PAYLOAD_FIELD")
    require(command["namespace"] == "A11_SYNTHETIC_OFFLINE_ONLY" and command["book_id"] == "46007447"
            and command["operation"] == "CREATE_FRAMES" and command["deletes"] == [] and
            command["uploads"] == [] and command["submit"] is False and command["ocr"] is False,
            "FORBIDDEN_OPERATION")


def parse_business_receipt(value, *, offline):
    require(offline, "LIVE_RECEIPT_CODEC_UNAVAILABLE")
    require(isinstance(value, dict) and value.get("namespace") == "A11_SYNTHETIC_OFFLINE_ONLY" and
            value.get("business_code") == 0 and value.get("operation") == "inserted" and
            value.get("platform_question_id") and value.get("append_at_global_end") is True,
            "BUSINESS_RECEIPT_UNKNOWN")
    return value["platform_question_id"]


def decode_a05_history(value):
    """Historical whitelist decoder only; never returns content VERIFIED or live eligibility."""
    return {"historical_only": True, "frame_business_success": value.get("code") == 0,
            "content_status": "CONTENT_PENDING", "text_persistence_proved": False,
            "live_eligible": False, "submission_status": "NOT_SUBMITTED"}
