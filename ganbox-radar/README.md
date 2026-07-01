# 🛰 GAN BOX Radar

GAN BOX ENGINE Phase 3 — S1 Candidate 자동 탐지 시스템

매일 24종목을 자동 스캔하여 S1 신호 형성 중인 종목을 사전에 감지합니다.

## 아키텍처

```
GitHub Actions (매일 06:30 KST 자동 실행)
    ↓
Python Scanner (GAN BOX Engine)
    ↓
Firebase Firestore (결과 저장)
    ↓
Web Dashboard + 이메일 알림
    ↓
TradingView (최종 진입 판단)
```

## 월 비용: $0

- GitHub Actions: 무료 2,000분/월 중 약 528분 사용
- Firebase: 무료 티어 내
- Yahoo Finance: 무료 API

---

## 설치 방법

### Step 1 — GitHub Repository 생성

1. https://github.com/new 에서 `ganbox-radar` 저장소 생성
2. 이 파일들을 업로드 또는 git push

### Step 2 — Firebase 프로젝트 생성

1. https://console.firebase.google.com 접속
2. 새 프로젝트 생성 (예: `ganbox-radar`)
3. Firestore Database 생성 (프로덕션 모드)
4. 프로젝트 설정 → 서비스 계정 → 새 비공개 키 생성 → JSON 다운로드

### Step 3 — GitHub Secrets 등록

GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret

| Secret 이름 | 값 |
|---|---|
| `FIREBASE_KEY` | Firebase 서비스 계정 JSON 전체 내용 |
| `EMAIL_FROM` | 발송 Gmail 주소 (예: radar@gmail.com) |
| `EMAIL_TO` | 수신 이메일 주소 |
| `EMAIL_PASSWORD` | Gmail 앱 비밀번호 (2단계 인증 필요) |

> **Gmail 앱 비밀번호 발급:**
> Google 계정 → 보안 → 2단계 인증 설정 후
> → 앱 비밀번호 → 앱(메일), 기기(기타) 선택 → 16자리 비밀번호 복사

### Step 4 — Dashboard Firebase 설정

`dashboard/index.html` 파일에서 firebaseConfig 값을 교체:

Firebase 콘솔 → 프로젝트 설정 → 내 앱 → 웹 앱 추가 → 설정값 복사

```javascript
const firebaseConfig = {
  apiKey:            "실제값으로 교체",
  authDomain:        "실제값으로 교체",
  projectId:         "실제값으로 교체",
  // ...
};
```

### Step 5 — Firebase Hosting 배포

```bash
npm install -g firebase-tools
firebase login
firebase init hosting   # Public directory: dashboard
firebase deploy --only hosting
```

### Step 6 — Firestore 보안 규칙 설정

Firebase 콘솔 → Firestore → 규칙:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Dashboard: 읽기 공개
    match /candidates/{doc} { allow read: if true; }
    match /scan_log/{doc}   { allow read: if true; }
    match /history/{doc}    { allow read: if true; }
    // 쓰기: 서비스 계정만 (GitHub Actions)
    match /{document=**}    { allow write: if false; }
  }
}
```

### Step 7 — 수동 테스트 실행

GitHub 저장소 → Actions → GAN BOX Radar → Run workflow

---

## 종목 추가 방법

`config.py`의 `TICKER_CONFIG`에 항목 추가 후 커밋:

```python
"NEW_TICKER": {"swing_pct": 10, "min_baseline": 5, "tier": 2, "name": "종목명"},
```

---

## Candidate 운영 규칙 (시뮬레이션 검증값)

| 항목 | 값 |
|---|---|
| 등록 조건 | VPF < -1.0 AND VPF 기울기 음전환 AND DN-BOX |
| 유효기간 | 20봉 (초과 시 자동 EXPIRED) |
| 소멸 조건 | EMA20 재진입 (97.4%) |
| 전환율 | 60봉 내 S1 발생 66.7% |
| 평균 Lead Time | 약 10봉 전 등록 |

---

## 로드맵

- **Phase 3 현재**: 24종목 자동 스캔 (Tier 1+2+3)
- **Phase 4**: 인버스 ETF 전략 연구 (SQQQ, SOXS)
- **Phase 5**: 크립토 현물 연구 (BTC, ETH)
