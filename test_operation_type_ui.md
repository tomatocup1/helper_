# 매장 운영 방식 UI 테스트 가이드

## 구현 완료 사항 ✅

### 1. 백엔드 API 수정
- `/api/user-stores/{user_id}`: operation_type 필드 추가
- `/api/reply-settings/{store_id}` GET: operation_type 조회 추가  
- `/api/reply-settings/{store_id}` POST: operation_type 저장 추가

### 2. 프론트엔드 UI 추가
- Store 및 ReplySettings 인터페이스에 operationType 필드 추가
- 매장 목록에 운영 방식 뱃지 표시
- 설정 페널에 운영 방식 선택 드롭다운 추가
- 운영 방식별 답글 톤 미리보기 업데이트

### 3. 운영 방식 옵션
- 🚚 배달전용 (`delivery_only`)
- 🏪 홀전용 (`dine_in_only`) 
- 📦 포장전용 (`takeout_only`)
- 🏪🚚 배달+홀 (`both`)

## 테스트 방법

### 1. 프론트엔드 테스트
```bash
cd frontend
npm run dev
# http://localhost:3000/owner-replies/settings 접속
```

### 2. 백엔드 테스트  
```bash
cd backend
python simple_baemin_api.py
# 포트 8002에서 API 서버 실행
```

### 3. 기능 테스트 체크리스트

#### 매장 목록 화면
- [ ] 각 매장에 운영 방식 뱃지가 표시되는가?
- [ ] 뱃지 색상과 아이콘이 올바른가?

#### 설정 화면  
- [ ] 운영 방식 드롭다운이 표시되는가?
- [ ] 4개 옵션이 모두 표시되는가?
- [ ] 선택 시 설명 텍스트가 변경되는가?
- [ ] 미리보기 답글이 운영 방식에 따라 변경되는가?

#### 저장 기능
- [ ] 운영 방식 변경 후 저장이 되는가?
- [ ] 페이지 새로고침 후에도 설정이 유지되는가?

### 4. 답글 톤별 미리보기 예시

#### 배달전용 매장
- 친근함: "다음에도 맛있는 음식으로 찾아뵐게요!"
- 정중함: "앞으로도 더 나은 서비스로 찾아뵐게요."
- 캐주얼: "다음에도 맛있게 배달해드릴게요!"

#### 홀전용 매장  
- 친근함: "다음에도 매장에서 뵙겠습니다!"
- 정중함: "다음에도 매장에서 뵙겠습니다."
- 캐주얼: "다음에도 또 놀러와 주세요!"

## 백엔드 AI 시스템 연동 확인

이제 AI 답글 생성 시 operation_type이 자동으로 고려됩니다:

```bash
python core/ai_reply/main.py --batch --user-id "사용자ID"
```

생성되는 답글이 설정한 운영 방식에 맞는지 확인해보세요!