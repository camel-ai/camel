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

import os

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import OpenAIAgentToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = """You are a helpful AI assistant that can use OpenAI's agent tools 
including web search and file search."""

# Set model config
model_config_dict = ChatGPTConfig(
    temperature=0.0,
).as_dict()

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=model_config_dict,
)

# Initialize toolkit and get tools
toolkit = OpenAIAgentToolkit(model=model)
tools = toolkit.get_tools()

# Set agent
agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)

# Example 1: Web Search
print("\n=== Using Web Search with Agent ===")
response = agent.step(
    "What was a positive news story from today? Use web search to find out."
)
print("Web Search Response:", response.msg.content)

# Example 2: Direct Web Search
print("\n=== Direct Web Search Usage ===")
web_result = toolkit.web_search(
    "What are the latest developments in renewable energy?"
)
print("Direct Web Search Result:", web_result)

# Example 3: File Search (if configured)
vector_store_id = os.getenv("OPENAI_VECTOR_STORE_ID")

if vector_store_id:
    print("\n=== Using File Search with Agent ===")
    response = agent.step(
        f"Search through my documents for information about climate change. "
        f"Use file search with vector store ID: {vector_store_id}"
    )
    print("File Search Response:", response.msg.content)

    print("\n=== Direct File Search Usage ===")
    file_result = toolkit.file_search(
        query="What are the key points about climate change?",
        vector_store_id=vector_store_id,
    )
    print("Direct File Search Result:", file_result)
else:
    print("\n=== File Search Examples Skipped ===")
    print("Set OPENAI_VECTOR_STORE_ID env var to run file search examples")


"""
=== Using Web Search with Agent ===
Web Search Response: Here are some uplifting news stories from today:

1. **Historic Marriage Milestone**: A Brazilian couple has set a new Guinness
World Record for the longest marriage of a living couple, celebrating 84 
years and 85 days together.

2. **Lottery Jackpot Win**: A Michigan man who consistently played the same 
lottery numbers for four years has won a $1.3 million jackpot in the state's 
Lotto 47 game.

3. **Miraculous Recovery**: A 23-year-old British woman, initially given only 
a 5% chance of survival after a life-threatening skiing accident, shared her 
inspiring story of recovery.

4. **Marathon for a Cause**: A Wisconsin doctor, who previously battled 
testicular cancer, ran seven marathons on seven continents—from 
Antarctica to North America—to raise awareness for the disease.

5. **Kindness in the Skies**: An airline passenger shared a story about 
a fellow flyer who offered $100 to switch their window seat for an aisle
seat, highlighting unexpected acts of kindness.

6. **Community Support**: A North Carolina mother is honoring the victims of 
an American Airlines flight that collided with an Army helicopter by 
supporting the skating community, demonstrating resilience and unity.

7. **Positive Outlook During Pandemic**: A study from Oregon State University 
confirms that individuals with positive and playful attitudes navigated the 
COVID-19 pandemic more effectively, underscoring the power of optimism.

8. **Random Act of Kindness**: An emergency room doctor and father of three in 
Fort Worth, Texas, was touched when a stranger left a heartfelt note and paid 
his family's breakfast bill at a local café.

9. **Mountain Rescue**: Two experienced hikers were rescued from the tallest 
mountain in the Northeast after a whiteout snowstorm stranded them at about 
5,000 feet, showcasing the dedication of rescue teams.

10. **Pilot's Reassurance**: An American Airlines pilot went viral after 
assuring passengers that he has "no higher calling" than "carefully" 
transporting them to their destination, following a recent tragic 
crash in D.C.

These stories highlight the resilience, kindness, and positive spirit 
present in our communities.

=== Direct Web Search Usage ===
Direct Web Search Result: Recent developments in renewable energy have marked 
significant progress across various sectors:

**Record Growth in Renewable Energy Capacity**

In 2023, the global renewable energy sector experienced unprecedented growth, 
adding 473 gigawatts (GW) new capacity—a 54% increase from the previous year. 
This surge was predominantly driven by solar photovoltaic and onshore wind 
installations, which together accounted for over 95% of the new capacity. 
Notably, solar PV alone contributed 346 GW, reflecting a 73% year-on-year 
increase. China played a pivotal role in this expansion, leading in solar PV, 
onshore wind, offshore wind, and hydropower installations. This dominance has 
contributed to a decline in the global weighted average cost of electricity 
(LCOE) for these technologies, making renewable power generation increasingly 
competitive. ([greenearth.news](https://greenearth.news/record-growth-in-
renewable-energy-473-gw-added-in-2023-marks-a-turning-point-in-global-power-
transition-report/?utm_source=openai))

**Advancements in Energy Storage Technologies**

The integration of renewable energy sources has been bolstered by significant 
advancements in energy storage solutions. In 2023, battery storage capacity 
expanded dramatically, with 95.9 GWh added, up from just 0.1 GWh in 2010. This 
growth has been accompanied by substantial reduction in costs, with price of 
battery storage projects decreasing by 89% between 2010 and 2023. These 
developments enhance reliability and scalability of renewable energy systems, 
addressing the intermittent nature of sources like wind and solar. 
([greenearth.news](https://greenearth.news/record-growth-in-renewable-energy-
473-gw-added-in-2023-marks-a-turning-point-in-global-power-transition-report/?
utm_source=openai))

**Innovations in Renewable Energy Technologies**

The renewable energy sector has witnessed several technological breakthroughs:

- **Solar Power**: The introduction of high-efficiency solar panels utilizing 
materials such as perovskite and gallium arsenide has significantly increased 
energy conversion rates. Additionally, building-integrated photovoltaics
are enabling the seamless integration of solar technology into architectural 
designs, transforming buildings into self-sustaining power generators. 
([toxigon.com](https://toxigon.com/renewable-energy-technologies-2023?
utm_source=openai))

- **Wind Energy**: Advancements in wind turbine technology, including the 
deployment of larger and more efficient turbines, have enhanced energy capture 
Offshore wind farms, particularly those utilizing floating wind turbines, are 
expanding the potential for wind power generation in deeper waters previously 
inaccessible to traditional fixed-bottom turbines. ([toxigon.com]
(https://toxigon.com/renewable-energy-technologies-2023?utm_source=openai))

- **Energy Storage**: Innovations in battery technology, such as development 
of advanced lithium-ion, solid-state batteries, have improved energy density, 
charging times, and safety features. These advancements facilitate the 
integration of renewable energy into the power grid and support transition to 
a low-carbon economy. ([toxigon.com](https://toxigon.com/renewable-energy-
technologies-2023?utm_source=openai))

**Global Investment and Policy Support**

The clean energy transition is gaining momentum, with substantial investments 
and policy support driving the shift towards renewable energy:

- The International Energy Agency (IEA) projects that $2 trillion will be 
allocated to clean energy in 2024, with 85% of new power plants being 
renewable. 
([time.com](https://time.com/7022326/climate-leadership-forum-green-economy-
clean-energy-transition/?utm_source=openai))

- China's dominance in green technology manufacturing, including turbines, 
solar panels, electric vehicles, and lithium-ion batteries, positions it as a 
leader in the global renewable energy market. This leadership is expected to 
continue, with China projected to install 60% of world's renewable capacity 
between now and 2030. ([ft.com](https://www.ft.com/content/d3650b44-0313-44c9-
a7aa-495549b158b5?utm_source=openai))

These developments underscore the rapid advancements in renewable energy, 
driven by technological innovation, substantial investments, and supportive 
policies, collectively contributing to a more sustainable and resilient 
global energy landscape.


## Recent Developments in Renewable Energy:
- [Record renewables growth fuels cost competitiveness -IRENA report shows]
(https://www.reuters.com/business/energy/record-renewables-growth-fuels-cost-
competitiveness-irena-report-shows-2024-09-24/?utm_source=openai)
- [Cheap Solar Panels Are Changing the World](https://www.theatlantic.com/science/
archive/2024/10/solar-power-energy-revolution-global-south/680351/?
utm_source=openai)
- [China is winning the race for green supremacy](https://www.ft.com/content/
d3650b44-0313-44c9-a7aa-495549b158b5?utm_source=openai) 

=== Using File Search with Agent ===
File Search Response: It appears that there are no mentions of "climate 
change" in the documents you've uploaded. If you need info or insights on
that topic, please let me know how I can assist you further!

=== Direct File Search Usage ===
Direct File Search Result: It looks like there were no relevant results in the 
uploaded files regarding climate change. However, I can provide summary of key
points about climate change:

1. **Definition**: Climate change refers to significant changes in global 
temperatures and weather patterns over time.

2. **Causes**:
- **Greenhouse Gas Emissions**: Increased levels of carbon dioxide (CO2), 
methane (CH4), and nitrous oxide (N2O) from human activities (e.g., burning 
fossil fuels, deforestation).
- **Natural Factors**: Volcanic eruptions, solar radiation variations, and 
natural greenhouse gas emissions.

3. **Impacts**:
- **Temperature Increases**: Global average temperatures have risen, leading 
to heatwaves and extreme weather.
- **Sea Level Rise**: Melting ice caps and glaciers contribute to rising sea 
levels, which can lead to coastal flooding.
- **Ecosystem Disruption**: Affects biodiversity, leading to habitat loss, 
changes in species distribution, and increased extinction rates.

4. **Social and Economic Consequences**:
- **Food and Water Security**: Impact on agricultural productivity and water 
availability.
- **Health Risks**: Increased prevalence of heat-related illnesses and spread 
of diseases.
- **Economic Costs**: Damage to infrastructure, increased disaster recovery 
costs, and shifts in market dynamics.

5. **Mitigation Strategies**:
- **Renewable Energy Sources**: Transition to solar, wind, and other renewable 
energy resources.
- **Energy Efficiency**: Improving energy use in buildings, transportation, 
and industry.
- **Conservation Practices**: Protecting forests, wetlands, and other 
ecosystems that sequester carbon.

6. **International Agreements**: Efforts like the Paris Agreement aim to unite 
countries to limit global warming to well below 2 degrees Celsius above pre-
industrial levels.

If you need more specific information or details from the files, 
feel free to ask!
"""
