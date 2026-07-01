# ============================================================
#  Notifier — 이메일 알림 (Gmail SMTP, 무료)
#  GitHub Actions Secret: EMAIL_FROM, EMAIL_TO, EMAIL_PASSWORD
# ============================================================

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _send_email(subject: str, body: str):
    """Gmail SMTP로 이메일 발송"""
    from_addr = os.environ.get("EMAIL_FROM")
    to_addr   = os.environ.get("EMAIL_TO")
    password  = os.environ.get("EMAIL_PASSWORD")

    if not all([from_addr, to_addr, password]):
        print("  ⚠️  이메일 환경변수 미설정 — 알림 건너뜀")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = from_addr
        msg["To"]      = to_addr
        msg.attach(MIMEText(body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_addr, password)
            server.sendmail(from_addr, to_addr, msg.as_string())
        print(f"  📧  이메일 발송 완료: {subject}")
    except Exception as e:
        print(f"  ❌  이메일 발송 실패: {e}")


def notify_new_candidate(ticker: str, vpf: float, vpf_slope: float,
                         close: float, tier: int, name: str):
    subject = f"[GAN BOX Radar] 🟢 {ticker} Candidate 등록"
    body = f"""
<html><body style="font-family:monospace;background:#0d1117;color:#e6edf3;padding:24px">
<h2 style="color:#58a6ff">🛰 GAN BOX Radar — Candidate 신규 등록</h2>
<table style="border-collapse:collapse;width:100%;max-width:480px">
  <tr><td style="padding:8px;color:#8b949e">종목</td>
      <td style="padding:8px;color:#fff;font-weight:bold">{ticker} <small style="color:#8b949e">({name})</small></td></tr>
  <tr style="background:#161b22"><td style="padding:8px;color:#8b949e">Tier</td>
      <td style="padding:8px;color:#fff">Tier {tier}</td></tr>
  <tr><td style="padding:8px;color:#8b949e">현재가</td>
      <td style="padding:8px;color:#fff">${close:.2f}</td></tr>
  <tr style="background:#161b22"><td style="padding:8px;color:#8b949e">VPF</td>
      <td style="padding:8px;color:#f85149">{vpf:.3f} (Zone A)</td></tr>
  <tr><td style="padding:8px;color:#8b949e">VPF 기울기</td>
      <td style="padding:8px;color:#f85149">{vpf_slope:.4f} (음전환)</td></tr>
</table>
<p style="margin-top:16px;color:#8b949e;font-size:12px">
  평균 10봉 후 S1 신호 발생 가능성 있음.<br>
  TradingView에서 GAN BOX Panel 확인 후 진입 여부 판단하세요.
</p>
<p style="color:#484f58;font-size:11px">GAN BOX Radar · 자동 발송</p>
</body></html>
"""
    _send_email(subject, body)


def notify_s1_fired(ticker: str, vpf: float, close: float,
                    tier: int, name: str):
    subject = f"[GAN BOX Radar] 🚨 {ticker} S1 신호 발생!"
    body = f"""
<html><body style="font-family:monospace;background:#0d1117;color:#e6edf3;padding:24px">
<h2 style="color:#3fb950">🚨 GAN BOX Radar — S1 신호 발생</h2>
<table style="border-collapse:collapse;width:100%;max-width:480px">
  <tr><td style="padding:8px;color:#8b949e">종목</td>
      <td style="padding:8px;color:#fff;font-weight:bold;font-size:18px">{ticker}</td></tr>
  <tr style="background:#161b22"><td style="padding:8px;color:#8b949e">신호</td>
      <td style="padding:8px;color:#3fb950;font-weight:bold">🟢 집중 매수 S1 (승률 90.9%)</td></tr>
  <tr><td style="padding:8px;color:#8b949e">현재가</td>
      <td style="padding:8px;color:#fff">${close:.2f}</td></tr>
  <tr style="background:#161b22"><td style="padding:8px;color:#8b949e">VPF</td>
      <td style="padding:8px;color:#f85149">{vpf:.3f} (Zone A)</td></tr>
  <tr><td style="padding:8px;color:#8b949e">종목명</td>
      <td style="padding:8px;color:#8b949e">{name} (Tier {tier})</td></tr>
</table>
<p style="margin-top:16px;color:#d29922;font-weight:bold">
  ⚠️ TradingView에서 GAN BOX Panel을 확인하세요.<br>
  Final Score, RR, TP/SL 확인 후 진입 여부를 결정하세요.
</p>
<p style="color:#484f58;font-size:11px">GAN BOX Radar · 자동 발송</p>
</body></html>
"""
    _send_email(subject, body)


def notify_expired(ticker: str, days: int, reason: str):
    subject = f"[GAN BOX Radar] ⏱ {ticker} Candidate 소멸 ({reason})"
    body = f"""
<html><body style="font-family:monospace;background:#0d1117;color:#e6edf3;padding:24px">
<h2 style="color:#d29922">⏱ GAN BOX Radar — Candidate 소멸</h2>
<table style="border-collapse:collapse;width:100%;max-width:480px">
  <tr><td style="padding:8px;color:#8b949e">종목</td>
      <td style="padding:8px;color:#fff;font-weight:bold">{ticker}</td></tr>
  <tr style="background:#161b22"><td style="padding:8px;color:#8b949e">소멸 사유</td>
      <td style="padding:8px;color:#d29922">{reason}</td></tr>
  <tr><td style="padding:8px;color:#8b949e">유지 기간</td>
      <td style="padding:8px;color:#8b949e">{days}봉</td></tr>
</table>
<p style="color:#484f58;font-size:11px">GAN BOX Radar · 자동 발송</p>
</body></html>
"""
    _send_email(subject, body)


def notify_daily_summary(candidates: list, s1_fired: list,
                         total_scanned: int, errors: list):
    """매일 스캔 완료 후 요약 발송 (Candidate가 있을 때만)"""
    if not candidates and not s1_fired:
        return  # 아무것도 없으면 발송 안 함

    subject = f"[GAN BOX Radar] 📊 오늘 스캔 완료 — Candidate {len(candidates)}건"
    rows = ""
    for c in s1_fired:
        rows += f'<tr style="background:#0a2a0a"><td style="padding:6px 10px;color:#3fb950;font-weight:bold">{c["ticker"]}</td><td style="padding:6px 10px;color:#3fb950">🚨 S1 발생!</td><td style="padding:6px 10px;color:#fff">${c["close"]:.2f}</td><td style="padding:6px 10px;color:#f85149">{c["vpf"]:.2f}</td></tr>'
    for c in candidates:
        rows += f'<tr><td style="padding:6px 10px;color:#fff;font-weight:bold">{c["ticker"]}</td><td style="padding:6px 10px;color:#58a6ff">🟢 Candidate {c["days"]}봉</td><td style="padding:6px 10px;color:#fff">${c["close"]:.2f}</td><td style="padding:6px 10px;color:#f85149">{c["vpf"]:.2f}</td></tr>'

    err_html = ""
    if errors:
        err_html = f'<p style="color:#f85149;font-size:12px">스캔 실패: {", ".join(errors)}</p>'

    body = f"""
<html><body style="font-family:monospace;background:#0d1117;color:#e6edf3;padding:24px">
<h2 style="color:#58a6ff">🛰 GAN BOX Radar — 일일 스캔 결과</h2>
<p style="color:#8b949e">{total_scanned}종목 스캔 완료</p>
<table style="border-collapse:collapse;width:100%;max-width:560px">
  <tr style="background:#21262d">
    <th style="padding:8px 10px;text-align:left;color:#8b949e">종목</th>
    <th style="padding:8px 10px;text-align:left;color:#8b949e">상태</th>
    <th style="padding:8px 10px;text-align:left;color:#8b949e">현재가</th>
    <th style="padding:8px 10px;text-align:left;color:#8b949e">VPF</th>
  </tr>
  {rows}
</table>
{err_html}
<p style="color:#484f58;font-size:11px">GAN BOX Radar · 자동 발송</p>
</body></html>
"""
    _send_email(subject, body)
