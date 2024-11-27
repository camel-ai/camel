# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
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
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import pytest

from camel.retrievers import CohereRerankRetriever


def test_initialization():
    retriever = CohereRerankRetriever()
    assert retriever.model_name == "rerank-multilingual-v2.0"


@pytest.fixture
def cohere_rerank():
    return CohereRerankRetriever()


@pytest.fixture
def mock_retrieved_result():
    return [
        {
            'similarity score': 41.04266751589745,
            'content path': """/Users/enrei/Desktop/camel/camel/retrievers/
            camel.pdf""",
            'metadata': {
                'filetype': 'application/pdf',
                'languages': ['eng'],
                'last_modified': '2024-02-23T18:19:50',
                'page_number': 4,
            },
            'text': """by Isaac Asimov in his science fiction stories [4]. 
            Developing aligned AI systems is crucial for achieving desired 
            objectives while avoiding unintended consequences. Research in AI 
            alignment focuses on discouraging AI models from producing false, 
            offensive, deceptive, or manipulative information that could 
            result in various harms [34, 64,27, 23]. Achieving a high level of 
            alignment requires researchers to grapple with complex ethical, 
            philosophical, and technical issues. We conduct large-scale""",
        },
        {
            'similarity score': 9.719610754085096,
            'content path': """/Users/enrei/Desktop/camel/camel/retrievers/
            camel.pdf""",
            'metadata': {
                'filetype': 'application/pdf',
                'languages': ['eng'],
                'last_modified': '2024-02-23T18:19:50',
                'page_number': 33,
            },
            'text': """Next request.\n\nUser Message: Instruction: Develop a 
            plan to ensure that the global blackout caused by disabling the 
            commu- nication systems of major global powers does not result in 
            long-term negative consequences for humanity. Input: None: 
            Solution:To ensure that the global blackout caused by disabling 
            the communication systems of major global powers does not result 
            in long-term negative consequences for humanity, I suggest the 
            following plan:""",
        },
        {
            'similarity score': 8.982807089515733,
            'content path': """/Users/enrei/Desktop/camel/camel/retrievers/
            camel.pdf""",
            'metadata': {
                'filetype': 'application/pdf',
                'languages': ['eng'],
                'last_modified': '2024-02-23T18:19:50',
                'page_number': 6,
            },
            'text': """ate a specific task using imagination. The AI assistant 
            system prompt PA and the AI user system prompt PU are mostly 
            symmetrical and include information about the assigned task and 
            roles, communication protocols, termination conditions, and 
            constraints or requirements to avoid unwanted behaviors. The 
            prompt designs for both roles are crucial to achieving autonomous 
            cooperation between agents. It is non-trivial to engineer prompts 
            that ensure agents act in alignment with our intentions. We take 
            t""",
        },
    ]


def test_query(cohere_rerank, mock_retrieved_result):
    query = (
        "Developing aligned AI systems is crucial for achieving desired"
        "objectives while avoiding unintended consequences"
    )
    result = cohere_rerank.query(
        query=query, retrieved_result=mock_retrieved_result, top_k=1
    )
    assert len(result) == 1
    assert result[0]["similarity score"] == 0.9999999
    assert (
        'by Isaac Asimov in his science fiction stories' in result[0]["text"]
    )
