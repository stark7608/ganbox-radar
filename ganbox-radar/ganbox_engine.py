# ============================================================
#  GAN BOX Engine — Python 이식본
#  백테스트에서 검증된 로직 그대로 사용
#  절대 변경 금지: FSM, VPF, EMA, Candidate 판정 조건
# ============================================================

import numpy as np
import pandas as pd


# ── VPF 계산 ─────────────────────────────────────────────────
def calc_vpf(src: np.ndarray, length: int = 400, length1: int = 100) -> np.ndarray:
    """
    VPF (Volume Price Force) 계산
    선형회귀 잔차 → 정규화 → 단일 SMA 스무딩
    검증값: length=400, length1=100, 단일 SMA (이중 스무딩 금지)
    """
    n = len(src)
    dist = np.full(n, np.nan)
    x = np.arange(1, length + 1, dtype=float)

    for i in range(length - 1, n):
        w = src[i - length + 1:i + 1][::-1]
        sx = x.sum()
        sy = w.sum()
        sxy = (x * w).sum()
        sx2 = (x ** 2).sum()
        denom = length * sx2 - sx ** 2
        if denom == 0:
            continue
        slope = (length * sxy - sx * sy) / denom
        intercept = (sy - slope * sx) / length
        y1 = intercept + slope
        dist[i] = src[i] - y1

    d = pd.Series(dist)
    roll_mean = d.rolling(length1).mean()
    roll_std  = d.rolling(length1).std()
    dist_n = np.where(roll_std != 0, (dist - roll_mean) / roll_std, 0.0)

    # 단일 SMA 스무딩 (검증값: 10봉)
    vpf = pd.Series(dist_n).rolling(10).mean().values
    return vpf


# ── EMA 계산 ─────────────────────────────────────────────────
def calc_ema(src: pd.Series, span: int = 20) -> np.ndarray:
    return src.ewm(span=span, adjust=False).mean().values


# ── FSM 실행 ─────────────────────────────────────────────────
def run_fsm(df: pd.DataFrame, swing_pct: float = 12.0, lag_bars: int = 20) -> np.ndarray:
    """
    GAN BOX FSM 상태 배열 반환
    state 1 = UP-BOX (상승 파동)
    state 2 = DN-BOX (하락 파동)
    절대 변경 금지 영역
    """
    n = len(df)
    close = df['close'].values
    high  = df['high'].values
    low   = df['low'].values
    ema20 = df['ema20'].values

    state_arr = np.ones(n, dtype=int)

    state = 1
    ch = high[0]; chi = 0
    cl = low[0];  cli = 0
    lch = np.nan; lcl = np.nan
    lht = np.nan; lhb = np.nan
    llt = np.nan; llb = np.nan
    ta_f = False; ti = 0

    for i in range(1, n):
        c = close[i]; h = high[i]; l = low[i]; ema = ema20[i]

        if state == 1:
            if not np.isnan(llb) and c < llb:
                state = 2; cl = l; cli = i; ta_f = False
            else:
                if h > ch: ch = h; chi = i; ta_f = False
                dp = (ch - l) / ch * 100 if ch > 0 else 0
                if (dp >= swing_pct or c < ema) and not ta_f:
                    ta_f = True; ti = i
                if ta_f:
                    if dp >= swing_pct and c < ema:
                        if not np.isnan(lcl):
                            lht = max(ch, lcl); lhb = min(ch, lcl)
                        lch = ch; state = 2; cl = l; cli = i; ta_f = False
                    if i - ti > lag_bars:
                        ta_f = False
        else:
            if not np.isnan(lht) and c > lht:
                state = 1; ch = h; chi = i; ta_f = False
            else:
                if l < cl: cl = l; cli = i; ta_f = False
                rp = (h - cl) / cl * 100 if cl > 0 else 0
                if (rp >= swing_pct or c > ema) and not ta_f:
                    ta_f = True; ti = i
                if ta_f:
                    if rp >= swing_pct and c > ema:
                        if not np.isnan(lch):
                            llt = max(lch, cl); llb = min(lch, cl)
                        lcl = cl; state = 1; ch = h; chi = i; ta_f = False
                    if i - ti > lag_bars:
                        ta_f = False

        state_arr[i] = state

    return state_arr


# ── Candidate 탐지 ───────────────────────────────────────────
def detect_candidate(df: pd.DataFrame, config: dict) -> dict:
    """
    현재 봉 기준 S1 Candidate 상태 판정

    Candidate 등록 조건 (시뮬레이션 검증값):
      1. VPF < -1.0  (Zone A)
      2. vpf_slope < 0  (기울기 음전환, 5봉 기준)
      3. FSM state == 2  (DN-BOX)

    소멸 조건:
      - EMA20 재진입 (97.4% 케이스)
      - VPF >= -1.0 (2.6%)
      - 유효기간 초과 (20봉)

    반환:
      is_candidate : bool
      vpf          : float
      vpf_slope    : float
      state        : int (1=UP, 2=DN)
      s1_signal    : bool  (UP-BOX 전환 + Zone A 조건 동시 충족)
      cancel_reason: str | None
    """
    swing   = config.get("swing_pct", 12)
    min_bl  = config.get("min_baseline", 5)
    max_life = 20  # 유효기간 고정

    # 데이터 준비
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    if 'adj close' in df.columns:
        df['close'] = df['adj close']

    df['ema20'] = calc_ema(df['close'])
    df['vpf']   = calc_vpf(df['close'].values)
    df['vpf_slope'] = df['vpf'] - df['vpf'].shift(5)
    df['state'] = run_fsm(df, swing_pct=swing)

    # 최신 봉 기준
    latest = df.iloc[-1]
    vpf        = float(latest['vpf'])       if not np.isnan(latest['vpf'])       else np.nan
    vpf_slope  = float(latest['vpf_slope']) if not np.isnan(latest['vpf_slope']) else np.nan
    state      = int(latest['state'])
    close_price= float(latest['close'])
    ema20_val  = float(latest['ema20'])

    # S1 신호 체크 (UP-BOX 전환 봉에서만 발생)
    prev_state = int(df.iloc[-2]['state']) if len(df) >= 2 else state
    upbox_transition = (state == 1 and prev_state == 2)
    s1_signal = (upbox_transition
                 and not np.isnan(vpf)
                 and vpf < -1.0
                 and not np.isnan(vpf_slope)
                 and vpf_slope < 0)

    # Candidate 조건
    if np.isnan(vpf) or np.isnan(vpf_slope):
        is_candidate = False
        cancel_reason = "DATA_INSUFFICIENT"
    elif vpf >= -1.0:
        is_candidate = False
        cancel_reason = "VPF_ABOVE_ZONE_A"
    elif vpf_slope >= 0:
        is_candidate = False
        cancel_reason = "SLOPE_POSITIVE"
    elif state != 2:
        is_candidate = False
        cancel_reason = "NOT_DN_BOX"
    elif close_price >= ema20_val:
        is_candidate = False
        cancel_reason = "EMA_REENTER"
    else:
        is_candidate = True
        cancel_reason = None

    return {
        "is_candidate": is_candidate,
        "s1_signal":    s1_signal,
        "vpf":          round(vpf, 4) if not np.isnan(vpf) else None,
        "vpf_slope":    round(vpf_slope, 4) if not np.isnan(vpf_slope) else None,
        "state":        state,
        "close":        round(close_price, 2),
        "ema20":        round(ema20_val, 2),
        "cancel_reason": cancel_reason,
    }
