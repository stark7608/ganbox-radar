# ============================================================
#  GAN BOX Engine v2.0 — S1 + S3 + Watch + Warming 감지
#  절대 변경 금지: FSM, VPF 계산 로직
# ============================================================

import numpy as np
import pandas as pd


def calc_vpf(src: np.ndarray, length: int = 400, length1: int = 100) -> np.ndarray:
    n = len(src)
    dist = np.full(n, np.nan)
    x = np.arange(1, length + 1, dtype=float)
    for i in range(length - 1, n):
        w = src[i - length + 1:i + 1][::-1]
        sx = x.sum(); sy = w.sum()
        sxy = (x * w).sum(); sx2 = (x ** 2).sum()
        denom = length * sx2 - sx ** 2
        if denom == 0: continue
        slope = (length * sxy - sx * sy) / denom
        intercept = (sy - slope * sx) / length
        dist[i] = src[i] - (intercept + slope)
    d = pd.Series(dist)
    roll_mean = d.rolling(length1).mean()
    roll_std  = d.rolling(length1).std()
    dist_n = np.where(roll_std != 0, (dist - roll_mean) / roll_std, 0.0)
    return pd.Series(dist_n).rolling(10).mean().values


def calc_ema(src: pd.Series, span: int = 20) -> np.ndarray:
    return src.ewm(span=span, adjust=False).mean().values


def run_fsm(df: pd.DataFrame, swing_pct: float = 12.0) -> np.ndarray:
    n = len(df)
    close = df['close'].values
    high  = df['high'].values
    low   = df['low'].values
    ema20 = df['ema20'].values
    state_arr = np.ones(n, dtype=int)
    state = 1
    ch = high[0]; cl = low[0]
    lch = np.nan; lcl = np.nan
    lht = np.nan; lhb = np.nan
    llt = np.nan; llb = np.nan
    ta_f = False; ti = 0

    for i in range(1, n):
        c = close[i]; h = high[i]; l = low[i]; ema = ema20[i]
        if state == 1:
            if not np.isnan(llb) and c < llb:
                state = 2; cl = l; ta_f = False
            else:
                if h > ch: ch = h; ta_f = False
                dp = (ch - l) / ch * 100 if ch > 0 else 0
                if (dp >= swing_pct or c < ema) and not ta_f:
                    ta_f = True; ti = i
                if ta_f:
                    if dp >= swing_pct and c < ema:
                        if not np.isnan(lcl):
                            lht = max(ch, lcl); lhb = min(ch, lcl)
                        lch = ch; state = 2; cl = l; ta_f = False
                    if i - ti > 20: ta_f = False
        else:
            if not np.isnan(lht) and c > lht:
                state = 1; ch = h; ta_f = False
            else:
                if l < cl: cl = l; ta_f = False
                rp = (h - cl) / cl * 100 if cl > 0 else 0
                if (rp >= swing_pct or c > ema) and not ta_f:
                    ta_f = True; ti = i
                if ta_f:
                    if rp >= swing_pct and c > ema:
                        if not np.isnan(lch):
                            llt = max(lch, cl); llb = min(lch, cl)
                        lcl = cl; state = 1; ch = h; ta_f = False
                    if i - ti > 20: ta_f = False
        state_arr[i] = state
    return state_arr


def detect_signals(df: pd.DataFrame, config: dict) -> dict:
    """
    S1 / S3 / Watch / Warming 4단계 신호 감지

    반환:
        signal_type : "S1" | "S3" | "CANDIDATE" | "WATCH" | "WARMING" | "NONE"
        vpf         : float
        vpf_slope   : float
        state       : 1(UP) | 2(DN)
        close       : float
        cancel_reason: str | None
    """
    swing = config.get("swing_pct", 12)

    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    if 'adj close' in df.columns:
        df['close'] = df['adj close']

    df['ema20']     = calc_ema(df['close'])
    df['vpf']       = calc_vpf(df['close'].values)
    df['vpf_slope'] = df['vpf'] - df['vpf'].shift(5)
    df['state']     = run_fsm(df, swing_pct=swing)

    latest    = df.iloc[-1]
    prev      = df.iloc[-2] if len(df) >= 2 else latest

    vpf       = float(latest['vpf'])       if not np.isnan(latest['vpf'])       else None
    vpf_slope = float(latest['vpf_slope']) if not np.isnan(latest['vpf_slope']) else None
    state     = int(latest['state'])
    close_px  = float(latest['close'])
    ema_val   = float(latest['ema20'])
    prev_state= int(prev['state'])

    if vpf is None or vpf_slope is None:
        return _result("NONE", vpf, vpf_slope, state, close_px, "DATA_INSUFFICIENT")

    # ── UP-BOX 전환 감지 ──────────────────────────────────
    upbox = (state == 1 and prev_state == 2)

    # ── S1 신호 ───────────────────────────────────────────
    if upbox and vpf < -1.0 and vpf_slope < 0:
        return _result("S1", vpf, vpf_slope, state, close_px, None)

    # ── S3 신호 ───────────────────────────────────────────
    if upbox and -1.0 <= vpf < 0.0:
        return _result("S3", vpf, vpf_slope, state, close_px, None)

    # ── S1 Candidate (DN-BOX + Zone A + 기울기↓) ─────────
    if state == 2 and vpf < -1.0 and vpf_slope < 0:
        if close_px >= ema_val:
            return _result("NONE", vpf, vpf_slope, state, close_px, "EMA_REENTER")
        return _result("CANDIDATE", vpf, vpf_slope, state, close_px, None)

    # ── Watch (DN-BOX + -1.0 <= VPF < -0.5) ─────────────
    if state == 2 and -1.0 <= vpf < -0.5:
        return _result("WATCH", vpf, vpf_slope, state, close_px, None)

    # ── Warming (DN-BOX + VPF < 0) ───────────────────────
    if state == 2 and vpf < 0.0:
        return _result("WARMING", vpf, vpf_slope, state, close_px, None)

    return _result("NONE", vpf, vpf_slope, state, close_px, "NO_CONDITION")


def _result(signal_type, vpf, vpf_slope, state, close_px, reason):
    return {
        "signal_type":  signal_type,
        "vpf":          round(vpf, 4)       if vpf       is not None else None,
        "vpf_slope":    round(vpf_slope, 4) if vpf_slope is not None else None,
        "state":        state,
        "close":        round(close_px, 2),
        "cancel_reason": reason,
    }
