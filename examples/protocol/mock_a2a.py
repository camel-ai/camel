import asyncio
import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.parse

class A2AMockHandler(BaseHTTPRequestHandler):
    """Mock A2A service handler"""
    
    def process_query(self, query):
        """
        Dynamically process user query and return answe
        """
        print(f"🧠 RAW QUERY >>> {query}")
        # Exchange rate table
        exchange_rates = {
            'usd_to_inr': 83.5,    # 1 USD = 83.5 INR
            'usd_to_eur': 0.92,    # 1 USD = 0.92 EUR
            'eur_to_usd': 1.1,     # 1 EUR = 1.1 USD
            'gbp_to_usd': 1.27,    # 1 GBP = 1.27 USD
        }

        # 1️⃣ Extract first numeric amount
        amount_match = re.search(r'(\d+(?:\.\d+)?)', query)
        if not amount_match:
            return "Have problem understanding the amount"

        amount = float(amount_match.group(1))

        # 2️⃣ Extract all currency codes in order of appearance
        currencies = re.findall(r'\b(USD|EUR|INR|GBP)\b', query, re.IGNORECASE)

        if len(currencies) < 2:
            return "Have problem understanding the currencies"

        source_currency = currencies[0].upper()
        target_currency = currencies[1].upper()

        # 3️⃣ Look up exchange rate
        rate_key = f'{source_currency.lower()}_to_{target_currency.lower()}'

        if rate_key not in exchange_rates:
            return "Currncy conversion not supported"

        result = amount * exchange_rates[rate_key]
        return f"{result:.2f}"

    
    def get_answer_from_request(self, request_data):
        """Extract question from JSON-RPC request and get answer"""
        print(f"📨 Received request_data: {request_data}")
        try:
            params = request_data.get("params", {})
            message = params.get("message", {})
            parts = message.get("parts", [])

            # Get the text from the last message
            if parts:
                
                task_text = parts[0].get("text", "")
                
                print(f"🎯 提取到的核心文本: {task_text}")
                
                answer = self.process_query(task_text)
                return answer
        except Exception as e:
            print(f"❌ Error processing request: {e}")
        
        return "No value find"  # Default answer
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/.well-known/agent-card.json":
            # Return a valid A2A agent card with all required fields
            agent_card = {
                "id": "mock-a2a-agent",
                "name": "Mock A2A Agent",
                "description": "A mock A2A agent for testing",
                "url": "http://localhost:10000",
                "version": "1.0.0",
                "capabilities": {
                    "textProcessing": True,
                    "messaging": True
                },
                "defaultInputModes": ["text"],
                "defaultOutputModes": ["text"],
                "skills": [
                    {
                        "id": "query",
                        "name": "Query",
                        "description": "Process a query",
                        "tags": ["text_processing"],
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            }
                        }
                    }
                ]
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(agent_card).encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_POST(self):
        """Handle POST requests - A2A uses JSON-RPC protocol !!!!!"""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            request_data = json.loads(body.decode())
        except:
            request_data = {}
        
        # Handle JSON-RPC requests
        if self.path == "/" or self.path == "/message/send":
            # Extract the JSON-RPC request ID
            request_id = request_data.get("id", "mock-response-123")
            
            # Dynamically get the answer
            answer = self.get_answer_from_request(request_data)
            
            # Properly formatted JSON-RPC response for A2A with Message as result
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "kind": "message",
                    "message_id": f"msg-{request_id}",
                    "role": "agent",
                    "context_id": "ctx-xyz",
                    "parts": [
                        {
                            "kind": "text",
                            "text": answer  # Dynamic answer
                        }
                    ]
                }
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def log_message(self, format, *args):
        print(format % args)

def run_server():
    """Run the mock A2A service"""
    server = HTTPServer(("localhost", 10000), A2AMockHandler)
    print("Mock A2A service running on http://localhost:10000")
    print("Agent card available at http://localhost:10000/.well-known/agent-card.json")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n Shutting down mock A2A service...")
        server.shutdown()

if __name__ == "__main__":
    run_server()