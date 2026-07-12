# ============================================================
#  Firebase Client v2.0
# ============================================================

import os, json, datetime
import firebase_admin
from firebase_admin import credentials, firestore

_db = None

def get_db():
    global _db
    if _db: return _db
    key_json = os.environ.get("FIREBASE_KEY")
    if not key_json:
        raise RuntimeError("FIREBASE_KEY 환경변수 없음")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(json.loads(key_json)))
    _db = firestore.client()
    return _db

def now_kst():
    kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    return kst.strftime("%Y-%m-%d %H:%M KST")

def today_str():
    kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    return kst.strftime("%Y-%m-%d")

def month_str():
    kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    return kst.strftime("%Y-%m")

# ── Candidate 저장 ────────────────────────────────────────
def save_candidate(ticker: str, result: dict, prev_doc: dict | None) -> str:
    db  = get_db()
    ref = db.collection("candidates").document(ticker)
    now = firestore.SERVER_TIMESTAMP
    stype = result["signal_type"]

    # S1 / S3 신호 발생
    if stype in ("S1", "S3"):
        ref.set({
            "ticker":       ticker,
            "status":       stype,
            "signal_type":  stype,
            "vpf":          result["vpf"],
            "vpf_slope":    result["vpf_slope"],
            "close":        result["close"],
            "cancel_reason": None,
            "confidence":   "reserved",
            "updated_at":   now,
        }, merge=True)
        _save_history(ticker, stype,
                      prev_doc.get("days_active", 0) if prev_doc else 0,
                      result["vpf"])
        return stype

    # Candidate / Watch / Warming
    if stype in ("CANDIDATE", "WATCH", "WARMING"):
        prev_status = prev_doc.get("status") if prev_doc else None
        if prev_status not in ("CANDIDATE", "WATCH", "WARMING"):
            ref.set({
                "ticker":       ticker,
                "status":       stype,
                "signal_type":  stype,
                "created_at":   now,
                "days_active":  1,
                "vpf":          result["vpf"],
                "vpf_slope":    result["vpf_slope"],
                "close":        result["close"],
                "cancel_reason": None,
                "confidence":   "reserved",
                "updated_at":   now,
            })
            return "NEW_" + stype
        else:
            prev_days = prev_doc.get("days_active", 0)
            new_days  = prev_days + 1
            if new_days > 20 and stype == "CANDIDATE":
                _expire(ref, ticker, result, prev_days)
                return "EXPIRED"
            ref.update({
                "status":       stype,
                "signal_type":  stype,
                "days_active":  new_days,
                "vpf":          result["vpf"],
                "vpf_slope":    result["vpf_slope"],
                "close":        result["close"],
                "updated_at":   now,
            })
            return stype

    # NONE — 기존 Candidate 소멸 처리
    prev_status = prev_doc.get("status") if prev_doc else None
    if prev_status in ("CANDIDATE", "WATCH", "WARMING"):
        days   = prev_doc.get("days_active", 0)
        reason = result.get("cancel_reason", "UNKNOWN")
        _expire(ref, ticker, result, days, reason)
        return "CANCELLED"
    ref.set({"ticker": ticker, "status": "NONE",
             "updated_at": now}, merge=True)
    return "NONE"


def _expire(ref, ticker, result, days, reason="EXPIRED"):
    ref.update({"status": reason, "cancel_reason": reason,
                "days_active": days,
                "updated_at": firestore.SERVER_TIMESTAMP})
    _save_history(ticker, reason, days, result.get("vpf") or 0)


def _save_history(ticker, outcome, lifetime_bars, vpf_at_create):
    db = get_db()
    db.collection("history").add({
        "ticker":        ticker,
        "outcome":       outcome,
        "lifetime_bars": lifetime_bars,
        "vpf_at_create": vpf_at_create,
        "closed_at":     firestore.SERVER_TIMESTAMP,
    })


def get_existing_candidate(ticker: str) -> dict | None:
    db  = get_db()
    doc = db.collection("candidates").document(ticker).get()
    return doc.to_dict() if doc.exists else None


# ── TP/SL 포지션 체크 ─────────────────────────────────────
def get_active_positions() -> list[dict]:
    """모든 사용자의 ACTIVE 포지션 조회"""
    db   = get_db()
    docs = db.collection_group("positions").where(
        "status", "==", "ACTIVE"
    ).stream()
    return [{"id": d.id, "ref": d.reference, **d.to_dict()} for d in docs]


def close_position(ref, status: str):
    ref.update({"status": status,
                "closed_at": firestore.SERVER_TIMESTAMP})


# ── FCM 토큰 관리 ─────────────────────────────────────────
def get_all_tokens() -> list[str]:
    db   = get_db()
    docs = db.collection("fcm_tokens").stream()
    return [d.to_dict().get("token") for d in docs if d.to_dict().get("token")]


def remove_invalid_token(token: str):
    db = get_db()
    docs = db.collection("fcm_tokens").where("token", "==", token).stream()
    for d in docs:
        d.reference.delete()


# ── 이력 30일 자동 삭제 ───────────────────────────────────
def cleanup_old_history():
    db      = get_db()
    cutoff  = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    docs    = db.collection("history").where(
        "closed_at", "<", cutoff
    ).stream()
    deleted = 0
    for d in docs:
        d.reference.delete()
        deleted += 1
    if deleted:
        print(f"  🗑  이력 {deleted}건 삭제 (30일 초과)")


# ── 사용량 추적 ───────────────────────────────────────────
def record_usage(reads: int, writes: int):
    """scan_log에 사용량 누적 기록"""
    db      = get_db()
    today   = today_str()
    month   = month_str()
    ref     = db.collection("scan_log").document(today)

    try:
        doc = ref.get()
        prev = doc.to_dict() if doc.exists else {}
    except Exception:
        prev = {}

    prev_reads  = prev.get("reads_today", 0)
    prev_writes = prev.get("writes_today", 0)

    # 월 누적은 이번 달 전체 합산
    month_ref  = db.collection("usage_monthly").document(month)
    try:
        m_doc  = month_ref.get()
        m_prev = m_doc.to_dict() if m_doc.exists else {}
    except Exception:
        m_prev = {}

    ref.set({
        "reads_today":  prev_reads  + reads,
        "writes_today": prev_writes + writes,
        "updated_at":   now_kst(),
    }, merge=True)

    month_ref.set({
        "reads_month":  m_prev.get("reads_month",  0) + reads,
        "writes_month": m_prev.get("writes_month", 0) + writes,
        "updated_at":   now_kst(),
    }, merge=True)


# ── 스캔 로그 저장 ────────────────────────────────────────
def save_scan_log(total: int, results: dict, errors: list,
                  reads_est: int, writes_est: int):
    db  = get_db()
    today = today_str()

    s1_count   = sum(1 for v in results.values() if v in ("S1",))
    s3_count   = sum(1 for v in results.values() if v in ("S3",))
    cand_count = sum(1 for v in results.values()
                     if v in ("CANDIDATE","NEW_CANDIDATE"))

    db.collection("scan_log").document(today).set({
        "scanned_at":       firestore.SERVER_TIMESTAMP,
        "scanned_at_kst":   now_kst(),
        "tickers_scanned":  total,
        "s1_count":         s1_count,
        "s3_count":         s3_count,
        "candidate_count":  cand_count,
        "errors":           errors,
        "status":           "FAILED" if len(errors) == total
                            else "PARTIAL" if errors else "SUCCESS",
        "reads_today_est":  reads_est,
        "writes_today_est": writes_est,
    }, merge=True)

    record_usage(reads_est, writes_est)


# ── 초대 코드 검증 ────────────────────────────────────────
def verify_invite_code(code: str, user_id: str) -> bool:
    db  = get_db()
    ref = db.collection("valid_codes").document(code)
    doc = ref.get()
    if not doc.exists:
        return False
    data = doc.to_dict()
    if not data.get("is_active", False):
        return False
    used_by = data.get("used_by", [])
    max_uses = data.get("max_uses", 10)
    if len(used_by) >= max_uses and user_id not in used_by:
        return False
    if user_id not in used_by:
        ref.update({"used_by": firestore.ArrayUnion([user_id])})
    return True
