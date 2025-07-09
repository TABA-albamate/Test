"""
간단한 OCR 테스트 스크립트
"""

from paddleocr_test import HybridScheduleProcessor
import os

def test_images():
    """
    여러 이미지 파일로 OCR 테스트
    """
    image_files = [
        # 새로 생성한 테스트 이미지
        "test_schedule_created.png",
        # 새로 다운로드한 샘플 이미지들
        "sample_schedule.png",
        "test_schedule.jpg",
        # 기존 JPG 파일들
        "image1.jpg",
        "image2.jpg", 
        "image3.jpg",
        "image4.jpg",
        "image5.jpg",
        "image6.jpg",
        "image7.jpg",
        "image44.jpg",
        "cafe_schedule.jpg",
        # 기존 PNG 파일들
        "1751515637288.png",
        "1751515637465.png", 
        "1751515637611.png",
        "KakaoTalk_20200225_123355128.png",
        "KakaoTalk_20200225_123418979.png"
    ]
    
    processor = HybridScheduleProcessor("dummy")
    
    for img_file in image_files:
        if os.path.exists(img_file):
            print(f"\n🔍 {img_file} 테스트 중...")
            result = processor.test_paddleocr_basic(img_file)
            
            if result['success']:
                text_count = result['text_count']
                text_preview = result['extracted_text'][:100]
                print(f"   ✅ 성공: {text_count}개 텍스트 추출")
                print(f"   📄 미리보기: {text_preview}...")
                
                if text_count > 0:
                    print(f"   🎯 이 이미지로 표 구조 분석 테스트 가능!")
                    return img_file
            else:
                print(f"   ❌ 실패: {result['error']}")
    
    print("\n❌ 모든 이미지에서 텍스트를 추출하지 못했습니다.")
    return None

if __name__ == "__main__":
    print("🚀 이미지 OCR 테스트")
    print("=" * 40)
    
    best_image = test_images()
    
    if best_image:
        print(f"\n🎯 추천 테스트 이미지: {best_image}")
        print("이 이미지로 표 구조 분석을 진행하세요!")
    else:
        print("\n💡 더 선명한 근무표 이미지를 준비해주세요.") 