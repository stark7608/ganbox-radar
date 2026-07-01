#!/usr/bin/env python3
# ============================================================
#  GAN BOX Radar — 메인 스캐너
#  GitHub Actions에서 매일 자동 실행
#  실행: python scanner.py
# ============================================================

import time
import yfinance as yf

from config import TICKER_CONFIG
from ganbox_engine import detect_candidate
from firebase_client import (
    get_existing_candidate, save_candidate,
    save_scan_log
)
from notifier import (
    notify_new_candidate, notify_s1_fired,
    notify_expired, notify_daily_summary
)


def run_scan():
    print("=" * 56)
    print("  🛰  GAN BOX Radar — 스캔 시작")
    print("=" * 56)

    total         = 0
    candidate_cnt = 0
    errors        = []

    # 요약용 리스트
    today_candidates = []
    today_s1         = []

    for ticker, cfg in TICKER_CONFIG.items():
        total += 1
        print(f"\n  [{total:02d}/{len(TICKER_CONFIG)}] {ticker} ({cfg['name']}) 분석 중...")

        try:
            # ── 시세 다운로드 ──────────────────────────────
            df = yf.download(ticker, period="3y", progress=False, auto_adjust=True)
            if df is None or len(df) < 500:
                raise ValueError(f"데이터 부족: {len(df) if df is not None else 0}봉")

            df.columns = [c.lower() for c in df.columns]

            # ── GAN BOX Engine 실행 ────────────────────────
            result = detect_candidate(df, cfg)

            # ── 기존 Candidate 상태 조회 ───────────────────
            prev_doc = get_existing_candidate(ticker)

            # ── Firebase 저장 ──────────────────────────────
            event = save_candidate(ticker, result, prev_doc)

            # ── 이벤트 처리 & 알림 ─────────────────────────
            if event == "S1_FIRED":
                print(f"       🚨 S1 신호 발생! VPF={result['vpf']:.3f}")
                notify_s1_fired(ticker, result['vpf'], result['close'],
                                cfg['tier'], cfg['name'])
                today_s1.append({
                    "ticker": ticker, "vpf": result['vpf'],
                    "close": result['close']
                })
                candidate_cnt += 1

            elif event == "NEW":
                print(f"       🟢 Candidate 신규 등록 VPF={result['vpf']:.3f}")
                notify_new_candidate(ticker, result['vpf'], result['vpf_slope'],
                                     result['close'], cfg['tier'], cfg['name'])
                today_candidates.append({
                    "ticker": ticker, "vpf": result['vpf'],
                    "close": result['close'], "days": 1
                })
                candidate_cnt += 1

            elif event == "ACTIVE":
                days = (prev_doc.get("days_active", 0) + 1) if prev_doc else 1
                print(f"       🔵 Candidate 유지 중 ({days}봉) VPF={result['vpf']:.3f}")
                today_candidates.append({
                    "ticker": ticker, "vpf": result['vpf'],
                    "close": result['close'], "days": days
                })
                candidate_cnt += 1

            elif event == "CANCELLED":
                reason = result.get("cancel_reason", "UNKNOWN")
                days   = prev_doc.get("days_active", 0) if prev_doc else 0
                print(f"       🔴 Candidate 소멸 ({reason}, {days}봉)")
                notify_expired(ticker, days, reason)

            elif event == "EXPIRED":
                days = prev_doc.get("days_active", 0) if prev_doc else 20
                print(f"       ⏱  유효기간 초과 ({days}봉)")
                notify_expired(ticker, days, "EXPIRED")

            else:
                print(f"       ⚪ 해당 없음 (VPF={result.get('vpf', 'N/A')})")

        except Exception as e:
            print(f"       ❌ 오류 발생: {e}")
            errors.append(ticker)

        # Rate Limit 방지
        time.sleep(0.5)

    # ── 스캔 로그 저장 ──────────────────────────────────────
    save_scan_log(total, candidate_cnt, errors)

    # ── 일일 요약 이메일 ────────────────────────────────────
    notify_daily_summary(today_candidates, today_s1, total, errors)

    # ── 결과 출력 ───────────────────────────────────────────
    print("\n" + "=" * 56)
    print(f"  ✅  스캔 완료")
    print(f"      총 {total}종목 | Candidate {candidate_cnt}건 | 오류 {len(errors)}건")
    if errors:
        print(f"      오류 종목: {', '.join(errors)}")
    print("=" * 56)


if __name__ == "__main__":
    run_scan()
