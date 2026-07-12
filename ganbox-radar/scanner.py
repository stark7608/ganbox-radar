#!/usr/bin/env python3
# ============================================================
#  GAN BOX Radar Scanner v2.0
#  매일 07:00 / 19:00 KST 자동 실행
# ============================================================

import time
import datetime
import yfinance as yf
import pandas_market_calendars as mcal

from config import TICKER_CONFIG, SETTINGS
from ganbox_engine import detect_signals
from firebase_client import (
    get_db, get_existing_candidate, save_candidate,
    save_scan_log, cleanup_old_history,
    get_active_positions, close_position, get_all_tokens,
)
from notifier import (
    notify_s1, notify_s3, notify_candidate_new,
    notify_tp_hit, notify_sl_hit,
    notify_scan_failed, notify_daily_summary,
)


def is_market_day() -> bool:
    """오늘이 NYSE 거래일인지 확인"""
    nyse  = mcal.get_calendar("NYSE")
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    sched = nyse.schedule(start_date=today, end_date=today)
    return not sched.empty


def get_scan_tickers() -> list[str]:
    """기본 24종목 + 사용자 추가 종목 합산 (최대 추가 10개)"""
    base = list(TICKER_CONFIG.keys())
    try:
        db   = get_db()
        docs = db.collection("user_watchlist").stream()
        extra = set()
        for d in docs:
            ticker = d.id.split("__")[-1] if "__" in d.id else d.id
            ticker = ticker.upper()
            if ticker not in base:
                extra.add(ticker)
        # 추가 스캔 한도
        extra_limited = list(extra)[:SETTINGS["max_extra_scan"]]
        return base + extra_limited
    except Exception as e:
        print(f"  watchlist 조회 실패: {e}")
        return base


def check_tp_sl(tickers_data: dict):
    """포지션 TP/SL 도달 체크"""
    positions = get_active_positions()
    if not positions:
        return

    for pos in positions:
        ticker     = pos.get("ticker", "")
        entry      = pos.get("entry_price", 0)
        tp         = pos.get("tp_price")
        sl         = pos.get("sl_price")
        user_token = pos.get("fcm_token")
        current    = tickers_data.get(ticker)

        if current is None or not tp or not sl:
            continue

        if current >= tp:
            close_position(pos["ref"], "TP_HIT")
            notify_tp_hit(ticker, tp, current, user_token)
            print(f"  🎯 {ticker} TP 도달 ${current:.2f}")

        elif current <= sl:
            close_position(pos["ref"], "SL_HIT")
            notify_sl_hit(ticker, sl, current, user_token)
            print(f"  🛑 {ticker} SL 도달 ${current:.2f}")


def run_scan():
    print("=" * 56)
    print(f"  🛰  GAN BOX Radar v2.0 — {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 56)

    # 휴장일 체크
    if not is_market_day():
        print("  📅 NYSE 휴장일 — 스캔 스킵")
        return

    tickers      = get_scan_tickers()
    total        = len(tickers)
    errors       = []
    results      = {}
    current_prices = {}

    s1_list = []; s3_list = []; cand_list = []
    reads_est  = 0
    writes_est = 0

    print(f"  대상 종목: {total}개\n")

    for i, ticker in enumerate(tickers, 1):
        cfg = TICKER_CONFIG.get(ticker, {
            "swing_pct": 10, "min_baseline": 5,
            "tier": 3, "name": ticker
        })
        print(f"  [{i:02d}/{total}] {ticker} ({cfg['name']}) ...")

        try:
            df = yf.download(ticker, period="3y",
                             progress=False, auto_adjust=True)
            if df is None or len(df) < 500:
                raise ValueError(f"데이터 부족: {len(df) if df is not None else 0}봉")

            df.columns = [c.lower() for c in df.columns]
            result = detect_signals(df, cfg)
            current_prices[ticker] = result["close"]

            prev_doc = get_existing_candidate(ticker)
            reads_est += 1

            event = save_candidate(ticker, result, prev_doc)
            writes_est += 1
            results[ticker] = event

            stype = result["signal_type"]
            name  = cfg["name"]

            if stype == "S1":
                s1_list.append(ticker)
                notify_s1(ticker, result["vpf"], result["close"], name)
                print(f"       ✅ S1 신호! VPF={result['vpf']:.3f}")

            elif stype == "S3":
                s3_list.append(ticker)
                notify_s3(ticker, result["vpf"], result["close"], name)
                print(f"       ✅ S3 신호! VPF={result['vpf']:.3f}")

            elif event.startswith("NEW_"):
                stage = event.replace("NEW_", "")
                cand_list.append(ticker)
                notify_candidate_new(ticker, result["vpf"],
                                     result["close"], name, stage)
                print(f"       🟢 {stage} 신규 등록 VPF={result['vpf']:.3f}")

            elif event in ("CANDIDATE", "WATCH", "WARMING"):
                cand_list.append(ticker)
                days = (prev_doc.get("days_active", 0) + 1) if prev_doc else 1
                print(f"       🔵 {event} 유지 ({days}봉)")

            elif event == "CANCELLED":
                print(f"       🔴 소멸 ({result.get('cancel_reason')})")

            else:
                print(f"       ⚪ 이상 없음 (VPF={result.get('vpf', 'N/A')})")

        except Exception as e:
            print(f"       ❌ 오류: {e}")
            errors.append(ticker)

        time.sleep(SETTINGS["yfinance_delay_sec"])

    # TP/SL 체크
    print("\n  TP/SL 포지션 체크...")
    check_tp_sl(current_prices)
    reads_est += 10  # positions 읽기 추정

    # 이력 30일 정리
    cleanup_old_history()
    writes_est += 5

    # 스캔 로그 저장
    save_scan_log(total, results, errors, reads_est, writes_est)
    writes_est += 2

    # 일일 요약 발송
    notify_daily_summary(s1_list, s3_list, cand_list, total)

    # 스캔 실패 알림
    if errors:
        notify_scan_failed(errors)

    print(f"\n{'=' * 56}")
    print(f"  ✅ 완료: {total}종목 | S1 {len(s1_list)} | S3 {len(s3_list)}"
          f" | 후보 {len(cand_list)} | 오류 {len(errors)}")
    print(f"  예상 사용량 — 읽기 {reads_est}건 / 쓰기 {writes_est}건")
    print("=" * 56)


if __name__ == "__main__":
    run_scan()
