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
import asyncio
import pytest
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
import os

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.societies.workforce.workforce import Workforce
from camel.tasks.task import Task
from camel.types import ModelPlatformType, ModelType

# Import the mock A2A handler
sys.path.insert(0, os.path.dirname(__file__))
from mock_a2a import A2AMockHandler


class TestA2AProtocol:
    """Test suite for A2A protocol and mock service integration"""
    
    @pytest.fixture
    def mock_server(self):
        """Start mock A2A server for testing"""
        server = HTTPServer(("localhost", 10000), A2AMockHandler)
        server.allow_reuse_address = True
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        # Wait for server to start
        time.sleep(0.5)
        
        yield server
        
        # Cleanup
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)
    
    @pytest.mark.asyncio
    async def test_a2a_agent_card_endpoint(self, mock_server):
        """Test that mock A2A service returns valid agent card"""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:10000/.well-known/agent-card.json",
                timeout=5.0
            )
            
            assert response.status_code == 200
            agent_card = response.json()
            
            # Verify required fields
            assert agent_card["id"] == "mock-a2a-agent"
            assert agent_card["name"] == "Mock A2A Agent"
            assert agent_card["version"] == "1.0.0"
            assert "capabilities" in agent_card
            assert agent_card["capabilities"]["textProcessing"] is True
    
    @pytest.mark.asyncio
    async def test_a2a_currency_conversion_usd_to_eur(self, mock_server):
        """Test A2A protocol currency conversion: USD to EUR"""
        import httpx
        
        # Create JSON-RPC request
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "message.send",
            "params": {
                "message": {  # Dict
                    "parts": [  # list
                        {
                            "text": "how much is 10 USD in EUR?"
                        }
                    ]
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:10000/",
                json=request_data,
                timeout=5.0
            )
            
            assert response.status_code == 200
            result = response.json()
            
            # Verify JSON-RPC response structure
            assert result["jsonrpc"] == "2.0"
            assert result["id"] == "test-1"
            assert "result" in result
            
            # Verify the conversion result
            message_result = result["result"]
            assert message_result["kind"] == "message"
            assert message_result["role"] == "agent"
            
            answer = message_result["parts"][0]["text"]
            print(f"Conversion result: 10 USD = {answer} EUR")
            
            # Expected: 10 * 0.92 = 9.20 EUR
            assert answer == "9.20"
    

    
    @pytest.mark.asyncio
    async def test_a2a_workforce_integration(self, mock_server):
        """Test A2A protocol with Workforce integration"""
        base_url = "http://localhost:10000"
        http_kwargs = {
            "timeout": 30.0,
            "headers": {
                "User-Agent": "workforce-a2a-client/0.1",
            },
        }
        
        # Create Gemini model for coordinator and task agents
        gemini_model = ModelFactory.create(
            model_platform=ModelPlatformType.GEMINI,
            model_type=ModelType.GEMINI_2_5_FLASH,
        )
        
        # Create coordinator agent with Gemini
        coordinator_agent = ChatAgent(model=gemini_model)
        
        # Create task agent with Gemini
        task_agent = ChatAgent(model=gemini_model)
        
        # Create workforce with Gemini-based agents
        workforce = Workforce(
            "A2A Example Workforce",
            coordinator_agent=coordinator_agent,
            task_agent=task_agent,
        )
        await workforce.add_a2a_agent_worker(
            base_url=base_url,
            http_kwargs=http_kwargs,
        )
        
        # Execute task
        task1 = Task(content="convert from 10 USD to EUR")
        result1 = await workforce.process_task_async(task1)
        
        # Verify result exists
        assert result1 is not None
        assert result1.result is not None
        print(f"Workforce task result: {result1.result}")


# Legacy main function for manual testing
async def main():
    """Manual test runner - useful for development"""
    base_url = "http://localhost:10000"
    http_kwargs = {
        "timeout": 30.0,
        "headers": {
            "User-Agent": "workforce-a2a-client/0.1",
        },
    }

    # Create Gemini model for coordinator and task agents
    gemini_model = ModelFactory.create(
        model_platform=ModelPlatformType.GEMINI,
        model_type=ModelType.GEMINI_2_5_FLASH,
    )

    # Create coordinator agent with Gemini
    coordinator_agent = ChatAgent(model=gemini_model)

    # Create task agent with Gemini
    task_agent = ChatAgent(model=gemini_model)

    # Create workforce with Gemini-based agents
    workforce = Workforce(
        "A2A Example Workforce",
        coordinator_agent=coordinator_agent,
        task_agent=task_agent,
    )
    await workforce.add_a2a_agent_worker(
        base_url=base_url,
        http_kwargs=http_kwargs,
    )

    task1 = Task(content="how much is 10 USD in EUR?")
    result1 = await workforce.process_task_async(task1)
    print(f"Task 1 result: {result1.result}")


if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v", "-s"])
    
    # Or uncomment to run manually without pytest
    # asyncio.run(main())
