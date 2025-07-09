import pytesseract
from PIL import Image
import time
import re
import json
from collections import Counter
import numpy as np

# Tesseract 경로 설정 (Windows 환경)
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\User\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts\pytesseract.exe'

class CafeScheduleTesseractTester:
    def __init__(self, image_path):
        self.image_path = image_path
        self.expected_data = self.define_expected_data()
        self.test_results = {}
        
    def define_expected_data(self):
        """카페/학원 스케줄표 예상 데이터 정의"""
        return {
            "staff_names": ["임미지", "이정현", "박서영", "김서정", "허승기"],
            "shift_codes": ["CL", "X", "13-17", "11-15", "12-17", "9-13", "12-15:30"],
            "dates": list(range(1, 31)),  # 1일~30일 (달에 따라 다름)
            "time_patterns": [
                "13-17", "11-15", "12-17", "9-13", "12-15:30"
            ],
            "special_codes": {
                "CL": "마감/클로징",
                "X": "휴무",
                "OP": "오픈"
            },
            "total_cells": 5 * 23,  # 5명 × 23일 정도
            "korean_elements": ["임미지", "이정현", "박서영", "김서정", "허승기"],
            "complexity_factors": [
                "mixed_time_formats",  # 13-17, 12-15:30 등
                "special_symbols",     # CL, X 등
                "table_structure",     # 격자형 표
                "korean_names",        # 한국어 이름
                "number_time_mix"      # 숫자와 시간 혼재
            ]
        }
    
    def run_complete_test(self):
        """전체 성능 테스트 실행"""
        print("🚀 카페/학원 스케줄 - Tesseract 성능 테스트 시작")
        print("📋 테스트 이미지: 복잡한 시간표 형태 (중간 난이도)")
        print("=" * 70)
        
        # 기본 OCR 실행 및 데이터 수집
        self.execute_base_ocr()
        
        # 9개 항목별 테스트 실행
        scores = {
            'accuracy': self.test_accuracy(),
            'completeness': self.test_completeness(), 
            'speed': self.test_speed(),
            'structure': self.test_structure(),
            'readability': self.test_readability(),
            'error_handling': self.test_error_handling(),
            'korean_support': self.test_korean_support(),
            'consistency': self.test_consistency(),
            'complexity': self.test_complexity_handling()
        }
        
        # 가중평균 계산
        weights = {
            'accuracy': 25, 'completeness': 20, 'korean_support': 15,
            'structure': 10, 'speed': 10, 'readability': 8,
            'consistency': 5, 'complexity': 4, 'error_handling': 3
        }
        
        total_score = sum(scores[key] * weights[key] for key in scores) / 100
        scores['total'] = round(total_score, 1)
        
        # 결과 출력
        self.print_final_results(scores)
        return scores
    
    def execute_base_ocr(self):
        """기본 OCR 실행 및 결과 저장"""
        try:
            img = Image.open(self.image_path)
            start_time = time.time()
            
            # 여러 OCR 설정 시도
            configs = [
                r'--oem 3 --psm 6',  # 기본 설정
                r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz가-힣()[]:/\-+,.XCL',
                r'--oem 3 --psm 4',  # 단일 컬럼 텍스트
                r'--oem 3 --psm 8'   # 단일 단어
            ]
            
            results = []
            for config in configs:
                try:
                    result = pytesseract.image_to_string(img, lang='kor+eng', config=config)
                    results.append(result)
                except:
                    results.append("")
            
            # 가장 긴 결과를 메인 결과로 선택
            best_result = max(results, key=len) if results else ""
            
            end_time = time.time()
            
            self.test_results.update({
                'raw_text': best_result,
                'all_results': results,
                'processing_time': end_time - start_time,
                'image_size': img.size,
                'text_length': len(best_result)
            })
            
        except Exception as e:
            print(f"❌ OCR 실행 오류: {e}")
            self.test_results.update({
                'raw_text': "",
                'processing_time': 999,
                'error': str(e)
            })
    
    def test_accuracy(self):
        """1. 정확도 테스트 (25%)"""
        print("📊 1. 정확도 테스트")
        
        extracted_text = self.test_results.get('raw_text', '')
        score = 0
        
        # 스태프 이름 인식 (40점)
        recognized_names = 0
        for name in self.expected_data['staff_names']:
            if name in extracted_text:
                recognized_names += 1
            elif any(char in extracted_text for char in name):  # 부분 일치
                recognized_names += 0.5
        
        name_score = (recognized_names / len(self.expected_data['staff_names'])) * 40
        score += name_score
        
        # 시간대 인식 (30점)
        time_patterns_found = 0
        for pattern in self.expected_data['time_patterns']:
            if pattern in extracted_text or pattern.replace('-', '') in extracted_text:
                time_patterns_found += 1
        
        time_score = (time_patterns_found / len(self.expected_data['time_patterns'])) * 30
        score += time_score
        
        # 특수 코드 인식 (20점)
        special_codes_found = 0
        for code in ['CL', 'X']:
            count = extracted_text.count(code)
            if count >= 3:  # 충분히 많이 발견됨
                special_codes_found += 1
            elif count >= 1:  # 일부 발견됨
                special_codes_found += 0.5
        
        special_score = (special_codes_found / 2) * 20
        score += special_score
        
        # 숫자 인식 (10점)
        numbers = re.findall(r'\d+', extracted_text)
        if len(numbers) >= 15:
            number_score = 10
        elif len(numbers) >= 10:
            number_score = 7
        elif len(numbers) >= 5:
            number_score = 4
        else:
            number_score = 1
        score += number_score
        
        print(f"   ✅ 이름 인식: {recognized_names:.1f}/{len(self.expected_data['staff_names'])} (점수: {name_score:.1f})")
        print(f"   ✅ 시간대 인식: {time_patterns_found}/{len(self.expected_data['time_patterns'])} (점수: {time_score:.1f})")
        print(f"   ✅ 특수코드 인식: {special_codes_found:.1f}/2 (점수: {special_score:.1f})")
        print(f"   ✅ 숫자 인식: {len(numbers)}개 (점수: {number_score})")
        print(f"   🎯 정확도 총점: {score:.1f}/100")
        
        return min(score, 100)
    
    def test_completeness(self):
        """2. 완성도 테스트 (20%)"""
        print("\n📊 2. 완성도 테스트")
        
        extracted_text = self.test_results.get('raw_text', '')
        score = 0
        
        # 전체 스케줄 라인 수 계산
        lines = [line.strip() for line in extracted_text.split('\n') if line.strip()]
        
        # 의미있는 스케줄 라인 식별
        schedule_lines = []
        for line in lines:
            # 이름이나 시간이 포함된 라인
            if (any(name in line for name in self.expected_data['staff_names']) or
                any(time in line for time in ['13-17', '11-15', '12-17', '9-13']) or
                'CL' in line or 'X' in line):
                schedule_lines.append(line)
        
        # 예상 총 라인 수 (5명)
        expected_lines = 5
        completeness_ratio = min(len(schedule_lines) / expected_lines, 1.0)
        
        # 데이터 밀도 평가
        total_expected_entries = 5 * 20  # 5명 × 약 20일
        
        # 스케줄 엔트리 추정
        cl_count = extracted_text.count('CL')
        x_count = extracted_text.count('X')
        time_entries = len(re.findall(r'\d{1,2}-\d{1,2}', extracted_text))
        
        total_entries = cl_count + x_count + time_entries
        entry_ratio = min(total_entries / total_expected_entries, 1.0)
        
        # 완성도 점수 계산
        score = (completeness_ratio * 60) + (entry_ratio * 40)
        
        print(f"   ✅ 인식된 스케줄 라인: {len(schedule_lines)}/{expected_lines}")
        print(f"   ✅ 총 스케줄 엔트리: {total_entries}개 (예상: {total_expected_entries})")
        print(f"   ✅ CL 엔트리: {cl_count}개")
        print(f"   ✅ X(휴무) 엔트리: {x_count}개")
        print(f"   ✅ 시간 엔트리: {time_entries}개")
        print(f"   🎯 완성도 점수: {score:.1f}/100")
        
        return score
    
    def test_speed(self):
        """3. 속도 테스트 (10%)"""
        print("\n📊 3. 속도 테스트")
        
        processing_time = self.test_results.get('processing_time', 999)
        
        # 카페 스케줄은 상대적으로 복잡하므로 기준 조정
        if processing_time <= 3:
            score = 100
        elif processing_time <= 6:
            score = 85
        elif processing_time <= 10:
            score = 70
        elif processing_time <= 15:
            score = 50
        elif processing_time <= 25:
            score = 30
        else:
            score = 10
            
        print(f"   ✅ 처리시간: {processing_time:.2f}초")
        print(f"   🎯 속도 점수: {score}/100")
        
        return score
    
    def test_structure(self):
        """4. 구조화 테스트 (10%)"""
        print("\n📊 4. 구조화 테스트")
        
        extracted_text = self.test_results.get('raw_text', '')
        score = 0
        
        # 표 헤더 인식 (날짜 줄)
        header_score = 0
        lines = extracted_text.split('\n')
        for line in lines[:3]:  # 상위 3줄에서 날짜 헤더 찾기
            numbers_in_line = len(re.findall(r'\b\d{1,2}\b', line))
            if numbers_in_line >= 5:  # 날짜가 여러개 있으면 헤더로 판단
                header_score = 25
                break
            elif numbers_in_line >= 3:
                header_score = 15
        
        score += header_score
        
        # 행별 구조 인식 (이름 + 스케줄)
        structured_rows = 0
        for line in lines:
            # 이름으로 시작하고 스케줄 데이터가 있는 행
            has_name = any(name in line for name in self.expected_data['staff_names'])
            has_schedule = any(pattern in line for pattern in ['CL', 'X', '13-17', '11-15', '12-17'])
            
            if has_name and has_schedule:
                structured_rows += 1
            elif has_name or has_schedule:
                structured_rows += 0.5
        
        structure_score = min((structured_rows / 5) * 40, 40)  # 5명 기준
        score += structure_score
        
        # 열 정렬 인식
        column_score = 0
        # 시간 패턴이 규칙적으로 등장하는지 확인
        time_positions = []
        for match in re.finditer(r'\d{1,2}-\d{1,2}', extracted_text):
            time_positions.append(match.start())
        
        if len(time_positions) >= 10:
            column_score = 35
        elif len(time_positions) >= 5:
            column_score = 25
        elif len(time_positions) >= 2:
            column_score = 15
        
        score += column_score
        
        print(f"   ✅ 헤더 인식: {header_score}/25")
        print(f"   ✅ 행 구조: {structured_rows:.1f}/5 (점수: {structure_score:.1f}/40)")
        print(f"   ✅ 열 정렬: {len(time_positions)}개 시간패턴 (점수: {column_score}/35)")
        print(f"   🎯 구조화 점수: {score:.1f}/100")
        
        return min(score, 100)
    
    def test_readability(self):
        """5. 가독성 테스트 (8%)"""
        print("\n📊 5. 가독성 테스트")
        
        extracted_text = self.test_results.get('raw_text', '')
        
        # 텍스트 정리도 (불필요한 문자 비율)
        total_chars = len(extracted_text)
        meaningful_chars = len(re.findall(r'[가-힣A-Za-z0-9:\-X]', extracted_text))
        clean_ratio = meaningful_chars / max(total_chars, 1)
        
        # 라인 정리도
        lines = [line.strip() for line in extracted_text.split('\n') if line.strip()]
        meaningful_lines = [line for line in lines if len(line) > 2 and 
                          (any(c.isalnum() for c in line) or 'CL' in line or 'X' in line)]
        
        line_quality = len(meaningful_lines) / max(len(lines), 1)
        
        # 스케줄 패턴 명확성
        clear_patterns = 0
        total_patterns = 0
        for line in meaningful_lines:
            total_patterns += 1
            # 명확한 스케줄 패턴이 있는지 확인
            if (any(name in line for name in self.expected_data['staff_names']) and
                (any(time in line for time in ['13-17', '11-15', '12-17']) or 
                 'CL' in line or 'X' in line)):
                clear_patterns += 1
        
        pattern_clarity = clear_patterns / max(total_patterns, 1)
        
        # 가독성 점수 계산
        score = (clean_ratio * 30) + (line_quality * 40) + (pattern_clarity * 30)
        
        print(f"   ✅ 텍스트 정리도: {clean_ratio:.1%}")
        print(f"   ✅ 의미있는 라인: {len(meaningful_lines)}/{len(lines)} ({line_quality:.1%})")
        print(f"   ✅ 패턴 명확성: {clear_patterns}/{total_patterns} ({pattern_clarity:.1%})")
        print(f"   🎯 가독성 점수: {score:.1f}/100")
        
        return score
    
    def test_error_handling(self):
        """6. 오류처리 테스트 (3%)"""
        print("\n📊 6. 오류처리 테스트")
        
        score = 100
        error_count = 0
        
        # 기본 실행 오류 확인
        if 'error' in self.test_results:
            error_count += 1
            score -= 40
        
        # 결과 유효성 검사
        raw_text = self.test_results.get('raw_text', '')
        if len(raw_text) < 10:  # 너무 짧은 결과
            error_count += 1
            score -= 30
        
        # 다중 설정 시도 결과 확인
        all_results = self.test_results.get('all_results', [])
        failed_configs = sum(1 for result in all_results if len(result) < 5)
        if failed_configs > 2:
            error_count += 1
            score -= 30
        
        print(f"   ✅ 기본 실행: {'성공' if 'error' not in self.test_results else '실패'}")
        print(f"   ✅ 결과 유효성: {'양호' if len(raw_text) >= 10 else '부족'}")
        print(f"   ✅ 설정 안정성: {len(all_results) - failed_configs}/{len(all_results)} 성공")
        print(f"   🎯 오류처리 점수: {max(score, 0)}/100")
        
        return max(score, 0)
    
    def test_korean_support(self):
        """7. 한국어 특화도 테스트 (15%)"""
        print("\n📊 7. 한국어 특화도 테스트")
        
        extracted_text = self.test_results.get('raw_text', '')
        score = 0
        
        # 한국어 이름 인식 정확도
        name_recognition = 0
        for name in self.expected_data['korean_elements']:
            if name in extracted_text:
                name_recognition += 1
            elif len([c for c in name if c in extracted_text]) >= len(name) // 2:
                name_recognition += 0.3  # 부분 인식
        
        name_score = (name_recognition / len(self.expected_data['korean_elements'])) * 60
        
        # 한국어 문자 비율
        korean_chars = len(re.findall(r'[가-힣]', extracted_text))
        total_chars = len(re.findall(r'[가-힣A-Za-z]', extracted_text))
        korean_ratio = korean_chars / max(total_chars, 1)
        
        # 예상 한국어 비율 (이름들로 인해 약 30-40% 예상)
        if korean_ratio >= 0.2:
            ratio_score = 40
        elif korean_ratio >= 0.1:
            ratio_score = 25
        elif korean_ratio >= 0.05:
            ratio_score = 15
        else:
            ratio_score = 5
        
        score = name_score + ratio_score
        
        print(f"   ✅ 한국어 이름 인식: {name_recognition:.1f}/{len(self.expected_data['korean_elements'])} (점수: {name_score:.1f})")
        print(f"   ✅ 한국어 문자 비율: {korean_ratio:.1%} (점수: {ratio_score})")
        print(f"   🎯 한국어 특화도 점수: {score:.1f}/100")
        
        return min(score, 100)
    
    def test_consistency(self):
        """8. 일관성 테스트 (5%)"""
        print("\n📊 8. 일관성 테스트")
        
        # 여러 설정으로 실행한 결과들의 일관성 확인
        all_results = self.test_results.get('all_results', [])
        
        if len(all_results) < 2:
            score = 50
            print(f"   ⚠️ 일관성 테스트 데이터 부족")
        else:
            # 결과들의 유사성 계산
            similarities = []
            main_result = all_results[0]
            
            for result in all_results[1:]:
                # 공통 단어 비율로 유사성 측정
                words1 = set(main_result.split())
                words2 = set(result.split())
                
                if len(words1) == 0 and len(words2) == 0:
                    similarity = 1.0
                elif len(words1) == 0 or len(words2) == 0:
                    similarity = 0.0
                else:
                    common_words = len(words1.intersection(words2))
                    total_words = len(words1.union(words2))
                    similarity = common_words / total_words
                
                similarities.append(similarity)
            
            avg_similarity = np.mean(similarities) if similarities else 0
            
            if avg_similarity >= 0.8:
                score = 100
            elif avg_similarity >= 0.6:
                score = 80
            elif avg_similarity >= 0.4:
                score = 60
            elif avg_similarity >= 0.2:
                score = 40
            else:
                score = 20
            
            print(f"   ✅ 설정별 결과 유사성: {avg_similarity:.1%}")
        
        print(f"   🎯 일관성 점수: {score}/100")
        return score
    
    def test_complexity_handling(self):
        """9. 복잡도 대응력 테스트 (4%)"""
        print("\n📊 9. 복잡도 대응력 테스트")
        
        extracted_text = self.test_results.get('raw_text', '')
        
        complexity_scores = {}
        
        # 혼재된 시간 형식 처리 (13-17, 12-15:30)
        time_formats = ['13-17', '11-15', '12-17', '9-13', '12-15:30']
        recognized_formats = sum(1 for fmt in time_formats if fmt in extracted_text)
        complexity_scores['time_formats'] = (recognized_formats / len(time_formats)) * 25
        
        # 특수 기호 처리 (CL, X)
        special_symbols = ['CL', 'X']
        recognized_symbols = sum(1 for symbol in special_symbols if symbol in extracted_text)
        complexity_scores['special_symbols'] = (recognized_symbols / len(special_symbols)) * 25
        
        # 표 구조 복잡성 (격자형 데이터)
        lines = [line.strip() for line in extracted_text.split('\n') if line.strip()]
        structured_lines = sum(1 for line in lines if len(line.split()) >= 3)
        table_score = min((structured_lines / 5) * 25, 25)  # 5줄 이상이면 만점
        complexity_scores['table_structure'] = table_score
        
        # 다국어 혼재 (한국어 + 영어 + 숫자)
        has_korean = len(re.findall(r'[가-힣]', extracted_text)) > 0
        has_english = len(re.findall(r'[A-Za-z]', extracted_text)) > 0
        has_numbers = len(re.findall(r'\d', extracted_text)) > 0
        
        multilang_count = sum([has_korean, has_english, has_numbers])
        complexity_scores['multilingual'] = (multilang_count / 3) * 25
        
        total_score = sum(complexity_scores.values())
        
        print(f"   ✅ 시간 형식 처리: {recognized_formats}/{len(time_formats)} (점수: {complexity_scores['time_formats']:.1f})")
        print(f"   ✅ 특수 기호 처리: {recognized_symbols}/{len(special_symbols)} (점수: {complexity_scores['special_symbols']:.1f})")
        print(f"   ✅ 표 구조 처리: {structured_lines}줄 (점수: {complexity_scores['table_structure']:.1f})")
        print(f"   ✅ 다국어 처리: {multilang_count}/3 (점수: {complexity_scores['multilingual']:.1f})")
        print(f"   🎯 복잡도 대응력 점수: {total_score:.1f}/100")
        
        return total_score
    
    def print_final_results(self, scores):
        """최종 결과 출력"""
        print("\n" + "=" * 70)
        print("🏆 카페/학원 스케줄 - TESSERACT 성능 테스트 최종 결과")
        print("=" * 70)
        
        # 점수별 출력
        print(f"1. 정확도 (25%):        {scores['accuracy']:.1f}/100")
        print(f"2. 완성도 (20%):        {scores['completeness']:.1f}/100") 
        print(f"3. 한국어 특화도 (15%): {scores['korean_support']:.1f}/100")
        print(f"4. 속도 (10%):          {scores['speed']:.1f}/100")
        print(f"5. 구조화 (10%):        {scores['structure']:.1f}/100")
        print(f"6. 가독성 (8%):         {scores['readability']:.1f}/100")
        print(f"7. 일관성 (5%):         {scores['consistency']:.1f}/100")
        print(f"8. 복잡도 대응력 (4%):  {scores['complexity']:.1f}/100")
        print(f"9. 오류처리 (3%):       {scores['error_handling']:.1f}/100")
        
        print("-" * 70)
        print(f"🎯 총점 (가중평균):     {scores['total']:.1f}/100")
        
        # 등급 산정
        if scores['total'] >= 90:
            grade = "A+ (탁월함)"
            emoji = "🌟"
        elif scores['total'] >= 80:
            grade = "A (우수함)"  
            emoji = "⭐"
        elif scores['total'] >= 70:
            grade = "B (양호함)"
            emoji = "👍"
        elif scores['total'] >= 60:
            grade = "C (보통함)"
            emoji = "👌"
        else:
            grade = "D (개선필요)"
            emoji = "📈"
            
        print(f"🏅 등급:               {grade} {emoji}")
        
        # 강점/약점 분석
        print("\n📊 성능 분석:")
        strengths = [k for k, v in scores.items() if k != 'total' and v >= 70]
        weaknesses = [k for k, v in scores.items() if k != 'total' and v < 50]
        
        if strengths:
            print(f"✅ 강점: {', '.join(strengths)}")
        if weaknesses:
            print(f"❌ 약점: {', '.join(weaknesses)}")
        
        print("=" * 70)
        
        # 추출된 텍스트 미리보기
        raw_text = self.test_results.get('raw_text', '')
        if raw_text:
            print("\n📄 추출된 텍스트 미리보기 (첫 300자):")
            print("-" * 70)
            preview = raw_text[:300] + ("..." if len(raw_text) > 300 else "")
            print(preview)
            print("-" * 70)
        
        # 다음 단계 안내
        print("\n🚀 다음 단계:")
        print("1. EasyOCR 테스트 실행")
        print("2. PaddleOCR 테스트 실행") 
        print("3. 성능 비교 분석")
        print("4. 최적 OCR 서비스 선정")

# 실행 코드
if __name__ == "__main__":
    # 이미지 파일 경로 설정 (실제 파일명으로 변경 필요)
    image_path = "cafe_schedule.jpg"  # ← 실제 이미지 파일명으로 변경하세요
    
    print("📋 카페/학원 스케줄 이미지 분석 정보:")
    print("- 스태프: 임미지, 이정현, 박서영, 김서정, 허승기")
    print("- 근무 형태: CL(클로징), X(휴무), 시간대(13-17, 11-15 등)")
    print("- 난이도: 중간 (복잡한 시간 형식 + 특수 기호)")
    print("-" * 50)
    
    # 테스트 실행
    tester = CafeScheduleTesseractTester(image_path)
    results = tester.run_complete_test()
    
    # 결과 JSON으로 저장 (선택사항)
    import json
    with open('tesseract_test_results.json', 'w', encoding='utf-8') as f:
        json.dump({
            'service': 'Tesseract',
            'image_type': 'cafe_schedule',
            'scores': results,
            'test_date': time.strftime('%Y-%m-%d %H:%M:%S')
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 테스트 결과가 'tesseract_test_results.json'에 저장되었습니다.")
    print("🎯 이제 EasyOCR과 PaddleOCR 테스트를 진행해보세요!")