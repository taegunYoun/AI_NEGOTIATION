import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import requests
import json
import logging
from typing import Dict, Tuple, List, Optional, Any
from datetime import datetime, timedelta

# 한글 폰트 설정
plt.rcParams['font.family'] = ['DejaVu Sans', 'Malgun Gothic', 'Apple Gothic', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API 설정
API_BASE_URL = "http://localhost:8000"  # FastAPI 서버 주소
SIMULATE_ENDPOINT = f"{API_BASE_URL}/simulate"

# 상수 정의 (API와 동일하게 유지)
class Config:
    MAX_ROUNDS = 15
    MIN_PRICE = 1
    MAX_PRICE = 100000
    MIN_QUANTITY = 1
    MAX_QUANTITY = 100000
    MIN_DELIVERY_DAYS = 1
    MAX_DELIVERY_DAYS = 365
    # API와 일치하는 영어 전략명
    ALLOWED_STRATEGIES = ["aggressive", "conservative", "balanced"]
    STRATEGY_DISPLAY = {
        "aggressive": "공격적",
        "conservative": "보수적", 
        "balanced": "균형적"
    }
    PAYMENT_METHODS = ["현금", "30일 후불", "60일 후불", "90일 후불", "분할결제"]
    QUALITY_GRADES = ["A급", "B급", "C급", "표준"]
    MARKET_POSITIONS = ["strong", "weak", "neutral"]
    MARKET_DISPLAY = {
        "strong": "강세",
        "weak": "약세",
        "neutral": "중간"
    }
    URGENCY_LEVELS = ["high", "medium", "low"]
    URGENCY_DISPLAY = {
        "high": "긴급",
        "medium": "보통",
        "low": "여유"
    }

def call_api(data: dict) -> dict:
    """FastAPI 서버 호출"""
    try:
        logger.info(f"API 호출 시작: {SIMULATE_ENDPOINT}")
        response = requests.post(
            SIMULATE_ENDPOINT,
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info("API 호출 성공")
            return response.json()
        else:
            logger.error(f"API 호출 실패: {response.status_code}, {response.text}")
            return {
                "success": False,
                "error": f"서버 오류 (HTTP {response.status_code}): {response.text}"
            }
    
    except requests.exceptions.ConnectionError:
        logger.error("API 서버 연결 실패")
        return {
            "success": False,
            "error": "API 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요."
        }
    except requests.exceptions.Timeout:
        logger.error("API 호출 타임아웃")
        return {
            "success": False,
            "error": "서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
        }
    except Exception as e:
        logger.error(f"API 호출 중 예외 발생: {str(e)}")
        return {
            "success": False,
            "error": f"예상치 못한 오류가 발생했습니다: {str(e)}"
        }

def validate_inputs(cost, seller_target, min_qty, deliv_start, deliv_end, 
                   buyer_target, budget_limit, buyer_qty, buyer_deliv, profit_margin):
    """입력값 검증"""
    errors = []
    
    if cost >= seller_target:
        errors.append("판매자 목표가격이 원가보다 높아야 합니다.")
    
    if buyer_target >= budget_limit:
        errors.append("예산 한도가 구매자 목표가격보다 높아야 합니다.")
    
    if deliv_start > deliv_end:
        errors.append("납기 시작일이 종료일보다 클 수 없습니다.")
    
    if profit_margin < 0 or profit_margin > 100:
        errors.append("이익률은 0~100% 범위여야 합니다.")
    
    if min_qty <= 0 or buyer_qty <= 0:
        errors.append("수량은 양수여야 합니다.")
    
    if buyer_deliv <= 0:
        errors.append("희망 납기일은 양수여야 합니다.")
    
    return errors

def create_charts(result, metrics, rounds, prices, effective_prices):
    """차트 생성 함수"""
    try:
        if not prices or not rounds:
            st.warning("차트를 생성할 데이터가 충분하지 않습니다.")
            return
        
        # 탭으로 구분
        tab1, tab2, tab3 = st.tabs(["💰 가격 변화", "📊 성과 분석", "🎯 협상 효율성"])
        
        with tab1:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            # 명목 가격 변화
            seller_p = [x[0] for x in prices]
            buyer_p = [x[1] for x in prices]
            
            ax1.plot(rounds, seller_p, label="판매자 제안가 (명목)", marker="o", 
                    linewidth=3, color='#FF6B6B', markersize=8)
            ax1.plot(rounds, buyer_p, label="구매자 제안가 (명목)", marker="s", 
                    linewidth=3, color='#4ECDC4', markersize=8)
            ax1.set_xlabel("협상 라운드", fontsize=12)
            ax1.set_ylabel("명목 단가 (원)", fontsize=12)
            ax1.set_title("📊 명목 가격 협상 진행 과정", fontsize=14, fontweight='bold')
            ax1.legend(fontsize=11)
            ax1.grid(True, alpha=0.3)
            
            # 실질 가격 변화
            if effective_prices:
                seller_eff = [x[0] for x in effective_prices]
                buyer_eff = [x[1] for x in effective_prices]
                
                ax2.plot(rounds, seller_eff, label="판매자 실질가격", marker="^", 
                        linewidth=3, color='#FF8E53', markersize=8, linestyle='--')
                ax2.plot(rounds, buyer_eff, label="구매자 실질가격", marker="v", 
                        linewidth=3, color='#95E1D3', markersize=8, linestyle='--')
                ax2.set_xlabel("협상 라운드", fontsize=12)
                ax2.set_ylabel("실질 단가 (원)", fontsize=12)
                ax2.set_title("💎 실질 가격 협상 진행 과정", fontsize=14, fontweight='bold')
                ax2.legend(fontsize=11)
                ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
        
        with tab2:
            if result:
                # 성과 분석 차트
                fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
                
                # 만족도 비교
                satisfaction_data = [metrics.get('seller_satisfaction', 0), 
                                   metrics.get('buyer_satisfaction', 0)]
                satisfaction_labels = ['판매자', '구매자']
                colors = ['#FF6B6B', '#4ECDC4']
                
                bars1 = ax1.bar(satisfaction_labels, satisfaction_data, color=colors, 
                               alpha=0.8, width=0.6)
                ax1.set_title('🎯 양측 만족도 비교', fontsize=14, fontweight='bold')
                ax1.set_ylabel('만족도 (%)', fontsize=12)
                ax1.set_ylim(0, 100)
                
                # 막대 위에 값 표시
                for bar, value in zip(bars1, satisfaction_data):
                    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                            f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
                
                # 위험도 및 신뢰도
                risk_data = [100-metrics.get('risk_score', 0), 
                           metrics.get('delivery_reliability', 0), 
                           metrics.get('price_competitiveness', 0)]
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
                win_win_score = metrics.get('win_win_score', 0)
                win_lose_data = [win_win_score, 100-win_win_score]
                win_lose_labels = ['Win-Win', 'Win-Lose']
                colors3 = ['#4ECDC4', '#FFB6C1']
                
                wedges, texts, autotexts = ax3.pie(win_lose_data, labels=win_lose_labels, 
                                                  colors=colors3, autopct='%1.1f%%', 
                                                  startangle=90)
                ax3.set_title('🤝 협상 결과 유형', fontsize=14, fontweight='bold')
                
                # 총 거래가치 표시
                total_value = result.get('total_value', 0)
                ax4.text(0.5, 0.6, f'💎 총 거래금액', ha='center', va='center', 
                        fontsize=16, fontweight='bold', transform=ax4.transAxes)
                ax4.text(0.5, 0.4, f'{total_value:,.0f}원', ha='center', va='center', 
                        fontsize=24, fontweight='bold', color='#2E8B57', 
                        transform=ax4.transAxes)
                ax4.text(0.5, 0.2, f'단가: {result.get("effective_price", 0):,.0f}원 × 수량: {result.get("qty", 0):,}개', 
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
                ax1.plot(rounds, price_gap, marker='o', linewidth=3, 
                        color='#FF6B6B', markersize=8)
                ax1.fill_between(rounds, price_gap, alpha=0.3, color='#FF6B6B')
                ax1.set_xlabel('협상 라운드', fontsize=12)
                ax1.set_ylabel('가격 격차 (원)', fontsize=12)
                ax1.set_title('📉 가격 격차 수렴 과정', fontsize=14, fontweight='bold')
                ax1.grid(True, alpha=0.3)
                
                # 협상 효율성 레이더 차트
                efficiency_factors = ['속도', '만족도', '안정성', '경제성']
                speed_score = max(0, 100 - len(rounds) * 5)
                satisfaction_score = metrics.get('win_win_score', 0)
                stability_score = 100 - metrics.get('risk_score', 0)
                economics_score = metrics.get('price_competitiveness', 0)
                
                efficiency_scores = [speed_score, satisfaction_score, 
                                   stability_score, economics_score]
                
                angles = np.linspace(0, 2 * np.pi, len(efficiency_factors), 
                                   endpoint=False).tolist()
                efficiency_scores += efficiency_scores[:1]
                angles += angles[:1]
                
                ax2 = plt.subplot(122, projection='polar')
                ax2.plot(angles, efficiency_scores, 'o-', linewidth=3, 
                        color='#4ECDC4', markersize=8)
                ax2.fill(angles, efficiency_scores, alpha=0.25, color='#4ECDC4')
                ax2.set_xticks(angles[:-1])
                ax2.set_xticklabels(efficiency_factors, fontsize=11)
                ax2.set_ylim(0, 100)
                ax2.set_title('🎯 협상 효율성 레이더', fontsize=14, 
                             fontweight='bold', pad=20)
                ax2.grid(True)
                
                plt.tight_layout()
                st.pyplot(fig)
                plt.close(fig)
    
    except Exception as e:
        st.error(f"차트 생성 중 오류가 발생했습니다: {str(e)}")
        logger.error(f"차트 생성 오류: {str(e)}")

def main():
    st.set_page_config(
        page_title="AI 협상 시뮬레이터",
        page_icon="🤝",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    st.title("🤝 AI 협상 시뮬레이터")
    st.markdown("복합조건을 고려한 실시간 협상 시뮬레이션")
    
    # API 서버 상태 확인
    try:
        health_check = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if health_check.status_code == 200:
            st.success("✅ API 서버 연결됨")
        else:
            st.error("❌ API 서버 응답 오류")
    except:
        st.error("❌ API 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
        st.info("💡 터미널에서 `uvicorn api.main:app --reload` 명령으로 서버를 시작하세요.")
        return
    
    # 협상 가이드 표시
    with st.expander("📋 협상 시뮬레이션 가이드", expanded=False):
        st.markdown("""
        ### 💡 협상에서 고려되는 핵심 요소들
        
        **🎯 가격 관련**
        - **명목가격 vs 실질가격**: 결제조건, 품질등급, 보증기간 등을 반영한 실제 비용
        - **총 거래가치**: 단가 × 수량으로 계산되는 전체 계약 규모
        
        **📊 품질 및 위험관리**
        - **품질등급별 가격차이**: A급(+15%) > B급(+8%) > 표준 > C급(-5%)
        - **보증기간**: 12개월 기준, 매월 +1.5% 가격 할증
        - **지연 페널티**: 납기 지연 시 적용되는 손해 배상률
        
        **💰 결제조건**
        - **현금결제**: 5% 할인 혜택
        - **후불결제**: 30일(표준), 60일(+2%), 90일(+5%)
        
        **📈 협상 전략**
        - **공격적**: 빠른 양보, 적극적 거래 추진
        - **보수적**: 신중한 양보, 안정적 조건 추구
        - **균형적**: 분석적 접근, 합리적 타협점 모색
        """)
    
    # 세션 상태 초기화
    if 'simulation_count' not in st.session_state:
        st.session_state.simulation_count = 0
    
    try:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏪 판매자 정보")
            cost = st.number_input("원가 (원)", min_value=1.0, max_value=100000.0, 
                                  value=800.0, step=1.0, key="seller_cost")
            seller_target = st.number_input("목표 단가 (원)", min_value=cost, 
                                          max_value=100000.0, value=max(1200.0, cost), 
                                          step=1.0, key="seller_target")
            profit_margin = st.slider("목표 이익률 (%)", min_value=5.0, max_value=50.0, 
                                    value=20.0, step=1.0, key="profit_margin")
            min_qty = st.number_input("최소 수량 (개)", min_value=1, max_value=100000, 
                                    value=800, step=1, key="min_qty")
            
            col1_1, col1_2 = st.columns(2)
            with col1_1:
                deliv_start = st.number_input("납기 시작일", min_value=1, max_value=365, 
                                            value=3, step=1, key="deliv_start")
            with col1_2:
                deliv_end = st.number_input("납기 종료일", min_value=deliv_start, 
                                          max_value=365, value=max(7, deliv_start), 
                                          step=1, key="deliv_end")
            
            # 선택 옵션들 - 표시용과 실제 값 분리
            market_display = st.selectbox("시장 지위", 
                                        list(Config.MARKET_DISPLAY.values()), 
                                        index=2, key="market_position")
            market_position = [k for k, v in Config.MARKET_DISPLAY.items() 
                             if v == market_display][0]
            
            s_strategy_display = st.selectbox("판매자 협상전략", 
                                            list(Config.STRATEGY_DISPLAY.values()), 
                                            index=0, key="s_strategy")
            s_strategy = [k for k, v in Config.STRATEGY_DISPLAY.items() 
                         if v == s_strategy_display][0]
        
        with col2:
            st.subheader("🛒 구매자 정보")
            buyer_target = st.number_input("목표 단가 (원)", min_value=1.0, 
                                         max_value=100000.0, value=1000.0, 
                                         step=1.0, key="buyer_target")
            budget_limit = st.number_input("예산 한도 (원)", min_value=buyer_target, 
                                         max_value=100000.0, 
                                         value=max(1500.0, buyer_target), 
                                         step=1.0, key="budget_limit")
            buyer_qty = st.number_input("목표 수량 (개)", min_value=1, max_value=100000, 
                                      value=1000, step=1, key="buyer_qty")
            buyer_deliv = st.number_input("희망 납기일", min_value=1, max_value=365, 
                                        value=5, step=1, key="buyer_deliv")
            
            urgency_display = st.selectbox("구매 긴급도", 
                                         list(Config.URGENCY_DISPLAY.values()), 
                                         index=1, key="urgency")
            urgency = [k for k, v in Config.URGENCY_DISPLAY.items() 
                      if v == urgency_display][0]
            
            b_strategy_display = st.selectbox("구매자 협상전략", 
                                            list(Config.STRATEGY_DISPLAY.values()), 
                                            index=1, key="b_strategy")
            b_strategy = [k for k, v in Config.STRATEGY_DISPLAY.items() 
                         if v == b_strategy_display][0]
        
        # 전략 설명
        strategy_desc = {
            "공격적": "빠른 양보, 적극적 거래 추진 (높은 리스크)",
            "보수적": "신중한 양보, 안정적 거래 (긴 협상시간)",
            "균형적": "분석적 접근, 합리적 타협점 모색"
        }
        
        col1.caption(f"선택 전략: {strategy_desc.get(s_strategy_display, '')}")
        col2.caption(f"선택 전략: {strategy_desc.get(b_strategy_display, '')}")
        
        # 입력값 검증
        validation_errors = validate_inputs(
            cost, seller_target, min_qty, deliv_start, deliv_end,
            buyer_target, budget_limit, buyer_qty, buyer_deliv, profit_margin
        )
        
        if validation_errors:
            st.error("❌ 입력값 오류:")
            for error in validation_errors:
                st.error(f"• {error}")
            return
        
        # 시뮬레이션 실행
        if st.button("🚀 협상 시작", type="primary", use_container_width=True):
            st.session_state.simulation_count += 1
            
            # API 호출 데이터 준비
            api_data = {
                "cost": cost,
                "seller_target": seller_target,
                "min_qty": min_qty,
                "deliv_range": [deliv_start, deliv_end],
                "buyer_target": buyer_target,
                "buyer_qty": buyer_qty,
                "buyer_deliv": buyer_deliv,
                "s_strategy": s_strategy,
                "b_strategy": b_strategy,
                "profit_margin": profit_margin,
                "budget_limit": budget_limit,
                "market_position": market_position,
                "urgency": urgency
            }
            
            with st.spinner("🔄 협상 진행 중... AI가 복잡한 조건들을 분석하고 있습니다."):
                api_response = call_api(api_data)
            
            # API 응답 처리
            if api_response.get("success", True):  # success 키가 없으면 True로 가정
                result = api_response.get("result")
                log = api_response.get("log", [])
                rounds = api_response.get("rounds", [])
                prices = api_response.get("prices", [])
                effective_prices = api_response.get("effective_prices", [])
                metrics = api_response.get("metrics", {})
                
                # 결과 표시
                if result:
                    st.success("🎉 협상 성공!")
                    
                    # 핵심 성과 지표
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("💰 최종 단가", f"{result.get('price', 0):,.0f}원", 
                                 delta=f"실질: {result.get('effective_price', 0):,.0f}원")
                    with col2:
                        st.metric("📦 최종 수량", f"{result.get('qty', 0):,}개", 
                                 delta=f"총액: {result.get('total_value', 0):,.0f}원")
                    with col3:
                        st.metric("🚚 최종 납기", f"{result.get('delivery', 0)}일", 
                                 delta=f"페널티: {result.get('penalty_rate', 0)}%")
                    with col4:
                        st.metric("🤝 Win-Win 점수", f"{metrics.get('win_win_score', 0):.1f}점", 
                                 delta="상호이익 달성도")
                    
                    # 상세 협상 결과
                    st.subheader("📋 최종 계약 조건")
                    result_col1, result_col2 = st.columns(2)
                    
                    with result_col1:
                        st.markdown(f"""
                        **💰 가격 정보**
                        - 명목 단가: {result.get('price', 0):,.0f}원
                        - 실질 단가: {result.get('effective_price', 0):,.0f}원
                        - 총 계약금액: {result.get('total_value', 0):,.0f}원
                        - 대량할인: {result.get('discount_rate', 0)}%
                        
                        **📊 품질 및 보증**
                        - 품질 등급: {result.get('quality_grade', '표준')}
                        - 보증 기간: {result.get('warranty_months', 12)}개월
                        - 지연 페널티: {result.get('penalty_rate', 0)}%
                        """)
                    
                    with result_col2:
                        st.markdown(f"""
                        **💳 결제 및 납기**
                        - 결제 조건: {result.get('payment_method', '현금')}
                        - 납기일: {result.get('delivery', 0)}일
                        - 수량: {result.get('qty', 0):,}개
                        
                        **📈 성과 분석**
                        - 판매자 만족도: {metrics.get('seller_satisfaction', 0):.1f}%
                        - 구매자 만족도: {metrics.get('buyer_satisfaction', 0):.1f}%
                        - 위험 점수: {metrics.get('risk_score', 0):.1f}점
                        """)
                    
                    # 협상 로그 표시
                    st.subheader("📜 협상 진행 과정")
                    with st.expander("상세 협상 로그 보기", expanded=False):
                        for line in log:
                            st.write(line)
                    
                    # 차트 생성
                    if prices and rounds:
                        st.subheader("📈 협상 진행 과정 시각화")
                        create_charts(result, metrics, rounds, prices, effective_prices)
                
                else:
                    st.error("💔 협상 결렬 - 양측이 합의점을 찾지 못했습니다.")
                    st.info("🔍 조건을 조정하여 다시 시도해보세요.")
                    
                    # 실패 로그도 표시
                    if log:
                        with st.expander("협상 실패 과정 보기", expanded=False):
                            for line in log:
                                st.write(line)
            
            else:
                # API 오류 처리
                error_message = api_response.get("error", "알 수 없는 오류가 발생했습니다.")
                st.error(f"❌ 시뮬레이션 실행 실패: {error_message}")
    
    except Exception as e:
        st.error(f"애플리케이션 오류가 발생했습니다: {str(e)}")
        logger.error(f"UI 오류: {str(e)}")

if __name__ == "__main__":
    main()