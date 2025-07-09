import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
import numpy as np

def analyze_image5_structure(ocr_results):
    """image5.jpg의 특정 구조를 분석하여 개선된 파싱을 수행합니다."""
    
    # 2차원 그리드로 변환
    grid = cluster_texts_to_grid(ocr_results)
    
    # 그리드 크기 계산
    n_rows = max(grid.keys()) + 1 if grid else 0
    n_cols = max(max(cols.keys()) for cols in grid.values()) + 1 if grid else 0
    
    print(f"📋 그리드 크기: {n_rows}행 x {n_cols}열")
    
    # 실제 구조 분석
    # image5.jpg는 3주차 근무표로 보임
    # 행 0, 6, 12, 18: 요일/일자 헤더
    # 행 1-5, 7-11, 13-17, 19-23: 직원별 근무 정보
    
    schedules = []
    
    # 주차별로 분석
    weeks = [
        (0, 5),   # 1주차: 행 0-5
        (6, 11),  # 2주차: 행 6-11  
        (12, 17), # 3주차: 행 12-17
        (18, 23)  # 4주차: 행 18-23
    ]
    
    for week_idx, (start_row, end_row) in enumerate(weeks):
        print(f"\n📅 {week_idx + 1}주차 분석:")
        
        # 헤더 행에서 날짜 정보 추출
        header_row = start_row
        header_texts = [grid.get(header_row, {}).get(col, '') for col in range(n_cols)]
        print(f"   헤더: {header_texts}")
        
        # 날짜 추출 (예: 3, 5, 9, 10, 11, 12, 13, 14, 15)
        dates = []
        for col in range(n_cols):
            text = header_texts[col]
            if text.isdigit():
                # 2025년 1월 기준으로 날짜 생성
                day = int(text)
                try:
                    date = datetime(2025, 1, day).strftime('%Y-%m-%d')
                    dates.append(date)
                except:
                    dates.append('')
            else:
                dates.append('')
        
        print(f"   날짜: {dates}")
        
        # 직원별 근무 정보 분석
        for row in range(start_row + 1, end_row + 1):
            row_texts = [grid.get(row, {}).get(col, '') for col in range(n_cols)]
            
            # 직원명 추출 (첫 번째 열)
            staff_name = row_texts[0] if row_texts else ''
            
            if staff_name and len(staff_name) >= 2:  # 유효한 직원명인 경우
                print(f"   👤 {staff_name}: {row_texts[1:]}")
                
                # 각 열(날짜)별 근무 정보 분석
                for col in range(1, min(len(row_texts), len(dates))):
                    cell_text = row_texts[col]
                    date = dates[col]
                    
                    if cell_text and cell_text != '' and date:
                        # 시간대 파싱
                        time_range = parse_time_range(cell_text)
                        
                        if time_range[0] and time_range[1]:
                            # 유효한 시간대가 있는 경우
                            schedule = {
                                'staff_name': staff_name,
                                'date': date,
                                'start_time': time_range[0],
                                'end_time': time_range[1],
                                'cell_text': cell_text,
                                'week': week_idx + 1
                            }
                            schedules.append(schedule)
                            print(f"      📅 {date} {time_range[0]}-{time_range[1]} ({cell_text})")
                        elif 'CL' in cell_text or 'X' in cell_text:
                            # 특별 근무 (CL: Close, X: 휴무 등)
                            schedule = {
                                'staff_name': staff_name,
                                'date': date,
                                'start_time': None,
                                'end_time': None,
                                'cell_text': cell_text,
                                'week': week_idx + 1,
                                'special_duty': True
                            }
                            schedules.append(schedule)
                            print(f"      📅 {date} 특별근무 ({cell_text})")
    
    return schedules

def cluster_texts_to_grid(ocr_results, row_eps=30, col_eps=30):
    """bbox 중심 좌표를 기준으로 행/열 클러스터링하여 2차원 그리드로 변환"""
    # bbox 중심 좌표 계산
    items = []
    for item in ocr_results:
        bbox = item['bbox']
        cx = np.mean([p[0] for p in bbox])
        cy = np.mean([p[1] for p in bbox])
        items.append({'text': item['text'], 'cx': cx, 'cy': cy, 'bbox': bbox, 'confidence': item['confidence']})

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

def parse_time_range(text):
    """시간 범위 파싱"""
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

def schedules_to_gcal_json(schedules, staff_name=None):
    """Google Calendar API용 JSON 변환"""
    events = []
    for sch in schedules:
        if staff_name and sch['staff_name'] != staff_name:
            continue
            
        if not sch['date'] or not sch['start_time'] or not sch['end_time']:
            continue
            
        start_dt = f"{sch['date']}T{sch['start_time']}:00"
        end_dt = f"{sch['date']}T{sch['end_time']}:00"
        
        summary = f"{sch['staff_name']} 근무"
        if sch.get('special_duty'):
            summary = f"{sch['staff_name']} {sch['cell_text']}"
            
        events.append({
            'summary': summary,
            'description': f"주차: {sch['week']}주차, 셀내용: {sch['cell_text']}",
            'start': {'dateTime': start_dt, 'timeZone': 'Asia/Seoul'},
            'end': {'dateTime': end_dt, 'timeZone': 'Asia/Seoul'}
        })
    return events

def main():
    """메인 실행 함수"""
    # image5_ocr_results.json에서 OCR 결과 읽기
    try:
        with open('image5_ocr_results.json', 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)
            ocr_results = ocr_data['extracted_texts']
    except FileNotFoundError:
        print("❌ image5_ocr_results.json 파일을 찾을 수 없습니다.")
        print("먼저 test_image5.py를 실행해주세요.")
        return
    
    print("🔍 image5.jpg 근무표 분석 시작")
    print("=" * 60)
    
    # 개선된 구조 분석
    schedules = analyze_image5_structure(ocr_results)
    
    print(f"\n📊 분석 결과 요약:")
    print(f"총 일정 수: {len(schedules)}개")
    
    # 직원별 일정 요약
    staff_summary = defaultdict(list)
    for sch in schedules:
        staff_summary[sch['staff_name']].append(sch)
    
    print(f"\n👥 직원별 일정:")
    for staff, staff_schedules in staff_summary.items():
        print(f"   {staff}: {len(staff_schedules)}개 일정")
        for sch in staff_schedules[:3]:  # 처음 3개만 표시
            if sch.get('special_duty'):
                print(f"     - {sch['date']} {sch['cell_text']}")
            else:
                print(f"     - {sch['date']} {sch['start_time']}-{sch['end_time']}")
        if len(staff_schedules) > 3:
            print(f"     ... 외 {len(staff_schedules)-3}개 더")
    
    # Google Calendar JSON 생성
    print(f"\n💾 Google Calendar JSON 생성 중...")
    
    # 전체 일정
    all_events = schedules_to_gcal_json(schedules)
    with open('image5_all_schedules.json', 'w', encoding='utf-8') as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)
    print(f"   전체 일정: image5_all_schedules.json ({len(all_events)}개)")
    
    # 직원별 일정
    for staff in staff_summary.keys():
        staff_events = schedules_to_gcal_json(schedules, staff)
        if staff_events:
            filename = f'image5_{staff}_schedules.json'
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(staff_events, f, ensure_ascii=False, indent=2)
            print(f"   {staff} 일정: {filename} ({len(staff_events)}개)")
    
    print(f"\n✅ 분석 완료!")

if __name__ == "__main__":
    main() 