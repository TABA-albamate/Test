import json
import re
from collections import defaultdict
from datetime import datetime
import numpy as np

def cluster_texts_to_grid(ocr_results, row_eps=30, col_eps=30):
    """
    bbox 중심 좌표를 기준으로 행/열 클러스터링하여 2차원 그리드로 변환
    ocr_results: [{'text': str, 'confidence': float, 'bbox': [x1, y1, x2, y2]}]
    return: grid[row][col] = cell_text
    """
    # bbox 중심 좌표 계산
    items = []
    for item in ocr_results:
        bbox = item['bbox']
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
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

# --- 날짜 매핑 ---
def extract_dates_from_row(row_texts, base_year=None, base_month=None):
    dates = []
    year = base_year or datetime.now().year
    month = base_month
    for text in row_texts:
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
        else:
            m2 = re.match(r'\d{1,2}', text)
            if m2 and month:
                day = int(m2.group())
                try:
                    date = datetime(year, month, day).strftime('%Y-%m-%d')
                except:
                    date = ''
            else:
                date = ''
        dates.append(date)
    return dates

# --- 포지션 정보 추출 ---
def extract_positions_from_row(row_texts):
    return [t.strip() for t in row_texts]

# --- 시간대 파싱 ---
def parse_time_range(text):
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*[~-]\s*(\d{1,2})(?::(\d{2}))?', text)
    if m:
        h1, m1, h2, m2 = m.group(1), m.group(2), m.group(3), m.group(4)
        t1 = f"{int(h1):02d}:{int(m1) if m1 else 0:02d}"
        t2 = f"{int(h2):02d}:{int(m2) if m2 else 0:02d}"
        return t1, t2
    return None, None

def extract_time_ranges_from_row(row_texts):
    return [parse_time_range(t) for t in row_texts]

# --- 일정 생성 ---
def generate_schedules(grid, dates, positions, time_ranges, staff_name):
    schedules = []
    n_rows = max(grid.keys())+1
    n_cols = max(max(cols.keys()) for cols in grid.values())+1
    for row in range(n_rows):
        for col in range(n_cols):
            cell = grid.get(row, {}).get(col, '')
            if staff_name in cell:
                date = dates[col] if col < len(dates) else ''
                position = positions[col] if col < len(positions) else ''
                start, end = time_ranges[col] if col < len(time_ranges) else (None, None)
                schedules.append({
                    'date': date,
                    'position': position,
                    'start': start,
                    'end': end,
                    'cell_text': cell
                })
    return schedules

# --- Google Calendar JSON 변환 ---
def schedules_to_gcal_json(schedules, staff_name):
    events = []
    for sch in schedules:
        if not sch['date'] or not sch['start'] or not sch['end']:
            continue
        start_dt = f"{sch['date']}T{sch['start']}:00"
        end_dt = f"{sch['date']}T{sch['end']}:00"
        events.append({
            'summary': f"{staff_name} {sch['position']}",
            'description': sch['cell_text'],
            'start': {'dateTime': start_dt, 'timeZone': 'Asia/Seoul'},
            'end': {'dateTime': end_dt, 'timeZone': 'Asia/Seoul'}
        })
    return events

# --- 메인 파이프라인 함수 ---
def parse_schedule_from_tesseract_result(ocr_result_json_path, staff_name, date_row=0, pos_row=1, time_row=2, data_start_row=3):
    with open(ocr_result_json_path, encoding='utf-8') as f:
        ocr_results = json.load(f)[0]['extracted_texts']  # 첫 번째 이미지 기준
    grid = cluster_texts_to_grid(ocr_results)
    n_rows = max(grid.keys())+1
    n_cols = max(max(cols.keys()) for cols in grid.values())+1
    grid_rows = [[grid.get(row, {}).get(col, '') for col in range(n_cols)] for row in range(n_rows)]
    dates = extract_dates_from_row(grid_rows[date_row])
    positions = extract_positions_from_row(grid_rows[pos_row])
    time_ranges = extract_time_ranges_from_row(grid_rows[time_row])
    schedules = generate_schedules(grid, dates, positions, time_ranges, staff_name)
    gcal_json = schedules_to_gcal_json(schedules, staff_name)
    return gcal_json

if __name__ == "__main__":
    staff_name = "임민지"  # 찾을 직원명
    gcal_json = parse_schedule_from_tesseract_result('tesseract_test_results.json', staff_name)
    with open(f'tesseract_gcal_events_{staff_name}.json', 'w', encoding='utf-8') as f:
        json.dump(gcal_json, f, ensure_ascii=False, indent=2)
    print(f"Google Calendar 일정 JSON이 저장되었습니다: tesseract_gcal_events_{staff_name}.json") 