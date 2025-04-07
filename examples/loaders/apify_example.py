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

from camel.loaders import Apify

apify = Apify()

run_input = {
    "startUrls": [{"url": "https://www.camel-ai.org/"}],
    "maxCrawlDepth": 0,
    "maxCrawlPages": 1,
}
actor_result = apify.run_actor(
    actor_id="apify/website-content-crawler", run_input=run_input
)

print(actor_result["status"])
'''
===============================================================================
SUCCEEDED
===============================================================================
'''

print(actor_result["defaultDatasetId"])
'''
===============================================================================
HoKb31FJzHm0ni51k
===============================================================================
'''

dataset_result = apify.get_dataset_items(
    dataset_id=actor_result["defaultDatasetId"]
)

print(dataset_result)
'''
===============================================================================
[{'url': 'https://www.camel-ai.org/', 'crawl': {'loadedUrl': 'https://www.camel
-ai.org/', 'loadedTime': '2024-10-27T04:51:16.651Z', 'referrerUrl': 'https://ww
w.camel-ai.org/', 'depth': 0, 'httpStatusCode': 200}, 'metadata': 
{'canonicalUrl': 'https://www.camel-ai.org/', 'title': 'CAMEL-AI', 
'description': 'CAMEL-AI.org is the 1st LLM multi-agent framework and an 
open-source community dedicated to finding the scaling law of agents.', 
'author': None, 'keywords': None, 'languageCode': 'en', 'openGraph':
[{'property': 'og:title', 'content': 'CAMEL-AI'}, {'property': 
'og:description', 'content': 'CAMEL-AI.org is the 1st LLM multi-agent 
framework and an open-source community dedicated to finding the scaling law of 
agents.'}, {'property': 'twitter:title', 'content': 'CAMEL-AI'}, {'property': 
'twitter:description', 'content': 'CAMEL-AI.org is the 1st LLM multi-agent 
framework and an open-source community dedicated to finding the scaling law of 
agents.'}, {'property': 'og:type', 'content': 'website'}], 'jsonLd': None, 
'headers': {'date': 'Sun, 27 Oct 2024 04:50:18 GMT', 'content-type': 'text/
html', 'cf-ray': '8d901082dae7efbe-PDX', 'cf-cache-status': 'HIT', 'age': '10
 81', 'content-encoding': 'gzip', 'last-modified': 'Sat, 26 Oct 2024 11:51:32 G
 MT', 'strict-transport-security': 'max-age=31536000', 'surrogate-control': 'ma
 x-age=432000', 'surrogate-key': 'www.camel-ai.org 6659a154491a54a40551bc78 pag
 eId:6686a2bcb7ece5fb40457491 668181a0a818ade34e653b24 6659a155491a54a40551bd7e
 ', 'x-lambda-id': 'd6c4424b-ac67-4c54-b52a-cb2a22ca09f0', 'vary': 'Accept-Enco
 ding', 'set-cookie': '__cf_bm=oX5EmZ2SNJDOBQXI8dL_reCYlCpp1FMzu40qCNxiopU-1730
 004618-1.0.1.1-3teEeqUoemzHWAeGCtlPJVqdmAbiFkyu3JxopKfQFFndSCi_Z56RR.UDjLGZiq.
 L_4LvAZYmNKxQ.k6VRhbA7g; path=/; expires=Sun, 27-Oct-24 05:20:18 GMT; domain=.
 cdn.webflow.com; HttpOnly; Secure; SameSite=None\n_cfuvid=om_8lj9jNMIh.HEIxEAq
 gszhEWaKlyS2kdXKwqGedSM-1730004618924-0.0.1.1-604800000; path=/; domain=.cdn.w
 ebflow.com; HttpOnly; Secure; SameSite=None', 'alt-svc': 'h3=":443"; ma=86400'
 , 'x-cluster-name': 'us-west-2-prod-hosting-red', 'x-firefox-spdy': 'h2'}}, 's
 creenshotUrl': None, 'text': 'Build Multi-Agent Systems for _\nFEATURES & Inte
 grations\nSeamless integrations with\npopular platforms \nScroll to explore ou
 r features & integrations.', 'markdown': '# Build Multi-Agent Systems for \\_
 \n\nFEATURES & Integrations\n\n## Seamless integrations with  \npopular platfo
 rms\n\nScroll to explore our features & integrations.'}]
===============================================================================
'''
