#!/usr/bin/env python3
"""
요기요 크롤러 업데이트 테스트
업데이트된 셀렉터가 2개 매장을 모두 수집하는지 확인
"""
import requests
import json

def test_yogiyo_crawler():
    """요기요 크롤러 테스트"""
    print("🔍 요기요 크롤러 업데이트 테스트 시작")
    print("=" * 50)
    
    # 테스트용 계정 정보 (실제 계정 정보로 변경 필요)
    test_data = {
        "platform": "yogiyo",
        "credentials": {
            "username": "your_username",  # 실제 계정으로 변경
            "password": "your_password"   # 실제 계정으로 변경
        }
    }
    
    try:
        print("📡 API 요청 전송 중...")
        response = requests.post(
            "http://localhost:8001/api/v1/platform/connect",
            json=test_data,
            timeout=120  # 2분 타임아웃
        )
        
        print(f"📊 응답 상태 코드: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API 호출 성공!")
            print(f"🎯 성공 여부: {result.get('success', False)}")
            print(f"💬 메시지: {result.get('message', 'N/A')}")
            
            stores = result.get('stores', [])
            print(f"🏪 수집된 매장 수: {len(stores)}")
            
            if stores:
                print("\n📋 매장 목록:")
                for i, store in enumerate(stores, 1):
                    print(f"  {i}. {store.get('store_name', 'N/A')} (ID: {store.get('platform_store_id', 'N/A')})")
                    
                # 2개 매장 수집 성공 여부 확인
                if len(stores) >= 2:
                    print("\n🎉 성공! 2개 이상의 매장을 수집했습니다!")
                    print("✅ 셀렉터 업데이트가 정상적으로 작동합니다.")
                else:
                    print(f"\n⚠️  {len(stores)}개 매장만 수집됨. 추가 개선이 필요할 수 있습니다.")
            else:
                print("❌ 매장 수집 실패 또는 매장이 없습니다.")
                
        else:
            print(f"❌ API 호출 실패: {response.status_code}")
            try:
                error_data = response.json()
                print(f"오류 내용: {error_data}")
            except:
                print(f"응답 내용: {response.text}")
                
    except requests.exceptions.Timeout:
        print("⏰ 요청 타임아웃 (2분 초과)")
    except requests.exceptions.ConnectionError:
        print("🔌 연결 실패 - 백엔드 서버가 실행 중인지 확인하세요")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")

if __name__ == "__main__":
    print("⚠️  주의: 실제 계정 정보를 입력한 후 테스트하세요!")
    print("현재는 더미 계정 정보로 설정되어 있습니다.\n")
    test_yogiyo_crawler()