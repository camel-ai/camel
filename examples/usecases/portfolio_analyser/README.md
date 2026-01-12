# 🤖 AI-Powered Investment Portfolio Analyzer

An intelligent portfolio analysis tool that leverages the CAMEL multi-agent framework to provide comprehensive investment insights. The system employs three specialized AI agents working together to deliver expert-level financial analysis, market research, and risk assessment.

---

## 🚀 Features

- **Multi-Agent Analysis**: Three specialized AI agents collaborate to provide comprehensive insights:
  - 📊 **Financial Analyst**: Performance metrics, ratios, and quantitative analysis
  - 🔍 **Market Researcher**: Industry trends, sentiment, and competitive analysis  
  - ⚠️ **Risk Assessor**: Portfolio risk evaluation and mitigation strategies

- **Real-Time Market Data**: Fetches live stock prices and historical data via Yahoo Finance
- **Interactive Portfolio Builder**: Configure custom portfolios with flexible weight allocation
- **Visual Analytics**: Dynamic charts and metrics visualization
- **Comprehensive Reporting**: Detailed analysis across multiple dimensions

---

## 📦 Requirements

### Python Dependencies
```bash
pip install -r requirements.txt
```

### API Requirements
- **OpenAI API Key**: Required for CAMEL AI agents
- Create a `.env` file with your API key:
```
OPENAI_API_KEY=your_openai_api_key_here
```

---

## 🛠️ Installation & Setup

1. **Clone or download the project files**

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**
   - Create a `.env` file in the project root
   - Add your OpenAI API key: `OPENAI_API_KEY=your_key_here`

4. **Run the application:**
```bash
streamlit run app.py
```

5. **Open your browser** to the provided local URL (typically `http://localhost:8501`)

---

## 💼 How to Use

### 1. Portfolio Configuration
- Set your total portfolio value
- Enter stock symbols (comma-separated, e.g., `AAPL,GOOGL,MSFT`)
- Adjust allocation weights using the sliders
- Select analysis period (30, 90, 180, or 252 days)

### 2. AI Analysis
- Click "🚀 Start AI Analysis" to begin
- The system will initialize three AI agents
- Watch as agents analyze your portfolio from different perspectives

### 3. Review Results
Navigate through three comprehensive analysis tabs:

**📊 Financial Analysis**
- Portfolio performance evaluation
- Key financial metrics interpretation
- Return and volatility analysis
- Performance attribution insights

**🔍 Market Research**
- Current market conditions analysis
- Industry trends and competitive positioning
- Economic factors affecting performance
- Market sentiment evaluation

**⚠️ Risk Assessment**
- Portfolio diversification analysis
- Risk concentration evaluation
- Potential risk scenarios
- Risk mitigation recommendations

---

## 🏗️ Architecture

### Multi-Agent System
```
Portfolio Manager (User Input)
    ↓
┌─────────────────┬─────────────────┬─────────────────┐
│ Financial       │ Market          │ Risk            │
│ Analyst Agent   │ Researcher      │ Assessor Agent  │
│                 │ Agent           │                 │
│ • Metrics       │ • Trends        │ • Diversification│
│ • Performance   │ • Sentiment     │ • Scenarios     │
│ • Attribution   │ • Competition   │ • Mitigation    │
└─────────────────┴─────────────────┴─────────────────┘
    ↓
Comprehensive Portfolio Analysis Report
```

### Data Flow
1. **Input**: Portfolio symbols, weights, and parameters
2. **Data Fetching**: Real-time market data via Yahoo Finance API
3. **Agent Processing**: Parallel analysis by specialized AI agents
4. **Output**: Multi-dimensional insights and recommendations

---

## 🔧 Configuration Options

### Portfolio Settings
- **Portfolio Value**: Minimum $1,000, adjustable in $1,000 increments
- **Stock Symbols**: Any valid ticker symbols (NYSE, NASDAQ, etc.)
- **Allocation Weights**: Flexible percentage allocation (auto-normalized)
- **Analysis Period**: 30, 90, 180, or 252 trading days

### Agent Customization
Each agent can be customized by modifying their system messages in the `PortfolioAnalyzer` class:
- `_create_financial_analyst()`: Modify financial analysis focus
- `_create_market_researcher()`: Adjust research priorities  
- `_create_risk_assessor()`: Customize risk evaluation criteria

---

## 📊 Sample Analysis Output

### Key Metrics Displayed
- **Total Return**: Weighted portfolio return over analysis period
- **Volatility**: Portfolio price volatility percentage
- **Holdings Count**: Number of individual positions
- **Current Prices**: Real-time stock prices and changes

### Agent Insights Examples
- **Financial**: "The portfolio demonstrates strong risk-adjusted returns with a Sharpe ratio of 1.2..."
- **Market Research**: "Current market conditions favor technology stocks due to AI adoption trends..."
- **Risk Assessment**: "Portfolio shows high correlation risk with 60% technology sector concentration..."

---

## 🛡️ Error Handling

The application includes comprehensive error handling for:
- Invalid stock symbols
- API connectivity issues
- Missing environment variables
- Data fetching failures
- Agent processing errors

---

## 🔮 Future Enhancements

- **Additional Asset Classes**: Bonds, ETFs, commodities, crypto
- **Advanced Metrics**: Sharpe ratio, Beta, Alpha, VaR calculations
- **Benchmark Comparisons**: S&P 500, sector indices
- **Portfolio Optimization**: Efficient frontier analysis
- **Historical Backtesting**: Strategy performance over time
- **Export Features**: PDF reports, CSV data export

---

## 🤝 Contributing

This project uses the CAMEL framework for multi-agent AI systems. Contributions welcome for:
- New agent specializations
- Enhanced analysis metrics
- Additional data sources
- UI/UX improvements

---

## 📝 License

This project is for educational and research purposes. Please ensure compliance with:
- Yahoo Finance API terms of service
- OpenAI API usage policies
- Financial data usage regulations

---

## 🆘 Troubleshooting

### Common Issues

**API Key Not Found**
```
❌ OpenAI API key not found!
```
Solution: Create `.env` file with `OPENAI_API_KEY=your_key`

**Stock Symbol Errors**
```
Error fetching data for SYMBOL: [details]
```
Solution: Verify ticker symbols are valid and actively traded

**Analysis Failures**
```
Analysis failed: [error details]
```
Solution: Check internet connection and API quotas

---

## 🔗 Powered By

- [CAMEL-AI Framework](https://github.com/camel-ai/camel) - Multi-agent AI system
- [Yahoo Finance API](https://github.com/ranaroussi/yfinance) - Market data
- [Streamlit](https://streamlit.io/) - Web interface
- [Plotly](https://plotly.com/) - Interactive visualizations
- [OpenAI GPT-4](https://openai.com/) - AI agent intelligence

---

*Built with ❤️ for smarter investment decisions*