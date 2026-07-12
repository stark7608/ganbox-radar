# ============================================================
#  GAN BOX Radar — 설정 파일 v2.0
#  ADMIN_PIN은 GitHub Secret으로 관리 (이 파일에 절대 입력 금지)
# ============================================================

import os

# ── 종목 설정 ──────────────────────────────────────────────
TICKER_CONFIG = {
    # Tier 1: 레버리지 3배 ETF
    "TQQQ": {"swing_pct": 12, "min_baseline": 5, "tier": 1, "name": "나스닥100 3배"},
    "TECL": {"swing_pct": 12, "min_baseline": 5, "tier": 1, "name": "테크 3배"},
    "SOXL": {"swing_pct": 12, "min_baseline": 3, "tier": 1, "name": "반도체 3배"},
    "SPXL": {"swing_pct": 12, "min_baseline": 5, "tier": 1, "name": "S&P500 3배"},
    "UPRO": {"swing_pct": 12, "min_baseline": 5, "tier": 1, "name": "S&P500 3배(PS)"},
    "LABU": {"swing_pct": 15, "min_baseline": 3, "tier": 1, "name": "바이오 3배"},
    "CURE": {"swing_pct": 12, "min_baseline": 3, "tier": 1, "name": "헬스케어 3배"},
    "FAS":  {"swing_pct": 12, "min_baseline": 3, "tier": 1, "name": "금융 3배"},
    "TNA":  {"swing_pct": 12, "min_baseline": 3, "tier": 1, "name": "소형주 3배"},
    "DFEN": {"swing_pct": 12, "min_baseline": 3, "tier": 1, "name": "방산 3배"},
    # Tier 2: 대형주
    "NVDA": {"swing_pct": 10, "min_baseline": 5, "tier": 2, "name": "엔비디아"},
    "AMD":  {"swing_pct": 10, "min_baseline": 5, "tier": 2, "name": "AMD"},
    "MSFT": {"swing_pct":  8, "min_baseline": 5, "tier": 2, "name": "마이크로소프트"},
    "META": {"swing_pct": 10, "min_baseline": 5, "tier": 2, "name": "메타"},
    "AMZN": {"swing_pct": 10, "min_baseline": 5, "tier": 2, "name": "아마존"},
    "GOOGL":{"swing_pct":  8, "min_baseline": 5, "tier": 2, "name": "알파벳"},
    "TSLA": {"swing_pct": 12, "min_baseline": 5, "tier": 2, "name": "테슬라"},
    "AAPL": {"swing_pct":  8, "min_baseline": 5, "tier": 2, "name": "애플"},
    # Tier 3: 섹터 ETF + 2배
    "QLD":  {"swing_pct":  8, "min_baseline": 5, "tier": 3, "name": "나스닥 2배"},
    "SSO":  {"swing_pct":  8, "min_baseline": 5, "tier": 3, "name": "S&P500 2배"},
    "SMH":  {"swing_pct":  8, "min_baseline": 5, "tier": 3, "name": "반도체 ETF"},
    "XLK":  {"swing_pct":  8, "min_baseline": 5, "tier": 3, "name": "테크 ETF"},
    "XAR":  {"swing_pct":  8, "min_baseline": 5, "tier": 3, "name": "방산 ETF"},
    "CIBR": {"swing_pct":  8, "min_baseline": 5, "tier": 3, "name": "사이버보안 ETF"},
}

# ── Candidate 운영 규칙 ────────────────────────────────────
CANDIDATE_RULES = {
    "max_lifetime_bars":      20,    # 유효기간 (봉)
    "vpf_zone_a":           -1.0,    # S1 Candidate 기준
    "vpf_zone_b_upper":      0.0,    # S3 Candidate 기준
    "vpf_watch_lower":      -0.5,    # Watch 단계 하한
    "vpf_warming_lower":     0.0,    # Warming 단계 (DN-BOX + VPF < 0)
}

# ── 운영 설정 ──────────────────────────────────────────────
SETTINGS = {
    "history_days":           30,    # 이력 보관 기간
    "read_warn_pct":        0.85,    # Firebase 읽기 경고 %
    "write_warn_pct":       0.85,    # Firebase 쓰기 경고 %
    "read_stop_pct":        0.95,    # Firebase 읽기 중지 %
    "write_stop_pct":       0.95,    # Firebase 쓰기 중지 %
    "firebase_daily_reads":  50000,  # Firestore 무료 읽기 한도/일
    "firebase_daily_writes": 20000,  # Firestore 무료 쓰기 한도/일
    "firebase_monthly_hosting": 10,  # Hosting 무료 GB/월
    "yfinance_delay_sec":    0.8,    # Rate Limit 방지 딜레이
    "max_watchlist_per_user": 30,    # 인당 관심종목 최대
    "max_extra_scan":         10,    # 기본 24종목 외 추가 스캔 한도
    "tradingview_interval":   "D",   # TradingView 기본 타임프레임
}

# ── 인증 ───────────────────────────────────────────────────
ADMIN_PIN_HASH = os.environ.get("ADMIN_PIN_HASH", "")
# PIN은 GitHub Secret(ADMIN_PIN_HASH)에서만 읽음
# 설정 방법: echo -n "your_pin" | sha256sum → 결과값을 Secret에 등록
