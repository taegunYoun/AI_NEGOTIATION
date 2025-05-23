from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import Tuple, List, Optional, Dict, Any
import logging
import traceback

# 상대 import를 절대 import로 변경
try:
    from api.logic import NegotiationSimulator, NegotiationMetrics
except ImportError:
    # 현재 디렉토리에서 직접 import 시도
    try:
        from logic import NegotiationSimulator, NegotiationMetrics
    except ImportError:
        raise ImportError("logic 모듈을 찾을 수 없습니다. 파일 경로를 확인해주세요.")

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Negotiation Simulator",
    description="복합조건 협상 시뮬레이션 API",
    version="1.0.0"
)

# CORS 허용 (Streamlit에서 요청 가능하도록)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 배포 시에는 도메인 제한 추천
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 입력 데이터 구조
class NegotiationInput(BaseModel):
    cost: float
    seller_target: float
    min_qty: int
    deliv_range: Tuple[int, int]
    buyer_target: float
    buyer_qty: int
    buyer_deliv: int
    s_strategy: str
    b_strategy: str
    profit_margin: float
    budget_limit: float
    market_position: str
    urgency: str
    
    # 입력값 검증
    @validator('cost', 'seller_target', 'buyer_target', 'profit_margin', 'budget_limit')
    def validate_positive_numbers(cls, v):
        if v <= 0:
            raise ValueError('양수여야 합니다')
        return v
    
    @validator('min_qty', 'buyer_qty', 'buyer_deliv')
    def validate_positive_integers(cls, v):
        if v <= 0:
            raise ValueError('양의 정수여야 합니다')
        return v
    
    @validator('deliv_range')
    def validate_delivery_range(cls, v):
        if len(v) != 2 or v[0] > v[1]:
            raise ValueError('배송 범위가 올바르지 않습니다 (시작일 <= 종료일)')
        return v
    
    @validator('s_strategy', 'b_strategy')
    def validate_strategy(cls, v):
        valid_strategies = ['aggressive', 'conservative', 'balanced']
        if v not in valid_strategies:
            raise ValueError(f'전략은 {valid_strategies} 중 하나여야 합니다')
        return v
    
    @validator('market_position')
    def validate_market_position(cls, v):
        valid_positions = ['strong', 'weak', 'neutral']
        if v not in valid_positions:
            raise ValueError(f'시장 위치는 {valid_positions} 중 하나여야 합니다')
        return v
    
    @validator('urgency')
    def validate_urgency(cls, v):
        valid_urgency = ['high', 'medium', 'low']
        if v not in valid_urgency:
            raise ValueError(f'긴급도는 {valid_urgency} 중 하나여야 합니다')
        return v

@app.get("/")
def read_root():
    """API 상태 확인"""
    return {"message": "AI Negotiation Simulator API is running"}

@app.get("/health")
def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/simulate")
def simulate(input_data: NegotiationInput):
    """협상 시뮬레이션 실행"""
    try:
        logger.info(f"협상 시뮬레이션 시작: {input_data.dict()}")
        
        # 시뮬레이션 실행
        result = NegotiationSimulator.simulate_negotiation(
            cost=input_data.cost,
            seller_target=input_data.seller_target,
            min_qty=input_data.min_qty,
            deliv_range=input_data.deliv_range,
            buyer_target=input_data.buyer_target,
            buyer_qty=input_data.buyer_qty,
            buyer_deliv=input_data.buyer_deliv,
            s_strategy=input_data.s_strategy,
            b_strategy=input_data.b_strategy,
            profit_margin=input_data.profit_margin,
            budget_limit=input_data.budget_limit,
            market_position=input_data.market_position,
            urgency=input_data.urgency
        )
        
        # 결과 언패킹 (반환값 개수에 따라 조정)
        if len(result) == 6:
            log, negotiation_result, rounds, prices, effective_prices, metrics = result
        else:
            # 예상과 다른 반환값 개수인 경우 처리
            logger.warning(f"예상과 다른 반환값 개수: {len(result)}")
            log, negotiation_result, rounds, prices, effective_prices, metrics = result[:6]
        
        # metrics 객체를 딕셔너리로 변환
        metrics_dict = {}
        if hasattr(metrics, '__dict__'):
            metrics_dict = metrics.__dict__
        elif isinstance(metrics, dict):
            metrics_dict = metrics
        
        response = {
            "success": True,
            "log": log if log else [],
            "result": negotiation_result if negotiation_result else {},
            "rounds": rounds if rounds else 0,
            "prices": prices if prices else [],
            "effective_prices": effective_prices if effective_prices else [],
            "metrics": metrics_dict,
        }
        
        logger.info("협상 시뮬레이션 완료")
        return response
        
    except ValueError as ve:
        logger.error(f"입력값 오류: {str(ve)}")
        raise HTTPException(status_code=400, detail=f"입력값 오류: {str(ve)}")
    
    except Exception as e:
        logger.error(f"시뮬레이션 실행 중 오류: {str(e)}")
        logger.error(f"상세 오류: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"시뮬레이션 실행 중 오류가 발생했습니다: {str(e)}"
        )

# 개발 환경에서 직접 실행할 때
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )