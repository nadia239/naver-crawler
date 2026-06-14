#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Sheets 핸들러 - Phase 2
크롤링 결과를 Google Sheets에 자동 저장
"""

import logging
from datetime import datetime

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


class GoogleSheetsHandler:
    """Google Sheets 연동 핸들러"""

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    def __init__(self, credentials_path='credentials.json', spreadsheet_id=None, sheet_name='크롤링결과'):
        if not GOOGLE_AVAILABLE:
            raise ImportError("google-api-python-client 패키지가 필요합니다: pip install -r requirements.txt")

        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.service = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """Google Sheets API 연결"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.SCOPES
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            self.logger.info("✅ Google Sheets 연결 성공")
            return True
        except FileNotFoundError:
            self.logger.error(f"❌ credentials.json 파일 없음: {self.credentials_path}")
            self.logger.error("   → Google Cloud Console에서 서비스 계정 키를 다운로드하세요.")
            return False
        except Exception as e:
            self.logger.error(f"❌ Google Sheets 연결 실패: {str(e)}")
            return False

    def create_spreadsheet(self, title=None):
        """새 스프레드시트 생성"""
        if title is None:
            title = f"네이버 크롤링 결과_{datetime.now().strftime('%Y%m%d')}"
        try:
            result = self.service.spreadsheets().create(
                body={'properties': {'title': title}},
                fields='spreadsheetId'
            ).execute()
            self.spreadsheet_id = result.get('spreadsheetId')
            self.logger.info(f"✅ 스프레드시트 생성 완료: {self.get_sheet_url()}")
            return self.spreadsheet_id
        except HttpError as e:
            self.logger.error(f"❌ 스프레드시트 생성 실패: {e}")
            return None

    def ensure_sheet_exists(self):
        """시트 탭이 없으면 새로 생성"""
        try:
            metadata = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            existing = [s['properties']['title'] for s in metadata.get('sheets', [])]
            if self.sheet_name in existing:
                return True
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': [{'addSheet': {'properties': {'title': self.sheet_name}}}]}
            ).execute()
            self.logger.info(f"시트 탭 생성: {self.sheet_name}")
            return True
        except Exception as e:
            self.logger.error(f"시트 탭 확인/생성 실패: {e}")
            return False

    def setup_header(self):
        """헤더 행 설정 (시트가 비어있을 때만)"""
        try:
            existing = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A1:H1'
            ).execute()

            if existing.get('values'):
                return True  # 이미 헤더 있음

            headers = [['구분', '순위', '키워드', '제목/업체명', 'URL', '블로그명/카테고리', '작성일/전화', '설명/주소', '검색일', '검색시간']]
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A1',
                valueInputOption='RAW',
                body={'values': headers}
            ).execute()
            self.logger.info(f"✅ 헤더 설정 완료")
            return True
        except HttpError as e:
            self.logger.error(f"❌ 헤더 설정 실패: {e}")
            return False

    def append_results(self, results):
        """결과 데이터를 시트에 추가"""
        if not results:
            self.logger.warning("추가할 결과가 없습니다.")
            return False

        rows = [
            [
                item.get('type', ''),
                item.get('rank', ''),
                item.get('keyword', ''),
                item.get('title', ''),
                item.get('url', ''),
                item.get('blog_name', ''),
                item.get('post_date', ''),
                item.get('description', ''),
                item.get('search_date', ''),
                item.get('search_time', '')
            ]
            for item in results
        ]

        try:
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A1',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': rows}
            ).execute()
            self.logger.info(f"✅ Google Sheets에 {len(rows)}개 결과 저장 완료")
            return True
        except HttpError as e:
            self.logger.error(f"❌ 데이터 저장 실패: {e}")
            return False

    def get_sheet_url(self):
        """스프레드시트 URL 반환"""
        if self.spreadsheet_id:
            return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"
        return None

    def upload_results(self, results):
        """키워드별 시트로 분리해서 업로드 (연결 → 시트 생성 → 헤더 → 데이터)"""
        if not self.connect():
            return None

        if not self.spreadsheet_id:
            if not self.create_spreadsheet():
                return None

        from collections import defaultdict
        grouped = defaultdict(list)
        for item in results:
            grouped[item['keyword']].append(item)

        for keyword, items in grouped.items():
            self.sheet_name = keyword
            if not self.ensure_sheet_exists():
                continue
            self.setup_header()
            self.append_results(items)
            self.logger.info(f"[{keyword}] {len(items)}개 저장")

        url = self.get_sheet_url()
        self.logger.info(f"🔗 스프레드시트 URL: {url}")
        return url
