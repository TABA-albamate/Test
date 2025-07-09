import pytesseract
import json
import time
import cv2
import numpy as np
from pathlib import Path
from PIL import Image
import re

# Tesseract 경로 설정 (Windows)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def test_tesseract_on_images():
    """TesseractOCR을 사용하여 모든 이미지에서 텍스트를 추출하고 분석합니다."""
    
    print("🔧 TesseractOCR 초기화 중...")
    
    # Tesseract 버전 확인
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✅ TesseractOCR 초기화 완료! (버전: {version})")
    except Exception as e:
        print(f"⚠️  Tesseract 경로 설정이 필요할 수 있습니다: {e}")
        print("   Windows의 경우: pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'")
        return
    
    # 이미지 파일들 찾기
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
    image_files = []
    
    for ext in image_extensions:
        image_files.extend(Path('.').glob(f'*{ext}'))
        image_files.extend(Path('.').glob(f'*{ext.upper()}'))
    
    if not image_files:
        print("❌ 이미지 파일을 찾을 수 없습니다.")
        return
    
    print(f"📁 발견된 이미지 파일: {len(image_files)}개")
    
    results = []
    
    for img_path in image_files:
        print(f"\n🖼️  처리 중: {img_path.name}")
        
        try:
            # 이미지 읽기 (OpenCV)
            image_cv = cv2.imread(str(img_path))
            if image_cv is None:
                print(f"❌ 이미지를 읽을 수 없습니다: {img_path}")
                continue
            
            # PIL Image로 변환 (Tesseract는 PIL Image를 선호)
            image_pil = Image.fromarray(cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB))
            
            # Tesseract OCR 실행
            start_time = time.time()
            
            # 한글 + 영어 인식 설정
            config = '--oem 3 --psm 6 -l kor+eng'
            
            # 텍스트 추출
            text = pytesseract.image_to_string(image_pil, config=config)
            
            # 상세 정보 추출 (bbox 포함)
            data = pytesseract.image_to_data(image_pil, config=config, output_type=pytesseract.Output.DICT)
            
            processing_time = time.time() - start_time
            
            # 결과 분석
            extracted_texts = []
            total_confidence = 0
            total_length = 0
            valid_text_count = 0
            
            # data에서 유효한 텍스트 추출
            for i in range(len(data['text'])):
                text_item = data['text'][i].strip()
                conf = data['conf'][i]
                
                if text_item and conf > 0:  # 유효한 텍스트만
                    extracted_texts.append({
                        'text': text_item,
                        'confidence': conf / 100.0,  # 0-100을 0-1로 변환
                        'bbox': [
                            data['left'][i],
                            data['top'][i],
                            data['left'][i] + data['width'][i],
                            data['top'][i] + data['height'][i]
                        ]
                    })
                    total_confidence += conf
                    total_length += len(text_item)
                    valid_text_count += 1
            
            avg_confidence = total_confidence / valid_text_count if valid_text_count > 0 else 0
            
            # 결과 저장
            result = {
                'image_name': img_path.name,
                'processing_time': processing_time,
                'text_count': valid_text_count,
                'avg_confidence': avg_confidence / 100.0,  # 0-1로 변환
                'total_length': total_length,
                'extracted_texts': extracted_texts,
                'full_text': text,
                'raw_data': {
                    'text': data['text'],
                    'conf': data['conf'],
                    'left': data['left'],
                    'top': data['top'],
                    'width': data['width'],
                    'height': data['height']
                }
            }
            
            results.append(result)
            
            # 결과 출력
            print(f"   ⏱️  처리 시간: {processing_time:.2f}초")
            print(f"   📝 추출된 텍스트 수: {valid_text_count}개")
            print(f"   🎯 평균 신뢰도: {avg_confidence/100:.2f}")
            print(f"   📏 총 텍스트 길이: {total_length}자")
            
            if extracted_texts:
                print(f"   📄 추출된 텍스트 미리보기:")
                for i, item in enumerate(extracted_texts[:10]):  # 처음 10개만 표시
                    print(f"      {i+1}. '{item['text']}' (신뢰도: {item['confidence']:.2f})")
                if len(extracted_texts) > 10:
                    print(f"      ... 외 {len(extracted_texts)-10}개 더")
                
                # 전체 텍스트 미리보기
                print(f"   📄 전체 텍스트 미리보기 (첫 200자):")
                print(f"      {text[:200]}...")
            else:
                print("   ❌ 텍스트를 추출하지 못했습니다.")
                
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            results.append({
                'image_name': img_path.name,
                'error': str(e),
                'processing_time': 0,
                'text_count': 0,
                'avg_confidence': 0,
                'total_length': 0,
                'extracted_texts': [],
                'full_text': ''
            })
    
    # 전체 결과 요약
    print(f"\n{'='*60}")
    print("📊 전체 결과 요약")
    print(f"{'='*60}")
    
    successful_images = [r for r in results if 'error' not in r and r['text_count'] > 0]
    failed_images = [r for r in results if 'error' in r or r['text_count'] == 0]
    
    print(f"✅ 성공: {len(successful_images)}개 이미지에서 텍스트 추출")
    print(f"❌ 실패: {len(failed_images)}개 이미지")
    
    if successful_images:
        avg_processing_time = sum(r['processing_time'] for r in successful_images) / len(successful_images)
        total_texts = sum(r['text_count'] for r in successful_images)
        avg_confidence = sum(r['avg_confidence'] for r in successful_images) / len(successful_images)
        
        print(f"⏱️  평균 처리 시간: {avg_processing_time:.2f}초")
        print(f"📝 총 추출된 텍스트: {total_texts}개")
        print(f"🎯 평균 신뢰도: {avg_confidence:.2f}")
    
    # 결과를 JSON 파일로 저장
    output_file = 'tesseract_test_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 결과가 '{output_file}'에 저장되었습니다.")
    
    # 가장 성공적인 이미지 표시
    if successful_images:
        best_image = max(successful_images, key=lambda x: x['text_count'])
        print(f"\n🏆 가장 많은 텍스트가 추출된 이미지: {best_image['image_name']}")
        print(f"   📝 추출된 텍스트: {best_image['text_count']}개")
        print(f"   🎯 평균 신뢰도: {best_image['avg_confidence']:.2f}")
        print(f"   📄 텍스트 미리보기: {best_image['full_text'][:100]}...")

def test_tesseract_on_single_image(image_path):
    """단일 이미지에 대해 TesseractOCR을 테스트합니다."""
    
    print(f"🔧 TesseractOCR로 {image_path} 테스트 중...")
    
    try:
        # 이미지 읽기
        image_cv = cv2.imread(image_path)
        if image_cv is None:
            print(f"❌ 이미지를 읽을 수 없습니다: {image_path}")
            return
        
        # PIL Image로 변환
        image_pil = Image.fromarray(cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB))
        
        # 다양한 설정으로 테스트
        configs = [
            ('기본 설정', '--oem 3 --psm 6 -l kor+eng'),
            ('한글 우선', '--oem 3 --psm 6 -l kor'),
            ('영어 우선', '--oem 3 --psm 6 -l eng'),
            ('단일 블록', '--oem 3 --psm 6 -l kor+eng'),
            ('자동 페이지', '--oem 3 --psm 3 -l kor+eng')
        ]
        
        for config_name, config in configs:
            print(f"\n📋 {config_name} 테스트:")
            start_time = time.time()
            
            # 텍스트 추출
            text = pytesseract.image_to_string(image_pil, config=config)
            
            # 상세 정보 추출
            data = pytesseract.image_to_data(image_pil, config=config, output_type=pytesseract.Output.DICT)
            
            processing_time = time.time() - start_time
            
            # 결과 분석
            valid_texts = []
            total_conf = 0
            valid_count = 0
            
            for i in range(len(data['text'])):
                text_item = data['text'][i].strip()
                conf = data['conf'][i]
                
                if text_item and conf > 0:
                    valid_texts.append(text_item)
                    total_conf += conf
                    valid_count += 1
            
            avg_conf = total_conf / valid_count if valid_count > 0 else 0
            
            print(f"   ⏱️  처리 시간: {processing_time:.2f}초")
            print(f"   📝 텍스트 수: {valid_count}개")
            print(f"   🎯 평균 신뢰도: {avg_conf/100:.2f}")
            print(f"   📄 텍스트 미리보기: {text[:100]}...")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    # 전체 이미지 테스트
    test_tesseract_on_images()
    
    # 특정 이미지 상세 테스트 (선택사항)
    # test_tesseract_on_single_image("image5.jpg") 