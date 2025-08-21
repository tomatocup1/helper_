#!/usr/bin/env python3
"""
네이버 캐차 자동 해결 모듈
이미지 및 음성 캐차를 AI 기술로 자동 인식하고 해결합니다.
"""

import os
import sys
import io
import base64
import asyncio
import logging
from typing import Optional, Tuple
import tempfile

# 기본 라이브러리
import numpy as np

# OCR 라이브러리
try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    import cv2
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    # 더미 클래스 정의
    class Image:
        class Image:
            pass

# 음성 인식 라이브러리 (선택적)
try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """캐차 자동 해결 클래스"""
    
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        초기화
        
        Args:
            tesseract_path: Tesseract 실행 파일 경로 (Windows의 경우 필요)
        """
        self.ocr_available = OCR_AVAILABLE
        self.speech_available = SPEECH_AVAILABLE
        
        if not self.ocr_available:
            logger.warning("OCR 라이브러리가 설치되지 않았습니다. pip install pytesseract pillow opencv-python")
        
        # Windows에서 Tesseract 경로 설정
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        elif sys.platform == "win32":
            # 일반적인 Windows Tesseract 설치 경로들
            possible_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME'))
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    logger.info(f"Tesseract 경로 설정: {path}")
                    break
            else:
                logger.warning("Tesseract가 설치되지 않았습니다. https://github.com/UB-Mannheim/tesseract/wiki 에서 설치하세요.")
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        캐차 이미지 전처리
        
        Args:
            image: 원본 이미지
            
        Returns:
            전처리된 이미지
        """
        try:
            # PIL을 OpenCV 형식으로 변환
            img_array = np.array(image)
            
            # 그레이스케일 변환
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # 이미지 크기 조정 (OCR 정확도 향상)
            height, width = gray.shape
            if height < 50 or width < 150:
                scale_factor = max(150 / width, 50 / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
            # 노이즈 제거
            gray = cv2.medianBlur(gray, 3)
            
            # 이진화 (Otsu 방법)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 모폴로지 연산으로 텍스트 정리
            kernel = np.ones((2, 2), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            # PIL 이미지로 다시 변환
            processed_image = Image.fromarray(binary)
            
            return processed_image
            
        except Exception as e:
            logger.error(f"이미지 전처리 실패: {e}")
            return image
    
    def extract_text_from_image(self, image: Image.Image) -> str:
        """
        이미지에서 텍스트 추출
        
        Args:
            image: 캐차 이미지
            
        Returns:
            인식된 텍스트
        """
        if not self.ocr_available:
            raise Exception("OCR 라이브러리가 설치되지 않았습니다.")
        
        try:
            # 이미지 전처리
            processed_image = self.preprocess_image(image)
            
            # OCR 설정 (숫자와 영문만, 단일 라인)
            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
            
            # 텍스트 추출
            text = pytesseract.image_to_string(processed_image, config=custom_config)
            
            # 결과 정리
            cleaned_text = ''.join(c for c in text if c.isalnum()).strip()
            
            logger.info(f"OCR 결과: '{cleaned_text}'")
            return cleaned_text
            
        except Exception as e:
            logger.error(f"OCR 텍스트 추출 실패: {e}")
            return ""
    
    async def solve_image_captcha(self, page, captcha_element) -> Optional[str]:
        """
        이미지 캐차 해결
        
        Args:
            page: Playwright 페이지 객체
            captcha_element: 캐차 이미지 요소
            
        Returns:
            인식된 캐차 텍스트 또는 None
        """
        try:
            logger.info("이미지 캐차 해결 시작")
            
            # 캐차 이미지 스크린샷
            screenshot_bytes = await captcha_element.screenshot()
            
            # PIL 이미지로 변환
            image = Image.open(io.BytesIO(screenshot_bytes))
            
            # OCR로 텍스트 인식
            captcha_text = self.extract_text_from_image(image)
            
            if captcha_text:
                logger.info(f"캐차 인식 성공: {captcha_text}")
                return captcha_text
            else:
                logger.warning("캐차 인식 실패")
                return None
                
        except Exception as e:
            logger.error(f"이미지 캐차 해결 실패: {e}")
            return None
    
    async def solve_audio_captcha(self, page) -> Optional[str]:
        """
        음성 캐차 해결 (기본 구현)
        
        Args:
            page: Playwright 페이지 객체
            
        Returns:
            인식된 음성 텍스트 또는 None
        """
        if not self.speech_available:
            logger.warning("음성 인식 라이브러리가 설치되지 않았습니다.")
            return None
        
        try:
            logger.info("음성 캐차 해결 시작")
            
            # 음성 재생 버튼 클릭
            play_button = await page.query_selector("#play_audio")
            if play_button:
                await play_button.click()
                await asyncio.sleep(2)  # 음성 재생 대기
            
            # TODO: 브라우저에서 음성 녹음 및 처리
            # 현재는 기본 구현으로 None 반환
            logger.warning("음성 캐차 자동 해결은 아직 구현되지 않았습니다.")
            return None
            
        except Exception as e:
            logger.error(f"음성 캐차 해결 실패: {e}")
            return None
    
    async def handle_captcha(self, page, max_attempts: int = 3) -> bool:
        """
        캐차 감지 및 자동 해결
        
        Args:
            page: Playwright 페이지 객체
            max_attempts: 최대 시도 횟수
            
        Returns:
            캐차 해결 성공 여부
        """
        try:
            logger.info("캐차 감지 및 해결 시작")
            
            for attempt in range(max_attempts):
                logger.info(f"캐차 해결 시도 {attempt + 1}/{max_attempts}")
                
                # 이미지 캐차 확인
                captcha_img = await page.query_selector("#captchaimg")
                captcha_input = await page.query_selector("#captcha")
                
                if captcha_img and captcha_input:
                    logger.info("이미지 캐차 감지됨")
                    
                    # 이미지 캐차 해결
                    captcha_text = await self.solve_image_captcha(page, captcha_img)
                    
                    if captcha_text:
                        # 캐차 답 입력
                        await captcha_input.fill(captcha_text)
                        await asyncio.sleep(0.5)
                        
                        # 로그인 버튼 다시 클릭
                        login_button = await page.query_selector("#log\\\\.login")
                        if login_button:
                            await login_button.click()
                            await asyncio.sleep(3)
                        
                        # 캐차가 해결되었는지 확인
                        current_url = page.url
                        if "captcha" not in current_url.lower() and "nidlogin" not in current_url:
                            logger.info("캐차 해결 성공!")
                            return True
                        elif "captcha" in current_url.lower():
                            logger.warning("캐차 답이 틀렸습니다. 재시도...")
                            continue
                    else:
                        logger.warning("캐차 인식 실패")
                
                # 음성 캐차 확인
                audio_captcha = await page.query_selector("#play_audio")
                audio_input = await page.query_selector("#chptcha")
                
                if audio_captcha and audio_input:
                    logger.info("음성 캐차 감지됨")
                    
                    # 음성 캐차 해결 시도
                    audio_text = await self.solve_audio_captcha(page)
                    
                    if audio_text:
                        await audio_input.fill(audio_text)
                        await asyncio.sleep(0.5)
                        
                        # 로그인 버튼 다시 클릭
                        login_button = await page.query_selector("#log\\\\.login")
                        if login_button:
                            await login_button.click()
                            await asyncio.sleep(3)
                        
                        # 캐차가 해결되었는지 확인
                        current_url = page.url
                        if "captcha" not in current_url.lower() and "nidlogin" not in current_url:
                            logger.info("음성 캐차 해결 성공!")
                            return True
                    else:
                        logger.warning("음성 캐차 인식 실패")
                
                # 캐차가 없으면 성공
                if not captcha_img and not audio_captcha:
                    logger.info("캐차가 없습니다.")
                    return True
                
                # 재시도를 위해 페이지 새로고침
                if attempt < max_attempts - 1:
                    logger.info("캐차 새로고침 후 재시도")
                    refresh_button = await page.query_selector(".btn_refresh, #refresh_captcha")
                    if refresh_button:
                        await refresh_button.click()
                        await asyncio.sleep(2)
            
            logger.error(f"캐차 해결 실패 (최대 {max_attempts}회 시도)")
            return False
            
        except Exception as e:
            logger.error(f"캐차 처리 중 오류: {e}")
            return False


def install_requirements():
    """필요한 패키지 설치"""
    import subprocess
    
    packages = [
        "pytesseract",
        "Pillow", 
        "opencv-python",
        "SpeechRecognition"  # 선택적
    ]
    
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} 설치 완료")
        except subprocess.CalledProcessError:
            print(f"❌ {package} 설치 실패")


if __name__ == "__main__":
    # 패키지 설치 스크립트
    if len(sys.argv) > 1 and sys.argv[1] == "install":
        install_requirements()
    else:
        print("사용법: python captcha_solver.py install")
        print("또는 CaptchaSolver 클래스를 임포트하여 사용하세요.")