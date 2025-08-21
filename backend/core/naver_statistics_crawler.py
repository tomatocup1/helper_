#!/usr/bin/env python3
"""
네이버 스마트플레이스 통계 크롤링 엔진
- 기존 네이버 로그인 시스템 재사용
- URL 기반 날짜 필터 적용으로 단순화
- 방문 전/후 지표, 유입 키워드/채널 데이터 수집
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from supabase import create_client, Client
from dotenv import load_dotenv

# 프로젝트 루트 경로를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

from naver_login_auto import NaverAutoLogin

class NaverStatisticsCrawler:
    def __init__(self, headless=True, timeout=30000, force_fresh_login=False):
        self.headless = headless
        self.timeout = timeout
        self.force_fresh_login = force_fresh_login
        
        # 기존 로그인 시스템 재사용
        self.login_system = NaverAutoLogin(
            headless=headless, 
            timeout=timeout, 
            force_fresh_login=force_fresh_login
        )
        
        # Supabase 클라이언트 초기화
        load_dotenv()
        supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_service_key:
            raise ValueError("Supabase 환경변수가 설정되지 않았습니다. NEXT_PUBLIC_SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY를 확인하세요.")
        
        self.supabase: Client = create_client(supabase_url, supabase_service_key)

    async def crawl_statistics(self, platform_id: str, platform_password: str, 
                             store_id: str, user_id: str, target_date: str = None) -> Dict:
        """통계 크롤링 메인 함수"""
        try:
            print(f"Starting statistics crawling for store: {store_id}")
            
            # 타겟 날짜 설정 (기본값: 전날)
            if not target_date:
                yesterday = datetime.now() - timedelta(days=1)
                target_date = yesterday.strftime('%Y-%m-%d')
            
            print(f"타겟 날짜: {target_date}")
            
            # 로그인 처리 및 브라우저 세션 유지
            login_result = await self.login_system.login(platform_id, platform_password, keep_browser_open=True)
            if not login_result['success']:
                return {
                    'success': False,
                    'error': f"로그인 실패: {login_result.get('error', 'Unknown error')}",
                    'statistics_collected': False
                }
            
            print("로그인 성공 - 통계 페이지 접속 중...")
            
            # 기존 브라우저 세션을 사용하여 통계 페이지 크롤링
            browser = login_result['browser']
            playwright = login_result['playwright'] 
            page = login_result['page']
            
            try:
                # 브라우저 연결 상태 확인
                current_url = page.url
                print(f"브라우저 연결 상태 양호 - 현재 URL: {current_url}")
                
                # 통계 데이터 수집
                statistics_data = await self._crawl_statistics_page_with_session(
                    browser, page, store_id, target_date
                )
                
                return await self._process_statistics_results(statistics_data, store_id, user_id, target_date)
                
            except Exception as e:
                print(f"통계 크롤링 실행 중 오류: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'statistics_collected': False
                }
            finally:
                # 크롤링 완료 후 브라우저 정리
                try:
                    if browser:
                        await browser.close()
                    if playwright:
                        await playwright.stop()
                except Exception as e:
                    print(f"브라우저 정리 중 오류: {str(e)}")
            
        except Exception as e:
            print(f"통계 크롤링 중 오류 발생: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'statistics_collected': False
            }

    async def _crawl_statistics_page_with_session(self, browser, page, store_id: str, target_date: str) -> Dict:
        """기존 브라우저 세션을 사용한 통계 페이지 크롤링"""
        try:
            # URL 기반 날짜 필터 적용으로 단순화된 통계 페이지 URL 생성
            statistics_url = self._build_statistics_url(store_id, target_date)
            
            print(f"통계 페이지 접속: {statistics_url}")
            await page.goto(statistics_url, wait_until='networkidle', timeout=self.timeout)
            
            # 페이지 로딩 완료 대기
            await page.wait_for_timeout(3000)
            
            # 팝업 닫기 처리
            await self._close_popup_if_exists(page)
            
            # 통계 데이터 수집
            statistics_data = {
                'date': target_date,
                'store_id': store_id
            }
            
            # 방문 전 지표 수집
            pre_visit_metrics = await self._extract_pre_visit_metrics(page)
            statistics_data.update(pre_visit_metrics)
            
            # 방문 후 지표 수집
            post_visit_metrics = await self._extract_post_visit_metrics(page)
            statistics_data.update(post_visit_metrics)
            
            # 유입 채널 데이터 수집
            inflow_channels = await self._extract_inflow_channels(page)
            statistics_data['inflow_channels'] = inflow_channels
            
            # 유입 키워드 데이터 수집  
            inflow_keywords = await self._extract_inflow_keywords(page)
            statistics_data['inflow_keywords'] = inflow_keywords
            
            print(f"통계 데이터 수집 완료: {len(statistics_data)}개 항목")
            return statistics_data
            
        except Exception as e:
            print(f"통계 페이지 크롤링 중 오류: {str(e)}")
            return {}

    def _build_statistics_url(self, store_id: str, target_date: str) -> str:
        """URL 기반 날짜 필터가 적용된 통계 페이지 URL 생성"""
        # URL 파라미터에 직접 날짜 지정으로 드롭박스 조작 불필요
        base_url = f"https://new.smartplace.naver.com/bizes/place/{store_id}/statistics"
        params = {
            'endDate': target_date,
            'startDate': target_date,
            'term': 'daily',
            'menu': 'reports'
        }
        
        param_string = '&'.join([f"{key}={value}" for key, value in params.items()])
        return f"{base_url}?{param_string}"

    async def _close_popup_if_exists(self, page) -> bool:
        """통계 페이지에서 나타나는 팝업 닫기"""
        try:
            print("팝업 확인 및 닫기 처리 중...")
            
            popup_close_selectors = [
                "i.fn-booking.fn-booking-close1",
                ".fn-booking-close1", 
                "i[aria-label='닫기']",
                ".popup_close",
                ".modal_close",
                "button[class*='close']",
                ".btn_close",
                "[data-action='close']",
                ".layer_close"
            ]
            
            for selector in popup_close_selectors:
                try:
                    close_button = await page.wait_for_selector(selector, timeout=2000)
                    if close_button:
                        is_visible = await close_button.is_visible()
                        if is_visible:
                            print(f"팝업 닫기 버튼 발견: {selector}")
                            await close_button.click()
                            await page.wait_for_timeout(1000)
                            print("팝업 닫기 완료")
                            return True
                except Exception:
                    continue
                    
            print("팝업이 없거나 이미 닫혀있음")
            return False
            
        except Exception as e:
            print(f"팝업 처리 중 오류: {str(e)}")
            return False

    async def _extract_pre_visit_metrics(self, page) -> Dict:
        """방문 전 지표 추출 (플레이스 유입, 예약·주문 신청, 스마트콜 통화)"""
        try:
            print("방문 전 지표 추출 중...")
            pre_visit_data = {}
            
            # 방문 전 지표 섹션 선택자
            pre_visit_section_selector = "div.ReportSummary_root__wt2sA:has(h3:contains('방문 전 지표'))"
            
            try:
                pre_visit_section = await page.wait_for_selector(pre_visit_section_selector, timeout=10000)
                if not pre_visit_section:
                    print("방문 전 지표 섹션을 찾을 수 없음")
                    return pre_visit_data
                
                # 모든 지표 항목 추출
                metric_items = await pre_visit_section.query_selector_all("li.ReportSummary_item__UUsqu")
                
                for item in metric_items:
                    # 지표명 추출
                    label_element = await item.query_selector("span.ReportSummary_label__pnVGQ")
                    if not label_element:
                        continue
                        
                    label_text = await label_element.text_content()
                    label_text = label_text.strip()
                    
                    # 현재 값 추출
                    value_element = await item.query_selector("em.ReportSummary_number__ATg7x")
                    current_value = 0
                    if value_element:
                        value_text = await value_element.text_content()
                        current_value = self._extract_number_from_text(value_text)
                    
                    # 전일 대비 증감률 추출
                    percent_element = await item.query_selector("span.ReportSummary_percent__uqs6_")
                    change_rate = None
                    if percent_element:
                        percent_text = await percent_element.text_content()
                        change_rate = self._extract_percentage_from_text(percent_text)
                    
                    # 전일 수치 추출
                    desc_element = await item.query_selector("span.ReportSummary_desc__V__vr")
                    previous_value = None
                    if desc_element:
                        desc_text = await desc_element.text_content()
                        previous_value = self._extract_previous_value(desc_text)
                    
                    # 데이터 저장
                    if "플레이스 유입" in label_text:
                        pre_visit_data['place_inflow'] = current_value
                        pre_visit_data['place_inflow_change'] = change_rate
                        pre_visit_data['place_inflow_previous'] = previous_value
                    elif "예약" in label_text or "주문" in label_text:
                        pre_visit_data['reservation_order'] = current_value
                        pre_visit_data['reservation_order_change'] = change_rate
                        pre_visit_data['reservation_order_previous'] = previous_value
                    elif "스마트콜" in label_text:
                        pre_visit_data['smart_call'] = current_value
                        pre_visit_data['smart_call_change'] = change_rate
                        pre_visit_data['smart_call_previous'] = previous_value
                
                print(f"방문 전 지표 추출 완료: {len(pre_visit_data)}개 항목")
                
            except Exception as e:
                print(f"방문 전 지표 섹션 처리 중 오류: {str(e)}")
            
            return pre_visit_data
            
        except Exception as e:
            print(f"방문 전 지표 추출 중 오류: {str(e)}")
            return {}

    async def _extract_post_visit_metrics(self, page) -> Dict:
        """방문 후 지표 추출 (리뷰 등록)"""
        try:
            print("방문 후 지표 추출 중...")
            post_visit_data = {}
            
            # 방문 후 지표 섹션 선택자
            post_visit_section_selector = "div.ReportSummary_root__wt2sA:has(h3:contains('방문 후 지표'))"
            
            try:
                post_visit_section = await page.wait_for_selector(post_visit_section_selector, timeout=10000)
                if not post_visit_section:
                    print("방문 후 지표 섹션을 찾을 수 없음")
                    return post_visit_data
                
                # 리뷰 등록 지표 항목 추출
                metric_items = await post_visit_section.query_selector_all("li.ReportSummary_item__UUsqu")
                
                for item in metric_items:
                    # 지표명 추출
                    label_element = await item.query_selector("span.ReportSummary_label__pnVGQ")
                    if not label_element:
                        continue
                        
                    label_text = await label_element.text_content()
                    label_text = label_text.strip()
                    
                    if "리뷰 등록" in label_text:
                        # 현재 값 추출
                        value_element = await item.query_selector("em.ReportSummary_number__ATg7x")
                        current_value = 0
                        if value_element:
                            value_text = await value_element.text_content()
                            current_value = self._extract_number_from_text(value_text)
                        
                        # 전일 대비 증감률 추출
                        percent_element = await item.query_selector("span.ReportSummary_percent__uqs6_")
                        change_rate = None
                        if percent_element:
                            percent_text = await percent_element.text_content()
                            change_rate = self._extract_percentage_from_text(percent_text)
                        
                        # 전일 수치 추출
                        desc_element = await item.query_selector("span.ReportSummary_desc__V__vr")
                        previous_value = None
                        if desc_element:
                            desc_text = await desc_element.text_content()
                            previous_value = self._extract_previous_value(desc_text)
                        
                        # 데이터 저장
                        post_visit_data['review_registration'] = current_value
                        post_visit_data['review_registration_change'] = change_rate
                        post_visit_data['review_registration_previous'] = previous_value
                        break
                
                print(f"방문 후 지표 추출 완료: {len(post_visit_data)}개 항목")
                
            except Exception as e:
                print(f"방문 후 지표 섹션 처리 중 오류: {str(e)}")
            
            return post_visit_data
            
        except Exception as e:
            print(f"방문 후 지표 추출 중 오류: {str(e)}")
            return {}

    async def _extract_inflow_channels(self, page) -> List[Dict]:
        """유입 채널 데이터 추출"""
        try:
            print("유입 채널 데이터 추출 중...")
            
            # 유입채널 탭 클릭
            try:
                channel_tab_selector = "button.SectionBox_button_tab__f3OJb:contains('유입채널')"
                await page.click(channel_tab_selector)
                await page.wait_for_timeout(2000)
                print("유입채널 탭 클릭 완료")
            except Exception as e:
                print(f"유입채널 탭 클릭 중 오류: {str(e)}")
                # 탭 클릭이 실패해도 데이터 추출 시도
            
            channels_data = []
            
            # 유입채널 목록 추출
            channel_list_selector = "ol.inflow_list.type_report"
            channel_list = await page.query_selector(channel_list_selector)
            
            if channel_list:
                channel_items = await channel_list.query_selector_all("li.Statistics_inflow_list_item__DljLO")
                
                for item in channel_items:
                    try:
                        # 순위 추출
                        rank_element = await item.query_selector("span.Statistics_ranking__eDYQA")
                        rank = 0
                        if rank_element:
                            rank_text = await rank_element.text_content()
                            rank = self._extract_number_from_text(rank_text)
                        
                        # 채널명 추출
                        name_element = await item.query_selector("span.Statistics_name__mA27g")
                        channel_name = ""
                        if name_element:
                            channel_name = await name_element.text_content()
                            channel_name = channel_name.strip()
                        
                        # 유입 횟수 추출
                        count_element = await item.query_selector("span.Statistics_percent___W5cW")
                        count = 0
                        if count_element:
                            count_text = await count_element.text_content()
                            count = self._extract_number_from_text(count_text)
                        
                        if channel_name and rank > 0:
                            channels_data.append({
                                'rank': rank,
                                'channel_name': channel_name,
                                'count': count
                            })
                    
                    except Exception as e:
                        print(f"개별 유입채널 항목 처리 중 오류: {str(e)}")
                        continue
            
            print(f"유입 채널 데이터 추출 완료: {len(channels_data)}개 채널")
            return channels_data
            
        except Exception as e:
            print(f"유입 채널 추출 중 오류: {str(e)}")
            return []

    async def _extract_inflow_keywords(self, page) -> List[Dict]:
        """유입 키워드 데이터 추출"""
        try:
            print("유입 키워드 데이터 추출 중...")
            
            # 유입키워드 탭 클릭
            try:
                keyword_tab_selector = "button.SectionBox_button_tab__f3OJb:contains('유입키워드')"
                await page.click(keyword_tab_selector)
                await page.wait_for_timeout(2000)
                print("유입키워드 탭 클릭 완료")
            except Exception as e:
                print(f"유입키워드 탭 클릭 중 오류: {str(e)}")
                # 탭 클릭이 실패해도 데이터 추출 시도
            
            keywords_data = []
            
            # 유입키워드 목록 추출
            keyword_list_selector = "ol.inflow_list.type_report"
            keyword_list = await page.query_selector(keyword_list_selector)
            
            if keyword_list:
                keyword_items = await keyword_list.query_selector_all("li.Statistics_inflow_list_item__DljLO")
                
                for item in keyword_items:
                    try:
                        # 순위 추출
                        rank_element = await item.query_selector("span.Statistics_ranking__eDYQA")
                        rank = 0
                        if rank_element:
                            rank_text = await rank_element.text_content()
                            rank = self._extract_number_from_text(rank_text)
                        
                        # 키워드 추출
                        name_element = await item.query_selector("span.Statistics_name__mA27g")
                        keyword = ""
                        if name_element:
                            keyword = await name_element.text_content()
                            keyword = keyword.strip()
                        
                        # 검색 횟수 추출
                        count_element = await item.query_selector("span.Statistics_percent___W5cW")
                        count = 0
                        if count_element:
                            count_text = await count_element.text_content()
                            count = self._extract_number_from_text(count_text)
                        
                        if keyword and rank > 0:
                            keywords_data.append({
                                'rank': rank,
                                'keyword': keyword,
                                'count': count
                            })
                    
                    except Exception as e:
                        print(f"개별 유입키워드 항목 처리 중 오류: {str(e)}")
                        continue
            
            print(f"유입 키워드 데이터 추출 완료: {len(keywords_data)}개 키워드")
            return keywords_data
            
        except Exception as e:
            print(f"유입 키워드 추출 중 오류: {str(e)}")
            return []

    def _extract_number_from_text(self, text: str) -> int:
        """텍스트에서 숫자 추출"""
        try:
            import re
            # 숫자만 추출 (콤마 제거)
            numbers = re.findall(r'[\d,]+', text.replace(',', ''))
            if numbers:
                return int(numbers[0])
            return 0
        except Exception:
            return 0

    def _extract_percentage_from_text(self, text: str) -> Optional[float]:
        """텍스트에서 퍼센트 값 추출"""
        try:
            import re
            # 퍼센트 값 추출 (100% 형태)
            percent_match = re.search(r'(\d+(?:\.\d+)?)%', text)
            if percent_match:
                return float(percent_match.group(1))
            return None
        except Exception:
            return None

    def _extract_previous_value(self, text: str) -> Optional[int]:
        """전일 수치 추출 ('전일 111회' 형태)"""
        try:
            import re
            # '전일 숫자회' 패턴에서 숫자 추출
            prev_match = re.search(r'전일\s*(\d+)', text)
            if prev_match:
                return int(prev_match.group(1))
            return None
        except Exception:
            return None

    async def _process_statistics_results(self, statistics_data: Dict, store_id: str, user_id: str, target_date: str) -> Dict:
        """통계 결과 처리 및 Supabase statistics_naver 테이블에 저장"""
        try:
            if not statistics_data:
                print("수집된 통계 데이터가 없습니다.")
                return {
                    'success': False,
                    'error': 'No statistics data collected',
                    'statistics_collected': False
                }
            
            # platform_store_id 조회
            platform_store_result = self.supabase.table('platform_stores').select('id').eq('user_id', user_id).eq('platform_store_id', store_id).eq('platform', 'naver').single().execute()
            
            if not platform_store_result.data:
                print(f"platform_stores 테이블에서 store_id {store_id}를 찾을 수 없습니다.")
                return {
                    'success': False,
                    'error': f'Store not found in platform_stores: {store_id}',
                    'statistics_collected': False
                }
            
            platform_store_uuid = platform_store_result.data['id']
            print(f"Platform store UUID: {platform_store_uuid}")
            
            # 기존 통계 데이터 확인 (중복 방지)
            existing_stats_result = self.supabase.table('statistics_naver').select('id').eq('platform_store_id', platform_store_uuid).eq('date', target_date).execute()
            
            # statistics_naver 테이블 구조에 맞게 데이터 변환
            stats_record = {
                'platform_store_id': platform_store_uuid,
                'date': target_date,
                'place_inflow': statistics_data.get('place_inflow', 0),
                'place_inflow_change': statistics_data.get('place_inflow_change'),
                'reservation_order': statistics_data.get('reservation_order', 0),
                'reservation_order_change': statistics_data.get('reservation_order_change'),
                'smart_call': statistics_data.get('smart_call', 0),
                'smart_call_change': statistics_data.get('smart_call_change'),
                'review_registration': statistics_data.get('review_registration', 0),
                'review_registration_change': statistics_data.get('review_registration_change'),
                'inflow_channels': json.dumps(statistics_data.get('inflow_channels', []), ensure_ascii=False),
                'inflow_keywords': json.dumps(statistics_data.get('inflow_keywords', []), ensure_ascii=False),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            if existing_stats_result.data:
                # 기존 데이터 업데이트
                print(f"기존 통계 데이터 업데이트: {target_date}")
                update_result = self.supabase.table('statistics_naver').update(stats_record).eq('platform_store_id', platform_store_uuid).eq('date', target_date).execute()
                
                if update_result.data:
                    print("통계 데이터 업데이트 완료")
                    return {
                        'success': True,
                        'statistics_collected': True,
                        'action': 'updated',
                        'date': target_date,
                        'table_used': 'statistics_naver'
                    }
                else:
                    raise Exception("Supabase 업데이트 실패")
            else:
                # 새 데이터 삽입
                print(f"새 통계 데이터 삽입: {target_date}")
                insert_result = self.supabase.table('statistics_naver').insert([stats_record]).execute()
                
                if insert_result.data:
                    print("통계 데이터 삽입 완료")
                    return {
                        'success': True,
                        'statistics_collected': True,
                        'action': 'inserted',
                        'date': target_date,
                        'table_used': 'statistics_naver'
                    }
                else:
                    raise Exception("Supabase 삽입 실패")
            
        except Exception as e:
            error_msg = f"통계 데이터 처리 중 오류: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'statistics_collected': False
            }

async def main():
    parser = argparse.ArgumentParser(description='네이버 스마트플레이스 통계 크롤링')
    parser.add_argument('--email', required=True, help='네이버 이메일/아이디')
    parser.add_argument('--password', required=True, help='네이버 비밀번호')
    parser.add_argument('--store-id', required=True, help='매장 ID (platform_store_id)')
    parser.add_argument('--user-id', required=True, help='사용자 ID (UUID)')
    parser.add_argument('--date', help='통계 날짜 (YYYY-MM-DD), 기본값: 전날')
    parser.add_argument('--headless', action='store_true', help='헤드리스 모드')
    parser.add_argument('--timeout', type=int, default=30000, help='타임아웃 (ms)')
    parser.add_argument('--force-fresh', action='store_true', help='기존 세션 무시하고 강제 새 로그인')
    
    args = parser.parse_args()
    
    crawler = NaverStatisticsCrawler(
        headless=args.headless, 
        timeout=args.timeout,
        force_fresh_login=args.force_fresh
    )
    
    result = await crawler.crawl_statistics(
        args.email, 
        args.password, 
        args.store_id,
        args.user_id,
        args.date
    )
    
    # 결과 출력 (JSON 형태)
    print(f"STATISTICS_RESULT:{json.dumps(result, ensure_ascii=False)}")
    
    return result['success']

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)