# ============================================================
#  Firebase Client — Firestore 저장/조회
# ============================================================

import os
import json
import datetime
import firebase_admin
from firebase_admin import credentials, firestore

_db = None


def get_db():
    global _db
    if _db is not None:
        return _db

    # GitHub Actions Secret에서 Firebase 키 로드
    key_json = os.environ.get("FIREBASE_KEY")
    if not key_json:
        raise RuntimeError("FIREBASE_KEY 환경변수가 없습니다.")

    key_dict = json.loads(key_json)
    if not firebase_admin._apps:
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    return _db


def now_kst() -> str:
    """현재 시각 KST 문자열"""
    utc = datetime.datetime.utcnow()
    kst = utc + datetime.timedelta(hours=9)
    return kst.strftime("%Y-%m-%d %H:%M KST")


def today_str() -> str:
    utc = datetime.datetime.utcnow()
    kst = utc + datetime.timedelta(hours=9)
    return kst.strftime("%Y-%m-%d")


# ── Candidate 저장 ────────────────────────────────────────────
def save_candidate(ticker: str, result: dict, prev_doc: dict | None):
    """
    Candidate 상태를 Firestore에 저장
    신규 등록 / 유지 / 소멸 처리 포함
    """
    db = get_db()
    ref = db.collection("candidates").document(ticker)
    now = firestore.SERVER_TIMESTAMP

    is_candidate = result["is_candidate"]
    s1_signal    = result["s1_signal"]

    # ── S1 신호 발생 ─────────────────────────────────────────
    if s1_signal:
        data = {
            "ticker":        ticker,
            "status":        "S1_FIRED",
            "vpf":           result["vpf"],
            "vpf_slope":     result["vpf_slope"],
            "close":         result["close"],
            "cancel_reason": None,
            "confidence":    "reserved",
            "updated_at":    now,
        }
        ref.set(data, merge=True)

        # History 기록
        _save_history(ticker, "S1_FIRED",
                      prev_doc.get("days_active", 0) if prev_doc else 0,
                      result["vpf"])
        return "S1_FIRED"

    # ── 신규 Candidate 등록 ──────────────────────────────────
    if is_candidate:
        prev_status = prev_doc.get("status") if prev_doc else None
        if prev_status not in ("ACTIVE",):
            # 새로 등록
            data = {
                "ticker":        ticker,
                "status":        "ACTIVE",
                "created_at":    now,
                "days_active":   1,
                "vpf":           result["vpf"],
                "vpf_slope":     result["vpf_slope"],
                "close":         result["close"],
                "cancel_reason": None,
                "confidence":    "reserved",
                "updated_at":    now,
            }
            ref.set(data)
            return "NEW"
        else:
            # 유지 — 경과일 증가
            prev_days = prev_doc.get("days_active", 0)
            new_days  = prev_days + 1

            # 유효기간 초과 체크 (20봉)
            if new_days > 20:
                _expire_candidate(ref, ticker, result, prev_days)
                return "EXPIRED"

            ref.update({
                "days_active": new_days,
                "vpf":         result["vpf"],
                "vpf_slope":   result["vpf_slope"],
                "close":       result["close"],
                "updated_at":  now,
            })
            return "ACTIVE"

    # ── Candidate 소멸 ───────────────────────────────────────
    else:
        prev_status = prev_doc.get("status") if prev_doc else None
        if prev_status == "ACTIVE":
            days = prev_doc.get("days_active", 0)
            reason = result.get("cancel_reason", "UNKNOWN")
            _expire_candidate(ref, ticker, result, days, reason=reason)
            return "CANCELLED"

        # 원래 없던 종목 → NONE 상태 유지
        ref.set({
            "ticker":     ticker,
            "status":     "NONE",
            "updated_at": now,
        }, merge=True)
        return "NONE"


def _expire_candidate(ref, ticker, result, days_active, reason="EXPIRED"):
    now = firestore.SERVER_TIMESTAMP
    ref.update({
        "status":        reason,
        "cancel_reason": reason,
        "days_active":   days_active,
        "updated_at":    now,
    })
    _save_history(ticker, reason, days_active,
                  result.get("vpf") or 0)


def _save_history(ticker: str, outcome: str,
                  lifetime_bars: int, vpf_at_create: float):
    db = get_db()
    db.collection("history").add({
        "ticker":        ticker,
        "outcome":       outcome,
        "lifetime_bars": lifetime_bars,
        "vpf_at_create": vpf_at_create,
        "closed_at":     firestore.SERVER_TIMESTAMP,
    })


# ── 기존 Candidate 조회 ──────────────────────────────────────
def get_existing_candidate(ticker: str) -> dict | None:
    db = get_db()
    doc = db.collection("candidates").document(ticker).get()
    return doc.to_dict() if doc.exists else None


# ── 스캔 로그 저장 ───────────────────────────────────────────
def save_scan_log(total: int, candidates: int, errors: list):
    db = get_db()
    db.collection("scan_log").document(today_str()).set({
        "scanned_at":       firestore.SERVER_TIMESTAMP,
        "scanned_at_kst":   now_kst(),
        "tickers_scanned":  total,
        "candidates_found": candidates,
        "errors":           errors,
    })
