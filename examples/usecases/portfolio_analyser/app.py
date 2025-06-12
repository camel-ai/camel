# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========


import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import yfinance as yf
import numpy as np
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# CAMEL imports
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Configure Streamlit page
st.set_page_config(
    page_title="AI Investment Portfolio Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

class PortfolioAnalyzer:
    def __init__(self):
        """Initialize the portfolio analyzer with CAMEL agents."""
        self.model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
        )
        
        # Create specialized agents
        self.financial_analyst = self._create_financial_analyst()
        self.market_researcher = self._create_market_researcher()
        self.risk_assessor = self._create_risk_assessor()
        
    def _create_financial_analyst(self):
        """Create a financial analyst agent."""
        system_message = BaseMessage.make_assistant_message(
            role_name="Financial Analyst",
            content="""You are an expert financial analyst specializing in portfolio analysis, 
            valuation metrics, and performance calculations. You excel at:
            - Calculating financial ratios and metrics
            - Analyzing portfolio performance and risk
            - Providing quantitative insights"""
        )
        
        return ChatAgent(
            system_message=system_message,
            model=self.model
        )
    
    def _create_market_researcher(self):
        """Create a market research agent."""
        system_message = BaseMessage.make_assistant_message(
            role_name="Market Researcher",
            content="""You are a market research specialist focused on analyzing 
            market trends and company fundamentals. You excel at:
            - Researching company fundamentals and news
            - Analyzing market trends and sentiment
            - Providing market context and insights"""
        )
        
        return ChatAgent(
            system_message=system_message,
            model=self.model
        )
    
    def _create_risk_assessor(self):
        """Create a risk assessment agent."""
        system_message = BaseMessage.make_assistant_message(
            role_name="Risk Assessor",
            content="""You are a risk management expert specializing in portfolio risk assessment. 
            You excel at:
            - Evaluating portfolio risk metrics
            - Analyzing correlation and diversification
            - Assessing sector and geographic exposure
            - Providing risk mitigation recommendations"""
        )
        
        return ChatAgent(
            system_message=system_message,
            model=self.model
        )
    
    def calculate_portfolio_metrics(self, portfolio_data, weights):
        """Calculate basic portfolio metrics."""
        if not portfolio_data:
            return {}
        
        # Calculate weighted returns
        total_return = 0
        price_changes = []
        
        for i, (symbol, data) in enumerate(portfolio_data.items()):
            if 'price_change' in data and i < len(weights):
                weighted_return = data['price_change'] * weights[i]
                total_return += weighted_return
                price_changes.append(data['price_change'])
        
        # Basic metrics
        metrics = {
            'total_return': total_return,
            'volatility': np.std(price_changes) if len(price_changes) > 1 else 0,
            'num_holdings': len(portfolio_data),
            'avg_return': np.mean(price_changes) if price_changes else 0
        }
        
        return metrics
    
    def analyze_portfolio(self, symbols, weights, portfolio_value, analysis_period=252):
        """Perform comprehensive portfolio analysis using multiple agents."""
        
        # Fetch market data
        portfolio_data = self._fetch_portfolio_data(symbols, analysis_period)
        
        if not portfolio_data:
            return {
                'financial_analysis': "Unable to fetch portfolio data",
                'market_research': "Unable to fetch market data for research",
                'risk_assessment': "Unable to perform risk assessment without data",
                'portfolio_data': {},
                'metrics': {}
            }
        
        # Calculate basic metrics
        metrics = self.calculate_portfolio_metrics(portfolio_data, weights)
        
        # Create analysis prompts
        portfolio_summary = f"""
        Portfolio Summary:
        - Symbols: {symbols}
        - Weights: {[f'{w*100:.1f}%' for w in weights]}
        - Total Value: ${portfolio_value:,.2f}
        - Analysis Period: {analysis_period} days
        - Current Metrics: {metrics}
        """
        
        # Task 1: Financial Analysis
        financial_task = f"""
        {portfolio_summary}
        
        Provide a comprehensive financial analysis covering:
        1. Portfolio performance evaluation
        2. Key financial metrics interpretation
        3. Return and volatility analysis
        4. Performance attribution insights
        """
        
        # Task 2: Market Research
        research_task = f"""
        {portfolio_summary}
        
        Provide market research insights covering:
        1. Current market conditions for these holdings
        2. Industry trends and competitive positioning
        3. Economic factors affecting performance
        4. Market sentiment analysis
        """
        
        # Task 3: Risk Assessment
        risk_task = f"""
        {portfolio_summary}
        
        Provide risk assessment covering:
        1. Portfolio diversification analysis
        2. Risk concentration evaluation
        3. Potential risk factors and scenarios
        4. Risk mitigation recommendations
        """
        
        # Execute agent tasks
        financial_response = self._execute_agent_task(self.financial_analyst, financial_task)
        research_response = self._execute_agent_task(self.market_researcher, research_task)
        risk_response = self._execute_agent_task(self.risk_assessor, risk_task)
        
        return {
            'financial_analysis': financial_response,
            'market_research': research_response,
            'risk_assessment': risk_response,
            'portfolio_data': portfolio_data,
            'metrics': metrics
        }
    
    def _fetch_portfolio_data(self, symbols, period):
        """Fetch portfolio data from Yahoo Finance."""
        try:
            data = {}
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period + 30)
            
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(start=start_date, end=end_date)
                    if not hist.empty and len(hist) > 1:
                        data[symbol] = {
                            'current_price': float(hist['Close'].iloc[-1]),
                            'price_change': float(((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100)
                        }
                except Exception as e:
                    st.warning(f"Error fetching data for {symbol}: {str(e)}")
                    
            return data
        except Exception as e:
            st.error(f"Error fetching portfolio data: {str(e)}")
            return {}
    
    def _execute_agent_task(self, agent, task):
        """Execute a task with a specific agent."""
        try:
            message = BaseMessage.make_user_message(role_name="Portfolio Manager", content=task)
            response = agent.step(message)
            return response.msgs[0].content if response.msgs else "No response generated"
        except Exception as e:
            return f"Error executing task: {str(e)}"

def check_environment():
    """Check if required environment variables are set."""
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_key:
        st.error("❌ OpenAI API key not found!")
        st.info("Please create a `.env` file with: OPENAI_API_KEY=your_key_here")
        return False
    else:
        st.sidebar.success("✅ API key loaded")
        return True

def main():
    st.title("🤖 AI-Powered Investment Portfolio Analyzer")
    st.markdown("*Powered by CAMEL Multi-Agent Framework*")
    
    # Check environment
    if not check_environment():
        st.stop()
    
    # Sidebar configuration
    st.sidebar.header("Portfolio Configuration")
    
    portfolio_value = st.sidebar.number_input(
        "Portfolio Value ($)", 
        min_value=1000, 
        value=100000, 
        step=1000
    )
    
    # Stock symbols
    default_symbols = "AAPL,GOOGL,MSFT,TSLA,AMZN"
    symbols_input = st.sidebar.text_input(
        "Stock Symbols (comma-separated)", 
        value=default_symbols
    )
    symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
    
    # Weights
    st.sidebar.write("Portfolio Weights (%)")
    weights = []
    for i, symbol in enumerate(symbols):
        weight = st.sidebar.slider(
            f"{symbol}", 
            min_value=0, 
            max_value=100, 
            value=100//len(symbols),
            key=f"weight_{i}"
        )
        weights.append(weight / 100)
    
    # Normalize weights
    total_weight = sum(weights)
    if total_weight > 0:
        weights = [w / total_weight for w in weights]
    
    # Analysis period
    analysis_period = st.sidebar.selectbox(
        "Analysis Period",
        options=[30, 90, 180, 252],
        index=3,
        format_func=lambda x: f"{x} days"
    )
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Portfolio Overview")
        
        if symbols:
            df_weights = pd.DataFrame({
                'Symbol': symbols,
                'Weight': [f"{w*100:.1f}%" for w in weights],
                'Value': [f"${portfolio_value * w:,.0f}" for w in weights]
            })
            st.dataframe(df_weights, use_container_width=True)
            
            # Allocation chart
            fig_pie = px.pie(
                values=[w*100 for w in weights], 
                names=symbols,
                title="Portfolio Allocation"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.header("Analysis Controls")
        
        if st.button("🚀 Start AI Analysis", type="primary", use_container_width=True):
            if not symbols:
                st.error("Please enter at least one stock symbol.")
                return
            
            if abs(sum(weights) - 1.0) > 0.01:
                st.error("Portfolio weights must sum to 100%.")
                return
            
            # Initialize analyzer
            with st.spinner("Initializing AI agents..."):
                try:
                    analyzer = PortfolioAnalyzer()
                except Exception as e:
                    st.error(f"Failed to initialize analyzer: {e}")
                    return
            
            # Run analysis
            with st.spinner("AI agents analyzing portfolio..."):
                try:
                    results = analyzer.analyze_portfolio(
                        symbols, weights, portfolio_value, analysis_period
                    )
                    
                    st.success("Analysis complete!")
                    
                    # Display results in tabs
                    tab1, tab2, tab3 = st.tabs(["📊 Financial Analysis", "🔍 Market Research", "⚠️ Risk Assessment"])
                    
                    with tab1:
                        st.header("Financial Analysis")
                        st.write(results['financial_analysis'])
                        
                        if results['metrics']:
                            st.subheader("Key Metrics")
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Total Return", f"{results['metrics'].get('total_return', 0):.2f}%")
                            with col2:
                                st.metric("Volatility", f"{results['metrics'].get('volatility', 0):.2f}%")
                            with col3:
                                st.metric("Holdings", results['metrics'].get('num_holdings', 0))
                            with col4:
                                st.metric("Portfolio Value", f"${portfolio_value:,.0f}")
                    
                    with tab2:
                        st.header("Market Research")
                        st.write(results['market_research'])
                        
                        if results['portfolio_data']:
                            st.subheader("Current Prices")
                            price_data = []
                            for symbol, data in results['portfolio_data'].items():
                                price_data.append({
                                    'Symbol': symbol,
                                    'Price': f"${data.get('current_price', 0):.2f}",
                                    'Change': f"{data.get('price_change', 0):.2f}%"
                                })
                            st.dataframe(pd.DataFrame(price_data), use_container_width=True)
                    
                    with tab3:
                        st.header("Risk Assessment")
                        st.write(results['risk_assessment'])
                        
                        st.subheader("Risk Summary")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Estimated VaR (5%)", f"${portfolio_value * 0.05:,.0f}")
                        with col2:
                            st.metric("Number of Holdings", len(symbols))
                
                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")

if __name__ == "__main__":
    main()