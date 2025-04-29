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

from camel.agents import ChatAgent
from camel.benchmarks import NexusBenchmark
from camel.benchmarks.nexus import construct_tool_descriptions

# Set up the agent to be benchmarked
agent = ChatAgent()

# Set up the Nexusraven Function Calling Benchmark
benchmark = NexusBenchmark(
    data_dir="NexusDatasets", save_to="NexusResults.jsonl"
)

# Download the benchmark data
benchmark.download()

# Set the task (sub-dataset) to be benchmarked
task = "OTX"

# Please note that the following step is only for demonstration purposes,
# it has been integrated into the run method of the benchmark.
# The tools fetched here are used to construct the prompt for the task,
# which will be passed to the agent for response.
tools = construct_tool_descriptions(task)
print('\nTool descriptions for the task:\n', tools)
'''
===============================================================================
"""
Function:
def getIndicatorForIPv6(apiKey: str, ip: str, section: str):
"""

    Retrieves comprehensive information for a specific IPv6 address from the 
    AlienVault database. 
    This function allows you to obtain various types of data. 
    The 'general' section provides general information about the IP, 
    including geo data, and a list of other available sections. 
    'reputation' offers OTX data on malicious activity observed by 
    AlienVault Labs. 'geo' details more verbose geographic data such 
    as country code and coordinates. 'malware' reveals malware samples 
    connected to the IP, 
    and 'urlList' shows URLs associated with the IP. Lastly, 'passiveDns' 
    includes passive DNS information about hostnames/domains 
    pointing to this IP.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - ip: string, required, IPv6 address to query
    - section: string, required, Specific data section to retrieve 
    (options: general, reputation, geo, malware, urlList, passiveDns)

"""
Function:
def getIndicatorForDomain(apiKey: str, domain: str, section: str):
"""

    Retrieves a comprehensive overview for a given domain name from the 
    AlienVault database. This function provides various data types 
    about the domain. The 'general' section includes general information 
    about the domain, such as geo data, and lists of other available 
    sections. 'geo' provides detailed geographic data including country 
    code and coordinates. The 'malware' section indicates malware samples 
    associated with the domain. 'urlList' shows URLs linked to the domain,
    'passiveDns' details passive DNS information about hostnames/domains
    associated with the domain, 
    and 'whois' gives Whois records for the domain.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - domain: string, required, Domain address to query
    - section: string, required, Specific data section to retrieve 
    (options: general, geo, malware, urlList, passiveDns, whois)

"""
Function:
def getIndicatorForHostname(apiKey: str, hostname: str, section: str):
"""

    Retrieves detailed information for a specific hostname from the 
    AlienVault database. This function provides various data types about 
    the hostname. The 'general' section includes general information 
    about the IP, geo data, and lists of other available sections. 
    'geo' provides detailed geographic data including country code 
    and coordinates. The 'malware' section indicates malware samples 
    associated with the hostname. 'urlList' shows URLs linked to 
    the hostname, and 'passiveDns' details passive DNS information 
    about hostnames/domains associated with the hostname.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - hostname: string, required, Single hostname address to query
    - section: string, required, Specific data section to retrieve 
    (options: general, geo, malware, urlList, passiveDns)

"""
Function:
def getIndicatorForFileHashes(apiKey: str, fileHash: str, section: str):
"""

    Retrieves information related to a specific file hash from the 
    AlienVault database. 
    This function provides two types of data: 'general', 
    which includes general metadata about the file hash and a list of other 
    available sections for the hash; and 'analysis', which encompasses both 
    dynamic and static analysis of the file, 
    including Cuckoo analysis, exiftool, etc.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - fileHash: string, required, Single file hash to query
    - section: string, required, Specific data section to retrieve 
    (options: general, analysis)

"""
Function:
def getIndicatorForUrl(apiKey: str, url: str, section: str):
"""

    Retrieves information related to a specific URL from the AlienVault 
    database. This function offers two types of data: 'general', 
    which includes historical geographic information, 
    any pulses this indicator is on, 
    and a list of other available sections for this URL; and 'url_list', 
    which provides full results from AlienVault Labs URL analysis, 
    potentially including multiple entries.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - url: string, required, Single URL to query
    - section: string, required, Specific data section to retrieve 
    (options: general, url_list)

"""
Function:
def getIndicatorForCVE(apiKey: str, cve: str, section: str):
"""

    Retrieves information related to a specific CVE 
    (Common Vulnerability Enumeration)
    from the AlienVault database. This function offers detailed data on CVEs.
    The 'General' section includes MITRE CVE data, such as CPEs 
    (Common Platform Enumerations), 
    CWEs (Common Weakness Enumerations), and other relevant details. 
    It also provides information on any pulses this indicator is on, 
    and lists other sections currently available for this CVE.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - cve: string, required, Specific CVE identifier to query 
        (e.g., 'CVE-2014-0160')
    - section: string, required, Specific data section to retrieve 
        ('general' only)

"""
Function:
def getIndicatorForNIDS(apiKey: str, nids: str, section: str):
"""

    Retrieves metadata information for a specific 
    Network Intrusion Detection System (NIDS) 
    indicator from the AlienVault database. This function is designed to 
    provide general metadata about NIDS indicators.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - nids: string, required, Specific NIDS indicator to query 
        (e.g., '2820184')
    - section: string, required, Specific data section to retrieve 
        ('general' only)

"""
Function:
def getIndicatorForCorrelationRules(apiKey: str, correlationRule: str,
 section: str):
"""

    Retrieves metadata information related to a specific Correlation Rule from
    the AlienVault database. This function is designed to provide 
    general metadata about 
    Correlation Rules used in network security and event correlation. 
    Correlation Rules are crucial for identifying patterns and potential 
    security threats in network data.

    Args:
    - apiKey: string, required, Your AlienVault API key
    - correlationRule: string, required, Specific Correlation Rule 
    identifier to query (e.g., '572f8c3c540c6f0161677877')
    - section: string, required, Specific data section to retrieve 
    ('general' only)

"""
===============================================================================
'''

# Run the benchmark
result = benchmark.run(agent, task, subset=10)
print("Total:", result["total"])
print("Correct:", result["correct"])
'''
===============================================================================
Total: 10
Correct: 9
===============================================================================
'''
