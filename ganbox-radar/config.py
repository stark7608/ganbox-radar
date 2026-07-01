# ============================================================
#  GAN BOX Radar — 종목 설정 파일
#  새 종목 추가: TICKER_CONFIG에 항목 추가 후 커밋
# ============================================================

# ── 종목별 파라미터 ──────────────────────────────────────────
# swing_pct    : GAN BOX FSM Swing % (종목 변동성에 따라 조정)
# min_baseline : FAN Score 최소 Baseline 봉수 (변동성 큰 종목 = 3)
# tier         : 1=레버리지3배 / 2=대형주 / 3=섹터+2배

TICKER_CONFIG = {
    # ── Tier 1: 레버리지 3배 ETF ────────────────────────────
    "TQQQ": {"swing_pct": 12, "min_baseline": 5, "tier": 1, "name": "나스닥100 3배"},
    "TECL": {"swing_pct": 12, "min_baseline": 5, "tier": 1, "name": "테크 3배"},
    "SOXL": {"swing_pct": 12, "min_baseline": 3, "tier": 1, "name": "반도체 3배"},
    "SPXL": {"swing_pct": 12, "min_baseline": 5, "tier": 1, "name": "S&P500 3배"},
    "UPRO": {"swing_pct": 12, "min_baseline": 5, "tier": 1, "name": "S&P500 3배(ProShares)"},
    "LABU": {"swing_pct": 15, "min_baseline": 3, "tier": 1, "name": "바이오 3배"},
    "CURE": {"swing_pct": 12, "min_baseline": 3, "tier": 1, "name": "헬스케어 3배"},
    "FAS":  {"swing_pct": 12, "min_baseline": 3, "tier": 1, "name": "금융 3배"},
    "TNA":  {"swing_pct": 12, "min_baseline": 3, "tier": 1, "name": "소형주 3배"},
    "DFEN": {"swing_pct": 12, "min_baseline": 3, "tier": 1, "name": "방산 3배"},
    # ── Tier 2: 나스닥 대형주 ───────────────────────────────
    "NVDA": {"swing_pct": 10, "min_baseline": 5, "tier": 2, "name": "엔비디아"},
    "AMD":  {"swing_pct": 10, "min_baseline": 5, "tier": 2, "name": "AMD"},
    "MSFT": {"swing_pct":  8, "min_baseline": 5, "tier": 2, "name": "마이크로소프트"},
    "META": {"swing_pct": 10, "min_baseline": 5, "tier": 2, "name": "메타"},
    "AMZN": {"swing_pct": 10, "min_baseline": 5, "tier": 2, "name": "아마존"},
    "GOOGL":{"swing_pct":  8, "min_baseline": 5, "tier": 2, "name": "알파벳"},
    "TSLA": {"swing_pct": 12, "min_baseline": 5, "tier": 2, "name": "테슬라"},
    "AAPL": {"swing_pct":  8, "min_baseline": 5, "tier": 2, "name": "애플"},
    # ── Tier 3: 섹터 ETF + 2배 ──────────────────────────────
    "QLD":  {"swing_pct":  8, "min_baseline": 5, "tier": 3, "name": "나스닥 2배"},
    "SSO":  {"swing_pct":  8, "min_baseline": 5, "tier": 3, "name": "S&P500 2배"},
    "SMH":  {"swing_pct":  8, "min_baseline": 5, "tier": 3, "name": "반도체 ETF"},
    "XLK":  {"swing_pct":  8, "min_baseline": 5, "tier": 3, "name": "테크 섹터 ETF"},
    "XAR":  {"swing_pct":  8, "min_baseline": 5, "tier": 3, "name": "항공우주/방산 ETF"},
    "CIBR": {"swing_pct":  8, "min_baseline": 5, "tier": 3, "name": "사이버보안 ETF"},
}

# ── Candidate 운영 규칙 (시뮬레이션 검증값) ─────────────────
CANDIDATE_RULES = {
    "max_lifetime_bars": 20,       # 유효기간: 20봉 초과 시 EXPIRED
    "vpf_zone_a_threshold": -1.0,  # VPF Zone A 기준
    "conversion_rate_ref": 66.7,   # 참고용 전환율 (TQQQ 백테스트)
    "lead_time_avg_bars": 10,      # 평균 선행 봉수
}

# ── 알림 설정 ────────────────────────────────────────────────
NOTIFY_EVENTS = ["CANDIDATE_NEW", "S1_FIRED", "CANDIDATE_EXPIRED"]
# CANDIDATE_NEW  : 신규 Candidate 등록 시
# S1_FIRED       : S1 신호 발생 시 (UP-BOX 전환 + VPF Zone A)
# CANDIDATE_EXPIRED : 유효기간 초과 자동 해제 시
