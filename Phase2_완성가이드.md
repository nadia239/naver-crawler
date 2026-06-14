# Phase 2 완성 가이드
## Google Sheets 자동 연동

---

## 개요

**목표:** 네이버 크롤링 결과를 Google Sheets에 자동 저장  
**버전:** v1.0  
**작성일:** 2026-06-14  
**상태:** 완성

**추가된 파일:**
- `sheets_handler.py` — Google Sheets 연동 클래스
- `requirements.txt` — 의존성 패키지 목록

**수정된 파일:**
- `config.json` — `google_sheets` 섹션 추가
- `scraper.py` — Sheets 업로드 로직 추가

---

## 준비 작업 (Google Cloud 설정)

### 1단계: Google Cloud 프로젝트 생성

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 상단 프로젝트 선택 → **새 프로젝트**
3. 프로젝트 이름 입력 (예: `naver-crawler`) → 만들기

### 2단계: Google Sheets API 활성화

1. 좌측 메뉴 → **API 및 서비스** → **라이브러리**
2. 검색창에 `Google Sheets API` 입력
3. **사용 설정** 클릭

### 3단계: 서비스 계정 생성

1. 좌측 메뉴 → **API 및 서비스** → **사용자 인증 정보**
2. **사용자 인증 정보 만들기** → **서비스 계정**
3. 서비스 계정 이름 입력 (예: `crawler-bot`) → 완료

### 4단계: credentials.json 다운로드

1. 생성된 서비스 계정 클릭
2. **키** 탭 → **키 추가** → **새 키 만들기**
3. **JSON** 선택 → 만들기
4. 다운로드된 파일을 `credentials.json`으로 저장 후 프로젝트 폴더에 복사

---

## config.json 설정

```json
{
  "google_sheets": {
    "enabled": true,
    "credentials_path": "credentials.json",
    "spreadsheet_id": "",
    "sheet_name": "크롤링결과",
    "auto_create": true
  }
}
```

| 항목 | 설명 | 기본값 |
|---|---|---|
| `enabled` | Google Sheets 연동 활성화 | `false` |
| `credentials_path` | 서비스 계정 키 파일 경로 | `credentials.json` |
| `spreadsheet_id` | 기존 시트 ID (비워두면 자동 생성) | `""` |
| `sheet_name` | 데이터를 저장할 시트 이름 | `크롤링결과` |
| `auto_create` | 시트 자동 생성 여부 | `true` |

### 기존 구글시트 사용하는 경우

1. 구글시트 URL에서 ID 복사
   ```
   https://docs.google.com/spreadsheets/d/[여기가_ID]/edit
   ```
2. `config.json`에 붙여넣기
   ```json
   "spreadsheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
   ```
3. 구글시트 **공유** → 서비스 계정 이메일 추가 (편집자 권한)
   - 이메일은 `credentials.json` 안의 `client_email` 값

---

## 실행

```bash
python scraper.py
```

성공 시 출력 예시:
```
✅ Google Sheets 연결 성공
✅ 스프레드시트 생성 완료: https://docs.google.com/spreadsheets/d/...
✅ 헤더 설정 완료
✅ Google Sheets에 30개 결과 저장 완료
🔗 Google Sheets: https://docs.google.com/spreadsheets/d/...
```

---

## 결과 시트 구조

| 순번 | 제목 | URL | 요약 | 사이트 | 키워드 | 검색일 | 검색시간 |
|---|---|---|---|---|---|---|---|
| 1 | AI 최신 뉴스 2026 | https://... | AI 기술의... | example.com | AI 최신 뉴스 | 2026-06-14 | 09:00:12 |
| 2 | ... | ... | ... | ... | ... | ... | ... |

- 실행할 때마다 기존 데이터 아래에 **누적 추가**됨
- 헤더는 최초 1회만 자동 생성

---

## 트러블슈팅

### "credentials.json 파일 없음"

서비스 계정 키를 다운로드해서 프로젝트 폴더에 복사했는지 확인:
```
c:\claude\4\
├── scraper.py
├── credentials.json   ← 여기에 있어야 함
└── config.json
```

### "권한 오류 (403 Forbidden)"

구글시트에 서비스 계정 이메일을 편집자로 공유했는지 확인:
1. 구글시트 → 공유
2. `credentials.json` 안의 `client_email` 값으로 공유

### "google-api-python-client 모듈 없음"

```bash
pip install -r requirements.txt
```

### Google Sheets 없이 Phase 1만 사용하고 싶을 때

`config.json`에서 비활성화:
```json
"google_sheets": {
  "enabled": false
}
```

---

## 체크리스트

- [ ] Google Cloud 프로젝트 생성
- [ ] Google Sheets API 활성화
- [ ] 서비스 계정 생성
- [ ] credentials.json 다운로드 및 프로젝트 폴더에 복사
- [ ] config.json에서 `enabled: true` 설정
- [ ] `python scraper.py` 실행
- [ ] 구글시트에 데이터 저장 확인

---

**다음 단계:** Phase 3 — GitHub Actions로 매일 자동 실행 설정
