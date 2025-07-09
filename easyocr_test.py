import easyocr
import time
import re
import json
from collections import Counter
from pathlib import Path
import cv2
import numpy as np

class EasyOCRPerformanceTester:
    def __init__(self, image_path):
        self.image_path = image_path
        self.expected_data = self.define_expected_data()
        self.test_results = {}
        
    def define_expected_data(self):
        """카페/학원 스케줄의 예상 데이터 정의"""
        return {
            "title": "카페/학원 스케줄",
            "staff_names": ["임미지", "이정현", "박서영", "김서정", "허승기"],
            "shift_codes": ["CL", "X", "13-17", "11-15", "09-13", "15-19"],
            "total_cells": 5 * 7,  # 5명 * 7일
            "korean_chars": ["카페", "학원", "스케줄", "근무", "휴무"]
        }
    
    def test_easyocr(self):
        """EasyOCR 실행 및 9개 항목 평가"""
        print("🚀 EasyOCR 성능 테스트 시작...")
        print("=" * 60)
        
        # 기본 OCR 실행
        accuracy_score = self.test_accuracy()
        completeness_score = self.test_completeness()
        speed_score = self.test_speed()
        structure_score = self.test_structure()
        readability_score = self.test_readability()
        error_handling_score = self.test_error_handling()
        korean_support_score = self.test_korean_support()
        consistency_score = self.test_consistency()
        complexity_score = self.test_complexity_handling()
        
        # 최종 점수 계산 (가중평균)
        weights = {
            'accuracy': 25, 'completeness': 20, 'korean_support': 15,
            'speed': 10, 'structure': 10, 'readability': 8,
            'consistency': 5, 'complexity': 4, 'error_handling': 3
        }
        
        total_score = (
            accuracy_score * weights['accuracy'] +
            completeness_score * weights['completeness'] +
            korean_support_score * weights['korean_support'] +
            speed_score * weights['speed'] +
            structure_score * weights['structure'] +
            readability_score * weights['readability'] +
            consistency_score * weights['consistency'] +
            complexity_score * weights['complexity'] +
            error_handling_score * weights['error_handling']
        ) / 100
        
        # 결과 출력
        self.print_results({
            'accuracy': accuracy_score,
            'completeness': completeness_score, 
            'speed': speed_score,
            'structure': structure_score,
            'readability': readability_score,
            'error_handling': error_handling_score,
            'korean_support': korean_support_score,
            'consistency': consistency_score,
            'complexity': complexity_score,
            'total': round(total_score, 1)
        })
        
        return self.test_results
    
    def test_accuracy(self):
        """1. 정확도 테스트 (25점)"""
        print("📊 1. 정확도 테스트")
        
        try:
            start_time = time.time()
            
            # EasyOCR 초기화 (한국어 + 영어)
            reader = easyocr.Reader(['ko', 'en'])
            
            # OCR 실행
            results = reader.readtext(self.image_path)
            
            processing_time = time.time() - start_time
            
            # 결과 텍스트 추출
            extracted_text = ' '.join([text[1] for text in results])
            
            # 정확도 평가
            accuracy_score = self.evaluate_text_accuracy(extracted_text, results)
            
            self.test_results['raw_text'] = extracted_text
            self.test_results['ocr_results'] = results
            self.test_results['processing_time'] = processing_time
            
            print(f"   ✅ 처리시간: {processing_time:.2f}초")
            print(f"   ✅ 추출 텍스트 길이: {len(extracted_text)}자")
            print(f"   ✅ 인식된 텍스트 블록: {len(results)}개")
            print(f"   ✅ 정확도 점수: {accuracy_score}/100")
            
            return accuracy_score
            
        except Exception as e:
            print(f"   ❌ 오류 발생: {e}")
            return 0
    
    def evaluate_text_accuracy(self, extracted_text, results):
        """텍스트 정확도 평가"""
        score = 0
        
        # 이름 인식 (30점)
        expected_names = ["임미지", "이정현", "박서영", "김서정", "허승기"]
        recognized_names = 0
        for name in expected_names:
            if name in extracted_text:
                recognized_names += 1
        score += (recognized_names / len(expected_names)) * 30
        
        # 시간대 인식 (30점)
        time_patterns = ["13-17", "11-15", "09-13", "15-19", "CL", "X"]
        recognized_times = 0
        for pattern in time_patterns:
            if pattern in extracted_text:
                recognized_times += 1
        score += (recognized_times / len(time_patterns)) * 30
        
        # 숫자 인식 (20점)
        numbers = re.findall(r'\d+', extracted_text)
        if len(numbers) >= 10:
            score += 20
        elif len(numbers) >= 5:
            score += 15
        elif len(numbers) >= 2:
            score += 10
            
        # 신뢰도 점수 (20점)
        if results:
            avg_confidence = sum([text[2] for text in results]) / len(results)
            score += avg_confidence * 20
            
        return min(score, 100)
    
    def test_completeness(self):
        """2. 완성도 테스트 (20점)"""
        print("\n📊 2. 완성도 테스트")
        
        results = self.test_results.get('ocr_results', [])
        score = 0
        
        # 인식된 텍스트 블록 수
        total_blocks = len(results)
        
        # 예상 스케줄 엔트리 수 (5명 * 7일 = 35개)
        expected_entries = 35
        
        # 완성도 계산
        if total_blocks >= expected_entries:
            score = 100
        elif total_blocks >= expected_entries * 0.7:
            score = 80
        elif total_blocks >= expected_entries * 0.5:
            score = 60
        elif total_blocks >= expected_entries * 0.3:
            score = 40
        elif total_blocks >= expected_entries * 0.1:
            score = 20
        else:
            score = 0
            
        print(f"   ✅ 인식된 텍스트 블록: {total_blocks}개")
        print(f"   ✅ 예상 엔트리: {expected_entries}개")
        print(f"   ✅ 완성도 점수: {score}/100")
        
        return score
    
    def test_speed(self):
        """3. 속도 테스트 (10점)"""
        print("\n📊 3. 속도 테스트")
        
        processing_time = self.test_results.get('processing_time', 999)
        
        # 속도 기준 (초)
        if processing_time <= 3:
            score = 100
        elif processing_time <= 5:
            score = 80
        elif processing_time <= 10:
            score = 60
        elif processing_time <= 15:
            score = 40
        elif processing_time <= 30:
            score = 20
        else:
            score = 10
            
        print(f"   ✅ 처리시간: {processing_time:.2f}초")
        print(f"   ✅ 속도 점수: {score}/100")
        
        return score
    
    def test_structure(self):
        """4. 구조화 테스트 (10점)"""
        print("\n📊 4. 구조화 테스트")
        
        results = self.test_results.get('ocr_results', [])
        score = 0
        
        # 텍스트 블록 위치 분석
        if len(results) >= 10:
            # 위치 기반 구조 분석
            positions = [(box[0][0], box[0][1]) for box in results]
            
            # 행 구조 인식 (50점)
            y_positions = [pos[1] for pos in positions]
            unique_rows = len(set([round(y, 2) for y in y_positions]))
            if unique_rows >= 5:
                score += 50
            elif unique_rows >= 3:
                score += 30
            elif unique_rows >= 2:
                score += 15
                
            # 열 구조 인식 (50점)
            x_positions = [pos[0] for pos in positions]
            unique_cols = len(set([round(x, 2) for x in x_positions]))
            if unique_cols >= 7:
                score += 50
            elif unique_cols >= 5:
                score += 30
            elif unique_cols >= 3:
                score += 15
                
        print(f"   ✅ 인식된 텍스트 블록: {len(results)}개")
        print(f"   ✅ 구조화 점수: {score}/100")
        
        return score
    
    def test_readability(self):
        """5. 가독성 테스트 (8점)"""
        print("\n📊 5. 가독성 테스트")
        
        extracted_text = self.test_results.get('raw_text', '')
        results = self.test_results.get('ocr_results', [])
        score = 0
        
        # 텍스트 정리도 (40점)
        clean_ratio = len(re.findall(r'[가-힣A-Za-z0-9]', extracted_text)) / max(len(extracted_text), 1)
        score += clean_ratio * 40
        
        # 신뢰도 기반 가독성 (60점)
        if results:
            avg_confidence = sum([text[2] for text in results]) / len(results)
            score += avg_confidence * 60
            
        print(f"   ✅ 텍스트 정리도: {clean_ratio:.1%}")
        print(f"   ✅ 평균 신뢰도: {avg_confidence:.1%}" if results else "   ✅ 평균 신뢰도: 0%")
        print(f"   ✅ 가독성 점수: {score:.1f}/100")
        
        return score
    
    def test_error_handling(self):
        """6. 오류처리 테스트 (3점)"""
        print("\n📊 6. 오류처리 테스트")
        
        score = 100  # 기본점수
        
        try:
            # 잘못된 이미지 경로 테스트
            reader = easyocr.Reader(['ko', 'en'])
            try:
                results = reader.readtext("nonexistent_image.jpg")
                score -= 30  # 오류 처리 부족
            except:
                pass  # 정상적인 오류 처리
                
            print(f"   ✅ 오류처리 점수: {score}/100")
            
        except Exception as e:
            score = 50
            print(f"   ⚠️ 오류 발생: {e}")
            print(f"   ✅ 오류처리 점수: {score}/100")
            
        return score
    
    def test_korean_support(self):
        """7. 한국어 특화도 테스트 (15점)"""
        print("\n📊 7. 한국어 특화도 테스트")
        
        extracted_text = self.test_results.get('raw_text', '')
        score = 0
        
        # 한국어 단어 인식 (60점)
        korean_words = re.findall(r'[가-힣]{2,}', extracted_text)
        expected_korean = ["임미지", "이정현", "박서영", "김서정", "허승기"]
        
        recognized_korean = 0
        for word in expected_korean:
            if word in extracted_text:
                recognized_korean += 1
                
        korean_ratio = recognized_korean / len(expected_korean)
        score += korean_ratio * 60
        
        # 한국어 문자 비율 (40점)
        korean_chars = len(re.findall(r'[가-힣]', extracted_text))
        total_chars = len(re.findall(r'[가-힣A-Za-z]', extracted_text))
        korean_char_ratio = korean_chars / max(total_chars, 1)
        score += korean_char_ratio * 40
        
        print(f"   ✅ 예상 한국어 단어 인식: {recognized_korean}/{len(expected_korean)}")
        print(f"   ✅ 한국어 문자 비율: {korean_char_ratio:.1%}")
        print(f"   ✅ 한국어 특화도 점수: {score:.1f}/100")
        
        return score
    
    def test_consistency(self):
        """8. 일관성 테스트 (5점)"""
        print("\n📊 8. 일관성 테스트")
        
        # 같은 이미지 3번 처리하여 일관성 확인
        results_list = []
        
        try:
            reader = easyocr.Reader(['ko', 'en'])
            
            for i in range(3):
                results = reader.readtext(self.image_path)
                extracted_text = ' '.join([text[1] for text in results])
                results_list.append(extracted_text)
                
            # 결과 비교
            if len(set(results_list)) == 1:
                score = 100  # 완전 일치
            elif len(set(results_list)) == 2:
                score = 70   # 부분 일치
            else:
                score = 40   # 불일치
                
        except:
            score = 50  # 오류 발생
            
        print(f"   ✅ 3회 테스트 결과 일관성")
        print(f"   ✅ 일관성 점수: {score}/100")
        
        return score
    
    def test_complexity_handling(self):
        """9. 복잡도 대응력 테스트 (4점)"""
        print("\n📊 9. 복잡도 대응력 테스트")
        
        extracted_text = self.test_results.get('raw_text', '')
        results = self.test_results.get('ocr_results', [])
        score = 0
        
        # 복잡한 요소들 처리 평가
        complexity_factors = {
            'table_structure': len(results) >= 10,  # 표 구조
            'mixed_languages': len(re.findall(r'[가-힣]', extracted_text)) > 0 and len(re.findall(r'[A-Za-z]', extracted_text)) > 0,  # 다국어
            'special_chars': any(char in extracted_text for char in ['(', ')', ':', '-', '/']),  # 특수문자
            'dense_data': len(results) > 20  # 데이터 밀도
        }
        
        handled_factors = sum(complexity_factors.values())
        score = (handled_factors / len(complexity_factors)) * 100
        
        print(f"   ✅ 표 구조 처리: {'✓' if complexity_factors['table_structure'] else '✗'}")
        print(f"   ✅ 다국어 처리: {'✓' if complexity_factors['mixed_languages'] else '✗'}")
        print(f"   ✅ 특수문자 처리: {'✓' if complexity_factors['special_chars'] else '✗'}")
        print(f"   ✅ 고밀도 데이터: {'✓' if complexity_factors['dense_data'] else '✗'}")
        print(f"   ✅ 복잡도 대응력 점수: {score:.1f}/100")
        
        return score
    
    def print_results(self, scores):
        """최종 결과 출력"""
        print("\n" + "=" * 60)
        print("🏆 EASYOCR 성능 테스트 최종 결과")
        print("=" * 60)
        
        print(f"1. 정확도 (25%):        {scores['accuracy']:.1f}/100")
        print(f"2. 완성도 (20%):        {scores['completeness']:.1f}/100") 
        print(f"3. 한국어 특화도 (15%): {scores['korean_support']:.1f}/100")
        print(f"4. 속도 (10%):          {scores['speed']:.1f}/100")
        print(f"5. 구조화 (10%):        {scores['structure']:.1f}/100")
        print(f"6. 가독성 (8%):         {scores['readability']:.1f}/100")
        print(f"7. 일관성 (5%):         {scores['consistency']:.1f}/100")
        print(f"8. 복잡도 대응력 (4%):  {scores['complexity']:.1f}/100")
        print(f"9. 오류처리 (3%):       {scores['error_handling']:.1f}/100")
        
        print("-" * 60)
        print(f"🎯 총점 (가중평균):     {scores['total']:.1f}/100")
        
        # 등급 매기기
        if scores['total'] >= 90:
            grade = "A+ (탁월함)"
        elif scores['total'] >= 80:
            grade = "A (우수함)"
        elif scores['total'] >= 70:
            grade = "B (양호함)"
        elif scores['total'] >= 60:
            grade = "C (보통함)"
        else:
            grade = "D (개선필요)"
            
        print(f"🏅 등급:               {grade}")
        print("=" * 60)
        
        # 추출된 텍스트 미리보기
        raw_text = self.test_results.get('raw_text', '')
        if raw_text:
            print("\n📄 추출된 텍스트 미리보기 (첫 500자):")
            print("-" * 60)
            print(raw_text[:500] + ("..." if len(raw_text) > 500 else ""))
            print("-" * 60)
        
        # 결과 저장
        with open('easyocr_test_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'scores': scores,
                'raw_text': raw_text,
                'processing_time': self.test_results.get('processing_time', 0),
                'ocr_results_count': len(self.test_results.get('ocr_results', []))
            }, f, ensure_ascii=False, indent=2)

def test_easyocr_on_images():
    """EasyOCR을 사용하여 모든 이미지에서 텍스트를 추출하고 분석합니다."""
    
    # EasyOCR 리더 초기화 (한국어, 영어 지원)
    print("🔧 EasyOCR 초기화 중...")
    reader = easyocr.Reader(['ko', 'en'], gpu=False)
    print("✅ EasyOCR 초기화 완료!")
    
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
            # 이미지 읽기
            image = cv2.imread(str(img_path))
            if image is None:
                print(f"❌ 이미지를 읽을 수 없습니다: {img_path}")
                continue
            
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
                    'confidence': float(confidence),  # numpy 타입을 float로 변환
                    'bbox': [[float(x) for x in point] for point in bbox]  # numpy 배열을 리스트로 변환
                })
                total_confidence += confidence
                total_length += len(text)
            
            avg_confidence = total_confidence / len(extracted_texts) if extracted_texts else 0
            
            # 결과 저장
            result = {
                'image_name': img_path.name,
                'processing_time': processing_time,
                'text_count': len(extracted_texts),
                'avg_confidence': avg_confidence,
                'total_length': total_length,
                'extracted_texts': extracted_texts,
                'full_text': ' '.join([item['text'] for item in extracted_texts])
            }
            
            results.append(result)
            
            # 결과 출력
            print(f"   ⏱️  처리 시간: {processing_time:.2f}초")
            print(f"   📝 추출된 텍스트 수: {len(extracted_texts)}개")
            print(f"   🎯 평균 신뢰도: {avg_confidence:.2f}")
            print(f"   📏 총 텍스트 길이: {total_length}자")
            
            if extracted_texts:
                print(f"   📄 추출된 텍스트 미리보기:")
                for i, item in enumerate(extracted_texts[:5]):  # 처음 5개만 표시
                    print(f"      {i+1}. '{item['text']}' (신뢰도: {item['confidence']:.2f})")
                if len(extracted_texts) > 5:
                    print(f"      ... 외 {len(extracted_texts)-5}개 더")
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
    output_file = 'easyocr_test_results.json'
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

if __name__ == "__main__":
    test_easyocr_on_images() 