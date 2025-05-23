from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
import random
import logging

logger = logging.getLogger(__name__)

# --- 공통 상수 정의 ---
class Config:
    MAX_ROUNDS = 15
    MIN_PRICE = 1
    MAX_PRICE = 100000
    MIN_QUANTITY = 1
    MAX_QUANTITY = 100000
    MIN_DELIVERY_DAYS = 1
    MAX_DELIVERY_DAYS = 365
    # 영어 전략명으로 변경 (main.py와 일치)
    ALLOWED_STRATEGIES = ["aggressive", "conservative", "balanced"]
    PAYMENT_METHODS = ["현금", "30일 후불", "60일 후불", "90일 후불", "분할결제"]
    QUALITY_GRADES = ["A급", "B급", "C급", "표준"]
    MARKET_POSITIONS = ["strong", "weak", "neutral"]
    URGENCY_LEVELS = ["high", "medium", "low"]

# --- Offer 클래스 ---
@dataclass
class Offer:
    price: float
    qty: int
    delivery: int
    payment_method: str = "현금"
    quality_grade: str = "표준"
    warranty_months: int = 12
    penalty_rate: float = 0.0
    discount_rate: float = 0.0

    def validate(self) -> bool:
        """오퍼 유효성 검증"""
        try:
            return (
                Config.MIN_PRICE <= self.price <= Config.MAX_PRICE and
                Config.MIN_QUANTITY <= self.qty <= Config.MAX_QUANTITY and
                Config.MIN_DELIVERY_DAYS <= self.delivery <= Config.MAX_DELIVERY_DAYS and
                self.payment_method in Config.PAYMENT_METHODS and
                self.quality_grade in Config.QUALITY_GRADES and
                0 <= self.warranty_months <= 60 and
                0 <= self.penalty_rate <= 10 and
                0 <= self.discount_rate <= 20
            )
        except (TypeError, ValueError):
            return False

    def calculate_effective_price(self) -> float:
        """실효 가격 계산"""
        payment_multiplier = {
            "현금": 0.95,
            "30일 후불": 1.0,
            "60일 후불": 1.02,
            "90일 후불": 1.05,
            "분할결제": 1.03
        }
        quality_multiplier = {
            "A급": 1.15,
            "B급": 1.08,
            "C급": 0.95,
            "표준": 1.0
        }
        
        warranty_multiplier = 1 + (self.warranty_months - 12) * 0.015
        volume_discount = 1 - (self.discount_rate / 100)
        
        effective_price = (
            self.price * 
            payment_multiplier.get(self.payment_method, 1.0) * 
            quality_multiplier.get(self.quality_grade, 1.0) * 
            warranty_multiplier * 
            volume_discount
        )
        
        return max(0, effective_price)

    def calculate_total_value(self) -> float:
        """총 가치 계산"""
        return self.calculate_effective_price() * self.qty

# --- 협상 성과 지표 ---
@dataclass
class NegotiationMetrics:
    total_value: float = 0.0
    seller_satisfaction: float = 0.0
    buyer_satisfaction: float = 0.0
    risk_score: float = 0.0
    delivery_reliability: float = 0.0
    price_competitiveness: float = 0.0
    win_win_score: float = 0.0
    rounds_completed: int = 0
    negotiation_efficiency: float = 0.0

# --- 입력 검증 도우미 ---
class InputValidator:
    @staticmethod
    def validate_numeric_input(value: Any, min_val: float, max_val: float, name: str) -> float:
        try:
            num_value = float(value)
            if not (min_val <= num_value <= max_val):
                raise ValueError(f"{name}은(는) {min_val}~{max_val} 범위여야 합니다.")
            return num_value
        except (TypeError, ValueError) as e:
            raise ValueError(f"{name} 값이 올바르지 않습니다: {str(e)}")

    @staticmethod
    def validate_strategy(strategy: str) -> str:
        if strategy not in Config.ALLOWED_STRATEGIES:
            raise ValueError(f"허용되지 않는 전략입니다: {strategy}. 허용된 전략: {Config.ALLOWED_STRATEGIES}")
        return strategy

    @staticmethod
    def validate_delivery_range(start: int, end: int) -> Tuple[int, int]:
        if start > end:
            raise ValueError("납기 시작일이 종료일보다 클 수 없습니다.")
        if start < Config.MIN_DELIVERY_DAYS or end > Config.MAX_DELIVERY_DAYS:
            raise ValueError(f"납기는 {Config.MIN_DELIVERY_DAYS}~{Config.MAX_DELIVERY_DAYS}일 범위여야 합니다.")
        return (start, end)

# --- Seller 에이전트 ---
class SecureSellerAgent:
    def __init__(self, cost, target_price, min_qty, delivery_range, strategy, profit_margin, market_position):
        # 입력값 검증
        self.cost = InputValidator.validate_numeric_input(cost, Config.MIN_PRICE, Config.MAX_PRICE, "원가")
        self.target_price = InputValidator.validate_numeric_input(target_price, cost, Config.MAX_PRICE, "목표가격")
        self.min_qty = int(InputValidator.validate_numeric_input(min_qty, Config.MIN_QUANTITY, Config.MAX_QUANTITY, "최소수량"))
        self.delivery_range = InputValidator.validate_delivery_range(delivery_range[0], delivery_range[1])
        self.strategy = InputValidator.validate_strategy(strategy)
        self.profit_margin = InputValidator.validate_numeric_input(profit_margin, 0, 100, "이익률")
        
        if market_position not in Config.MARKET_POSITIONS:
            raise ValueError(f"시장위치는 {Config.MARKET_POSITIONS} 중 하나여야 합니다.")
        self.market_position = market_position
        
        # 초기 오퍼 설정
        self.offer_price = target_price
        self.offer_qty = min_qty
        self.offer_delivery = delivery_range[1]  # 더 여유있는 납기로 시작
        self.preferred_payment = "30일 후불"
        self.min_quality = "표준"
        self.max_warranty = 24
        self.rounds_participated = 0
        self.concession_history = []

    def make_offer(self) -> Offer:
        """현재 조건으로 오퍼 생성"""
        # 전략에 따른 조정
        price_adjustment = self._get_price_adjustment()
        adjusted_price = max(self.cost * 1.05, self.offer_price * price_adjustment)
        
        offer = Offer(
            price=adjusted_price,
            qty=self.offer_qty,
            delivery=self.offer_delivery,
            payment_method=self.preferred_payment,
            quality_grade=self.min_quality,
            warranty_months=self.max_warranty,
            penalty_rate=1.0,
            discount_rate=self._calculate_discount()
        )
        
        # 유효성 검증
        if not offer.validate():
            logger.warning("판매자 오퍼 유효성 검증 실패, 기본값으로 조정")
            offer = self._create_safe_offer()
        
        return offer

    def _get_price_adjustment(self) -> float:
        """전략에 따른 가격 조정 계수"""
        base_adjustment = 1.0
        
        if self.strategy == "aggressive":
            base_adjustment = 1.0 - (self.rounds_participated * 0.02)  # 라운드마다 2% 감소
        elif self.strategy == "conservative":
            base_adjustment = 1.0 - (self.rounds_participated * 0.005)  # 라운드마다 0.5% 감소
        else:  # balanced
            base_adjustment = 1.0 - (self.rounds_participated * 0.01)  # 라운드마다 1% 감소
        
        # 시장 위치에 따른 조정
        if self.market_position == "strong":
            base_adjustment *= 1.02
        elif self.market_position == "weak":
            base_adjustment *= 0.98
        
        return max(0.8, base_adjustment)  # 최소 20% 할인까지

    def _calculate_discount(self) -> float:
        """할인율 계산"""
        if self.rounds_participated > 5:
            return min(5.0, self.rounds_participated * 0.5)
        return 0.0

    def _create_safe_offer(self) -> Offer:
        """안전한 기본 오퍼 생성"""
        return Offer(
            price=max(self.cost * 1.1, self.target_price * 0.9),
            qty=self.min_qty,
            delivery=self.delivery_range[1],
            payment_method="30일 후불",
            quality_grade="표준",
            warranty_months=12,
            penalty_rate=0.0,
            discount_rate=0.0
        )

    def respond(self, buyer_offer: Offer) -> str:
        """구매자 오퍼에 대한 응답"""
        self.rounds_participated += 1
        
        if not buyer_offer or not buyer_offer.validate():
            return "counter"
        
        effective_price = buyer_offer.calculate_effective_price()
        min_acceptable = self.cost * (1 + self.profit_margin / 100)
        
        # 수락 조건 확인
        if (effective_price >= min_acceptable and 
            buyer_offer.qty >= self.min_qty and
            self.delivery_range[0] <= buyer_offer.delivery <= self.delivery_range[1]):
            return "accept"
        
        # 너무 많은 라운드가 진행되면 조건을 완화
        if self.rounds_participated >= Config.MAX_ROUNDS - 2:
            if effective_price >= self.cost * 1.02:  # 최소 2% 마진
                return "accept"
        
        return "counter"

# --- Buyer 에이전트 ---
class SecureBuyerAgent:
    def __init__(self, target_price, target_qty, desired_delivery, strategy, budget_limit, urgency):
        # 입력값 검증
        self.target_price = InputValidator.validate_numeric_input(target_price, Config.MIN_PRICE, Config.MAX_PRICE, "목표가격")
        self.target_qty = int(InputValidator.validate_numeric_input(target_qty, Config.MIN_QUANTITY, Config.MAX_QUANTITY, "목표수량"))
        self.desired_delivery = int(InputValidator.validate_numeric_input(desired_delivery, Config.MIN_DELIVERY_DAYS, Config.MAX_DELIVERY_DAYS, "희망납기"))
        self.strategy = InputValidator.validate_strategy(strategy)
        self.budget_limit = InputValidator.validate_numeric_input(budget_limit, target_price, Config.MAX_PRICE, "예산한도")
        
        if urgency not in Config.URGENCY_LEVELS:
            raise ValueError(f"긴급도는 {Config.URGENCY_LEVELS} 중 하나여야 합니다.")
        self.urgency = urgency
        
        # 초기 오퍼 설정
        self.offer_price = target_price
        self.offer_qty = target_qty
        self.offer_delivery = desired_delivery
        self.preferred_payment = "현금"
        self.min_quality = "표준"
        self.required_warranty = 12
        self.rounds_participated = 0
        self.concession_history = []

    def make_offer(self) -> Offer:
        """현재 조건으로 오퍼 생성"""
        # 전략에 따른 조정
        price_adjustment = self._get_price_adjustment()
        adjusted_price = min(self.budget_limit, self.offer_price * price_adjustment)
        
        offer = Offer(
            price=adjusted_price,
            qty=self.offer_qty,
            delivery=self.offer_delivery,
            payment_method=self.preferred_payment,
            quality_grade=self.min_quality,
            warranty_months=self.required_warranty,
            penalty_rate=1.0,
            discount_rate=0.0
        )
        
        # 유효성 검증
        if not offer.validate():
            logger.warning("구매자 오퍼 유효성 검증 실패, 기본값으로 조정")
            offer = self._create_safe_offer()
        
        return offer

    def _get_price_adjustment(self) -> float:
        """전략에 따른 가격 조정 계수"""
        base_adjustment = 1.0
        
        if self.strategy == "aggressive":
            base_adjustment = 1.0 + (self.rounds_participated * 0.03)  # 라운드마다 3% 증가
        elif self.strategy == "conservative":
            base_adjustment = 1.0 + (self.rounds_participated * 0.01)  # 라운드마다 1% 증가
        else:  # balanced
            base_adjustment = 1.0 + (self.rounds_participated * 0.02)  # 라운드마다 2% 증가
        
        # 긴급도에 따른 조정
        if self.urgency == "high":
            base_adjustment *= 1.05
        elif self.urgency == "low":
            base_adjustment *= 0.98
        
        return min(1.5, base_adjustment)  # 최대 50% 증가까지

    def _create_safe_offer(self) -> Offer:
        """안전한 기본 오퍼 생성"""
        return Offer(
            price=min(self.budget_limit * 0.8, self.target_price * 1.1),
            qty=self.target_qty,
            delivery=self.desired_delivery,
            payment_method="현금",
            quality_grade="표준",
            warranty_months=12,
            penalty_rate=0.0,
            discount_rate=0.0
        )

    def respond(self, seller_offer: Offer) -> str:
        """판매자 오퍼에 대한 응답"""
        self.rounds_participated += 1
        
        if not seller_offer or not seller_offer.validate():
            return "counter"
        
        effective_price = seller_offer.calculate_effective_price()
        total_cost = effective_price * seller_offer.qty
        
        # 수락 조건 확인
        if (total_cost <= self.budget_limit and 
            seller_offer.qty >= self.target_qty * 0.8 and  # 목표 수량의 80% 이상
            seller_offer.delivery <= self.desired_delivery * 1.2):  # 희망 납기의 120% 이하
            return "accept"
        
        # 긴급하거나 너무 많은 라운드가 진행되면 조건을 완화
        if (self.urgency == "high" and self.rounds_participated >= 5) or self.rounds_participated >= Config.MAX_ROUNDS - 2:
            if total_cost <= self.budget_limit * 1.1:  # 예산의 110%까지 허용
                return "accept"
        
        return "counter"

# --- 협상 분석기 ---
class NegotiationAnalyzer:
    @staticmethod
    def calculate_metrics(seller_agent, buyer_agent, final_offer, rounds) -> NegotiationMetrics:
        """협상 성과 지표 계산"""
        if not final_offer:
            return NegotiationMetrics(rounds_completed=rounds)
        
        try:
            # 기본 지표 계산
            total_value = final_offer["price"] * final_offer["qty"]
            
            # 만족도 계산
            seller_satisfaction = min(100, max(0, 
                (final_offer["price"] / seller_agent.target_price) * 100))
            buyer_satisfaction = min(100, max(0, 
                ((buyer_agent.budget_limit - final_offer["price"]) / buyer_agent.budget_limit) * 100))
            
            # Win-Win 점수 계산
            if seller_satisfaction > 0 and buyer_satisfaction > 0:
                win_win_score = 2 * (seller_satisfaction * buyer_satisfaction) / (seller_satisfaction + buyer_satisfaction)
            else:
                win_win_score = 0
            
            # 리스크 점수 계산
            delivery_risk = max(0, (final_offer.get("delivery", 7) - 3) * 10)
            quality_risk = {"A급": 5, "B급": 15, "C급": 30, "표준": 20}.get(
                final_offer.get("quality_grade", "표준"), 20)
            penalty_risk = final_offer.get("penalty_rate", 1) * 10
            risk_score = min(100, delivery_risk + quality_risk + penalty_risk)
            
            # 기타 지표
            delivery_reliability = max(0, min(100, (21 - final_offer.get("delivery", 7)) * 5))
            price_competitiveness = min(100, max(0, 
                ((seller_agent.cost * 2 - final_offer["price"]) / seller_agent.cost) * 100))
            
            # 협상 효율성
            negotiation_efficiency = max(0, min(100, (Config.MAX_ROUNDS - rounds) / Config.MAX_ROUNDS * 100))
            
            return NegotiationMetrics(
                total_value=total_value,
                seller_satisfaction=seller_satisfaction,
                buyer_satisfaction=buyer_satisfaction,
                risk_score=risk_score,
                delivery_reliability=delivery_reliability,
                price_competitiveness=price_competitiveness,
                win_win_score=win_win_score,
                rounds_completed=rounds,
                negotiation_efficiency=negotiation_efficiency
            )
        
        except Exception as e:
            logger.error(f"지표 계산 중 오류: {str(e)}")
            return NegotiationMetrics(rounds_completed=rounds)

# --- 시뮬레이터 ---
class NegotiationSimulator:
    @staticmethod
    def simulate_negotiation(
        cost: float,
        seller_target: float,
        min_qty: int,
        deliv_range: Tuple[int, int],
        buyer_target: float,
        buyer_qty: int,
        buyer_deliv: int,
        s_strategy: str,
        b_strategy: str,
        profit_margin: float,
        budget_limit: float,
        market_position: str,
        urgency: str
    ) -> Tuple[List[str], Optional[Dict], List[int], List[Tuple[float, float]], List[Tuple[float, float]], NegotiationMetrics]:
        """협상 시뮬레이션 실행"""
        
        log = []
        prices = []
        effective_prices = []
        
        try:
            # 에이전트 생성
            seller = SecureSellerAgent(
                cost, seller_target, min_qty, deliv_range, 
                s_strategy, profit_margin, market_position
            )
            buyer = SecureBuyerAgent(
                buyer_target, buyer_qty, buyer_deliv, 
                b_strategy, budget_limit, urgency
            )
            
            log.append("협상 시작")
            
            # 협상 진행
            for round_num in range(1, Config.MAX_ROUNDS + 1):
                log.append(f"--- 라운드 {round_num} ---")
                
                # 판매자 오퍼
                seller_offer = seller.make_offer()
                log.append(f"판매자 오퍼: 가격={seller_offer.price:.2f}, 수량={seller_offer.qty}, 납기={seller_offer.delivery}")
                prices.append((seller_offer.price, buyer.offer_price))
                effective_prices.append((seller_offer.calculate_effective_price(), buyer.offer_price))
                
                # 구매자 응답
                buyer_response = buyer.respond(seller_offer)
                if buyer_response == "accept":
                    log.append("구매자가 판매자 오퍼를 수락했습니다!")
                    final_offer = {
                        "price": seller_offer.price,
                        "qty": seller_offer.qty,
                        "delivery": seller_offer.delivery,
                        "payment_method": seller_offer.payment_method,
                        "quality_grade": seller_offer.quality_grade,
                        "warranty_months": seller_offer.warranty_months,
                        "penalty_rate": seller_offer.penalty_rate,
                        "discount_rate": seller_offer.discount_rate,
                        "effective_price": seller_offer.calculate_effective_price(),
                        "total_value": seller_offer.calculate_total_value()
                    }
                    metrics = NegotiationAnalyzer.calculate_metrics(seller, buyer, final_offer, round_num)
                    return log, final_offer, [round_num], prices, effective_prices, metrics
                
                # 구매자 오퍼
                buyer_offer = buyer.make_offer()
                log.append(f"구매자 오퍼: 가격={buyer_offer.price:.2f}, 수량={buyer_offer.qty}, 납기={buyer_offer.delivery}")
                
                # 판매자 응답
                seller_response = seller.respond(buyer_offer)
                if seller_response == "accept":
                    log.append("판매자가 구매자 오퍼를 수락했습니다!")
                    final_offer = {
                        "price": buyer_offer.price,
                        "qty": buyer_offer.qty,
                        "delivery": buyer_offer.delivery,
                        "payment_method": buyer_offer.payment_method,
                        "quality_grade": buyer_offer.quality_grade,
                        "warranty_months": buyer_offer.warranty_months,
                        "penalty_rate": buyer_offer.penalty_rate,
                        "discount_rate": buyer_offer.discount_rate,
                        "effective_price": buyer_offer.calculate_effective_price(),
                        "total_value": buyer_offer.calculate_total_value()
                    }
                    metrics = NegotiationAnalyzer.calculate_metrics(seller, buyer, final_offer, round_num)
                    return log, final_offer, [round_num], prices, effective_prices, metrics
                
                log.append("양측 모두 거부, 다음 라운드로 진행")
            
            # 최대 라운드 도달
            log.append("최대 라운드에 도달했습니다. 협상이 결렬되었습니다.")
            metrics = NegotiationMetrics(rounds_completed=Config.MAX_ROUNDS)
            return log, None, [], prices, effective_prices, metrics
            
        except Exception as e:
            logger.error(f"시뮬레이션 실행 중 오류: {str(e)}")
            log.append(f"시뮬레이션 오류: {str(e)}")
            return log, None, [], prices, effective_prices, NegotiationMetrics()