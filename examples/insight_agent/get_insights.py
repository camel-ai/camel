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
import json

from colorama import Fore

from camel.agents.insight_agent import InsightAgent
from camel.configs import ChatGPTConfig


def main(model_type=None) -> None:
    context_text = """**The Production Environment of the Acme Program System**
The Acme Program System, henceforth referred to as APS, is hosted in a state-of-the-art production environment, which has been meticulously designed to ensure optimal performance, security, and reliability.
**Infrastructure Setup**:
1. **Data Centers:** APS is hosted across multiple geographically dispersed data centers. These data centers are strategically located in North America, Europe, and Asia to ensure seamless global access and provide redundancy. Each data center is equipped with advanced cooling systems, redundant power sources, and high-speed network connections to facilitate uninterrupted service.
2. **Servers:** Within each data center, APS employs a cluster of high-performance servers. These servers run on the latest Intel Xeon processors, equipped with DDR5 RAM and NVMe SSDs, ensuring speedy processing and data retrieval. They also employ RAID configurations to safeguard against potential data loss.
3. **Networking:** Our production environment utilizes top-tier networking equipment with multi-gigabit connections, guaranteeing rapid data transmission. We also employ redundant ISPs, ensuring that a failure with one provider doesn't lead to system downtime.
**Software Configuration**:
1. **Operating System:** APS runs on Linux Ubuntu 20.04 LTS. We chose Ubuntu due to its stability, vast community support, and frequent security patches.
2. **Database:** The system leverages PostgreSQL 12 as its primary relational database management system. Known for its ACID compliance and extensibility, PostgreSQL ensures data integrity and allows for complex queries, which are vital for APS's operations.
3. **Backend Framework:** The core of APS is built using the Python Django framework, which offers a robust set of tools for web development and ensures secure, scalable, and maintainable code.
4. **Load Balancers:** To distribute incoming traffic and prevent any single server from being a bottleneck, we employ Nginx as our load balancer. It not only ensures smooth user experience during traffic surges but also provides additional layers of security.
**Security Measures**:
1. **Firewalls:** All entry and exit points in our production environment are safeguarded by sophisticated firewall systems, preventing unauthorized access and potential attacks.
2. **Data Encryption:** At rest or in transit, all data within APS is encrypted using advanced encryption standards (AES-256), ensuring data confidentiality.
3. **Regular Audits:** The APS production environment undergoes periodic security audits by third-party agencies, ensuring adherence to the latest security standards and best practices.
**Maintenance & Monitoring**:
1. **Backup & Recovery:** Regular backups of all data are taken and stored in geographically distinct locations. This ensures quick recovery in the unfortunate event of data loss or system failures.
2. **Monitoring Tools:** We use a combination of Grafana, Prometheus, and ELK Stack (Elasticsearch, Logstash, Kibana) to monitor server health, application performance, and log analytics, providing real-time insights and facilitating rapid issue resolution.
3. **Continuous Deployment:** Employing Jenkins and Docker, APS follows a CI/CD approach, enabling seamless code integration, testing, and deployment, ensuring that the latest features and patches reach our users without causing system downtimes.
"""  # noqa: E501

    insights_instruction = (
        "The CONTEXT TEXT is related to code implementation. " +
        "Pay attention to the code structure code environment.")

    model_config_description = ChatGPTConfig()
    insight_agent = InsightAgent(model=model_type,
                                 model_config=model_config_description)

    insights_json = insight_agent.run(
        context_text=context_text, insights_instruction=insights_instruction)
    print(Fore.GREEN + f"Insights from the context text:\n"
          f"{json.dumps(insights_json, indent=4)}")


if __name__ == "__main__":
    main()
