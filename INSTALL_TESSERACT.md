# Tesseract OCR 설치 가이드

## 문제 상황
현재 `pytesseract.exe` 경로를 사용하고 있지만, 이는 Python 패키지의 실행 파일이지 실제 Tesseract OCR 엔진이 아닙니다.

## 해결 방법

### 1. Tesseract OCR 엔진 설치

#### Windows에서 설치:
1. [Tesseract 다운로드 페이지](https://github.com/UB-Mannheim/tesseract/wiki) 방문
2. 최신 버전 다운로드 (예: `tesseract-ocr-w64-setup-5.3.1.20230401.exe`)
3. 설치 시 다음 옵션 선택:
   - **Additional language data (download)** 체크
   - **Korean** 언어팩 선택
4. 기본 설치 경로: `C:\Program Files\Tesseract-OCR\`

#### 설치 확인:
```bash
# 명령 프롬프트에서
"C:\Program Files\Tesseract-OCR\tesseract.exe" --version
```

### 2. 환경 변수 설정 (선택사항)

#### PowerShell에서:
```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

#### 시스템 환경 변수에 추가:
1. 시스템 속성 → 고급 → 환경 변수
2. 새로 만들기: 변수명 `TESSERACT_CMD`, 값 `C:\Program Files\Tesseract-OCR\tesseract.exe`

### 3. 테스트 이미지 준비

현재 `image3.jpg` 파일이 없습니다. 다음 중 하나를 선택하세요:

#### 옵션 A: 간단한 텍스트 이미지 생성
```python
from PIL import Image, ImageDraw, ImageFont

# 800x400 크기의 흰색 이미지 생성
image = Image.new('RGB', (800, 400), color='white')
draw = ImageDraw.Draw(image)

# 텍스트 그리기
text = "안녕하세요! 이것은 테스트 텍스트입니다.\nHello! This is a test text."
draw.text((50, 50), text, fill='black')

# 저장
image.save('image3.jpg', 'JPEG')
```

#### 옵션 B: 기존 이미지 파일 사용
- JPG, PNG, BMP 형식의 이미지 파일을 `image3.jpg`로 이름 변경
- 프로젝트 폴더에 저장

### 4. 실행 테스트

```bash
python app.py
```

## 예상 결과

설치가 완료되면 다음과 같은 출력을 볼 수 있습니다:

```
Tesseract 경로 설정됨: C:\Program Files\Tesseract-OCR\tesseract.exe
=== Tesseract 결과 ===
처리시간: 1.23초
추출텍스트:
안녕하세요! 이것은 테스트 텍스트입니다.
Hello! This is a test text.
```

## 문제 해결

### "Tesseract 경로를 찾을 수 없습니다" 오류
- Tesseract가 올바르게 설치되었는지 확인
- 설치 경로가 `C:\Program Files\Tesseract-OCR\`인지 확인

### 언어팩 오류
- 한국어 언어팩이 설치되었는지 확인
- `tesseract --list-langs` 명령어로 설치된 언어 확인

### 이미지 파일 오류
- `image3.jpg` 파일이 프로젝트 폴더에 있는지 확인
- 이미지 파일이 손상되지 않았는지 확인 