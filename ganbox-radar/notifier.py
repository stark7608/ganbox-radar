# ============================================================
#  Notifier v2.0 — FCM 푸시 전용
# ============================================================

from firebase_admin import messaging
from firebase_client import get_all_tokens, remove_invalid_token


def _send(title: str, body: str, data: dict = {},
          admin_only: bool = False):
    tokens = get_all_tokens()
    if not tokens:
        print("  FCM 토큰 없음"); return

    # admin_only: Firebase에서 admin 필드로 필터링
    # 현재는 전체 발송 (추후 admin 필드 추가 시 분기)

    try:
        msg = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in data.items()},
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    color="#1a1a2a", sound="default",
                    channel_id="ganbox_radar"
                ),
            ),
            tokens=tokens,
        )
        resp = messaging.send_each_for_multicast(msg)
        print(f"  📱 FCM: 성공 {resp.success_count} / 실패 {resp.failure_count}")

        # 실패 토큰 자동 삭제 (좀비 토큰 정리)
        for i, r in enumerate(resp.responses):
            if not r.success and i < len(tokens):
                err = str(r.exception)
                if "registration-token-not-registered" in err or \
                   "invalid-registration-token" in err:
                    remove_invalid_token(tokens[i])
                    print(f"  🗑  좀비 토큰 삭제: {tokens[i][:20]}...")
    except Exception as e:
        print(f"  FCM 실패: {e}")


def notify_s1(ticker: str, vpf: float, close: float, name: str):
    _send(
        f"S1 신호 — {ticker}",
        f"{name} · VPF {vpf:.2f} · ${close:.2f}",
        {"type": "S1", "ticker": ticker},
    )

def notify_s3(ticker: str, vpf: float, close: float, name: str):
    _send(
        f"S3 신호 — {ticker}",
        f"{name} · VPF {vpf:.2f} · ${close:.2f}",
        {"type": "S3", "ticker": ticker},
    )

def notify_candidate_new(ticker: str, vpf: float, close: float,
                         name: str, stage: str):
    labels = {"CANDIDATE": "Candidate 등록",
              "WATCH": "Watch 진입", "WARMING": "Warming 진입"}
    _send(
        f"{labels.get(stage, stage)} — {ticker}",
        f"{name} · VPF {vpf:.2f} · ${close:.2f}",
        {"type": stage, "ticker": ticker},
    )

def notify_tp_hit(ticker: str, tp_price: float,
                  current: float, user_token: str = None):
    """TP 도달 알림 — 해당 사용자에게만"""
    _send_to_user(
        f"TP 도달 — {ticker}",
        f"목표가 ${tp_price:.2f} 도달 · 현재가 ${current:.2f}",
        {"type": "TP_HIT", "ticker": ticker},
        user_token,
    )

def notify_sl_hit(ticker: str, sl_price: float,
                  current: float, user_token: str = None):
    """SL 도달 알림 — 해당 사용자에게만"""
    _send_to_user(
        f"SL 도달 — {ticker}",
        f"손절가 ${sl_price:.2f} 도달 · 현재가 ${current:.2f}",
        {"type": "SL_HIT", "ticker": ticker},
        user_token,
    )

def _send_to_user(title: str, body: str, data: dict, token: str | None):
    if not token:
        _send(title, body, data); return
    try:
        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in data.items()},
            android=messaging.AndroidConfig(priority="high"),
            token=token,
        )
        messaging.send(msg)
        print(f"  📱 FCM(개인): {title}")
    except Exception as e:
        print(f"  FCM 개인 발송 실패: {e}")

def notify_scan_failed(errors: list, admin_token: str = None):
    """스캔 실패 알림 — 관리자에게만"""
    body = f"실패 종목: {', '.join(errors[:5])}"
    if len(errors) > 5:
        body += f" 외 {len(errors)-5}건"
    _send_to_user(
        f"스캔 실패 {len(errors)}건",
        body,
        {"type": "SCAN_FAILED"},
        admin_token,
    )

def notify_daily_summary(s1: list, s3: list,
                         candidates: list, total: int):
    if not s1 and not s3 and not candidates: return
    parts = []
    if s1:  parts.append(f"S1: {','.join(s1)}")
    if s3:  parts.append(f"S3: {','.join(s3)}")
    cnt = len(candidates)
    if cnt: parts.append(f"후보 {cnt}건")
    _send(
        f"스캔 완료 — {total}종목",
        " · ".join(parts),
        {"type": "DAILY_SUMMARY"},
    )
