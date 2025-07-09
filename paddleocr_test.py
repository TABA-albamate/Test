"""
PaddleOCR + 표 구조 분석 방식 Phase 2: 표 구조 분석 및 데이터 추출
목표: OCR 결과를 2차원 그리드로 변환하여 구조화된 근무표 데이터 추출
"""

import paddleocr
import openai
import json
import time
from PIL import Image
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import re
from datetime import datetime, timedelta

class TableStructureAnalyzer:
    def __init__(self):
        """
        표 구조 분석기 초기화
        """
        self.grid_data = []
        self.date_mapping = {}
        self.position_mapping = {}
        self.time_slots = {}
        self.employee_schedules = {}
        
    def analyze_ocr_result(self, ocr_result) -> Dict:
        """
        OCR 결과를 분석하여 표 구조 정보 추출
        """
        print("\n🔍 표 구조 분석 시작")
        print("-" * 50)
        
        try:
            # OCR 결과를 2차원 그리드로 변환
            self._convert_to_grid(ocr_result)
            
            # 각 단계별 분석 수행
            self._extract_date_mapping()
            self._extract_position_info()
            self._extract_time_slots()
            self._identify_employee_schedules()
            
            # 분석 결과 반환
            analysis_result = {
                'grid_data': self.grid_data,
                'date_mapping': self.date_mapping,
                'position_mapping': self.position_mapping,
                'time_slots': self.time_slots,
                'employee_schedules': self.employee_schedules
            }
            
            self._print_analysis_summary(analysis_result)
            return analysis_result
            
        except Exception as e:
            print(f"❌ 표 구조 분석 오류: {e}")
            return {'error': str(e)}
    
    def _convert_to_grid(self, ocr_result):
        """
        OCR 결과를 2차원 그리드로 변환
        """
        print("📊 OCR 결과를 2차원 그리드로 변환 중...")
        
        if not ocr_result or not ocr_result[0]:
            raise ValueError("OCR 결과가 비어있습니다")
        
        # 좌표 기반으로 텍스트를 그리드에 배치
        text_boxes = []
        for line in ocr_result[0]:
            if (
                len(line) >= 2 and 
                isinstance(line[1], (tuple, list)) and 
                len(line[1]) >= 2 and 
                line[1][0] and line[1][1] is not None
            ):
                bbox = line[0]  # 바운딩 박스 좌표
                text = line[1][0]  # 텍스트
                confidence = line[1][1]  # 신뢰도
                
                # 중심점 계산
                center_x = sum(point[0] for point in bbox) / 4
                center_y = sum(point[1] for point in bbox) / 4
                
                text_boxes.append({
                    'text': text,
                    'x': center_x,
                    'y': center_y,
                    'confidence': confidence,
                    'bbox': bbox
                })
        
        # Y좌표로 정렬하여 행 구분
        text_boxes.sort(key=lambda x: x['y'])
        
        # 행별로 그룹화
        rows = []
        current_row = []
        last_y = None
        y_threshold = 20  # 같은 행으로 간주할 Y좌표 차이 임계값
        
        for box in text_boxes:
            if last_y is None or abs(box['y'] - last_y) <= y_threshold:
                current_row.append(box)
            else:
                if current_row:
                    # X좌표로 정렬하여 열 순서 결정
                    current_row.sort(key=lambda x: x['x'])
                    rows.append(current_row)
                current_row = [box]
            last_y = box['y']
        
        if current_row:
            current_row.sort(key=lambda x: x['x'])
            rows.append(current_row)
        
        # 2차원 그리드 생성
        self.grid_data = []
        for row in rows:
            grid_row = []
            for box in row:
                grid_row.append({
                    'text': box['text'],
                    'confidence': box['confidence'],
                    'position': (box['x'], box['y'])
                })
            self.grid_data.append(grid_row)
        
        print(f"✅ 그리드 변환 완료: {len(self.grid_data)}행, 최대 {max(len(row) for row in self.grid_data) if self.grid_data else 0}열")
    
    def _extract_date_mapping(self):
        """
        날짜 매핑: "날짜" 행에서 월/일 정보 추출하여 각 열에 날짜 매핑
        """
        print("📅 날짜 정보 추출 중...")
        
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})',  # MM/DD 형식
            r'(\d{1,2})월(\d{1,2})일',  # MM월DD일 형식
            r'(\d{1,2})-(\d{1,2})',  # MM-DD 형식
            r'(\d{1,2})\.(\d{1,2})',  # MM.DD 형식
        ]
        
        for row_idx, row in enumerate(self.grid_data):
            for col_idx, cell in enumerate(row):
                text = cell['text'].strip()
                
                # 날짜 패턴 매칭
                for pattern in date_patterns:
                    match = re.search(pattern, text)
                    if match:
                        month = int(match.group(1))
                        day = int(match.group(2))
                        
                        # 2024년 기준으로 날짜 생성
                        try:
                            date_obj = datetime(2024, month, day)
                            self.date_mapping[col_idx] = {
                                'date': date_obj.strftime('%Y-%m-%d'),
                                'month': month,
                                'day': day,
                                'row': row_idx,
                                'text': text
                            }
                            print(f"   📅 열 {col_idx}: {date_obj.strftime('%m/%d')} 발견")
                        except ValueError:
                            continue
        
        print(f"✅ 날짜 매핑 완료: {len(self.date_mapping)}개 날짜 발견")
    
    def _extract_position_info(self):
        """
        포지션 정보: "포지션" 행에서 각 열의 포지션명 추출
        """
        print("👥 포지션 정보 추출 중...")
        
        position_keywords = ['포지션', '직책', '역할', '담당', '부서', '팀']
        
        for row_idx, row in enumerate(self.grid_data):
            # 첫 번째 셀에서 포지션 키워드 확인
            if row and any(keyword in row[0]['text'] for keyword in position_keywords):
                print(f"   📍 포지션 행 발견: 행 {row_idx}")
                
                for col_idx, cell in enumerate(row[1:], 1):  # 첫 번째 셀(헤더) 제외
                    position_name = cell['text'].strip()
                    if position_name and position_name not in ['', '-', 'X']:
                        self.position_mapping[col_idx] = {
                            'name': position_name,
                            'row': row_idx,
                            'text': position_name
                        }
                        print(f"      👤 열 {col_idx}: {position_name}")
                break
        
        print(f"✅ 포지션 매핑 완료: {len(self.position_mapping)}개 포지션 발견")
    
    def _extract_time_slots(self):
        """
        시간대 파싱: 시간 형식 행들을 찾아서 시작/종료 시간 추출
        """
        print("⏰ 시간대 정보 추출 중...")
        
        time_patterns = [
            r'(\d{1,2}):(\d{2})',  # HH:MM 형식
            r'(\d{1,2})시(\d{2})분',  # HH시MM분 형식
            r'(\d{1,2})시',  # HH시 형식
        ]
        
        time_keywords = ['시간', '근무', '시작', '종료', '출근', '퇴근']
        
        for row_idx, row in enumerate(self.grid_data):
            # 시간 관련 키워드가 포함된 행 찾기
            if any(keyword in ' '.join(cell['text'] for cell in row) for keyword in time_keywords):
                print(f"   ⏰ 시간대 행 발견: 행 {row_idx}")
                
                for col_idx, cell in enumerate(row):
                    text = cell['text'].strip()
                    
                    # 시간 패턴 매칭
                    for pattern in time_patterns:
                        match = re.search(pattern, text)
                        if match:
                            hour = int(match.group(1))
                            minute = int(match.group(2)) if len(match.groups()) > 1 else 0
                            
                            time_str = f"{hour:02d}:{minute:02d}"
                            self.time_slots[col_idx] = {
                                'time': time_str,
                                'hour': hour,
                                'minute': minute,
                                'row': row_idx,
                                'text': text
                            }
                            print(f"      🕐 열 {col_idx}: {time_str}")
                            break
        
        print(f"✅ 시간대 매핑 완료: {len(self.time_slots)}개 시간 발견")
    
    def _identify_employee_schedules(self):
        """
        일정 생성: 특정 직원의 이름이 포함된 셀을 찾아 일정 정보 생성
        """
        print("👨‍💼 직원 일정 정보 추출 중...")
        
        # 근무 타입 패턴
        work_patterns = {
            'D': {'name': '주간근무', 'start': '07:00', 'end': '16:00'},
            'E': {'name': '저녁근무', 'start': '13:00', 'end': '22:00'},
            'N': {'name': '야간근무', 'start': '21:30', 'end': '09:00'},
            'OFF': {'name': '휴무', 'start': None, 'end': None},
            '휴무': {'name': '휴무', 'start': None, 'end': None},
            '근무': {'name': '일반근무', 'start': '09:00', 'end': '18:00'},
        }
        
        # 직원 이름 패턴 (한글 이름)
        name_pattern = r'[가-힣]{2,4}'
        
        for row_idx, row in enumerate(self.grid_data):
            for col_idx, cell in enumerate(row):
                text = cell['text'].strip()
                
                # 직원 이름 확인
                name_match = re.search(name_pattern, text)
                if name_match:
                    employee_name = name_match.group()
                    
                    # 해당 직원의 근무 정보 수집
                    employee_schedule = {
                        'name': employee_name,
                        'row': row_idx,
                        'shifts': []
                    }
                    
                    # 같은 행에서 근무 타입 찾기
                    for shift_col_idx, shift_cell in enumerate(row):
                        shift_text = shift_cell['text'].strip()
                        
                        for pattern, work_info in work_patterns.items():
                            if pattern in shift_text:
                                # 날짜 정보 확인
                                date_info = self.date_mapping.get(shift_col_idx)
                                if date_info:
                                    shift_data = {
                                        'date': date_info['date'],
                                        'work_type': work_info['name'],
                                        'start_time': work_info['start'],
                                        'end_time': work_info['end'],
                                        'column': shift_col_idx,
                                        'text': shift_text
                                    }
                                    employee_schedule['shifts'].append(shift_data)
                    
                    if employee_schedule['shifts']:
                        self.employee_schedules[employee_name] = employee_schedule
                        print(f"   👤 {employee_name}: {len(employee_schedule['shifts'])}개 근무 일정")
        
        print(f"✅ 직원 일정 추출 완료: {len(self.employee_schedules)}명의 직원 발견")
    
    def _print_analysis_summary(self, result):
        """
        분석 결과 요약 출력
        """
        print("\n📊 표 구조 분석 결과 요약")
        print("=" * 60)
        print(f"📋 그리드 크기: {len(result['grid_data'])}행 x {max(len(row) for row in result['grid_data']) if result['grid_data'] else 0}열")
        print(f"📅 날짜 정보: {len(result['date_mapping'])}개")
        print(f"👥 포지션 정보: {len(result['position_mapping'])}개")
        print(f"⏰ 시간대 정보: {len(result['time_slots'])}개")
        print(f"👨‍💼 직원 일정: {len(result['employee_schedules'])}명")
        
        # 상세 정보 출력
        if result['date_mapping']:
            print("\n📅 날짜 매핑:")
            for col, info in result['date_mapping'].items():
                print(f"   열 {col}: {info['date']} ({info['text']})")
        
        if result['employee_schedules']:
            print("\n👨‍💼 직원별 근무 일정:")
            for name, schedule in result['employee_schedules'].items():
                print(f"   {name}:")
                for shift in schedule['shifts']:
                    print(f"     - {shift['date']}: {shift['work_type']} ({shift['start_time']}-{shift['end_time']})")

class HybridScheduleProcessor:
    def __init__(self, openai_api_key):
        """
        하이브리드 프로세서 초기화
        """
        # OpenAI API 설정
        openai.api_key = openai_api_key
        
        # PaddleOCR 초기화 (한국어 + 영어)
        self.ocr = paddleocr.PaddleOCR(
            use_angle_cls=True, 
            lang='korean',
            det_db_thresh=0.1,  # 감지 임계값을 낮춤 (기본값: 0.3)
            det_db_box_thresh=0.3,  # 박스 감지 임계값도 낮춤 (기본값: 0.5)
            det_db_unclip_ratio=1.6  # 텍스트 영역 확장 비율
        )
        
        # 표 구조 분석기 초기화
        self.table_analyzer = TableStructureAnalyzer()
        
        print("✅ PaddleOCR + 표 구조 분석 시스템 초기화 완료")
    
    def test_paddleocr_basic(self, image_path):
        """
        Phase 1-1: PaddleOCR 기본 테스트
        """
        print("\n🔍 Phase 1-1: PaddleOCR 기본 성능 테스트")
        print("-" * 50)
        
        try:
            start_time = time.time()
            
            # OCR 실행
            result = self.ocr.ocr(image_path)
            
            processing_time = time.time() - start_time
            
            # 텍스트 추출
            extracted_texts = []
            confidence_scores = []
            
            if result and result[0]:
                for line in result[0]:
                    if (
                        len(line) >= 2 and 
                        isinstance(line[1], (tuple, list)) and 
                        len(line[1]) >= 2 and 
                        line[1][0] and line[1][1] is not None
                    ):
                        text = line[1][0]
                        confidence = line[1][1]
                        extracted_texts.append(text)
                        confidence_scores.append(confidence)
            
            # 결과 분석
            total_text = " ".join(extracted_texts)
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            print(f"✅ OCR 처리 완료:")
            print(f"   처리 시간: {processing_time:.2f}초")
            print(f"   추출된 텍스트 수: {len(extracted_texts)}개")
            print(f"   평균 신뢰도: {avg_confidence:.2f}")
            print(f"   총 텍스트 길이: {len(total_text)}자")
            
            print(f"\n📄 추출된 텍스트 미리보기 (첫 200자):")
            print(f"   {total_text[:200]}{'...' if len(total_text) > 200 else ''}")
            
            return {
                'success': True,
                'extracted_text': total_text,
                'confidence': avg_confidence,
                'processing_time': processing_time,
                'text_count': len(extracted_texts)
            }
            
        except Exception as e:
            print(f"❌ PaddleOCR 오류: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_table_structure_analysis(self, image_path):
        """
        Phase 2-1: 표 구조 분석 테스트
        """
        print("\n🔍 Phase 2-1: 표 구조 분석 테스트")
        print("-" * 50)
        
        try:
            start_time = time.time()
            
            # OCR 실행
            ocr_result = self.ocr.ocr(image_path)
            
            if not ocr_result or not ocr_result[0]:
                return {'success': False, 'error': 'OCR 결과가 비어있습니다'}
            
            # 표 구조 분석
            analysis_result = self.table_analyzer.analyze_ocr_result(ocr_result)
            
            processing_time = time.time() - start_time
            
            if 'error' in analysis_result:
                return {'success': False, 'error': analysis_result['error']}
            
            print(f"\n✅ 표 구조 분석 완료:")
            print(f"   처리 시간: {processing_time:.2f}초")
            print(f"   분석된 직원 수: {len(analysis_result['employee_schedules'])}명")
            print(f"   추출된 근무 일정: {sum(len(schedule['shifts']) for schedule in analysis_result['employee_schedules'].values())}개")
            
            return {
                'success': True,
                'analysis_result': analysis_result,
                'processing_time': processing_time
            }
            
        except Exception as e:
            print(f"❌ 표 구조 분석 오류: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_calendar_json(self, analysis_result):
        """
        Phase 2-2: 분석 결과를 Google Calendar JSON으로 변환
        """
        print("\n📅 Phase 2-2: Google Calendar JSON 생성")
        print("-" * 50)
        
        try:
            calendar_events = []
            
            for employee_name, schedule in analysis_result['employee_schedules'].items():
                for shift in schedule['shifts']:
                    if shift['start_time'] and shift['end_time']:  # 휴무가 아닌 경우
                        # 시작 시간과 종료 시간 파싱
                        start_hour, start_minute = map(int, shift['start_time'].split(':'))
                        end_hour, end_minute = map(int, shift['end_time'].split(':'))
                        
                        # 날짜 파싱
                        date_obj = datetime.strptime(shift['date'], '%Y-%m-%d')
                        
                        # 시작 시간과 종료 시간 생성
                        start_datetime = date_obj.replace(hour=start_hour, minute=start_minute)
                        end_datetime = date_obj.replace(hour=end_hour, minute=end_minute)
                        
                        # 야간근무의 경우 다음날로 종료 시간 조정
                        if shift['work_type'] == '야간근무' and end_hour < start_hour:
                            end_datetime += timedelta(days=1)
                        
                        # Google Calendar 형식으로 변환
                        event = {
                            "summary": f"{employee_name} - {shift['work_type']}",
                            "start": {
                                "dateTime": start_datetime.strftime('%Y-%m-%dT%H:%M:%S+09:00'),
                                "timeZone": "Asia/Seoul"
                            },
                            "end": {
                                "dateTime": end_datetime.strftime('%Y-%m-%dT%H:%M:%S+09:00'),
                                "timeZone": "Asia/Seoul"
                            },
                            "description": f"근무자: {employee_name}\n근무 유형: {shift['work_type']}\n원본 텍스트: {shift['text']}",
                            "colorId": self._get_color_id(shift['work_type'])
                        }
                        
                        calendar_events.append(event)
            
            calendar_data = {
                "events": calendar_events
            }
            
            print(f"✅ Calendar JSON 생성 완료:")
            print(f"   생성된 이벤트: {len(calendar_events)}개")
            
            return {
                'success': True,
                'calendar_data': calendar_data,
                'event_count': len(calendar_events)
            }
            
        except Exception as e:
            print(f"❌ Calendar JSON 생성 오류: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_color_id(self, work_type):
        """
        근무 유형에 따른 색상 ID 반환
        """
        color_mapping = {
            '주간근무': '1',    # 빨간색
            '저녁근무': '2',    # 주황색
            '야간근무': '3',    # 노란색
            '일반근무': '4',    # 초록색
            '휴무': '5'         # 파란색
        }
        return color_mapping.get(work_type, '1')
    
    def test_full_table_analysis(self, image_path):
        """
        Phase 2-3: 전체 표 분석 파이프라인 테스트
        """
        print("\n🔄 Phase 2-3: 전체 표 분석 파이프라인 테스트")
        print("=" * 60)
        
        # 1단계: 표 구조 분석
        analysis_result = self.test_table_structure_analysis(image_path)
        if not analysis_result['success']:
            return {'success': False, 'stage': 'Table Analysis', 'error': analysis_result['error']}
        
        # 2단계: Calendar JSON 생성
        calendar_result = self.generate_calendar_json(analysis_result['analysis_result'])
        if not calendar_result['success']:
            return {'success': False, 'stage': 'Calendar Generation', 'error': calendar_result['error']}
        
        # 3단계: 결과 통합
        total_time = analysis_result['processing_time']
        
        print(f"\n🎉 전체 표 분석 파이프라인 성공!")
        print(f"   총 처리 시간: {total_time:.2f}초")
        print(f"   분석된 직원 수: {len(analysis_result['analysis_result']['employee_schedules'])}명")
        print(f"   생성된 이벤트: {calendar_result['event_count']}개")
        
        return {
            'success': True,
            'analysis_result': analysis_result['analysis_result'],
            'calendar_result': calendar_result,
            'total_time': total_time,
            'calendar_data': calendar_result['calendar_data']
        }

def main():
    """
    Phase 2 메인 실행 함수
    """
    print("🚀 PaddleOCR + 표 구조 분석 Phase 2 테스트")
    print("=" * 70)
    
    # 설정값 입력 (실제 사용시 수정 필요)
    OPENAI_API_KEY = "YOUR_OPENAI_API_KEY_HERE"  # sk-로 시작하는 키
    IMAGE_PATH = "근무표.png"  # 테스트할 근무표 이미지
    
    print("💡 사전 준비사항 확인:")
    print("   □ 근무표 이미지 파일 준비")
    print("   □ 필요 라이브러리 설치 완료")
    print("   □ 표 형태의 근무표 이미지 확인")
    
    try:
        # 하이브리드 프로세서 초기화
        processor = HybridScheduleProcessor(OPENAI_API_KEY)
        
        # 전체 표 분석 파이프라인 테스트 실행
        result = processor.test_full_table_analysis(IMAGE_PATH)
        
        if result['success']:
            print("\n✅ Phase 2 성공! 표 구조 분석 완료")
            print("🚀 Phase 3 계획:")
            print("   1. OCR 정확도 향상")
            print("   2. 복잡한 표 구조 처리")
            print("   3. 에러 처리 및 검증")
            
            # 결과 저장
            with open('table_analysis_result.json', 'w', encoding='utf-8') as f:
                json.dump(result['calendar_data'], f, ensure_ascii=False, indent=2)
            print("💾 결과가 'table_analysis_result.json'에 저장됨")
            
            # 분석 결과도 저장
            with open('analysis_details.json', 'w', encoding='utf-8') as f:
                json.dump(result['analysis_result'], f, ensure_ascii=False, indent=2, default=str)
            print("💾 상세 분석 결과가 'analysis_details.json'에 저장됨")
            
        else:
            print(f"\n❌ Phase 2 실패: {result['stage']} 단계에서 오류")
            print(f"   오류 내용: {result['error']}")
            print("\n🔧 해결 방법:")
            print("   1. 이미지 파일 확인")
            print("   2. 표 형태의 근무표인지 확인")
            print("   3. 이미지 품질 개선")
            
    except Exception as e:
        print(f"\n❌ 시스템 오류: {e}")
        print("💡 문제 해결:")
        print("   1. 라이브러리 설치: pip install paddleocr pillow opencv-python")
        print("   2. 이미지 파일 존재 확인")
        print("   3. 표 형태의 근무표 이미지 사용")

if __name__ == "__main__":
    main()

# Phase 2 체크리스트
def phase2_checklist():
    """
    Phase 2 완료 후 체크할 항목들
    """
    checklist = [
        "□ OCR 결과가 2차원 그리드로 변환되었는가?",
        "□ 날짜 정보가 각 열에 올바르게 매핑되었는가?",
        "□ 포지션 정보가 추출되었는가?",
        "□ 시간대 정보가 파싱되었는가?",
        "□ 직원별 근무 일정이 생성되었는가?",
        "□ Google Calendar JSON이 올바르게 생성되었는가?",
        "□ 전체 처리 시간이 10초 이내인가?"
    ]
    
    print("\n📋 Phase 2 완료 체크리스트:")
    for item in checklist:
        print(f"   {item}")
    
    print("\n✅ 모든 항목이 체크되면 Phase 3 진행!")

# 비용 계산기 (Phase 2는 GPT 사용 안함)
def estimate_phase2_cost():
    """
    Phase 2 사용 비용 예상 (GPT 사용 안함)
    """
    print(f"\n💰 Phase 2 비용 예상:")
    print(f"   GPT API 사용: 없음")
    print(f"   PaddleOCR: 무료")
    print(f"   총 비용: $0.00")
    
    return 0.0 