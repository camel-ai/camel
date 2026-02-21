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
import numpy as np
import requests
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional
import asyncio
from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# CAMEL AI imports with toolkits
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.configs import ChatGPTConfig
from camel.toolkits import (
    SearchToolkit,
    MathToolkit,
    WeatherToolkit,
)

# Configuration
st.set_page_config(
    page_title="AQI Monitoring System - CAMEL AI Enhanced",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

@dataclass
class AQIData:
    """Data structure for AQI information"""
    location: str
    aqi: int
    pm25: float
    pm10: float
    o3: float
    no2: float
    so2: float
    co: float
    timestamp: datetime
    category: str
    health_concern: str
    dominant_pollutant: str
    weather_conditions: Optional[Dict] = None

class EnhancedAQIMonitoringSystem:
    """Enhanced AQI Monitoring System using CAMEL AI with toolkits"""
    
    def __init__(self):
        self.api_key = None
        self.camel_agent = None
        self.search_toolkit = None
        self.math_toolkit = None
        self.weather_toolkit = None
        self.initialize_camel_system()
        
    def initialize_camel_system(self):
        """Initialize CAMEL AI system with toolkits"""
        # Get OpenAI API key from environment
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            st.error("❌ OpenAI API key required. Add OPENAI_API_KEY to .env file.")
            st.stop()
        
        # Initialize the CAMEL agent with enhanced environmental analysis capabilities
        system_message = BaseMessage.make_assistant_message(
            role_name="Advanced Environmental Data Analyst",
            content="""You are an expert environmental data analyst specializing in comprehensive Air Quality Index (AQI) monitoring and analysis. 
            
            Your capabilities include:
            1. Real-time air quality data analysis and interpretation
            2. Advanced statistical analysis of pollution trends
            3. Cross-referencing with weather data for correlation analysis
            4. Identifying pollution sources and patterns
            5. Providing actionable recommendations for individuals and communities
            6. Analyzing meteorological impacts on air quality
            7. Generating predictive insights based on historical patterns
            8. Creating comprehensive environmental health reports
            
            Always provide evidence-based, scientifically accurate insights.
            Focus on actionable recommendations and public health implications.
            Do not use external tools or make tool calls - provide analysis based on the data provided."""
        )
        
        # Create the model with optimized configuration
        model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O,
            model_config_dict={
                "temperature": 0.3,
                "max_tokens": 2000,
                "top_p": 0.9
            }
        )
        
        # Initialize ChatAgent without external tools to avoid tool call errors
        self.camel_agent = ChatAgent(
            system_message=system_message,
            model=model
        )
        
        st.success("✅ CAMEL AI system initialized successfully!")
    
    def get_aqi_category_and_dominant_pollutant(self, aqi_data) -> tuple:
        """Determine AQI category, health concern, and dominant pollutant"""
        if aqi_data['aqi'] <= 50:
            category, health_concern = "Good", "Little to no risk"
        elif aqi_data['aqi'] <= 100:
            category, health_concern = "Moderate", "Acceptable for most people"
        elif aqi_data['aqi'] <= 150:
            category, health_concern = "Unhealthy for Sensitive Groups", "Sensitive individuals may experience problems"
        elif aqi_data['aqi'] <= 200:
            category, health_concern = "Unhealthy", "General public may experience problems"
        elif aqi_data['aqi'] <= 300:
            category, health_concern = "Very Unhealthy", "Health alert: everyone may experience problems"
        else:
            category, health_concern = "Hazardous", "Emergency conditions: entire population affected"
        
        # Determine dominant pollutant
        pollutants = {
            'PM2.5': aqi_data.get('pm25', 0),
            'PM10': aqi_data.get('pm10', 0),
            'O3': aqi_data.get('o3', 0),
            'NO2': aqi_data.get('no2', 0),
            'SO2': aqi_data.get('so2', 0),
            'CO': aqi_data.get('co', 0)
        }
        
        dominant_pollutant = max(pollutants, key=pollutants.get) if any(pollutants.values()) else "Unknown"
        
        return category, health_concern, dominant_pollutant
    
    def fetch_aqi_data(self, city: str, api_key: str) -> Optional[AQIData]:
        """Fetch real-time AQI data from World Air Quality Index API"""
        try:
            # Using World Air Quality Index API
            url = f"https://api.waqi.info/feed/{city}/?token={api_key}"
            response = requests.get(url, timeout=15)
            
            if response.status_code != 200:
                st.error(f"HTTP Error {response.status_code} for {city}")
                return None
            
            data = response.json()
            if data['status'] != 'ok':
                st.error(f"API Error for {city}: {data.get('message', 'Unknown error')}")
                return None
            
            aqi_info = data['data']
            
            # Extract pollutant data safely
            iaqi = aqi_info.get('iaqi', {})
            
            # Create comprehensive data structure
            aqi_data_dict = {
                'aqi': aqi_info['aqi'],
                'pm25': iaqi.get('pm25', {}).get('v', 0) if 'pm25' in iaqi else 0,
                'pm10': iaqi.get('pm10', {}).get('v', 0) if 'pm10' in iaqi else 0,
                'o3': iaqi.get('o3', {}).get('v', 0) if 'o3' in iaqi else 0,
                'no2': iaqi.get('no2', {}).get('v', 0) if 'no2' in iaqi else 0,
                'so2': iaqi.get('so2', {}).get('v', 0) if 'so2' in iaqi else 0,
                'co': iaqi.get('co', {}).get('v', 0) if 'co' in iaqi else 0
            }
            
            category, health_concern, dominant_pollutant = self.get_aqi_category_and_dominant_pollutant(aqi_data_dict)
            
            return AQIData(
                location=aqi_info.get('city', {}).get('name', city),
                aqi=aqi_info['aqi'],
                pm25=aqi_data_dict['pm25'],
                pm10=aqi_data_dict['pm10'],
                o3=aqi_data_dict['o3'],
                no2=aqi_data_dict['no2'],
                so2=aqi_data_dict['so2'],
                co=aqi_data_dict['co'],
                timestamp=datetime.now(),
                category=category,
                health_concern=health_concern,
                dominant_pollutant=dominant_pollutant,
                weather_conditions=None
            )
        except Exception as e:
            st.error(f"Error fetching data for {city}: {str(e)}")
            return None
    
    def calculate_health_metrics(self, aqi_data: AQIData) -> Dict:
        """Calculate advanced health metrics using internal analysis"""
        try:
            calculation_query = f"""
            Analyze and calculate health risk metrics for this air quality data:
            - Location: {aqi_data.location}
            - AQI: {aqi_data.aqi}
            - PM2.5: {aqi_data.pm25} μg/m³
            - PM10: {aqi_data.pm10} μg/m³
            - O3: {aqi_data.o3} ppb
            - NO2: {aqi_data.no2} ppb
            - SO2: {aqi_data.so2} ppb
            - CO: {aqi_data.co} ppm
            
            Calculate and provide:
            1. Excess mortality risk percentage based on PM2.5 levels
            2. Respiratory health impact score (0-100)
            3. Cardiovascular risk multiplier
            4. Safe exposure time in hours for healthy adults
            5. Recommended indoor air purifier CADR rating needed
            6. WHO guideline comparisons
            
            Use established epidemiological relationships and WHO guidelines for your calculations.
            Provide specific numerical estimates where possible.
            """
            
            calc_message = BaseMessage.make_user_message(
                role_name="User", 
                content=calculation_query
            )
            
            response = self.camel_agent.step(calc_message)
            return {"analysis": response.msg.content}
        except Exception as e:
            return {"analysis": f"Health metrics calculation unavailable: {str(e)}"}
    
    def generate_comprehensive_analysis(self, aqi_data: AQIData) -> str:
        """Generate comprehensive analysis using CAMEL AI"""
        try:
            # Calculate health metrics first
            health_metrics = self.calculate_health_metrics(aqi_data)
            
            # Comprehensive analysis query
            analysis_query = f"""
            Provide a comprehensive environmental health analysis for {aqi_data.location} based on this data:
            
            **Current Air Quality:**
            - AQI: {aqi_data.aqi} ({aqi_data.category})
            - Dominant Pollutant: {aqi_data.dominant_pollutant}
            - PM2.5: {aqi_data.pm25:.1f} μg/m³
            - PM10: {aqi_data.pm10:.1f} μg/m³
            - O3: {aqi_data.o3:.1f} ppb
            - NO2: {aqi_data.no2:.1f} ppb
            - SO2: {aqi_data.so2:.1f} ppb
            - CO: {aqi_data.co:.1f} ppm
            - Timestamp: {aqi_data.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
            
            **Health Risk Analysis:**
            {health_metrics['analysis']}
            
            Please provide a structured analysis with:
            1. **Immediate Health Impact Assessment**
            2. **Pollution Source Analysis** 
            3. **Specific Recommendations by Population Group**
            4. **Short-term and Long-term Mitigation Strategies**
            5. **Comparison with WHO Guidelines**
            
            Format your response with clear sections and actionable insights.
            Be specific and provide practical recommendations.
            """
            
            analysis_message = BaseMessage.make_user_message(
                role_name="User",
                content=analysis_query
            )
            
            response = self.camel_agent.step(analysis_message)
            return response.msg.content
        except Exception as e:
            return f"Comprehensive analysis unavailable: {str(e)}"

def create_enhanced_dashboard():
    """Create the enhanced Streamlit dashboard"""
    st.title("🌍 Enhanced AQI Monitoring System")
    st.markdown("### Real-time Air Quality Analysis powered by CAMEL AI")
    
    # Display toolkit status
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.success("🔍 AI Analysis Active")
    with col2:
        st.success("📊 Health Metrics Active") 
    with col3:
        st.success("📈 Trend Analysis Active")
    with col4:
        st.success("🤖 CAMEL AI Enhanced")
    
    # Initialize the monitoring system
    if 'enhanced_aqi_system' not in st.session_state:
        with st.spinner("🔄 Initializing CAMEL AI system..."):
            try:
                st.session_state.enhanced_aqi_system = EnhancedAQIMonitoringSystem()
            except Exception as e:
                st.error(f"Failed to initialize system: {str(e)}")
                return
    
    # Sidebar configuration
    st.sidebar.header("🔧 Configuration")
    
    # API Key inputs
    st.sidebar.subheader("Required API Keys")
    
    # WAQI API Key
    waqi_api_key = st.sidebar.text_input(
        "World Air Quality Index API Key *", 
        value=os.getenv('WAQI_API_KEY', ''),
        type="password",
        help="Required: Get your free API key from https://aqicn.org/api/"
    )
    
    # OpenAI API Key status
    openai_key_status = "✅ Configured" if os.getenv('OPENAI_API_KEY') else "❌ Required in .env"
    st.sidebar.text(f"OpenAI API Key: {openai_key_status}")
    
    if not waqi_api_key:
        st.sidebar.error("⚠️ WAQI API key is required for real-time data!")
        st.sidebar.markdown("""
        **Setup Instructions:**
        1. Visit https://aqicn.org/api/
        2. Sign up for free
        3. Get your token
        4. Enter it above or add to .env as `WAQI_API_KEY=your_token`
        """)
        return
    
    # Enhanced city selection with global coverage
    cities = [
        "beijing", "delhi", "london", "new-york", "tokyo", "mumbai", "los-angeles", 
        "paris", "shanghai", "bangkok", "singapore", "hong-kong", "sydney", 
        "melbourne", "toronto", "berlin", "madrid", "rome", "moscow", "seoul",
        "cairo", "mexico-city", "sao-paulo", "buenos-aires", "lagos", "jakarta",
        "karachi", "dhaka", "manila", "tehran", "istanbul", "bogota", "lima",
        "kiev", "warsaw", "prague", "vienna", "stockholm", "oslo", "helsinki"
    ]
    
    selected_cities = st.sidebar.multiselect(
        "Select Cities for Analysis",
        cities,
        default=["delhi", "beijing", "london", "new-york"],
        help="Select multiple cities for comparative analysis"
    )
    
    # Analysis options
    st.sidebar.subheader("Analysis Options")
    include_health_calculations = st.sidebar.checkbox("📊 Include Advanced Health Calculations", value=True)
    
    # Auto-refresh options
    auto_refresh_interval = st.sidebar.selectbox(
        "Auto-refresh Interval",
        ["Disabled", "5 minutes", "15 minutes", "30 minutes", "1 hour"],
        index=0
    )
    
    # Main analysis button
    if st.sidebar.button("🚀 Start Enhanced Analysis", type="primary"):
        if not selected_cities:
            st.warning("Please select at least one city for analysis.")
            return
        
        # Create enhanced tabs (removed "Data Export" tab)
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Real-time Status", 
            "🤖 AI Analysis", 
            "📈 Comparative Analysis", 
            "🏥 Health Assessment"
        ])
        
        # Fetch and analyze data
        aqi_data_list = []
        
        with st.spinner("🔄 Fetching real-time AQI data and performing AI analysis..."):
            progress_bar = st.progress(0)
            
            for i, city in enumerate(selected_cities):
                progress_bar.progress((i + 1) / len(selected_cities))
                
                data = st.session_state.enhanced_aqi_system.fetch_aqi_data(city, waqi_api_key)
                if data:
                    aqi_data_list.append(data)
                    st.success(f"✅ Data fetched and analyzed for {data.location}")
                else:
                    st.error(f"❌ Failed to fetch data for {city}")
            
            progress_bar.empty()
        
        if not aqi_data_list:
            st.error("❌ No data could be fetched. Please check your API key and city names.")
            return
        
        # Store data in session state
        st.session_state.current_enhanced_data = aqi_data_list
        
        # Tab 1: Real-time Status
        with tab1:
            st.header("📊 Real-time Air Quality Status")
            
            # Enhanced metrics display
            for data in aqi_data_list:
                with st.expander(f"🏙️ {data.location} - AQI {data.aqi} ({data.category})", expanded=True):
                    
                    # Create metrics columns
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("🎯 AQI Level", data.aqi, delta=data.category)
                        st.metric("🌫️ PM2.5", f"{data.pm25:.1f} μg/m³")
                    
                    with col2:
                        st.metric("💨 PM10", f"{data.pm10:.1f} μg/m³")
                        st.metric("☀️ Ozone", f"{data.o3:.1f} ppb")
                    
                    with col3:
                        st.metric("🚗 NO2", f"{data.no2:.1f} ppb")
                        st.metric("🏭 SO2", f"{data.so2:.1f} ppb")
                    
                    with col4:
                        st.metric("💨 CO", f"{data.co:.1f} ppm")
                        st.metric("⚠️ Dominant", data.dominant_pollutant)
                    
                    # Health concern alert
                    if data.aqi > 100:
                        st.error(f"🚨 Health Alert: {data.health_concern}")
                    elif data.aqi > 50:
                        st.warning(f"⚠️ Health Notice: {data.health_concern}")
                    else:
                        st.success(f"✅ Health Status: {data.health_concern}")
        
        # Tab 2: AI Analysis (removed buttons)
        with tab2:
            st.header("🤖 Advanced AI Analysis")
            
            for data in aqi_data_list:
                with st.expander(f"🔬 Comprehensive Analysis: {data.location}", expanded=True):
                    with st.spinner(f"🧠 Generating comprehensive analysis for {data.location}..."):
                        
                        # Generate comprehensive analysis
                        analysis = st.session_state.enhanced_aqi_system.generate_comprehensive_analysis(data)
                        
                        # Display analysis
                        st.markdown(analysis)
        
        # Tab 3: Comparative Analysis
        with tab3:
            st.header("📈 Multi-City Comparative Analysis")
            
            if len(aqi_data_list) > 1:
                # Create comparison dataframe
                comparison_df = pd.DataFrame([
                    {
                        'City': data.location,
                        'AQI': data.aqi,
                        'Category': data.category,
                        'PM2.5': data.pm25,
                        'PM10': data.pm10,
                        'O3': data.o3,
                        'NO2': data.no2,
                        'SO2': data.so2,
                        'CO': data.co,
                        'Dominant_Pollutant': data.dominant_pollutant
                    } for data in aqi_data_list
                ])
                
                # Multi-city AQI comparison
                fig1 = px.bar(
                    comparison_df,
                    x='City',
                    y='AQI',
                    color='AQI',
                    color_continuous_scale=['green', 'yellow', 'orange', 'red', 'purple', 'maroon'],
                    title="🏆 Multi-City AQI Comparison",
                    text='Category'
                )
                fig1.update_traces(textposition='outside')
                fig1.add_hline(y=50, line_dash="dash", line_color="green", annotation_text="Good")
                fig1.add_hline(y=100, line_dash="dash", line_color="yellow", annotation_text="Moderate")
                fig1.add_hline(y=150, line_dash="dash", line_color="orange", annotation_text="Unhealthy for Sensitive")
                st.plotly_chart(fig1, use_container_width=True)
                
                # Pollutant radar chart
                pollutant_cols = ['PM2.5', 'PM10', 'O3', 'NO2', 'SO2', 'CO']
                
                fig2 = go.Figure()
                
                for _, row in comparison_df.iterrows():
                    fig2.add_trace(go.Scatterpolar(
                        r=[row[col] for col in pollutant_cols],
                        theta=pollutant_cols,
                        fill='toself',
                        name=row['City']
                    ))
                
                fig2.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True)
                    ),
                    title="🌐 Multi-Pollutant Comparison Radar Chart"
                )
                st.plotly_chart(fig2, use_container_width=True)
                
                # Dominant pollutant distribution
                fig3 = px.pie(
                    comparison_df,
                    names='Dominant_Pollutant',
                    title="🎯 Dominant Pollutant Distribution"
                )
                st.plotly_chart(fig3, use_container_width=True)
            
            else:
                st.info("Select multiple cities for comparative analysis.")
        
        # Tab 4: Health Assessment
        with tab4:
            st.header("🏥 Advanced Health Risk Assessment")
            
            for data in aqi_data_list:
                with st.expander(f"🩺 Health Assessment: {data.location}", expanded=True):
                    
                    # Health risk matrix
                    st.subheader("Risk Assessment Matrix")
                    
                    risk_data = {
                        'Population Group': [
                            'Children (0-12 years)',
                            'Teens (13-18 years)', 
                            'Healthy Adults (19-64 years)',
                            'Seniors (65+ years)',
                            'Pregnant Women',
                            'People with Asthma',
                            'People with Heart Disease',
                            'Outdoor Workers'
                        ],
                        'Risk Level': [],
                        'Recommended Actions': []
                    }
                    
                    # Calculate risk levels based on AQI
                    for group in risk_data['Population Group']:
                        if data.aqi <= 50:
                            risk_level = "Low"
                            action = "Normal activities"
                        elif data.aqi <= 100:
                            if group in ['Children (0-12 years)', 'Seniors (65+ years)', 'People with Asthma', 'People with Heart Disease']:
                                risk_level = "Moderate"
                                action = "Limit prolonged outdoor exertion"
                            else:
                                risk_level = "Low"
                                action = "Normal activities"
                        elif data.aqi <= 150:
                            if group in ['Children (0-12 years)', 'Seniors (65+ years)', 'People with Asthma', 'People with Heart Disease', 'Pregnant Women']:
                                risk_level = "High"
                                action = "Avoid outdoor activities"
                            else:
                                risk_level = "Moderate"
                                action = "Limit outdoor activities"
                        else:
                            risk_level = "Very High"
                            action = "Stay indoors, wear masks if must go out"
                        
                        risk_data['Risk Level'].append(risk_level)
                        risk_data['Recommended Actions'].append(action)
                    
                    risk_df = pd.DataFrame(risk_data)
                    
                    # Color-code the risk levels
                    def color_risk_level(val):
                        if val == 'Low':
                            return 'background-color: #d4edda; color: #155724'
                        elif val == 'Moderate':
                            return 'background-color: #fff3cd; color: #856404'
                        elif val == 'High':
                            return 'background-color: #f8d7da; color: #721c24'
                        else:
                            return 'background-color: #d1ecf1; color: #0c5460'
                    
                    styled_df = risk_df.style.applymap(color_risk_level, subset=['Risk Level'])
                    st.dataframe(styled_df, use_container_width=True)
                    
                    # Calculate and display health metrics
                    if include_health_calculations:
                        health_metrics = st.session_state.enhanced_aqi_system.calculate_health_metrics(data)
                        st.subheader("📊 Calculated Health Metrics")
                        st.markdown(health_metrics['analysis'])
        

# Health recommendations based on AQI
def show_health_recommendations():
    """Display health recommendations sidebar"""
    st.sidebar.header("🏥 Health Recommendations")
    
    aqi_ranges = {
        "Good (0-50)": {
            "color": "🟢",
            "advice": "Air quality is satisfactory. Enjoy outdoor activities!"
        },
        "Moderate (51-100)": {
            "color": "🟡", 
            "advice": "Acceptable for most people. Sensitive individuals should limit prolonged outdoor exertion."
        },
        "Unhealthy for Sensitive Groups (101-150)": {
            "color": "🟠",
            "advice": "Sensitive groups should reduce outdoor activities."
        },
        "Unhealthy (151-200)": {
            "color": "🔴",
            "advice": "Everyone should limit outdoor activities."
        },
        "Very Unhealthy (201-300)": {
            "color": "🟣",
            "advice": "Health alert: avoid outdoor activities."
        },
        "Hazardous (301+)": {
            "color": "⚫",
            "advice": "Emergency conditions: stay indoors!"
        }
    }
    
    for range_name, info in aqi_ranges.items():
        st.sidebar.markdown(f"{info['color']} **{range_name}**")
        st.sidebar.markdown(f"_{info['advice']}_")
        st.sidebar.markdown("---")

def show_app_info():
    """Display application information"""
    st.sidebar.header("ℹ️ About")
    st.sidebar.markdown("""
    **AQI Monitoring System** provides real-time air quality data with AI-powered analysis.
    
    **Features:**
    - 🌍 Real-time AQI data from WAQI
    - 🤖 AI-powered analysis with CAMEL
    - 📊 Interactive visualizations
    - 📈 Trend analysis
    - 🏥 Health recommendations
    - 📱 Mobile-friendly interface
    
    **Data Source:** World Air Quality Index Project
    
    **AI Engine:** CAMEL (Communicative Agents for Mind Exploration of Large Scale Language Model Society)
    """)

if __name__ == "__main__":
    # Show health recommendations
    show_health_recommendations()
    
    # Show app information
    show_app_info()
    
    # Create main dashboard
    create_enhanced_dashboard()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <h4>🌍 AQI Monitoring System</h4>
        <p><strong>Powered by CAMEL AI & Streamlit</strong></p>
        <p><em>Data source: World Air Quality Index Project</em></p>
        <p>Made with ❤️ for environmental awareness</p>
    </div>
    """, unsafe_allow_html=True)