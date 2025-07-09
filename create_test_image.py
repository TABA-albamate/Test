"""
테스트용 이미지 생성 스크립트
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_test_image():
    """
    간단한 텍스트가 포함된 테스트 이미지 생성
    """
    # 이미지 크기 설정
    width, height = 800, 600
    
    # 흰색 배경 이미지 생성
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    try:
        # 기본 폰트 사용 (한글 지원)
        font = ImageFont.load_default()
        font_large = ImageFont.load_default()
    except:
        # 폰트 로드 실패시 기본값 사용
        font = None
        font_large = None
    
    # 테스트 텍스트 그리기
    texts = [
        "근무표 테스트",
        "2024년 12월",
        "월  화  수  목  금  토  일",
        "김철수  D   E   N   OFF  D   E   N",
        "이영희  E   N   OFF  D   E   N   OFF",
        "박민수  N   OFF  D   E   N   OFF  D"
    ]
    
    y_position = 50
    for i, text in enumerate(texts):
        if i == 0:  # 제목
            draw.text((50, y_position), text, fill='black', font=font_large)
            y_position += 60
        elif i == 1:  # 날짜
            draw.text((50, y_position), text, fill='blue', font=font)
            y_position += 40
        else:  # 근무 정보
            draw.text((50, y_position), text, fill='black', font=font)
            y_position += 30
    
    # 추가 설명 텍스트
    draw.text((50, 400), "D: 주간근무 (07:00-16:00)", fill='red', font=font)
    draw.text((50, 430), "E: 저녁근무 (13:00-22:00)", fill='orange', font=font)
    draw.text((50, 460), "N: 야간근무 (21:30-09:00)", fill='purple', font=font)
    draw.text((50, 490), "OFF: 휴무", fill='green', font=font)
    
    # 이미지 저장
    filename = "test_schedule_created.png"
    image.save(filename)
    print(f"✅ 테스트 이미지 생성 완료: {filename}")
    
    return filename

if __name__ == "__main__":
    print("🎨 테스트 이미지 생성 중...")
    test_image = create_test_image()
    print(f"📁 생성된 파일: {test_image}")
    print("이제 이 이미지로 OCR 테스트를 진행하세요!") 