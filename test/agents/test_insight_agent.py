# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import pytest
from mock import patch

from camel.agents import ChatAgent
from camel.agents.insight_agent import InsightAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
from camel.types import ModelType, RoleType


@patch.object(ChatAgent, 'step')
@pytest.mark.parametrize("model_type", [None, ModelType.GPT_3_5_TURBO])
def test_insight_agent(mock_step, model_type):
    mock_content = generate_mock_content()
    mock_msg = BaseMessage(role_name="Insight Agent",
                           role_type=RoleType.ASSISTANT, meta_dict=None,
                           content=mock_content)

    # Mock the step function
    mock_step.return_value = ChatAgentResponse(msgs=[mock_msg],
                                               terminated=False, info={})

    context_text = """**The Production Environment of the Acme Program System**
The Acme Program System, henceforth referred to as APS, is hosted in a state-of-the-art production environment, which has been meticulously designed to ensure optimal performance, security, and reliability.

1. **Data Centers:**
    - APS is hosted across **5** multiple geographically dispersed data centers. These data centers are strategically located in North America, Europe, and Asia to ensure seamless global access and provide redundancy.
    - **Security:** Each data center is fortified with biometric access controls, **72** CCTV cameras, and intruder alarm systems. All entry and exit points in our production environment are safeguarded by sophisticated firewall systems, preventing unauthorized access and potential attacks.
    - **Environmental Control:** Advanced humidity and temperature control systems maintain a constant **22°C (71.6°F)** with a **45%** relative humidity level.
    - **Disaster Recovery:** Each location can withstand up to **7.5** magnitude earthquakes. Each data center is equipped with advanced cooling systems, redundant power sources, and high-speed network connections to facilitate uninterrupted service.
2. **Servers:**
    - Within each data center, APS employs a cluster of **150** high-performance servers. These servers run on the latest Intel Xeon processors, equipped with DDR5 RAM and NVMe SSDs, ensuring speedy processing and data retrieval.
    - **Virtualization:** Our servers utilize KVM-based hypervisors to run an average of **20** virtual machines each.
    - **Server Management:** Automated with tools like Ansible and Puppet, ensuring **98%** uniform server setups across the data centers. They also employ RAID configurations to safeguard against potential data loss.
3. **Networking:**
    - Our production environment utilizes top-tier networking equipment with multi-gigabit connections, guaranteeing rapid data transmission. A **10 Gbps** dedicated VPN tunnel interconnects all the data centers.
    - **CDN:** APS's content reaches users through **3** leading CDNs, with over **200** edge locations worldwide. We also employ redundant ISPs, ensuring that a failure with one provider doesn't lead to system downtime.


1. **Operating System:**
    - APS runs on Linux Ubuntu 20.04 LTS. We chose Ubuntu due to its stability, vast community support, and frequent security patches. Custom kernel optimizations lead to a **15%** improvement in network I/O handling.
2. **Database:**
    - The system leverages PostgreSQL 12 as its primary relational database management system. Known for its ACID compliance and extensibility, PostgreSQL ensures data integrity and allows for complex queries, which are vital for APS's operations. The primary database and its **3** replicas ensure **99.999%** data availability.
    - **Database Caching:** **12 TB** of data is cached using Redis and Memcached.
3. **Backend Framework:**
    - The core of APS is built using the Python Django framework. RabbitMQ, which handles an average of **1 million** messages daily, is used as a middleware for asynchronous processing.
4. **Load Balancers:**
    - To distribute incoming traffic and prevent any single server from being a bottleneck, we employ Nginx as our load balancer. It not only ensures smooth user experience during traffic surges but also provides additional layers of security. Sticky sessions benefit **85%** of our active users, reducing login prompts.


1. **Intrusion Detection Systems (IDS):** Advanced IDS solutions monitor network traffic, detecting and blocking an average of **500** suspicious activities daily.
2. **Two-Factor Authentication (2FA):** Over **300** administrators access the system daily using 2FA.
3. **Regular Audits & Penetration Testing:** The APS production environment undergoes periodic security audits by third-party agencies, ensuring adherence to the latest security standards and best practices. **4** major vulnerabilities have been rectified in the past year through regular testing.
4. **Data Encryption:** At rest or in transit, all data within APS is encrypted using advanced encryption standards (AES-256), ensuring data confidentiality.


1. **Backup & Recovery:** Regular backups of all data are taken and stored in geographically distinct locations. This ensures quick recovery in the unfortunate event of data loss or system failures.
2. **Server Patching:** **120** servers are patched every month.
3. **Monitoring Tools:** We use a combination of Grafana, Prometheus, and ELK Stack (Elasticsearch, Logstash, Kibana) to monitor server health, application performance, and log analytics, providing real-time insights and facilitating rapid issue resolution.
4. **Error Tracking:** Tools like Sentry rectify an average of **50** application errors daily.
5. **Continuous Deployment:** Employing Jenkins and Docker, APS follows a CI/CD approach, enabling seamless code integration, testing, and deployment, ensuring that the latest features and patches reach our users without causing system downtimes. APS has maintained a **99.98%** uptime over the past year.


1. **Auto-scaling:** Depending on the load, APS infrastructure can dynamically scale up or down using cloud solutions like AWS EC2 and Kubernetes.
2. **Database Sharding:** To handle vast amounts of data, APS's database is sharded, distributing data across **5** shards.


1. **Web Performance:** APS scores an average of **92** on Google Lighthouse.
2. **Analytics:** APS integrates with Google Analytics and Matomo to track the behavior of over **2 million** unique monthly visitors."""  # noqa: E501

    insights_instruction = (
        "The INSIGHT will be used as retrieve index in database.")

    model_config_description = ChatGPTConfig()

    # Construct insight agent
    insight_agent = InsightAgent(model_type=model_type,
                                 model_config=model_config_description)

    # Generate the insights dictionary based on the mock step function
    conditions_and_quality = \
        insight_agent.run(context_text=context_text,
                          insights_instruction=insights_instruction)

    expected_dict = generate_expected_content()

    assert conditions_and_quality == expected_dict


# Generate mock content for the insight agent
def generate_mock_content():
    return """You need to generate multiple insights, and the number of insights depend on the number of Topic/Functionality Segmentation. So the total number of insights is 6.
Insight 1:
- Topic Segmentation:
Data Centers
- Entity Recognition:
["APS", "5", "North America", "Europe", "Asia", "72", "22°C (71.6°F)", "45%", "7.5"]
- Extract Details:
APS is hosted across 5 multiple geographically dispersed data centers. These data centers are strategically located in North America, Europe, and Asia to ensure seamless global access and provide redundancy. Each data center is fortified with biometric access controls, 72 CCTV cameras, and intruder alarm systems. All entry and exit points in our production environment are safeguarded by sophisticated firewall systems, preventing unauthorized access and potential attacks. Advanced humidity and temperature control systems maintain a constant 22°C (71.6°F) with a 45% relative humidity level. Each location can withstand up to 7.5 magnitude earthquakes.
- Contextual Understanding:
N/A
- Formulate Questions:
1. What is the number of data centers hosting APS?
2. Where are the data centers located?
3. What security measures are implemented in the data centers?
4. What is the temperature and humidity level maintained in the data centers?
5. How much magnitude earthquake can each location withstand?
- Answer to "Formulate Questions" using CONTEXT TEXT:
1. APS is hosted across 5 data centers.
2. The data centers are located in North America, Europe, and Asia.
3. The data centers are fortified with biometric access controls, CCTV cameras, intruder alarm systems, and firewall systems.
4. The temperature is maintained at 22°C (71.6°F) with a relative humidity level of 45%.
5. Each location can withstand up to 7.5 magnitude earthquakes.
- Iterative Feedback:
N/A

Insight 2:
- Topic Segmentation:
Servers
- Entity Recognition:
["APS", "150", "Intel Xeon", "DDR5 RAM", "NVMe SSDs", "20"]
- Extract Details:
Within each data center, APS employs a cluster of 150 high-performance servers. These servers run on the latest Intel Xeon processors, equipped with DDR5 RAM and NVMe SSDs, ensuring speedy processing and data retrieval. Our servers utilize KVM-based hypervisors to run an average of 20 virtual machines each.
- Contextual Understanding:
N/A
- Formulate Questions:
1. How many servers are employed by APS?
2. What processors are used in the servers?
3. What type of RAM and storage are used in the servers?
4. How many virtual machines can each server run on average?
- Answer to "Formulate Questions" using CONTEXT TEXT:
1. APS employs 150 servers.
2. The servers use Intel Xeon processors.
3. The servers are equipped with DDR5 RAM and NVMe SSDs.
4. Each server can run an average of 20 virtual machines.
- Iterative Feedback:
N/A"""  # noqa: E501


# Generate expected dictionary of insights
def generate_expected_content():
    return {
        "insight 1": {
            "topic_segmentation":
            "Data Centers",
            "entity_recognition": [
                "\"APS\"", "\"5\"", "\"North America\"", "\"Europe\"",
                "\"Asia\"", "\"72\"", "\"22\u00b0C (71.6\u00b0F)\"", "\"45%\"",
                "\"7.5\""
            ],
            "extract_details":
            ("APS is hosted across 5 multiple geographically dispersed "
             "data centers. These data centers are strategically "
             "located in North America, Europe, and Asia to ensure "
             "seamless global access and provide redundancy. Each data "
             "center is fortified with biometric access controls, 72 "
             "CCTV cameras, and intruder alarm systems. All entry and "
             "exit points in our production environment are safeguarded "
             "by sophisticated firewall systems, preventing "
             "unauthorized access and potential attacks. Advanced "
             "humidity and temperature control systems maintain a "
             "constant 22\u00b0C (71.6\u00b0F) with a 45% relative "
             "humidity level. Each location can withstand up to 7.5 "
             "magnitude earthquakes."),
            "contextual_understanding":
            None,
            "formulate_questions":
            ("1. What is the number of data centers hosting APS?\n2. "
             "Where are the data centers located?\n3. What security "
             "measures are implemented in the data centers?\n4. What "
             "is the temperature and humidity level maintained in "
             "the data centers?\n5. How much magnitude earthquake can "
             "each location withstand?"),
            "answer_to_formulate_questions":
            ("1. APS is hosted across 5 data centers.\n2. The data "
             "centers are located in North America, Europe, and Asia.\n"
             "3. The data centers are fortified with biometric access "
             "controls, CCTV cameras, intruder alarm systems, and "
             "firewall systems.\n4. The temperature is maintained at "
             "22\u00b0C (71.6\u00b0F) with a relative humidity level "
             "of 45%.\n5. Each location can withstand up to 7.5 "
             "magnitude earthquakes."),
            "iterative_feedback":
            None
        },
        "insight 2": {
            "topic_segmentation":
            "Servers",
            "entity_recognition": [
                "\"APS\"", "\"150\"", "\"Intel Xeon\"", "\"DDR5 RAM\"",
                "\"NVMe SSDs\"", "\"20\""
            ],
            "extract_details":
            ("Within each data center, APS employs a cluster of 150 "
             "high-performance servers. These servers run on the "
             "latest Intel Xeon processors, equipped with DDR5 RAM and "
             "NVMe SSDs, ensuring speedy processing and data "
             "retrieval. Our servers utilize KVM-based hypervisors to "
             "run an average of 20 virtual machines each."),
            "contextual_understanding":
            None,
            "formulate_questions":
            ("1. How many servers are employed by APS?\n2. What "
             "processors are used in the servers?\n3. What type of RAM "
             "and storage are used in the servers?\n4. How many "
             "virtual machines can each server run on average?"),
            "answer_to_formulate_questions":
            ("1. APS employs 150 servers.\n2. The servers use Intel "
             "Xeon processors.\n3. The servers are equipped with DDR5 "
             "RAM and NVMe SSDs.\n4. Each server can run an average of "
             "20 virtual machines."),
            "iterative_feedback":
            None
        }
    }
