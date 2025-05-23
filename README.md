# 🤝 AI 협상 시뮬레이터

복합조건을 고려한 실시간 B2B 협상 시뮬레이션 시스템

## 📋 프로젝트 개요

이 시스템은 AI 기반의 협상 시뮬레이터로, 판매자와 구매자 간의 복잡한 협상 과정을 시뮬레이션합니다. 단순한 가격 협상을 넘어서 품질, 납기, 결제조건, 보증 등 다양한 요소를 종합적으로 고려합니다.

### 🎯 주요 기능

- **🧠 지능형 협상 에이전트**: 각기 다른 전략을 가진 AI 에이전트
- **📊 복합조건 분석**: 가격, 수량, 납기, 품질, 결제조건 등 다차원 협상
- **📈 실시간 시각화**: 협상 진행 과정과 성과 지표를 그래프로 표시
- **🎨 직관적 UI**: Streamlit 기반의 사용자 친화적 인터페이스
- **⚡ 고성능 API**: FastAPI 기반의 빠른 백엔드 서버

### 💡 협상 고려 요소

**가격 관련**

- 명목가격 vs 실질가격 (결제조건, 품질 등급 반영)
- 대량 구매 할인
- 총 거래 가치 계산

**품질 및 리스크**

- 품질 등급: A급(+15%), B급(+8%), 표준, C급(-5%)
- 보증 기간: 12개월 기준, 매월 +1.5% 할증
- 지연 페널티: 납기 지연 시 손해 배상률

**결제 조건**

- 현금결제: 5% 할인
- 후불결제: 30일(표준), 60일(+2%), 90일(+5%)
- 분할결제: 3% 할증

## 🏗️ 시스템 아키텍처

```
AI_negotiation/
├── api/                    # FastAPI 백엔드
│   ├── main.py            # API 서버 메인
│   └── logic.py           # 협상 로직 엔진
├── app/                    # Streamlit 프론트엔드
│   └── streamlit_ui.py    # 웹 인터페이스
├── requirements.txt        # 패키지 의존성
├── run_server.py          # 실행 스크립트
└── README.md              # 프로젝트 문서
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd AI_negotiation

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 시스템 실행

**방법 1: 통합 실행 스크립트 사용 (권장)**

```bash
python run_server.py
```

**방법 2: 개별 실행**

```bash
# 터미널 1: API 서버 실행
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 터미널 2: Streamlit 앱 실행
streamlit run app/streamlit_ui.py --server.port 8501
```

### 3. 시스템 접속

- **웹 인터페이스**: http://localhost:8501
- **API 문서**: http://localhost:8000/docs
- **API 상태**: http://localhost:8000/health

## 📊 사용 가이드

### 기본 협상 설정

1. **판매자 정보 입력**

   - 원가, 목표 단가, 최소 수량
   - 납기 가능 범위, 시장 지위
   - 협상 전략 선택

2. **구매자 정보 입력**

   - 목표 단가, 예산 한도, 희망 수량
   - 희망 납기일, 구매 긴급도
   - 협상 전략 선택

3. **협상 실행**
   - "협상 시작" 버튼 클릭
   - 실시간 협상 과정 관찰
   - 결과 분석 및 차트 확인

### 협상 전략

- **공격적 (Aggressive)**: 빠른 양보, 적극적 거래 추진
- **보수적 (Conservative)**: 신중한 양보, 안정적 조건 추구
- **균형적 (Balanced)**: 분석적 접근, 합리적 타협점 모색

## 📈 성과 지표

### 주요 KPI

- **Win-Win 점수**: 양측 만족도의 조화평균
- **판매자/구매자 만족도**: 각각의 목표 달성률
- **위험 점수**: 납기, 품질, 페널티 종합 평가
- **가격 경쟁력**: 원가 대비 최종 가격의 합리성
- **협상 효율성**: 라운드 수, 시간 대비 성과

### 시각화 차트

- **가격 변화 추이**: 명목가격 vs 실질가격
- **성과 분석**: 만족도, 위험도, 신뢰도
- **협상 효율성**: 레이더 차트, 수렴 패턴

## 🛠️ 기술 스택

### 백엔드

- **FastAPI**: 고성능 비동기 웹 프레임워크
- **Pydantic**: 데이터 검증 및 직렬화
- **Uvicorn**: ASGI 서버

### 프론트엔드

- **Streamlit**: 데이터 앱 구축 프레임워크
- **Matplotlib**: 데이터 시각화
- **Pandas/Numpy**: 데이터 처리

### 통신

- **HTTP REST API**: 프론트엔드-백엔드 통신
- **JSON**: 데이터 교환 형식

## 🔧 API 엔드포인트

### POST /simulate

협상 시뮬레이션 실행

**Request Body:**

```json
{
  "cost": 800.0,
  "seller_target": 1200.0,
  "min_qty": 800,
  "deliv_range": [3, 7],
  "buyer_target": 1000.0,
  "buyer_qty": 1000,
  "buyer_deliv": 5,
  "s_strategy": "aggressive",
  "b_strategy": "conservative",
  "profit_margin": 20.0,
  "budget_limit": 1500.0,
  "market_position": "neutral",
  "urgency": "medium"
}
```

**Response:**

```json
{
  "success": true,
  "log": ["협상 진행 로그"],
  "result": {
    "price": 1150.0,
    "qty": 950,
    "delivery": 6,
    "effective_price": 1087.5,
    "total_value": 1033125.0
  },
  "metrics": {
    "win_win_score": 85.2,
    "seller_satisfaction": 88.1,
    "buyer_satisfaction": 82.3
  }
}
```

## 🐛 문제 해결

### 일반적인 오류

**1. 서버 연결 실패**

```
❌ API 서버에 연결할 수 없습니다
```

- 해결: `python run_server.py`로 서버 재시작

**2. 포트 충돌**

```
⚠️ 포트 8000이 이미 사용 중입니다
```

- 해결: 기존 프로세스 종료 후 재시작

**3. 패키지 누락**

```
❌ 다음 패키지들이 설치되지 않았습니다
```

- 해결: `pip install -r requirements.txt`

### 로그 확인

- **API 서버 로그**: 터미널에서 FastAPI 서버 출력 확인
- **Streamlit 로그**: 브라우저 개발자 도구 콘솔 확인
- **협상 로그**: 웹 인터페이스의 "상세 협상 로그 보기" 섹션

## 🤝 기여 방법

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 라이센스

이 프로젝트는 MIT 라이센스 하에 있습니다. 자세한 내용은 `LICENSE` 파일을 참고하세요.

## 📞 지원

문제가 발생하거나 기능 제안이 있으시면 GitHub Issues를 통해 연락주세요.

---

**Made with ❤️ by AI Negotiation Team**
