# 한국형 AI 답글 우선순위 시스템 개선 완료

## 🎯 개선 목표
사장님 확인 시스템을 단순하고 직관적으로 만들어, 설정된 시간 후 자동으로 답글이 달리도록 개선

## 📋 변경사항

### 1. 우선순위 단순화 (5단계 → 4단계)

**이전 (복잡함):**
- URGENT, HIGH, MEDIUM, LOW, AUTO

**현재 (단순함):**
- **DANGER**: 위험 - 항상 사장님 확인 필요 (무제한 대기)
- **NORMAL**: 일반 - negative_review_delay_hours 후 자동 답글  
- **CHECK**: 체크 - 개인화 필요한 긍정 리뷰 (짧은 지연)
- **AUTO**: 자동 - 즉시 자동 답글

### 2. 분류 기준 최적화

#### DANGER (위험 - 무제한 대기)
- 법적 문제: 소비자보호원, 보건소, 고소, 신고
- 위생 문제: 식중독, 벌레, 이물질, 곰팡이
- 심각한 불만: 최악, 다시는, 절대, 비추천
- 1점 리뷰 전체

#### NORMAL (일반 - 설정 시간 후 자동)
- 환불/클레임: 환불, 돈돌려, 반품
- 일반 불만: 실망, 별로, 불친절, 짜증
- 직접 연락 요구: 전화, 연락, 답변, 설명
- 2-3점 리뷰

#### CHECK (체크 - 개인화 필요)
- 질문 포함 긍정: 메뉴, 추천, 문의, 궁금
- 혼재된 의견: 하지만, 그런데, 아쉽 (4-5점 리뷰)

#### AUTO (자동 - 즉시 처리)
- 단순 긍정 리뷰 (4-5점, 문제없음)

### 3. 지연 시간 설정

```python
if priority == ReviewPriority.DANGER:
    # 위험: 항상 사장님 확인 필요 (무제한 대기)
    return "high_risk", 0, True

elif priority == ReviewPriority.NORMAL:
    # 일반: negative_review_delay_hours 후 자동 답글
    return "medium_risk", negative_delay_hours, False

elif priority == ReviewPriority.CHECK:
    # 체크: 개인화 필요 (최대 12시간)
    return "low_risk", min(negative_delay_hours, 12), False

elif priority == ReviewPriority.AUTO:
    # 자동: 즉시 자동 답글
    return "low_risk", 0, False
```

## 🔄 동작 방식

1. **리뷰 수집** → 우선순위 자동 분류
2. **DANGER**: 사장님이 승인할 때까지 무한 대기
3. **NORMAL**: 24시간(설정값) 후 사장님이 응답 안하면 자동 답글
4. **CHECK**: 12시간 후 자동 답글 (개인화 여지 있지만 긍정적)
5. **AUTO**: 즉시 자동 답글 (단순 긍정)

## 🧪 테스트 결과

```
Priority Classification Test:
식중독 걸렸습니다... -> DANGER (PASS)
환불 해주세요... -> NORMAL (PASS)  
메뉴 문의드려요... -> CHECK (PASS)
맛있어요... -> AUTO (PASS)

AI Reply Manager Integration:
Case 1: 식중독 걸렸습니다 -> high_risk, 0h delay, approval: True
Case 2: 불친절하네요 -> medium_risk, 24h delay, approval: False
Case 3: 메뉴 문의드려요 -> low_risk, 12h delay, approval: False  
Case 4: 맛있어요 -> low_risk, 0h delay, approval: False
```

## 📁 수정된 파일

1. **korean_reply_system.py**
   - `ReviewPriority` enum 4단계로 단순화
   - `get_priority_level()` 로직 최적화

2. **ai_reply_manager.py**  
   - `_map_priority_to_settings()` 새로 생성
   - `analyze_review()` 메서드 업데이트
   - 매장별 `negative_review_delay_hours` 설정 연동

3. **test_korean_reply.py**
   - 테스트 케이스 4단계로 업데이트

## ✅ 완료 상태

- [x] 5단계 → 4단계 우선순위 단순화  
- [x] 매장 설정 `negative_review_delay_hours` 연동
- [x] DANGER 리뷰 무한 대기 처리
- [x] NORMAL 리뷰 자동 답글 처리  
- [x] 통합 테스트 완료
- [x] 기존 AI 답글 매니저와 호환성 유지

## 🚀 결과

**"사장님 확인 시스템이 단순했으면 좋겠어"** 요구사항 완료!

이제 매장에서 24시간으로 설정하면, DANGER를 제외한 모든 리뷰가 24시간 후에는 자동으로 답글이 달립니다.