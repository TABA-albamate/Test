import json
import re
from collections import defaultdict
from datetime import datetime
import numpy as np

def debug_tesseract_result(json_path):
    """Tesseract 결과를 디버깅합니다."""
    print("🔍 Tesseract 결과 디버깅 시작")
    print("=" * 60)
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 총 이미지 수: {len(data)}")
    
    # 첫 번째 이미지 분석
    first_image = data[0]
    print(f"🖼️  첫 번째 이미지: {first_image['image_name']}")
    print(f"📝 추출된 텍스트 수: {first_image['text_count']}")
    print(f"🎯 평균 신뢰도: {first_image['avg_confidence']:.2f}")
    
    # 텍스트 미리보기
    texts = first_image['extracted_texts']
    print(f"\n📄 텍스트 미리보기 (처음 20개):")
    for i, item in enumerate(texts[:20]):
        print(f"   {i+1}. '{item['text']}' (신뢰도: {item['confidence']:.2f}) - bbox: {item['bbox']}")
    
    return first_image['extracted_texts']

def cluster_texts_to_grid_debug(ocr_results, row_eps=30, col_eps=30):
    """디버깅 정보를 포함한 그리드 변환"""
    print(f"\n🔧 그리드 변환 시작 (텍스트 수: {len(ocr_results)})")
    
    # bbox 중심 좌표 계산
    items = []
    for item in ocr_results:
        bbox = item['bbox']
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        items.append({
            'text': item['text'], 
            'cx': cx, 
            'cy': cy, 
            'bbox': bbox, 
            'confidence': item['confidence']
        })
    
    print(f"   📍 좌표 계산 완료")
    
    # y좌표(행) 클러스터링
    ys = np.array([it['cy'] for it in items])
    y_sorted_idx = np.argsort(ys)
    row_clusters = []
    for idx in y_sorted_idx:
        y = ys[idx]
        found = False
        for row in row_clusters:
            if abs(row[0] - y) < row_eps:
                row.append(y)
                found = True
                break
        if not found:
            row_clusters.append([y])
    
    row_centers = [np.mean(row) for row in row_clusters]
    print(f"   📏 행 클러스터: {len(row_clusters)}개 행 발견")
    
    # 각 텍스트에 행 인덱스 할당
    for it in items:
        it['row'] = int(np.argmin([abs(it['cy']-rc) for rc in row_centers]))
    
    # x좌표(열) 클러스터링 (행별로)
    grid = defaultdict(lambda: defaultdict(list))
    for row in range(len(row_centers)):
        row_items = [it for it in items if it['row']==row]
        if not row_items:
            continue
            
        xs = np.array([it['cx'] for it in row_items])
        x_sorted_idx = np.argsort(xs)
        col_clusters = []
        for idx in x_sorted_idx:
            x = xs[idx]
            found = False
            for col in col_clusters:
                if abs(col[0] - x) < col_eps:
                    col.append(x)
                    found = True
                    break
            if not found:
                col_clusters.append([x])
        
        col_centers = [np.mean(col) for col in col_clusters]
        for it in row_items:
            it['col'] = int(np.argmin([abs(it['cx']-cc) for cc in col_centers]))
            grid[row][it['col']].append(it)
    
    # 각 셀에 텍스트 합치기
    grid_text = defaultdict(dict)
    for row in grid:
        for col in grid[row]:
            cell_text = ' '.join([it['text'] for it in grid[row][col]])
            grid_text[row][col] = cell_text.strip()
    
    print(f"   📋 그리드 생성 완료")
    return grid_text

def analyze_grid_structure(grid):
    """그리드 구조를 분석합니다."""
    if not grid:
        print("❌ 그리드가 비어있습니다.")
        return
    
    n_rows = max(grid.keys()) + 1
    n_cols = max(max(cols.keys()) for cols in grid.values()) + 1
    
    print(f"\n📊 그리드 구조 분석:")
    print(f"   크기: {n_rows}행 x {n_cols}열")
    
    print(f"\n📄 그리드 내용:")
    for row in range(n_rows):
        row_text = []
        for col in range(n_cols):
            cell = grid.get(row, {}).get(col, '')
            row_text.append(f"'{cell}'" if cell else "''")
        print(f"   행 {row}: [{', '.join(row_text)}]")
    
    return n_rows, n_cols

def extract_dates_from_row(row_texts, base_year=2025, base_month=1):
    """날짜 추출 (개선된 버전)"""
    dates = []
    year = base_year
    month = base_month
    
    for text in row_texts:
        if not text:
            dates.append('')
            continue
            
        # 숫자만 있는 경우 (일자)
        if text.isdigit():
            try:
                day = int(text)
                date = datetime(year, month, day).strftime('%Y-%m-%d')
                dates.append(date)
            except:
                dates.append('')
        else:
            # 날짜 패턴 검색
            m = re.search(r'(\d{1,4})[./-](\d{1,2})[./-]?(\d{1,2})?', text)
            if m:
                if m.lastindex == 3:
                    y, mth, d = m.groups()
                    if len(y) == 4:
                        year, month, day = int(y), int(mth), int(d)
                    else:
                        month, day = int(y), int(mth)
                    try:
                        date = datetime(year, month, day).strftime('%Y-%m-%d')
                    except:
                        date = ''
                elif m.lastindex == 2:
                    month, day = int(m.group(1)), int(m.group(2))
                    try:
                        date = datetime(year, month, day).strftime('%Y-%m-%d')
                    except:
                        date = ''
                else:
                    date = ''
                dates.append(date)
            else:
                dates.append('')
    
    return dates

def parse_time_range(text):
    """시간 범위 파싱 (개선된 버전)"""
    if not text:
        return None, None
        
    # '13-17', '11-15', '12-17' 등의 형식
    m = re.search(r'(\d{1,2})[./-](\d{1,2})', text)
    if m:
        h1, h2 = int(m.group(1)), int(m.group(2))
        return f"{h1:02d}:00", f"{h2:02d}:00"
    
    # '12-15.30' 같은 형식
    m = re.search(r'(\d{1,2})[./-](\d{1,2})\.(\d{2})', text)
    if m:
        h1, h2, m2 = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{h1:02d}:00", f"{h2:02d}:{m2:02d}"
    
    return None, None

def find_staff_schedules(grid, staff_name, dates, time_ranges):
    """직원 일정 찾기 (개선된 버전)"""
    schedules = []
    n_rows = max(grid.keys()) + 1
    n_cols = max(max(cols.keys()) for cols in grid.values()) + 1
    
    print(f"\n🔍 '{staff_name}' 직원 일정 검색:")
    
    for row in range(n_rows):
        for col in range(n_cols):
            cell = grid.get(row, {}).get(col, '')
            if staff_name in cell:
                date = dates[col] if col < len(dates) else ''
                start, end = time_ranges[col] if col < len(time_ranges) else (None, None)
                
                print(f"   📅 행 {row}, 열 {col}: '{cell}' -> {date} {start}-{end}")
                
                if date and start and end:
                    schedules.append({
                        'date': date,
                        'start_time': start,
                        'end_time': end,
                        'cell_text': cell,
                        'row': row,
                        'col': col
                    })
    
    return schedules

def main():
    """메인 실행 함수"""
    json_path = 'tesseract_test_results.json'
    
    # 1. Tesseract 결과 디버깅
    ocr_results = debug_tesseract_result(json_path)
    
    # 2. 그리드 변환
    grid = cluster_texts_to_grid_debug(ocr_results)
    
    # 3. 그리드 구조 분석
    n_rows, n_cols = analyze_grid_structure(grid)
    
    # 4. 날짜/시간대 추출
    print(f"\n📅 날짜/시간대 추출:")
    
    # 첫 번째 행에서 날짜 추출
    first_row = [grid.get(0, {}).get(col, '') for col in range(n_cols)]
    print(f"   첫 번째 행: {first_row}")
    dates = extract_dates_from_row(first_row)
    print(f"   추출된 날짜: {dates}")
    
    # 시간대 추출 (각 행에서)
    all_time_ranges = []
    for row in range(n_rows):
        row_texts = [grid.get(row, {}).get(col, '') for col in range(n_cols)]
        time_ranges = [parse_time_range(text) for text in row_texts]
        all_time_ranges.append(time_ranges)
        print(f"   행 {row} 시간대: {time_ranges}")
    
    # 5. 직원 일정 검색
    staff_name = "임민지"
    schedules = find_staff_schedules(grid, staff_name, dates, all_time_ranges[0])  # 첫 번째 행의 시간대 사용
    
    # 6. 결과 출력
    print(f"\n📊 최종 결과:")
    print(f"   발견된 일정: {len(schedules)}개")
    
    for i, sch in enumerate(schedules):
        print(f"   {i+1}. {sch['date']} {sch['start_time']}-{sch['end_time']} ({sch['cell_text']})")
    
    # 7. Google Calendar JSON 생성
    if schedules:
        events = []
        for sch in schedules:
            start_dt = f"{sch['date']}T{sch['start_time']}:00"
            end_dt = f"{sch['date']}T{sch['end_time']}:00"
            events.append({
                'summary': f"{staff_name} 근무",
                'description': sch['cell_text'],
                'start': {'dateTime': start_dt, 'timeZone': 'Asia/Seoul'},
                'end': {'dateTime': end_dt, 'timeZone': 'Asia/Seoul'}
            })
        
        output_file = f'debug_tesseract_gcal_{staff_name}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Google Calendar JSON 저장: {output_file}")
    else:
        print(f"\n❌ 일정을 찾지 못했습니다.")

if __name__ == "__main__":
    main() 