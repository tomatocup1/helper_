#!/usr/bin/env python3
"""
CoupangEats 테이블 기반 리뷰 추출 테스트
사용자가 제공한 실제 HTML 구조를 기반으로 새로운 추출 로직 검증
"""

import asyncio
import sys
import os
from playwright.async_api import async_playwright
import logging

# 현재 디렉토리를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 실제 HTML 구조 (사용자 제공) - 모든 tr을 하나의 tbody에 포함
MOCK_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CoupangEats 리뷰 테스트</title>
</head>
<body>
    <div class="review-container">
        <table>
            <tbody>
                <!-- 첫 번째 리뷰 (텍스트 있음) -->
                <tr>
                    <td class="eqn7l9b0">
                        <!-- 좌측: 요약 정보 -->
                        <div>김** 44회 주문</div>
                        <div>주문번호 12CCY4ㆍ2025-09-16</div>
                        <div>치킨 2마리</div>
                        <div>콜라 1개</div>
                    </td>
                    <td class="eqn7l9b9">
                        <!-- 우측: 상세 정보 -->
                        <div>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="orange">★</svg>
                        </div>
                        <p class="css-16m6tj eqn7l9b5">정말 맛있어요! 치킨이 바삭하고 소스도 좋았습니다.</p>
                        <div>
                            <button>사장님 댓글 등록하기</button>
                        </div>
                    </td>
                </tr>

                <!-- 두 번째 리뷰 (텍스트 없음 - 별점만) -->
                <tr>
                    <td class="eqn7l9b0">
                        <div>최** 2회 주문</div>
                        <div>주문번호 9XK4L1ㆍ2025-09-15</div>
                        <div>피자 1판</div>
                    </td>
                    <td class="eqn7l9b9">
                        <div>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="gray">★</svg>
                        </div>
                        <!-- 텍스트 없음 -->
                        <div>
                            <button>사장님 댓글 등록하기</button>
                        </div>
                    </td>
                </tr>

                <!-- 세 번째 리뷰 -->
                <tr>
                    <td class="eqn7l9b0">
                        <div>박** 15회 주문</div>
                        <div>주문번호 1SU2MKㆍ2025-09-14</div>
                        <div>햄버거 세트</div>
                        <div>감자튀김 추가</div>
                    </td>
                    <td class="eqn7l9b9">
                        <div>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="gray">★</svg>
                            <svg width="20" height="20" fill="gray">★</svg>
                        </div>
                        <p class="css-16m6tj eqn7l9b5">배송이 조금 늦었지만 맛은 좋았어요</p>
                        <div>
                            <button>사장님 댓글 등록하기</button>
                        </div>
                    </td>
                </tr>

                <!-- 네 번째 리뷰 -->
                <tr>
                    <td class="eqn7l9b0">
                        <div>이** 8회 주문</div>
                        <div>주문번호 7QP9X2ㆍ2025-09-13</div>
                        <div>짜장면</div>
                    </td>
                    <td class="eqn7l9b9">
                        <div>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="orange">★</svg>
                            <svg width="20" height="20" fill="orange">★</svg>
                        </div>
                        <p class="css-16m6tj eqn7l9b5">항상 맛있게 잘 먹고 있습니다. 다음에도 주문할게요!</p>
                        <div>
                            <button>사장님 댓글 등록하기</button>
                        </div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</body>
</html>
"""

async def test_table_extraction():
    """테이블 기반 리뷰 추출 테스트"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Mock HTML 로드
        await page.set_content(MOCK_HTML)

        logger.info("Mock HTML 로드 완료")

        # 새로운 테이블 기반 추출 로직 테스트
        reviews = []

        # tbody 요소 찾기
        tbody_elements = await page.query_selector_all('tbody')
        logger.info(f"tbody 요소 {len(tbody_elements)}개 발견")

        for tbody in tbody_elements:
            tr_elements = await tbody.query_selector_all('tr')
            logger.info(f"tbody 내 tr 요소 {len(tr_elements)}개 발견")

            for i, tr in enumerate(tr_elements):
                try:
                    tr_text = await tr.inner_text()
                    tr_html = await tr.inner_html()

                    # 리뷰 행인지 확인하는 조건들
                    has_reviewer = '**' in tr_text and '회 주문' in tr_text
                    has_order_number = '주문번호' in tr_text and 'ㆍ' in tr_text
                    has_reply_button = '사장님 댓글 등록하기' in tr_text
                    has_table_structure = 'eqn7l9b0' in tr_html and 'eqn7l9b9' in tr_html
                    is_reasonable_size = 50 < len(tr_text) < 5000  # 최소 50자에서 5000자 사이

                    logger.info(f"TR {i+1} 검사 결과:")
                    logger.info(f"  - has_reviewer: {has_reviewer}")
                    logger.info(f"  - has_order_number: {has_order_number}")
                    logger.info(f"  - has_reply_button: {has_reply_button}")
                    logger.info(f"  - has_table_structure: {has_table_structure}")
                    logger.info(f"  - is_reasonable_size: {is_reasonable_size} (text length: {len(tr_text)})")
                    logger.info(f"  - TR 텍스트: {tr_text[:200]}...")

                    if (has_reviewer and has_order_number and has_reply_button and
                        has_table_structure and is_reasonable_size):

                        logger.info(f"✓ 리뷰 TR {i+1} 발견: {tr_text[:100]}...")

                        # 데이터 추출
                        review_data = await extract_review_from_tr(tr, i+1)
                        if review_data:
                            reviews.append(review_data)
                        else:
                            logger.warning(f"TR {i+1} 데이터 추출 실패")
                    else:
                        logger.info(f"✗ TR {i+1}은 리뷰가 아님")

                except Exception as e:
                    logger.error(f"TR {i} 처리 중 오류: {e}")
                    continue

        await browser.close()

        # 결과 출력
        logger.info(f"\n총 {len(reviews)}개의 리뷰 추출 완료:")
        for i, review in enumerate(reviews, 1):
            logger.info(f"\n리뷰 {i}:")
            logger.info(f"  - 리뷰어: {review['reviewer_name']}")
            logger.info(f"  - 주문 횟수: {review['order_count']}")
            logger.info(f"  - 별점: {review['rating']}")
            logger.info(f"  - 주문번호: {review['order_number']}")
            logger.info(f"  - 주문 날짜: {review['review_date']}")
            logger.info(f"  - 리뷰 텍스트: '{review['review_text']}'")
            logger.info(f"  - 메뉴: {review['menu_items']}")
            logger.info(f"  - ID: {review['coupangeats_review_id']}")

        return reviews

async def extract_review_from_tr(review_tr, review_number: int):
    """TR에서 리뷰 데이터 추출 - 실제 구현"""
    try:
        import re
        import hashlib

        logger.info(f"TR 리뷰 {review_number} 추출 시작...")

        # TR 전체 텍스트 및 HTML 가져오기
        tr_text = await review_tr.inner_text()
        tr_html = await review_tr.inner_html()

        # TD 요소들 찾기
        left_td = await review_tr.query_selector('td.eqn7l9b0')
        right_td = await review_tr.query_selector('td.eqn7l9b9')

        if not left_td or not right_td:
            logger.warning(f"TR {review_number}: 좌우 TD 구조를 찾을 수 없음")
            return None

        # 1. 리뷰어 정보 추출
        reviewer_name = ""
        order_count = ""

        reviewer_match = re.search(r'([가-힣]+\*\*)\s*(\d+)회\s*주문', tr_text)
        if reviewer_match:
            reviewer_name = reviewer_match.group(1)
            order_count = reviewer_match.group(2)
            logger.info(f"리뷰어 정보: {reviewer_name}, 주문 횟수: {order_count}")
        else:
            logger.warning(f"TR {review_number}: 리뷰어 정보를 찾을 수 없음")
            return None

        # 2. 주문번호 추출
        order_number = ""
        order_date = ""
        order_match = re.search(r'주문번호\s*([A-Z0-9]+)ㆍ(\d{4}-\d{2}-\d{2})', tr_text)
        if order_match:
            order_number = order_match.group(1)
            order_date = order_match.group(2)
            logger.info(f"주문 정보: {order_number}, 날짜: {order_date}")

        # 3. 별점 추출
        rating = 0
        try:
            svg_elements = await right_td.query_selector_all('svg')
            filled_stars = 0
            for svg in svg_elements:
                # SVG의 fill 속성 확인 (HTML 속성으로)
                fill_attr = await svg.get_attribute('fill')
                if fill_attr and 'orange' in fill_attr:
                    filled_stars += 1
            rating = filled_stars
            logger.info(f"별점: {rating}점")
        except Exception as e:
            logger.debug(f"별점 추출 실패: {e}")

        # 4. 리뷰 텍스트 추출
        review_text = ""
        try:
            text_selectors = [
                'p.css-16m6tj.eqn7l9b5',
                'p[class*="css-16m6tj"]',
                'p[class*="eqn7l9b5"]',
                'td p',
                'div p'
            ]

            for selector in text_selectors:
                try:
                    text_element = await right_td.query_selector(selector)
                    if text_element:
                        review_text = await text_element.inner_text()
                        review_text = review_text.strip()
                        if review_text and len(review_text) > 5:
                            logger.info(f"리뷰 텍스트 추출 성공: {review_text[:50]}...")
                            break
                except Exception:
                    continue

            if not review_text:
                review_text = ""
                logger.info(f"리뷰 텍스트 없음 (별점만 있는 리뷰)")

        except Exception as e:
            logger.debug(f"리뷰 텍스트 추출 실패: {e}")
            review_text = ""

        # 5. 메뉴 정보 추출
        menu_items = []
        try:
            left_text = await left_td.inner_text()
            menu_lines = left_text.split('\\n')
            for line in menu_lines:
                line = line.strip()
                if (line and
                    any(ord(c) >= 0xAC00 and ord(c) <= 0xD7A3 for c in line) and
                    len(line) > 2 and len(line) < 50 and
                    '주문번호' not in line and '회 주문' not in line):
                    menu_items.append(line)
        except Exception as e:
            logger.debug(f"메뉴 정보 추출 실패: {e}")

        # 6. 고유 ID 생성
        if order_number:
            review_id = f"{order_number}_{reviewer_name}_{rating}"
        else:
            content_for_hash = f"{reviewer_name}_{review_text[:100]}_{rating}"
            review_id = hashlib.md5(content_for_hash.encode()).hexdigest()[:12]

        # 7. 리뷰 데이터 구성
        review_data = {
            'coupangeats_review_id': review_id,
            'reviewer_name': reviewer_name or "익명",
            'rating': rating,
            'review_text': review_text,
            'review_date': order_date,
            'order_number': order_number,
            'order_count': int(order_count) if order_count.isdigit() else 0,
            'menu_items': menu_items,
            'review_images': [],
            'platform': 'coupangeats'
        }

        logger.info(f"TR 리뷰 {review_number} 추출 완료: {reviewer_name} ({rating}점)")
        return review_data

    except Exception as e:
        logger.error(f"TR 리뷰 {review_number} 추출 실패: {e}")
        return None

if __name__ == "__main__":
    logger.info("CoupangEats 테이블 기반 리뷰 추출 테스트 시작")
    reviews = asyncio.run(test_table_extraction())

    print("\n" + "="*60)
    print("테스트 결과 요약:")
    print("="*60)
    print(f"추출된 리뷰 수: {len(reviews)}")
    print(f"예상 리뷰 수: 4")
    print(f"성공률: {len(reviews)/4*100:.1f}%")

    if len(reviews) == 4:
        print("SUCCESS: 모든 리뷰가 성공적으로 추출되었습니다!")
        print("\n특이사항:")
        text_reviews = [r for r in reviews if r['review_text']]
        no_text_reviews = [r for r in reviews if not r['review_text']]
        print(f"- 텍스트가 있는 리뷰: {len(text_reviews)}개")
        print(f"- 별점만 있는 리뷰: {len(no_text_reviews)}개")

        # 중복 ID 체크
        ids = [r['coupangeats_review_id'] for r in reviews]
        unique_ids = set(ids)
        if len(ids) == len(unique_ids):
            print("SUCCESS: 모든 리뷰 ID가 고유합니다!")
        else:
            print("ERROR: 중복 ID가 발견되었습니다!")

    else:
        print("ERROR: 일부 리뷰 추출에 실패했습니다.")