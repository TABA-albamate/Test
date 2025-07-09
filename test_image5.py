import easyocr
import json
import time
import cv2
from pathlib import Path
from table_schedule_parser import parse_schedule_from_ocr_result, cluster_texts_to_grid, extract_dates_from_row, extract_positions_from_row, extract_time_ranges_from_row, generate_schedules

def test_image5_ocr():
    """image5.jpg에 대해 EasyOCR을 실행하고 결과를 분석합니다."""
    
    print("🔧 EasyOCR 초기화 중...")
    reader = easyocr.Reader(['ko', 'en'], gpu=False)
    print("✅ EasyOCR 초기화 완료!")
    
    # image5.jpg 읽기
    image_path = "image5.jpg"
    if not Path(image_path).exists():
        print(f"❌ {image_path} 파일을 찾을 수 없습니다.")
        return
    
    print(f"\n🖼️  처리 중: {image_path}")
    
    try:
        # 이미지 읽기
        image = cv2.imread(image_path)
        if image is None:
            print(f"❌ 이미지를 읽을 수 없습니다: {image_path}")
            return
        
        # EasyOCR로 텍스트 추출
        start_time = time.time()
        ocr_results = reader.readtext(image)
        processing_time = time.time() - start_time
        
        # 결과 분석
        extracted_texts = []
        total_confidence = 0
        total_length = 0
        
        for (bbox, text, confidence) in ocr_results:
            extracted_texts.append({
                'text': text,
                'confidence': float(confidence),
                'bbox': [[float(x) for x in point] for point in bbox]
            })
            total_confidence += confidence
            total_length += len(text)
        
        avg_confidence = total_confidence / len(extracted_texts) if extracted_texts else 0
        
        # 결과 출력
        print(f"   ⏱️  처리 시간: {processing_time:.2f}초")
        print(f"   📝 추출된 텍스트 수: {len(extracted_texts)}개")
        print(f"   🎯 평균 신뢰도: {avg_confidence:.2f}")
        print(f"   📏 총 텍스트 길이: {total_length}자")
        
        if extracted_texts:
            print(f"   📄 추출된 텍스트 미리보기:")
            for i, item in enumerate(extracted_texts[:10]):  # 처음 10개만 표시
                print(f"      {i+1}. '{item['text']}' (신뢰도: {item['confidence']:.2f})")
            if len(extracted_texts) > 10:
                print(f"      ... 외 {len(extracted_texts)-10}개 더")
        else:
            print("   ❌ 텍스트를 추출하지 못했습니다.")
            return
        
        # 결과를 JSON 파일로 저장
        result = {
            'image_name': image_path,
            'processing_time': processing_time,
            'text_count': len(extracted_texts),
            'avg_confidence': avg_confidence,
            'total_length': total_length,
            'extracted_texts': extracted_texts,
            'full_text': ' '.join([item['text'] for item in extracted_texts])
        }
        
        output_file = 'image5_ocr_results.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 OCR 결과가 '{output_file}'에 저장되었습니다.")
        
        # 표 구조 분석 테스트
        print(f"\n{'='*60}")
        print("📊 표 구조 분석 시작")
        print(f"{'='*60}")
        
        # 2차원 그리드로 변환
        grid = cluster_texts_to_grid(extracted_texts)
        
        # 그리드 출력
        n_rows = max(grid.keys()) + 1 if grid else 0
        n_cols = max(max(cols.keys()) for cols in grid.values()) + 1 if grid else 0
        
        print(f"📋 그리드 크기: {n_rows}행 x {n_cols}열")
        print("\n📄 그리드 내용:")
        for row in range(n_rows):
            row_text = []
            for col in range(n_cols):
                cell = grid.get(row, {}).get(col, '')
                row_text.append(f"'{cell}'" if cell else "''")
            print(f"   행 {row}: [{', '.join(row_text)}]")
        
        # 날짜/포지션/시간대 추출 테스트
        print(f"\n{'='*60}")
        print("🔍 정보 추출 테스트")
        print(f"{'='*60}")
        
        # 각 행별로 분석
        for row_idx in range(min(5, n_rows)):  # 처음 5행만 테스트
            row_texts = [grid.get(row_idx, {}).get(col, '') for col in range(n_cols)]
            print(f"\n📅 행 {row_idx} 분석:")
            print(f"   텍스트: {row_texts}")
            
            # 날짜 추출 테스트
            dates = extract_dates_from_row(row_texts)
            print(f"   날짜: {dates}")
            
            # 포지션 추출 테스트
            positions = extract_positions_from_row(row_texts)
            print(f"   포지션: {positions}")
            
            # 시간대 추출 테스트
            time_ranges = extract_time_ranges_from_row(row_texts)
            print(f"   시간대: {time_ranges}")
        
        # 직원명 찾기
        print(f"\n{'='*60}")
        print("👥 직원명 검색")
        print(f"{'='*60}")
        
        # 추출된 텍스트에서 직원명 패턴 찾기
        possible_names = []
        for item in extracted_texts:
            text = item['text']
            # 한글 이름 패턴 (2-4글자)
            if re.match(r'^[가-힣]{2,4}$', text) and len(text) >= 2:
                possible_names.append(text)
        
        print(f"발견된 가능한 직원명: {list(set(possible_names))}")
        
        # 각 가능한 직원명에 대해 일정 생성 테스트
        for staff_name in set(possible_names):
            print(f"\n🔍 '{staff_name}' 직원 일정 검색:")
            
            # 날짜/포지션/시간대 추출 (기본값: 0,1,2행)
            date_row = 0
            pos_row = 1
            time_row = 2
            
            dates = extract_dates_from_row([grid.get(date_row, {}).get(col, '') for col in range(n_cols)])
            positions = extract_positions_from_row([grid.get(pos_row, {}).get(col, '') for col in range(n_cols)])
            time_ranges = extract_time_ranges_from_row([grid.get(time_row, {}).get(col, '') for col in range(n_cols)])
            
            schedules = generate_schedules(grid, dates, positions, time_ranges, staff_name)
            
            if schedules:
                print(f"   ✅ {len(schedules)}개의 일정 발견:")
                for i, sch in enumerate(schedules):
                    print(f"      {i+1}. {sch['date']} {sch['position']} {sch['start']}-{sch['end']} ({sch['cell_text']})")
            else:
                print(f"   ❌ 일정을 찾지 못했습니다.")
        
        return output_file
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None

if __name__ == "__main__":
    import re
    test_image5_ocr() 