# 고도화된 복합조건 협상 시뮬레이터
import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import logging
from typing import Dict, Tuple, List, Optional, Any
from dataclasses import dataclass
import random
from datetime import datetime, timedelta

# 한글 폰트 설정
plt.rcParams['font.family'] = ['DejaVu Sans', 'Malgun Gothic', 'Apple Gothic']
plt.rcParams['axes.unicode_minus'] = False

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 상수 정의
class Config:
    MAX_ROUNDS = 15
    MIN_PRICE = 1
    MAX_PRICE = 100000
    MIN_QUANTITY = 1
    MAX_QUANTITY = 100000
    MIN_DELIVERY_DAYS = 1
    MAX_DELIVERY_DAYS = 365
    ALLOWED_STRATEGIES = ["공격적", "보수적", "무작위", "분석적"]
    PAYMENT_METHODS = ["현금", "30일 후불", "60일 후불", "90일 후불", "분할결제"]
    QUALITY_GRADES = ["A급", "B급", "C급", "표준"]

@dataclass
class Offer:
    """협상 제안을 나타내는 데이터 클래스"""
    price: float
    qty: int
    delivery: int
    payment_method: str = "현금"
    quality_grade: str = "표준"
    warranty_months: int = 12
    penalty_rate: float = 0.0  # 지연 시 페널티 비율 (%)
    discount_rate: float = 0.0  # 대량 구매 할인율 (%)
    
    def validate(self) -> bool:
        """제안 데이터 유효성 검증"""
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
    
    def calculate_effective_price(self) -> float:
        """실질 가격 계산 (결제조건, 품질, 보증, 할인 등 고려)"""
        base_price = self.price
        
        # 결제조건에 따른 할인/할증
        payment_multiplier = {
            "현금": 0.95,  # 5% 할인
            "30일 후불": 1.0,
            "60일 후불": 1.02,  # 2% 할증
            "90일 후불": 1.05,  # 5% 할증
            "분할결제": 1.03    # 3% 할증
        }
        
        # 품질등급에 따른 할증
        quality_multiplier = {
            "A급": 1.15,   # 15% 할증
            "B급": 1.08,   # 8% 할증
            "C급": 0.95,   # 5% 할인
            "표준": 1.0
        }
        
        # 보증기간에 따른 할증 (12개월 기준)
        warranty_multiplier = 1 + (self.warranty_months - 12) * 0.015
        
        # 대량 구매 할인 적용
        volume_discount = 1 - (self.discount_rate / 100)
        
        return base_price * payment_multiplier[self.payment_method] * quality_multiplier[self.quality_grade] * warranty_multiplier * volume_discount

    def calculate_total_value(self) -> float:
        """총 거래 금액 계산"""
        return self.calculate_effective_price() * self.qty

@dataclass
class NegotiationMetrics:
    """협상 성과 지표"""
    total_value: float = 0.0
    seller_satisfaction: float = 0.0
    buyer_satisfaction: float = 0.0
    risk_score: float = 0.0
    delivery_reliability: float = 0.0
    price_competitiveness: float = 0.0
    win_win_score: float = 0.0  # 상호 이익 점수

class InputValidator:
    """입력값 검증 클래스"""
    
    @staticmethod
    def validate_numeric_input(value: Any, min_val: float, max_val: float, name: str) -> float:
        """숫자 입력값 검증"""
        try:
            num_value = float(value)
            if not (min_val <= num_value <= max_val):
                raise ValueError(f"{name}은(는) {min_val}과 {max_val} 사이의 값이어야 합니다.")
            return num_value
        except (ValueError, TypeError) as e:
            logger.error(f"입력값 검증 실패 - {name}: {value}, 오류: {str(e)}")
            raise ValueError(f"올바른 {name}을(를) 입력해주세요.")
    
    @staticmethod
    def validate_strategy(strategy: str) -> str:
        """전략 선택 검증"""
        if strategy not in Config.ALLOWED_STRATEGIES:
            raise ValueError(f"허용되지 않는 전략입니다: {strategy}")
        return strategy
    
    @staticmethod
    def validate_delivery_range(start: int, end: int) -> Tuple[int, int]:
        """납기일 범위 검증"""
        if start > end:
            raise ValueError("납기 시작일이 종료일보다 클 수 없습니다.")
        return (start, end)

class SecureSellerAgent:
    """보안이 강화된 판매자 에이전트"""
    
    def __init__(self, cost: float, target_price: float, min_qty: int, 
                 delivery_range: Tuple[int, int], strategy: str, profit_margin: float = 20.0,
                 market_position: str = "중간"):
        # 입력값 검증
        self.cost = InputValidator.validate_numeric_input(cost, Config.MIN_PRICE, Config.MAX_PRICE, "원가")
        self.target_price = InputValidator.validate_numeric_input(target_price, self.cost, Config.MAX_PRICE, "목표가격")
        self.min_qty = int(InputValidator.validate_numeric_input(min_qty, Config.MIN_QUANTITY, Config.MAX_QUANTITY, "최소수량"))
        self.delivery_range = InputValidator.validate_delivery_range(*delivery_range)
        self.strategy = InputValidator.validate_strategy(strategy)
        self.profit_margin = max(5.0, min(50.0, profit_margin))
        self.market_position = market_position  # "강세", "중간", "약세"
        
        # 계산된 값들
        self.min_price = max(self.cost * (1 + self.profit_margin/100), Config.MIN_PRICE)
        self.offer_price = min(self.target_price + 10, Config.MAX_PRICE)
        self.offer_qty = min(self.min_qty + 200, Config.MAX_QUANTITY)
        self.offer_delivery = self.delivery_range[1]
        self.preferred_payment = "30일 후불"
        self.min_quality = "표준"
        self.max_warranty = 24
        
        # 협상 히스토리 및 분석
        self.concession_history = []
        self.rounds_participated = 0
        self.negotiation_power = self._calculate_negotiation_power()
        
        logger.info(f"판매자 에이전트 생성: 원가={self.cost}, 목표가격={self.target_price}, 시장지위={market_position}")

    def _calculate_negotiation_power(self) -> float:
        """협상력 계산 (시장 지위, 원가 경쟁력 등 고려)"""
        position_score = {"강세": 0.8, "중간": 0.5, "약세": 0.3}[self.market_position]
        margin_score = min(1.0, self.profit_margin / 30)  # 이익률이 높을수록 협상력 증가
        return (position_score + margin_score) / 2

    def make_offer(self) -> Offer:
        """안전한 제안 생성"""
        # 전략 및 협상력에 따른 조정
        if self.strategy == "분석적":
            price_adjustment = self._analyze_concession_pattern()
            self.offer_price = max(self.offer_price + price_adjustment, self.min_price)
        
        # 대량 구매 할인율 계산
        volume_discount = min(10.0, max(0, (self.offer_qty - 1000) / 500 * 2))
        
        offer = Offer(
            price=max(self.offer_price, self.min_price),
            qty=max(self.offer_qty, self.min_qty),
            delivery=max(self.offer_delivery, self.delivery_range[0]),
            payment_method=self.preferred_payment,
            quality_grade=self.min_quality,
            warranty_months=min(self.max_warranty, 24),
            penalty_rate=max(1.0, 3.0 - self.negotiation_power * 2),  # 협상력에 따른 페널티 조정
            discount_rate=volume_discount
        )
        
        if not offer.validate():
            logger.error(f"유효하지 않은 제안 생성됨: {offer}")
            raise ValueError("유효하지 않은 제안이 생성되었습니다.")
        
        self.rounds_participated += 1
        return offer

    def respond(self, buyer_offer: Offer) -> str:
        """구매자 제안에 대한 응답"""
        if not buyer_offer.validate():
            logger.warning(f"유효하지 않은 구매자 제안: {buyer_offer}")
            return "reject"
        
        # 실질 가격으로 평가
        effective_price = buyer_offer.calculate_effective_price()
        total_value = buyer_offer.calculate_total_value()
        
        # 수용 조건 평가 (다중 기준)
        price_acceptable = effective_price >= self.min_price
        qty_acceptable = buyer_offer.qty >= self.min_qty
        delivery_acceptable = self.delivery_range[0] <= buyer_offer.delivery <= self.delivery_range[1]
        payment_acceptable = buyer_offer.payment_method in Config.PAYMENT_METHODS
        
        # 총 거래가치가 큰 경우 일부 조건 완화
        high_value_deal = total_value > self.min_price * self.min_qty * 1.5
        
        acceptance_score = sum([price_acceptable, qty_acceptable, delivery_acceptable, payment_acceptable])
        
        if acceptance_score >= 4 or (acceptance_score >= 3 and high_value_deal):
            logger.info(f"판매자가 제안 수락 (실질가격: {effective_price:.0f}원, 총액: {total_value:.0f}원)")
            return "accept"
        else:
            # 양보 전략 실행
            concession = self._concede()
            self.concession_history.append(concession)
            
            self.offer_price = max(self.offer_price - concession, self.min_price)
            self.offer_qty = max(self.offer_qty - 50, self.min_qty)
            self.offer_delivery = max(self.delivery_range[0], self.offer_delivery - 1)
            
            # 고가치 거래 시 결제조건 완화
            if high_value_deal and self.rounds_participated > 3:
                self.preferred_payment = buyer_offer.payment_method
            
            return "counter"

    def _concede(self) -> float:
        """전략별 양보 계산"""
        base_concession = {
            "공격적": 30, 
            "보수적": 15, 
            "무작위": random.randint(15, 35),
            "분석적": 25
        }[self.strategy]
        
        # 협상력에 따른 조정
        power_modifier = (1 - self.negotiation_power) + 0.5
        
        # 라운드가 진행될수록 양보폭 증가 (단, 협상력이 높으면 덜 양보)
        round_multiplier = 1 + (self.rounds_participated * 0.08 * power_modifier)
        
        return min(base_concession * round_multiplier, 100)
    
    def _analyze_concession_pattern(self) -> float:
        """상대방 양보 패턴 분석"""
        if len(self.concession_history) < 2:
            return 0
        
        # 최근 양보 패턴이 증가하면 더 적게 양보
        recent_trend = self.concession_history[-1] - self.concession_history[-2]
        return -recent_trend * 0.3

class SecureBuyerAgent:
    """보안이 강화된 구매자 에이전트"""
    
    def __init__(self, target_price: float, target_qty: int, desired_delivery: int, 
                 strategy: str, budget_limit: float, urgency: str = "보통"):
        # 입력값 검증
        self.target_price = InputValidator.validate_numeric_input(target_price, Config.MIN_PRICE, Config.MAX_PRICE, "목표가격")
        self.target_qty = int(InputValidator.validate_numeric_input(target_qty, Config.MIN_QUANTITY, Config.MAX_QUANTITY, "목표수량"))
        self.desired_delivery = int(InputValidator.validate_numeric_input(desired_delivery, Config.MIN_DELIVERY_DAYS, Config.MAX_DELIVERY_DAYS, "희망납기"))
        self.strategy = InputValidator.validate_strategy(strategy)
        self.budget_limit = max(target_price, budget_limit)
        self.urgency = urgency  # "긴급", "보통", "여유"
        
        # 계산된 값들
        self.max_price = min(self.budget_limit, Config.MAX_PRICE)
        self.offer_price = max(self.target_price - 10, Config.MIN_PRICE)
        self.offer_qty = max(self.target_qty - 200, Config.MIN_QUANTITY)
        self.offer_delivery = self.desired_delivery
        self.preferred_payment = "현금"
        self.min_quality = "표준"
        self.required_warranty = 12
        
        # 협상 히스토리 및 분석
        self.concession_history = []
        self.rounds_participated = 0
        self.negotiation_power = self._calculate_negotiation_power()
        
        logger.info(f"구매자 에이전트 생성: 목표가격={self.target_price}, 예산한도={self.budget_limit}, 긴급도={urgency}")

    def _calculate_negotiation_power(self) -> float:
        """협상력 계산 (예산 여유도, 긴급도 등 고려)"""
        budget_ratio = self.target_price / self.budget_limit
        budget_score = 1 - budget_ratio  # 예산 여유가 클수록 협상력 증가
        
        urgency_score = {"긴급": 0.2, "보통": 0.5, "여유": 0.8}[self.urgency]
        
        return (budget_score + urgency_score) / 2

    def make_offer(self) -> Offer:
        """안전한 제안 생성"""
        # 전략 및 긴급도에 따른 조정
        if self.strategy == "분석적":
            price_adjustment = self._analyze_concession_pattern()
            self.offer_price = min(self.offer_price + price_adjustment, self.max_price)
        
        # 긴급도에 따른 가격 조정
        urgency_multiplier = {"긴급": 1.1, "보통": 1.0, "여유": 0.95}[self.urgency]
        adjusted_price = min(self.offer_price * urgency_multiplier, self.max_price)
        
        offer = Offer(
            price=min(adjusted_price, self.max_price),
            qty=max(self.offer_qty, Config.MIN_QUANTITY),
            delivery=max(self.offer_delivery, Config.MIN_DELIVERY_DAYS),
            payment_method=self.preferred_payment,
            quality_grade=self.min_quality,
            warranty_months=self.required_warranty,
            penalty_rate=max(0.5, 2.0 - self.negotiation_power),  # 협상력에 따른 페널티 조정
            discount_rate=0.0  # 구매자는 할인 요구
        )
        
        if not offer.validate():
            logger.error(f"유효하지 않은 제안 생성됨: {offer}")
            raise ValueError("유효하지 않은 제안이 생성되었습니다.")
        
        self.rounds_participated += 1
        return offer

    def respond(self, seller_offer: Offer) -> str:
        """판매자 제안에 대한 응답"""
        if not seller_offer.validate():
            logger.warning(f"유효하지 않은 판매자 제안: {seller_offer}")
            return "reject"
        
        # 실질 가격으로 평가
        effective_price = seller_offer.calculate_effective_price()
        total_value = seller_offer.calculate_total_value()
        
        # 수용 조건 평가 (다중 기준)
        price_acceptable = effective_price <= self.max_price
        qty_acceptable = seller_offer.qty >= self.target_qty
        delivery_acceptable = seller_offer.delivery <= self.desired_delivery
        quality_acceptable = seller_offer.quality_grade in Config.QUALITY_GRADES
        
        # 예산 대비 가격 경쟁력
        price_competitiveness = (self.max_price - effective_price) / self.max_price
        
        acceptance_score = sum([price_acceptable, qty_acceptable, delivery_acceptable, quality_acceptable])
        
        # 긴급한 경우 조건 완화, 여유로운 경우 까다롭게
        if self.urgency == "긴급":
            threshold = 3
        elif self.urgency == "여유":
            threshold = 4
        else:
            threshold = 3.5
        
        if acceptance_score >= threshold or (price_competitiveness > 0.2 and acceptance_score >= 3):
            logger.info(f"구매자가 제안 수락 (실질가격: {effective_price:.0f}원, 총액: {total_value:.0f}원)")
            return "accept"
        else:
            # 양보 전략 실행
            concession = self._concede()
            self.concession_history.append(concession)
            
            self.offer_price = min(self.offer_price + concession, self.max_price)
            self.offer_qty = min(self.offer_qty + 50, Config.MAX_QUANTITY)
            self.offer_delivery = min(self.offer_delivery + 1, Config.MAX_DELIVERY_DAYS)
            
            # 품질 요구사항 완화 (후반부에)
            if self.rounds_participated > 7:
                self.min_quality = seller_offer.quality_grade
            
            return "counter"

    def _concede(self) -> float:
        """전략별 양보 계산"""
        base_concession = {
            "공격적": 35, 
            "보수적": 20, 
            "무작위": random.randint(20, 40),
            "분석적": 28
        }[self.strategy]
        
        # 예산 한도에 가까워질수록 양보폭 감소
        budget_ratio = self.offer_price / self.max_price
        budget_multiplier = max(0.3, 1 - budget_ratio)
        
        # 긴급도에 따른 조정
        urgency_multiplier = {"긴급": 1.3, "보통": 1.0, "여유": 0.7}[self.urgency]
        
        return min(base_concession * budget_multiplier * urgency_multiplier, self.max_price - self.offer_price)
    
    def _analyze_concession_pattern(self) -> float:
        """상대방 양보 패턴 분석"""
        if len(self.concession_history) < 2:
            return 0
        
        recent_trend = self.concession_history[-1] - self.concession_history[-2]
        return recent_trend * 0.4

class NegotiationAnalyzer:
    """협상 분석 도구"""
    
    @staticmethod
    def calculate_metrics(seller_agent, buyer_agent, final_offer, rounds) -> NegotiationMetrics:
        """협상 성과 분석"""
        if not final_offer:
            return NegotiationMetrics()
        
        # 총 거래금액
        total_value = final_offer["price"] * final_offer["qty"]
        
        # 판매자 만족도 (목표 대비 달성률)
        seller_satisfaction = min(100, max(0, (final_offer["price"] / seller_agent.target_price) * 100))
        
        # 구매자 만족도 (예산 대비 절약률)
        buyer_satisfaction = min(100, max(0, ((buyer_agent.max_price - final_offer["price"]) / buyer_agent.max_price) * 100))
        
        # Win-Win 점수 (양쪽 만족도의 조화평균)
        if seller_satisfaction > 0 and buyer_satisfaction > 0:
            win_win_score = 2 * (seller_satisfaction * buyer_satisfaction) / (seller_satisfaction + buyer_satisfaction)
        else:
            win_win_score = 0
        
        # 위험 점수 (납기, 품질, 페널티 등 종합)
        delivery_risk = max(0, (final_offer.get("delivery", 7) - 3) * 10)
        quality_risk = {"A급": 5, "B급": 15, "C급": 30, "표준": 20}.get(final_offer.get("quality_grade", "표준"), 20)
        penalty_risk = final_offer.get("penalty_rate", 1) * 10
        risk_score = min(100, delivery_risk + quality_risk + penalty_risk)
        
        # 납기 신뢰도
        delivery_reliability = max(0, min(100, (21 - final_offer.get("delivery", 7)) * 5))
        
        # 가격 경쟁력 (원가 대비)
        price_competitiveness = min(100, max(0, ((seller_agent.cost * 2 - final_offer["price"]) / seller_agent.cost) * 100))
        
        return NegotiationMetrics(
            total_value=total_value,
            seller_satisfaction=seller_satisfaction,
            buyer_satisfaction=buyer_satisfaction,
            risk_score=risk_score,
            delivery_reliability=delivery_reliability,
            price_competitiveness=price_competitiveness,
            win_win_score=win_win_score
        )

class NegotiationSimulator:
    """협상 시뮬레이션 클래스"""
    
    @staticmethod
    def simulate_negotiation(cost: float, seller_target: float, min_qty: int, 
                           deliv_range: Tuple[int, int], buyer_target: float, 
                           buyer_qty: int, buyer_deliv: int, s_strategy: str, 
                           b_strategy: str, profit_margin: float, budget_limit: float,
                           market_position: str, urgency: str) -> Tuple[List[str], Optional[Dict], List[int], List[Tuple[float, float]], List[Tuple[float, float]], NegotiationMetrics]:
        """고도화된 협상 시뮬레이션"""
        try:
            seller = SecureSellerAgent(cost, seller_target, min_qty, deliv_range, s_strategy, profit_margin, market_position)
            buyer = SecureBuyerAgent(buyer_target, buyer_qty, buyer_deliv, b_strategy, budget_limit, urgency)
            
            log, prices, effective_prices, rounds = [], [], [], []
            
            for i in range(Config.MAX_ROUNDS):
                try:
                    seller_offer = seller.make_offer()
                    buyer_offer = buyer.make_offer()
                    
                    # 실질 가격 계산
                    seller_effective = seller_offer.calculate_effective_price()
                    buyer_effective = buyer_offer.calculate_effective_price()
                    
                    log.append(f"🔄 Round {i+1}")
                    log.append(f"📊 **판매자 제안 상세:**")
                    log.append(f"  • 💰 가격: {seller_offer.price:,.0f}원 → 실질가격: {seller_effective:,.0f}원")
                    log.append(f"  • 📦 수량: {seller_offer.qty:,}개 | 🚚 납기: {seller_offer.delivery}일")
                    log.append(f"  • 💳 결제: {seller_offer.payment_method} | 🏆 품질: {seller_offer.quality_grade}")
                    log.append(f"  • 🛡️ 보증: {seller_offer.warranty_months}개월 | ⚠️ 페널티: {seller_offer.penalty_rate}%")
                    if seller_offer.discount_rate > 0:
                        log.append(f"  • 🎯 대량할인: {seller_offer.discount_rate}%")
                    log.append(f"  • 💎 총 거래액: {seller_offer.calculate_total_value():,.0f}원")
                    
                    log.append(f"📊 **구매자 제안 상세:**")
                    log.append(f"  • 💰 가격: {buyer_offer.price:,.0f}원 → 실질가격: {buyer_effective:,.0f}원")
                    log.append(f"  • 📦 수량: {buyer_offer.qty:,}개 | 🚚 납기: {buyer_offer.delivery}일")
                    log.append(f"  • 💳 결제: {buyer_offer.payment_method} | 🏆 품질: {buyer_offer.quality_grade}")
                    log.append(f"  • 🛡️ 보증: {buyer_offer.warranty_months}개월 | ⚠️ 페널티: {buyer_offer.penalty_rate}%")
                    log.append(f"  • 💎 총 거래액: {buyer_offer.calculate_total_value():,.0f}원")
                    
                    prices.append((seller_offer.price, buyer_offer.price))
                    effective_prices.append((seller_effective, buyer_effective))
                    rounds.append(i+1)
                    
                    buyer_response = buyer.respond(seller_offer)
                    if buyer_response == "accept":
                        log.append("✅ **구매자가 판매자 제안 수락!**")
                        final_offer = {
                            "price": seller_offer.price, 
                            "qty": seller_offer.qty, 
                            "delivery": seller_offer.delivery,
                            "payment_method": seller_offer.payment_method,
                            "quality_grade": seller_offer.quality_grade,
                            "warranty_months": seller_offer.warranty_months,
                            "penalty_rate": seller_offer.penalty_rate,
                            "discount_rate": seller_offer.discount_rate,
                            "effective_price": seller_effective,
                            "total_value": seller_offer.calculate_total_value()
                        }
                        metrics = NegotiationAnalyzer.calculate_metrics(seller, buyer, final_offer, i+1)
                        return log, final_offer, rounds, prices, effective_prices, metrics
                    
                    seller_response = seller.respond(buyer_offer)
                    if seller_response == "accept":
                        log.append("✅ **판매자가 구매자 제안 수락!**")
                        final_offer = {
                            "price": buyer_offer.price, 
                            "qty": buyer_offer.qty, 
                            "delivery": buyer_offer.delivery,
                            "payment_method": buyer_offer.payment_method,
                            "quality_grade": buyer_offer.quality_grade,
                            "warranty_months": buyer_offer.warranty_months,
                            "penalty_rate": buyer_offer.penalty_rate,
                            "discount_rate": buyer_offer.discount_rate,
                            "effective_price": buyer_effective,
                            "total_value": buyer_offer.calculate_total_value()
                        }
                        metrics = NegotiationAnalyzer.calculate_metrics(seller, buyer, final_offer, i+1)
                        return log, final_offer, rounds, prices, effective_prices, metrics
                    
                    log.append("🔄 협상 계속...")
                    log.append("---")
                
                except Exception as e:
                    logger.error(f"라운드 {i+1}에서 오류 발생: {str(e)}")
                    log.append(f"❌ 라운드 {i+1}에서 오류 발생")
                    break
            
            log.append("❌ **협상 실패** (최대 라운드 초과)")
            return log, None, rounds, prices, effective_prices, NegotiationMetrics()
            
        except Exception as e:
            logger.error(f"협상 시뮬레이션 오류: {str(e)}")
            return [f"❌ 시뮬레이션 오류: {str(e)}"], None, [], [], [], NegotiationMetrics()

# Streamlit UI
def main():
    st.title("🔁 고도화된 복합 조건 AI 협상 시뮬레이터")
    
    # 협상 가이드 표시
    with st.expander("📋 협상 시 고려사항 가이드", expanded=False):
        st.markdown("""
        ### 💡 협상에서 꼭 따져야 할 핵심 항목들
        
        **🎯 가격 관련 (Price Dynamics)**
        - **명목가격 vs 실질가격**: 결제조건, 품질등급, 보증기간, 할인을 모두 반영한 실제 비용
        - **총 거래가치**: 단가 × 수량으로 계산되는 전체 계약 규모
        - **예산 효율성**: 목표 대비 실제 지출의 최적화 정도
        - **가격 경쟁력**: 시장가격 대비 우위 확보 여부
        
        **📊 품질 및 위험관리 (Quality & Risk)**
        - **품질등급별 가격차이**: A급(+15%) > B급(+8%) > 표준 > C급(-5%)
        - **보증기간**: 12개월 기준, 매월 +1.5% 가격 할증
        - **지연 페널티**: 납기 지연 시 적용되는 손해 배상률 (0.5~3%)
        - **위험점수**: 납기, 품질, 페널티를 종합한 리스크 평가
        
        **💰 결제조건 최적화 (Payment Terms)**
        - **현금결제**: 5% 할인 + 즉시 정산
        - **30일 후불**: 표준 조건 (0% 할증)
        - **60일 후불**: 2% 할증 + 현금흐름 개선
        - **90일 후불**: 5% 할증 + 장기 유동성 확보
        - **분할결제**: 3% 할증 + 위험 분산
        
        **📅 납기 및 물류 (Delivery & Logistics)**
        - **납기 신뢰도**: 요청 납기 준수 가능성 평가
        - **배송 리스크**: 지연 시 생산차질 및 기회비용
        - **긴급도별 전략**: 긴급(+10% 프리미엄) vs 여유(-5% 할인)
        
        **🤝 협상 심리학 (Negotiation Psychology)**
        - **협상력 지수**: 시장지위, 예산여유도, 긴급도 종합 평가
        - **양보 패턴**: 상대방 양보폭 분석을 통한 전략 수정
        - **Win-Win 점수**: 양측 만족도의 균형점 달성 여부
        - **만족도 지표**: 판매자/구매자 각각의 목표 달성률
        
        **📈 전략별 특징**
        - **공격적**: 빠른 양보, 적극적 거래 성사 (리스크 높음)
        - **보수적**: 신중한 양보, 안정적 조건 추구 (시간 소요)
        - **분석적**: 패턴 분석 기반 대응 (균형잡힌 결과)
        - **무작위**: 예측 불가능한 패턴 (불확실성 활용)
        """)
    
    # 세션 상태 초기화
    if 'simulation_count' not in st.session_state:
        st.session_state.simulation_count = 0
    
    try:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏪 판매자 정보")
            cost = st.number_input("원가", min_value=1.0, max_value=100000.0, value=800.0, step=1.0)
            seller_target = st.number_input("목표 단가", min_value=cost, max_value=100000.0, value=max(1200.0, cost), step=1.0)
            profit_margin = st.slider("목표 이익률 (%)", min_value=5.0, max_value=50.0, value=20.0, step=1.0)
            min_qty = st.number_input("최소 수량", min_value=1, max_value=100000, value=800, step=1)
            deliv_start = st.number_input("납기 가능 시작일", min_value=1, max_value=365, value=3, step=1)
            deliv_end = st.number_input("납기 가능 종료일", min_value=deliv_start, max_value=365, value=max(7, deliv_start), step=1)
            market_position = st.selectbox("시장 지위", ["강세", "중간", "약세"], index=1)
            s_strategy = st.selectbox("판매자 협상전략", Config.ALLOWED_STRATEGIES, index=0)
        
        with col2:
            st.subheader("🛒 구매자 정보")
            buyer_target = st.number_input("목표 단가", min_value=1.0, max_value=100000.0, value=1000.0, step=1.0)
            budget_limit = st.number_input("예산 한도", min_value=buyer_target, max_value=100000.0, value=max(1500.0, buyer_target), step=1.0)
            buyer_qty = st.number_input("목표 수량", min_value=1, max_value=100000, value=1000, step=1)
            buyer_deliv = st.number_input("희망 납기일", min_value=1, max_value=365, value=5, step=1)
            urgency = st.selectbox("구매 긴급도", ["긴급", "보통", "여유"], index=1)
            b_strategy = st.selectbox("구매자 협상전략", Config.ALLOWED_STRATEGIES, index=1)
        
        # 전략 설명
        strategy_desc = {
            "공격적": "빠른 양보, 적극적 거래 추진 (높은 리스크)",
            "보수적": "신중한 양보, 안정적 거래 (긴 협상시간)",
            "무작위": "예측 불가능한 협상 패턴 (불확실성)",
            "분석적": "패턴 분석 후 전략적 대응 (균형)"
        }
        
        col1.caption(f"선택 전략: {strategy_desc.get(s_strategy, '')}")
        col2.caption(f"선택 전략: {strategy_desc.get(b_strategy, '')}")
        
        # 시뮬레이션 횟수 제한
        if st.session_state.simulation_count >= 50:
            st.warning("⚠️ 시뮬레이션 횟수 제한에 도달했습니다. 페이지를 새로고침해주세요.")
            return
        
        if st.button("🚀 협상 시작", type="primary", use_container_width=True):
            st.session_state.simulation_count += 1
            
            with st.spinner("🔄 협상 진행 중... 각 라운드별 상세 분석을 수행합니다."):
                log, result, rounds, prices, effective_prices, metrics = NegotiationSimulator.simulate_negotiation(
                    cost, seller_target, min_qty, (deliv_start, deliv_end),
                    buyer_target, buyer_qty, buyer_deliv, s_strategy, b_strategy,
                    profit_margin, budget_limit, market_position, urgency
                )
            
            # 결과 표시
            if result:
                st.success("🎉 협상 성공!")
                
                # 핵심 성과 지표
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("💰 최종 단가", f"{result['price']:,.0f}원", 
                             delta=f"실질: {result['effective_price']:,.0f}원")
                with col2:
                    st.metric("📦 최종 수량", f"{result['qty']:,}개", 
                             delta=f"총액: {result['total_value']:,.0f}원")
                with col3:
                    st.metric("🚚 최종 납기", f"{result['delivery']}일", 
                             delta=f"페널티: {result['penalty_rate']}%")
                with col4:
                    st.metric("🤝 Win-Win 점수", f"{metrics.win_win_score:.1f}점", 
                             delta="상호이익 달성도")
                
                # 상세 협상 결과
                st.subheader("📋 최종 계약 조건")
                result_col1, result_col2 = st.columns(2)
                
                with result_col1:
                    st.markdown(f"""
                    **💰 가격 정보**
                    - 명목 단가: {result['price']:,.0f}원
                    - 실질 단가: {result['effective_price']:,.0f}원
                    - 총 계약금액: {result['total_value']:,.0f}원
                    - 대량할인: {result.get('discount_rate', 0)}%
                    
                    **📊 품질 및 보증**
                    - 품질 등급: {result['quality_grade']}
                    - 보증 기간: {result['warranty_months']}개월
                    - 지연 페널티: {result['penalty_rate']}%
                    """)
                
                with result_col2:
                    st.markdown(f"""
                    **💳 결제 및 납기**
                    - 결제 조건: {result['payment_method']}
                    - 납기일: {result['delivery']}일
                    - 수량: {result['qty']:,}개
                    
                    **📈 성과 분석**
                    - 판매자 만족도: {metrics.seller_satisfaction:.1f}%
                    - 구매자 만족도: {metrics.buyer_satisfaction:.1f}%
                    - 위험 점수: {metrics.risk_score:.1f}점
                    """)
                
            else:
                st.error("💔 협상 결렬 - 양측이 합의점을 찾지 못했습니다.")
                st.info("🔍 조건을 조정하여 다시 시도해보세요. 예산 한도를 늘리거나 목표 가격을 조정하면 성공 확률이 높아집니다.")
            
            # 협상 로그 표시
            st.subheader("📜 협상 진행 과정")
            with st.expander("상세 협상 로그 보기", expanded=False):
                for line in log:
                    if line.startswith("🔄"):
                        st.markdown(f"### {line}")
                    elif line.startswith("📊"):
                        st.markdown(f"**{line}**")
                    elif "---" in line:
                        st.divider()
                    else:
                        st.write(line)
            
            # 그래프 생성 (데이터가 있을 때만)
            if prices and rounds:
                try:
                    # 가격 변화 그래프
                    st.subheader("📈 협상 진행 과정 시각화")
                    
                    # 탭으로 구분
                    tab1, tab2, tab3 = st.tabs(["💰 가격 변화", "📊 성과 분석", "🎯 협상 효율성"])
                    
                    with tab1:
                        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
                        
                        # 명목 가격 변화
                        seller_p = [x[0] for x in prices]
                        buyer_p = [x[1] for x in prices]
                        
                        ax1.plot(rounds, seller_p, label="판매자 제안가 (명목)", marker="o", linewidth=3, color='#FF6B6B', markersize=8)
                        ax1.plot(rounds, buyer_p, label="구매자 제안가 (명목)", marker="s", linewidth=3, color='#4ECDC4', markersize=8)
                        ax1.set_xlabel("협상 라운드", fontsize=12)
                        ax1.set_ylabel("명목 단가 (원)", fontsize=12)
                        ax1.set_title("📊 명목 가격 협상 진행 과정", fontsize=14, fontweight='bold')
                        ax1.legend(fontsize=11)
                        ax1.grid(True, alpha=0.3)
                        
                        # 가격 설명
                        ax1.text(0.02, 0.98, "📌 빨간선: 판매자가 제시한 가격\n📌 청록선: 구매자가 제시한 가격\n💡 두 선이 만나는 지점이 합의점", 
                                transform=ax1.transAxes, fontsize=10, verticalalignment='top',
                                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.7))
                        
                        # 실질 가격 변화
                        if effective_prices:
                            seller_eff = [x[0] for x in effective_prices]
                            buyer_eff = [x[1] for x in effective_prices]
                            
                            ax2.plot(rounds, seller_eff, label="판매자 실질가격", marker="^", linewidth=3, color='#FF8E53', markersize=8, linestyle='--')
                            ax2.plot(rounds, buyer_eff, label="구매자 실질가격", marker="v", linewidth=3, color='#95E1D3', markersize=8, linestyle='--')
                            ax2.set_xlabel("협상 라운드", fontsize=12)
                            ax2.set_ylabel("실질 단가 (원)", fontsize=12)
                            ax2.set_title("💎 실질 가격 협상 진행 과정 (결제조건, 품질, 보증 반영)", fontsize=14, fontweight='bold')
                            ax2.legend(fontsize=11)
                            ax2.grid(True, alpha=0.3)
                            
                            # 실질가격 설명
                            ax2.text(0.02, 0.98, "📌 실선: 명목가격 (계약서상 가격)\n📌 점선: 실질가격 (모든 조건 반영)\n💡 실질가격이 실제 비용부담을 나타냄", 
                                    transform=ax2.transAxes, fontsize=10, verticalalignment='top',
                                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
                        
                        plt.tight_layout()
                        st.pyplot(fig)
                        plt.close(fig)
                    
                    with tab2:
                        if result:
                            # 성과 분석 차트
                            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
                            
                            # 만족도 비교
                            satisfaction_data = [metrics.seller_satisfaction, metrics.buyer_satisfaction]
                            satisfaction_labels = ['판매자', '구매자']
                            colors = ['#FF6B6B', '#4ECDC4']
                            
                            bars1 = ax1.bar(satisfaction_labels, satisfaction_data, color=colors, alpha=0.8, width=0.6)
                            ax1.set_title('🎯 양측 만족도 비교', fontsize=14, fontweight='bold')
                            ax1.set_ylabel('만족도 (%)', fontsize=12)
                            ax1.set_ylim(0, 100)
                            
                            # 막대 위에 값 표시
                            for bar, value in zip(bars1, satisfaction_data):
                                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                                        f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
                            
                            # 위험도 및 신뢰도
                            risk_data = [100-metrics.risk_score, metrics.delivery_reliability, metrics.price_competitiveness]
                            risk_labels = ['안전도', '납기신뢰도', '가격경쟁력']
                            colors2 = ['#95E1D3', '#F8B500', '#A8E6CF']
                            
                            bars2 = ax2.bar(risk_labels, risk_data, color=colors2, alpha=0.8)
                            ax2.set_title('📊 거래 품질 지표', fontsize=14, fontweight='bold')
                            ax2.set_ylabel('점수', fontsize=12)
                            ax2.set_ylim(0, 100)
                            
                            for bar, value in zip(bars2, risk_data):
                                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                                        f'{value:.1f}', ha='center', va='bottom', fontweight='bold')
                            
                            # Win-Win 점수 원형 차트
                            win_lose_data = [metrics.win_win_score, 100-metrics.win_win_score]
                            win_lose_labels = ['Win-Win', 'Win-Lose']
                            colors3 = ['#4ECDC4', '#FFB6C1']
                            
                            wedges, texts, autotexts = ax3.pie(win_lose_data, labels=win_lose_labels, colors=colors3, 
                                                              autopct='%1.1f%%', startangle=90)
                            ax3.set_title('🤝 협상 결과 유형', fontsize=14, fontweight='bold')
                            
                            # 총 거래가치 표시
                            ax4.text(0.5, 0.6, f'💎 총 거래금액', ha='center', va='center', 
                                    fontsize=16, fontweight='bold', transform=ax4.transAxes)
                            ax4.text(0.5, 0.4, f'{result["total_value"]:,.0f}원', ha='center', va='center', 
                                    fontsize=24, fontweight='bold', color='#2E8B57', transform=ax4.transAxes)
                            ax4.text(0.5, 0.2, f'단가: {result["effective_price"]:,.0f}원 × 수량: {result["qty"]:,}개', 
                                    ha='center', va='center', fontsize=12, transform=ax4.transAxes)
                            ax4.axis('off')
                            
                            plt.tight_layout()
                            st.pyplot(fig)
                            plt.close(fig)
                    
                    with tab3:
                        if result and len(rounds) > 1:
                            # 협상 효율성 분석
                            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
                            
                            # 가격 수렴 패턴
                            price_gap = [abs(s - b) for s, b in prices]
                            ax1.plot(rounds, price_gap, marker='o', linewidth=3, color='#FF6B6B', markersize=8)
                            ax1.fill_between(rounds, price_gap, alpha=0.3, color='#FF6B6B')
                            ax1.set_xlabel('협상 라운드', fontsize=12)
                            ax1.set_ylabel('가격 격차 (원)', fontsize=12)
                            ax1.set_title('📉 가격 격차 수렴 과정', fontsize=14, fontweight='bold')
                            ax1.grid(True, alpha=0.3)
                            
                            # 격차 감소율 표시
                            if len(price_gap) > 1:
                                reduction_rate = ((price_gap[0] - price_gap[-1]) / price_gap[0]) * 100
                                ax1.text(0.02, 0.98, f'💡 가격격차 감소율: {reduction_rate:.1f}%', 
                                        transform=ax1.transAxes, fontsize=11, verticalalignment='top',
                                        bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))
                            
                            # 협상 효율성 점수
                            efficiency_factors = ['속도', '만족도', '안정성', '경제성']
                            speed_score = max(0, 100 - len(rounds) * 5)  # 라운드가 적을수록 고득점
                            satisfaction_score = metrics.win_win_score
                            stability_score = 100 - metrics.risk_score
                            economics_score = metrics.price_competitiveness
                            
                            efficiency_scores = [speed_score, satisfaction_score, stability_score, economics_score]
                            
                            angles = np.linspace(0, 2 * np.pi, len(efficiency_factors), endpoint=False).tolist()
                            efficiency_scores += efficiency_scores[:1]  # 원형을 완성하기 위해 첫 값을 마지막에 추가
                            angles += angles[:1]
                            
                            ax2 = plt.subplot(122, projection='polar')
                            ax2.plot(angles, efficiency_scores, 'o-', linewidth=3, color='#4ECDC4', markersize=8)
                            ax2.fill(angles, efficiency_scores, alpha=0.25, color='#4ECDC4')
                            ax2.set_xticks(angles[:-1])
                            ax2.set_xticklabels(efficiency_factors, fontsize=11)
                            ax2.set_ylim(0, 100)
                            ax2.set_title('🎯 협상 효율성 레이더', fontsize=14, fontweight='bold', pad=20)
                            ax2.grid(True)
                            
                            # 평균 효율성 점수 표시
                            avg_efficiency = np.mean(efficiency_scores[:-1])
                            ax2.text(0, -0.15, f'종합 효율성: {avg_efficiency:.1f}점', 
                                    ha='center', va='center', transform=ax2.transAxes,
                                    fontsize=12, fontweight='bold', 
                                    bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgreen", alpha=0.7))
                            
                            plt.tight_layout()
                            st.pyplot(fig)
                            plt.close(fig)
                            
                            # 협상 인사이트
                            st.subheader("🧠 협상 인사이트")
                            insight_col1, insight_col2 = st.columns(2)
                            
                            with insight_col1:
                                st.markdown("**📈 성공 요인**")
                                if metrics.win_win_score > 70:
                                    st.success("✅ 양측 모두 만족하는 Win-Win 협상 달성")
                                elif metrics.seller_satisfaction > 80:
                                    st.info("🔵 판매자 우위의 협상 결과")
                                elif metrics.buyer_satisfaction > 80:
                                    st.info("🟢 구매자 우위의 협상 결과")
                                else:
                                    st.warning("⚠️ 타협적 협상 - 개선 여지 존재")
                                
                                if len(rounds) <= 5:
                                    st.success("⚡ 효율적인 빠른 협상")
                                elif len(rounds) <= 10:
                                    st.info("🔄 적정 수준의 협상 과정")
                                else:
                                    st.warning("🐌 장기간 협상 - 비효율 가능성")
                            
                            with insight_col2:
                                st.markdown("**🎯 개선 제안**")
                                if metrics.risk_score > 60:
                                    st.warning("⚠️ 높은 위험도 - 납기 및 품질 조건 재검토")
                                if metrics.delivery_reliability < 50:
                                    st.error("🚚 납기 신뢰도 부족 - 일정 조정 필요")
                                if metrics.price_competitiveness < 40:
                                    st.warning("💰 가격 경쟁력 부족 - 원가 절감 방안 검토")
                                if metrics.win_win_score < 50:
                                    st.info("🤝 상호 이익 증진을 위한 추가 조건 협의 권장")
                
                except Exception as e:
                    st.error(f"그래프 생성 중 오류가 발생했습니다: {str(e)}")
    
    except Exception as e:
        st.error(f"애플리케이션 오류가 발생했습니다: {str(e)}")
        logger.error(f"UI 오류: {str(e)}")

if __name__ == "__main__":
    main()