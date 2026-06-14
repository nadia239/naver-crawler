#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
네이버 블로그 & 플레이스 순위 크롤러
"""

import os
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import json
import time
import csv
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from collections import defaultdict

try:
    from sheets_handler import GoogleSheetsHandler
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False


class NaverSearchCrawler:

    BLOG_URL     = "https://search.naver.com/search.naver"
    NEXEARCH_URL = "https://search.naver.com/search.naver"

    def __init__(self, config_path='config.json'):
        self.config = self._load_config(config_path)
        self._setup_logging()
        self.headers = {
            'User-Agent': self.config['user_agent'],
            'Accept-Language': 'ko-KR,ko;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
        }
        self.logger.info("=" * 50)
        self.logger.info("네이버 블로그/플레이스 순위 크롤러 시작")
        self.logger.info(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 50)

    def _load_config(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"설정 파일 없음: {path}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"설정 파일 파싱 오류: {path}")
            sys.exit(1)

    def _setup_logging(self):
        log_cfg  = self.config.get('logging', {})
        level    = getattr(logging, log_cfg.get('level', 'INFO'))
        log_file = log_cfg.get('log_file', 'crawler.log')
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout),
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _get(self, url, params):
        timeout = self.config['search_settings']['timeout']
        try:
            r = requests.get(url, params=params, headers=self.headers, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.exceptions.RequestException as e:
            self.logger.error(f"요청 실패: {e}")
            return None

    # ──────────────────────────────────────────────
    # 공통: headline1 → 링크/블로그명/날짜 추출
    # ──────────────────────────────────────────────

    def _extract_view_items(self, scope, type_label, max_n):
        """scope(BeautifulSoup 요소) 안의 인기글/블로그 항목 추출"""
        results = []
        rank = 1
        for span in scope.select('span.sds-comps-text-type-headline1'):
            if rank > max_n:
                break
            title = span.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            # fds-ugc 조상 블록 탐색 (블로그명·날짜·링크가 모두 여기 안에 있음)
            block = span
            for _ in range(12):
                block = block.parent
                if block is None:
                    break
                if block.get('class') and any('fds-ugc' in c for c in block.get('class', [])):
                    break

            # 포스트 링크
            link = None
            if block:
                link = block.find('a', href=lambda h: h and any(
                    d in h for d in ('blog.naver', 'cafe.naver', 'in.naver')))

            url = link['href'] if link else ''

            # 블로그명 / 날짜
            blog_name = ''
            post_date = ''
            if block:
                name_el = block.select_one('span[class*="profile-info-title"]')
                date_el = block.select_one('span[class*="profile-info-subtext"]')
                blog_name = name_el.get_text(strip=True) if name_el else ''
                post_date = date_el.get_text(strip=True) if date_el else ''

            results.append({
                'type':        type_label,
                'rank':        rank,
                'keyword':     '',       # 호출 측에서 채움
                'title':       title,
                'url':         url,
                'blog_name':   blog_name,
                'post_date':   post_date,
                'description': '',
                'search_date': datetime.now().strftime('%Y-%m-%d'),
                'search_time': datetime.now().strftime('%H:%M:%S'),
            })
            rank += 1
        return results

    # ──────────────────────────────────────────────
    # 인기글 순위 (통합검색 메인 VIEW 섹션)
    # ──────────────────────────────────────────────

    def search_popular(self, keyword):
        """네이버 통합검색 '인기글' 섹션 순위"""
        self.logger.info(f"[인기글] '{keyword}' 검색 중...")

        r = self._get(self.BLOG_URL, {'where': 'blog', 'query': keyword})
        if not r:
            return []

        soup = BeautifulSoup(r.content, 'html.parser')
        max_n = self.config['search_settings']['max_results']

        # _fe_view_root 섹션 = 인기글 영역
        view_root = soup.select_one('div.sc_new._fe_view_root')
        if not view_root:
            self.logger.warning(f"[인기글] 인기글 섹션 없음: {keyword}")
            return []

        items = self._extract_view_items(view_root, '인기글', max_n)
        for item in items:
            item['keyword'] = keyword

        self.logger.info(f"[인기글] '{keyword}': {len(items)}개 수집")
        return items

    # ──────────────────────────────────────────────
    # 블로그 순위
    # ──────────────────────────────────────────────

    def search_blog(self, keyword):
        """네이버 블로그 탭 전체 검색 순위"""
        self.logger.info(f"[블로그] '{keyword}' 검색 중...")

        r = self._get(self.BLOG_URL, {'where': 'blog', 'query': keyword})
        if not r:
            return []

        soup  = BeautifulSoup(r.content, 'html.parser')
        max_n = self.config['search_settings']['max_results']

        items = self._extract_view_items(soup, '블로그', max_n)
        for item in items:
            item['keyword'] = keyword

        self.logger.info(f"[블로그] '{keyword}': {len(items)}개 수집")
        return items

    # ──────────────────────────────────────────────
    # 플레이스 순위
    # ──────────────────────────────────────────────

    def search_place(self, keyword):
        """네이버 플레이스 검색 순위 (통합검색 script 파싱)"""
        self.logger.info(f"[플레이스] '{keyword}' 검색 중...")

        r = self._get(self.NEXEARCH_URL, {'where': 'nexearch', 'query': keyword})
        if not r:
            return []

        soup    = BeautifulSoup(r.content, 'html.parser')
        max_n   = self.config['search_settings']['max_results']
        decoder = json.JSONDecoder()

        # PlaceListBusinessesItem 오브젝트를 script 태그에서 추출
        raw_items = []
        for script in soup.find_all('script'):
            text = script.string or ''
            if 'PlaceListBusinessesItem' not in text:
                continue

            pos = 0
            while True:
                idx = text.find('"PlaceListBusinessesItem"', pos)
                if idx < 0:
                    break
                obj_start = text.rfind('{', 0, idx)
                if obj_start < 0:
                    pos = idx + 1
                    continue
                try:
                    obj, _ = decoder.raw_decode(text, obj_start)
                    if obj.get('__typename') == 'PlaceListBusinessesItem':
                        raw_items.append(obj)
                except Exception:
                    pass
                pos = idx + 1
            break  # 첫 번째 script에서만 추출

        # 중복 제거 후 순위 부여
        results = []
        seen    = set()
        rank    = 1
        for item in raw_items:
            name = BeautifulSoup(item.get('name', ''), 'html.parser').get_text(strip=True)
            if not name or name in seen:
                continue
            seen.add(name)

            place_id  = item.get('id', '')
            place_url = f"https://map.naver.com/v5/entry/place/{place_id}" if place_id else ''
            address   = item.get('fullAddress') or item.get('roadAddress') or item.get('commonAddress', '')

            results.append({
                'type':        '플레이스',
                'rank':        rank,
                'keyword':     keyword,
                'title':       name,
                'url':         place_url,
                'blog_name':   item.get('category', ''),
                'post_date':   item.get('phone', ''),
                'description': address,
                'search_date': datetime.now().strftime('%Y-%m-%d'),
                'search_time': datetime.now().strftime('%H:%M:%S'),
            })
            rank += 1
            if rank > max_n:
                break

        self.logger.info(f"[플레이스] '{keyword}': {len(results)}개 수집")
        return results

    # ──────────────────────────────────────────────
    # 전체 크롤링
    # ──────────────────────────────────────────────

    def crawl_all_keywords(self):
        keywords = self.config['keywords']
        delay    = self.config['search_settings']['request_delay']
        all_results = []

        self.logger.info(f"총 {len(keywords)}개 키워드 크롤링 시작")

        for idx, keyword in enumerate(keywords, 1):
            self.logger.info(f"── [{idx}/{len(keywords)}] {keyword} ──")
            all_results.extend(self.search_popular(keyword))
            time.sleep(1)
            all_results.extend(self.search_blog(keyword))
            time.sleep(1)
            all_results.extend(self.search_place(keyword))
            if idx < len(keywords):
                self.logger.info(f"{delay}초 대기...")
                time.sleep(delay)

        self.logger.info(f"크롤링 완료 (총 {len(all_results)}개)")
        return all_results

    # ──────────────────────────────────────────────
    # 결과 저장
    # ──────────────────────────────────────────────

    FIELDS = ['type', 'rank', 'keyword', 'title', 'url',
              'blog_name', 'post_date', 'description', 'search_date', 'search_time']

    def export_to_json(self, results, filename='results.json'):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        self.logger.info(f"JSON 저장: {filename}")

    def export_to_csv(self, results, filename='results.csv'):
        if not results:
            return
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELDS)
            writer.writeheader()
            writer.writerows(results)
        self.logger.info(f"CSV 저장: {filename}")

    def export_to_markdown(self, results, filename='results.md'):
        if not results:
            return
        grouped = defaultdict(lambda: defaultdict(list))
        for r in results:
            grouped[r['keyword']][r['type']].append(r)

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# 네이버 블로그 & 플레이스 순위\n\n")
            f.write(f"수집 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            for keyword, types in grouped.items():
                f.write(f"---\n\n## 키워드: {keyword}\n\n")

                for type_name in ['인기글', '블로그', '플레이스']:
                    items = types.get(type_name, [])
                    if not items:
                        continue
                    f.write(f"### {type_name} 순위\n\n")
                    for item in items:
                        f.write(f"**{item['rank']}위** {item['title']}\n")
                        if type_name in ('인기글', '블로그'):
                            if item['blog_name']:
                                f.write(f"- 블로그: {item['blog_name']}\n")
                            if item['post_date']:
                                f.write(f"- 작성일: {item['post_date']}\n")
                        else:
                            if item['blog_name']:
                                f.write(f"- 카테고리: {item['blog_name']}\n")
                            if item['post_date']:
                                f.write(f"- 전화: {item['post_date']}\n")
                            if item['description']:
                                f.write(f"- 주소: {item['description']}\n")
                        f.write(f"- URL: {item['url']}\n\n")

        self.logger.info(f"Markdown 저장: {filename}")

    def print_summary(self, results):
        popular = [r for r in results if r['type'] == '인기글']
        blog    = [r for r in results if r['type'] == '블로그']
        place   = [r for r in results if r['type'] == '플레이스']

        print("\n" + "=" * 60)
        print("크롤링 결과 요약")
        print("=" * 60)
        print(f"인기글 {len(popular)}개  /  블로그 {len(blog)}개  /  플레이스 {len(place)}개  /  합계 {len(results)}개\n")

        keywords = list(dict.fromkeys(r['keyword'] for r in results))
        for kw in keywords:
            kw_pop   = [r for r in popular if r['keyword'] == kw]
            kw_blog  = [r for r in blog    if r['keyword'] == kw]
            kw_place = [r for r in place   if r['keyword'] == kw]
            print(f"[{kw}]")
            for r in kw_pop:
                print(f"  인기글 {r['rank']}위: {r['title'][:45]}  ({r['blog_name']})")
            for r in kw_blog:
                print(f"  블로그 {r['rank']}위: {r['title'][:45]}  ({r['blog_name']})")
            for r in kw_place:
                print(f"  플레이스 {r['rank']}위: {r['title']}  {r['description'][:30]}")
        print("=" * 60)


def main():
    try:
        crawler = NaverSearchCrawler('config.json')
        results = crawler.crawl_all_keywords()

        if not results:
            print("수집된 결과가 없습니다.")
            return

        crawler.export_to_json(results)
        crawler.export_to_csv(results)
        crawler.export_to_markdown(results)

        # Google Sheets 업로드
        sheets_config = crawler.config.get('google_sheets', {}).copy()
        if os.environ.get('GOOGLE_SHEETS_ENABLED', '').lower() == 'true':
            sheets_config['enabled'] = True
        if os.environ.get('GOOGLE_SHEETS_SPREADSHEET_ID'):
            sheets_config['spreadsheet_id'] = os.environ['GOOGLE_SHEETS_SPREADSHEET_ID']

        if sheets_config.get('enabled', False):
            if not SHEETS_AVAILABLE:
                crawler.logger.warning("google-api-python-client 미설치")
            else:
                handler = GoogleSheetsHandler(
                    credentials_path=sheets_config.get('credentials_path', 'credentials.json'),
                    spreadsheet_id=sheets_config.get('spreadsheet_id') or None,
                    sheet_name=sheets_config.get('sheet_name', '크롤링결과')
                )
                url = handler.upload_results(results)
                if url:
                    print(f"\nGoogle Sheets: {url}")

        crawler.print_summary(results)

    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
