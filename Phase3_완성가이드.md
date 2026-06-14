# Phase 3 완성 가이드
## GitHub Actions 매일 자동 실행

---

## 개요

**목표:** 매일 오전 9시(KST)에 크롤러를 자동 실행하고 결과를 저장  
**버전:** v1.0  
**작성일:** 2026-06-14  
**상태:** 완성

**추가된 파일:**
- `.github/workflows/daily-crawl.yml` — 자동 실행 워크플로우
- `.gitignore` — 민감 파일 제외 설정

**수정된 파일:**
- `scraper.py` — 환경변수 오버라이드 지원 추가

---

## 준비 작업

### 1단계: GitHub 저장소 생성

1. [github.com](https://github.com) 접속 → 로그인
2. 우측 상단 **+** → **New repository**
3. Repository name: `naver-crawler`
4. **Public** 또는 **Private** 선택
5. **Create repository** 클릭

### 2단계: 로컬 코드 업로드

```bash
# 프로젝트 폴더에서 실행
git init
git add .
git commit -m "네이버 크롤러 자동화 v1.0"
git branch -M main
git remote add origin https://github.com/[사용자명]/naver-crawler.git
git push -u origin main
```

> `credentials.json`은 `.gitignore`에 등록되어 있어 자동으로 제외됩니다.

### 3단계: GitHub Secrets 설정

저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret 이름 | 값 | 필수 여부 |
|---|---|---|
| `GOOGLE_CREDENTIALS` | `credentials.json` 파일 전체 내용 (JSON 텍스트) | Phase 2 사용 시 |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | 구글시트 ID | Phase 2 사용 시 |

**GOOGLE_CREDENTIALS 값 확인 방법:**

Windows:
```powershell
Get-Content credentials.json
```

Mac/Linux:
```bash
cat credentials.json
```

출력된 JSON 전체를 복사해서 Secret 값으로 입력

---

## 워크플로우 구조

```
.github/
└── workflows/
    └── daily-crawl.yml
```

**실행 순서:**

```
1. 코드 체크아웃
        ↓
2. Python 3.11 설치
        ↓
3. pip install -r requirements.txt
        ↓
4. credentials.json 생성 (Secret이 있을 때만)
        ↓
5. python scraper.py 실행
        ↓
6. 결과 파일 아티팩트 저장 (30일 보관)
        ↓
7. results.json / results.csv / results.md 저장소 커밋
```

---

## 실행 트리거

### 자동 실행 (매일 오전 9시 KST)

`daily-crawl.yml`의 cron 설정:
```yaml
schedule:
  - cron: '0 0 * * *'  # UTC 00:00 = KST 09:00
```

| UTC | KST | 설명 |
|---|---|---|
| 00:00 | 09:00 | 기본값 (오전 9시) |
| 01:00 | 10:00 | 오전 10시로 변경 시 |
| 22:00 (전날) | 07:00 | 오전 7시로 변경 시 |

**시간 변경 방법** — `daily-crawl.yml` 수정:
```yaml
- cron: '0 1 * * *'   # 오전 10시 KST
```

### 수동 실행

저장소 → **Actions** → **네이버 검색 크롤러** → **Run workflow** → **Run workflow**

---

## 결과 확인

### 아티팩트 다운로드

저장소 → **Actions** → 실행된 워크플로우 클릭 → **Artifacts** → 파일 다운로드

보관 기간: **30일**

### 저장소에 커밋된 결과

워크플로우가 성공하면 저장소에 아래 파일이 자동 커밋됩니다:
```
results.json
results.csv
results.md
```

커밋 메시지 예시:
```
자동 크롤링 결과 업데이트: 2026-06-14 00:00 UTC
```

---

## 트러블슈팅

### 워크플로우가 실행되지 않음

1. 저장소 → **Actions** 탭 → **"I understand my workflows, go ahead and enable them"** 클릭
2. Actions가 활성화되었는지 확인

### "Permission denied" 오류 (push 단계)

저장소 → **Settings** → **Actions** → **General** → **Workflow permissions**  
→ **Read and write permissions** 선택 후 저장

### Google Sheets 연동이 안 됨

1. `GOOGLE_CREDENTIALS` Secret이 올바른지 확인 (JSON 형식 그대로)
2. `GOOGLE_SHEETS_SPREADSHEET_ID` Secret 확인
3. 워크플로우 로그에서 오류 메시지 확인:
   저장소 → **Actions** → 실패한 실행 클릭 → 각 step 로그 확인

### cron이 예상 시간에 실행되지 않음

GitHub Actions cron은 UTC 기준이며, 서버 부하에 따라 최대 30분 지연될 수 있습니다.

---

## 비용

GitHub Actions는 **Public 저장소는 무료**, Private 저장소는 월 2,000분 무료 제공

크롤러 1회 실행 시간 약 2~5분이므로:
- 매일 실행 시 월 약 60~150분 사용
- Private 저장소도 무료 범위 내

---

## 체크리스트

- [ ] GitHub 저장소 생성
- [ ] `git push`로 코드 업로드 완료
- [ ] `.gitignore`로 credentials.json 제외 확인
- [ ] GitHub Secrets 설정 (`GOOGLE_CREDENTIALS`, `GOOGLE_SHEETS_SPREADSHEET_ID`)
- [ ] Actions 탭에서 워크플로우 활성화 확인
- [ ] 수동 실행으로 동작 테스트
- [ ] 결과 파일 아티팩트 다운로드 확인
- [ ] 저장소에 results 파일 자동 커밋 확인
- [ ] 다음 날 자동 실행 확인

---

**완성:** Phase 1 + 2 + 3 모두 완료  
크롤링 → Google Sheets 저장 → 매일 자동 실행이 완전히 자동화되었습니다.
