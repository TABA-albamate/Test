import json
import re
from collections import defaultdict
from datetime import datetime
import numpy as np

def cluster_texts_to_grid(ocr_results, row_eps=30, col_eps=30):
    """bbox 중심 좌표를 기준으로 행/열 클러스터링하여 2차원 그리드로 변환"""
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
    
    return grid_text

def extract_dates_from_row(row_texts, base_year=2025, base_month=1):
    """날짜 추출"""
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
    """시간 범위 파싱"""
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

def find_staff_schedules_improved(grid, staff_name, dates):
    """직원 일정 찾기 (개선된 버전)"""
    schedules = []
    n_rows = max(grid.keys()) + 1
    n_cols = max(max(cols.keys()) for cols in grid.values()) + 1
    
    print(f"\n🔍 '{staff_name}' 직원 일정 검색:")
    
    # 직원명을 부분 매칭으로 찾기
    staff_parts = list(staff_name)  # ['임', '민', '지']
    
    for row in range(n_rows):
        # 첫 번째 열에서 직원명 확인
        first_cell = grid.get(row, {}).get(0, '')
        if not first_cell:
            continue
            
        # 직원명이 포함되어 있는지 확인 (부분 매칭)
        if any(part in first_cell for part in staff_parts):
            print(f"   👤 행 {row}: '{first_cell}' (직원명 발견)")
            
            # 해당 행의 모든 셀에서 시간대 찾기
            for col in range(1, n_cols):  # 첫 번째 열(직원명) 제외
                cell = grid.get(row, {}).get(col, '')
                if not cell:
                    continue
                    
                # 시간대 파싱
                start, end = parse_time_range(cell)
                date = dates[col] if col < len(dates) else ''
                
                print(f"      📅 열 {col}: '{cell}' -> {date} {start}-{end}")
                
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

def schedules_to_gcal_json(schedules, staff_name):
    """Google Calendar API용 JSON 변환"""
    events = []
    for sch in schedules:
        if not sch['date'] or not sch['start_time'] or not sch['end_time']:
            continue
        start_dt = f"{sch['date']}T{sch['start_time']}:00"
        end_dt = f"{sch['date']}T{sch['end_time']}:00"
        events.append({
            'summary': f"{staff_name} 근무",
            'description': sch['cell_text'],
            'start': {'dateTime': start_dt, 'timeZone': 'Asia/Seoul'},
            'end': {'dateTime': end_dt, 'timeZone': 'Asia/Seoul'}
        })
    return events

def main():
    """메인 실행 함수"""
    json_path = 'tesseract_test_results.json'
    
    print("🔍 Tesseract 결과 분석 시작")
    print("=" * 60)
    
    # Tesseract 결과 읽기
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 첫 번째 이미지 사용
    first_image = data[0]
    print(f"🖼️  이미지: {first_image['image_name']}")
    print(f"📝 추출된 텍스트 수: {first_image['text_count']}")
    
    # 그리드 변환
    ocr_results = first_image['extracted_texts']
    grid = cluster_texts_to_grid(ocr_results)
    
    # 그리드 구조 분석
    n_rows = max(grid.keys()) + 1
    n_cols = max(max(cols.keys()) for cols in grid.values()) + 1
    print(f"📋 그리드 크기: {n_rows}행 x {n_cols}열")
    
    # 날짜 추출 (첫 번째 행)
    first_row = [grid.get(0, {}).get(col, '') for col in range(n_cols)]
    print(f"📅 첫 번째 행: {first_row}")
    dates = extract_dates_from_row(first_row)
    print(f"📅 추출된 날짜: {dates}")
    
    # 직원별 일정 검색
    staff_names = ["임민지", "이정연", "박서영", "김서정", "허슬기"]
    
    all_schedules = []
    
    for staff_name in staff_names:
        print(f"\n{'='*40}")
        schedules = find_staff_schedules_improved(grid, staff_name, dates)
        
        if schedules:
            print(f"✅ {staff_name}: {len(schedules)}개 일정 발견")
            all_schedules.extend(schedules)
            
            for i, sch in enumerate(schedules):
                print(f"   {i+1}. {sch['date']} {sch['start_time']}-{sch['end_time']} ({sch['cell_text']})")
        else:
            print(f"❌ {staff_name}: 일정 없음")
    
    # Google Calendar JSON 생성
    if all_schedules:
        print(f"\n💾 Google Calendar JSON 생성 중...")
        
        # 전체 일정
        all_events = schedules_to_gcal_json(all_schedules, "전체")
        with open('tesseract_all_schedules.json', 'w', encoding='utf-8') as f:
            json.dump(all_events, f, ensure_ascii=False, indent=2)
        print(f"   전체 일정: tesseract_all_schedules.json ({len(all_events)}개)")
        
        # 직원별 일정
        for staff_name in staff_names:
            staff_schedules = [s for s in all_schedules if any(part in grid.get(s['row'], {}).get(0, '') for part in list(staff_name))]
            if staff_schedules:
                staff_events = schedules_to_gcal_json(staff_schedules, staff_name)
                filename = f'tesseract_{staff_name}_schedules.json'
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(staff_events, f, ensure_ascii=False, indent=2)
                print(f"   {staff_name} 일정: {filename} ({len(staff_events)}개)")
        
        print(f"\n✅ 분석 완료! 총 {len(all_schedules)}개 일정 추출")
    else:
        print(f"\n❌ 일정을 찾지 못했습니다.")

if __name__ == "__main__":
    main() 