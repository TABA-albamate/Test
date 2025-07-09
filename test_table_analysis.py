"""
표 구조 분석 테스트 스크립트
근무표 이미지를 분석하여 표 구조를 파악하고 Google Calendar JSON을 생성합니다.
"""

import os
import sys
from paddleocr_test import HybridScheduleProcessor, phase2_checklist, estimate_phase2_cost

def test_with_sample_image():
    """
    샘플 이미지로 표 구조 분석 테스트
    """
    print("🧪 표 구조 분석 테스트 시작")
    print("=" * 50)
    
    # 사용 가능한 이미지 파일 찾기
    image_files = [
        "cafe_schedule.jpg",
        "image1.jpg",
        "image2.jpg",
        "image3.jpg",
        "image4.jpg",
        "image5.jpg",
        "image6.jpg",
        "image7.jpg"
    ]
    
    available_images = []
    for img_file in image_files:
        if os.path.exists(img_file):
            available_images.append(img_file)
    
    if not available_images:
        print("❌ 테스트할 이미지 파일을 찾을 수 없습니다!")
        print("💡 다음 파일 중 하나를 준비해주세요:")
        for img_file in image_files:
            print(f"   - {img_file}")
        return
    
    print(f"📁 발견된 이미지 파일: {len(available_images)}개")
    for img_file in available_images:
        print(f"   ✅ {img_file}")
    
    # 첫 번째 이미지로 테스트
    test_image = available_images[0]
    print(f"\n🎯 테스트 이미지: {test_image}")
    
    try:
        # 프로세서 초기화 (API 키는 필요 없음)
        processor = HybridScheduleProcessor("dummy_key")
        
        # 표 구조 분석 테스트
        print(f"\n🔍 {test_image} 분석 중...")
        result = processor.test_full_table_analysis(test_image)
        
        if result['success']:
            print("\n🎉 테스트 성공!")
            print(f"📊 분석 결과:")
            print(f"   - 처리 시간: {result['total_time']:.2f}초")
            print(f"   - 직원 수: {len(result['analysis_result']['employee_schedules'])}명")
            print(f"   - 생성된 이벤트: {result['calendar_result']['event_count']}개")
            
            # 체크리스트 실행
            phase2_checklist()
            
            # 비용 계산
            estimate_phase2_cost()
            
            print(f"\n💾 결과 파일:")
            print(f"   - table_analysis_result.json: Google Calendar 이벤트")
            print(f"   - analysis_details.json: 상세 분석 결과")
            
        else:
            print(f"\n❌ 테스트 실패: {result['stage']}")
            print(f"   오류: {result['error']}")
            
    except Exception as e:
        print(f"\n❌ 시스템 오류: {e}")
        print("💡 해결 방법:")
        print("   1. pip install paddleocr pillow opencv-python")
        print("   2. 이미지 파일이 올바른 형식인지 확인")
        print("   3. 표 형태의 근무표 이미지인지 확인")

def test_individual_components():
    """
    개별 컴포넌트 테스트
    """
    print("\n🔧 개별 컴포넌트 테스트")
    print("-" * 30)
    
    # 사용 가능한 이미지 찾기
    image_files = ["근무표.png", "군대 근무표.png", "cafe_schedule.jpg"]
    test_image = None
    
    for img_file in image_files:
        if os.path.exists(img_file):
            test_image = img_file
            break
    
    if not test_image:
        print("❌ 테스트할 이미지가 없습니다.")
        return
    
    try:
        processor = HybridScheduleProcessor("dummy_key")
        
        # 1. OCR 기본 테스트
        print("1️⃣ OCR 기본 테스트")
        ocr_result = processor.test_paddleocr_basic(test_image)
        if ocr_result['success']:
            print("   ✅ OCR 성공")
        else:
            print(f"   ❌ OCR 실패: {ocr_result['error']}")
        
        # 2. 표 구조 분석 테스트
        print("\n2️⃣ 표 구조 분석 테스트")
        table_result = processor.test_table_structure_analysis(test_image)
        if table_result['success']:
            print("   ✅ 표 구조 분석 성공")
        else:
            print(f"   ❌ 표 구조 분석 실패: {table_result['error']}")
        
        # 3. Calendar JSON 생성 테스트
        if table_result['success']:
            print("\n3️⃣ Calendar JSON 생성 테스트")
            calendar_result = processor.generate_calendar_json(table_result['analysis_result'])
            if calendar_result['success']:
                print("   ✅ Calendar JSON 생성 성공")
            else:
                print(f"   ❌ Calendar JSON 생성 실패: {calendar_result['error']}")
        
    except Exception as e:
        print(f"❌ 컴포넌트 테스트 오류: {e}")

if __name__ == "__main__":
    print("🚀 표 구조 분석 테스트 스크립트")
    print("=" * 50)
    
    # 메인 테스트 실행
    test_with_sample_image()
    
    # 개별 컴포넌트 테스트 (선택사항)
    print("\n" + "=" * 50)
    response = input("개별 컴포넌트 테스트도 실행하시겠습니까? (y/n): ")
    if response.lower() in ['y', 'yes', '예']:
        test_individual_components()
    
    print("\n✅ 테스트 완료!") 