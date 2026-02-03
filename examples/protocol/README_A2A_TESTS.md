# A2A Mock Service Tests

This directory contains test cases and utilities for testing the A2A (Agent-to-Agent) protocol integration with CAMEL-AI.

## Overview

The A2A protocol enables communication between different AI agents through a standardized JSON-RPC 2.0 interface. These tests verify the integration between CAMEL-AI's Workforce system and remote A2A agents.

## Components

### 1. `mock_a2a.py` - Mock A2A Service
A lightweight HTTP server that simulates an A2A agent for testing purposes.

**Features:**
- Runs on `http://localhost:10000`
- Implements A2A JSON-RPC 2.0 protocol
- Provides agent card metadata at `/.well-known/agent-card.json`
- Dynamically processes currency conversion queries
- Supports multiple currency pairs (USD↔INR, EUR↔USD, GBP↔USD)

**Usage:**
```bash
python mock_a2a.py
```

### 2. `test_a2a_mock.py` - Basic Connectivity Test
Tests the ability to connect to and interact with an A2A service.

**What it tests:**
- A2A service connectivity
- Agent card retrieval
- Basic agent metadata validation

**Usage:**
```bash
# Terminal 1: Start mock service
python mock_a2a.py

# Terminal 2: Run test
python test_a2a_mock.py

# run test a2a_protocol.py directly
or run a2a_ptrotocol.py 
```

**Expected Output:**
```
Connecting to A2A service at http://localhost:10000...
✓ Successfully connected to A2A service!
  Agent ID: ...
  Agent description: A mock A2A agent for testing
  Agent card: {...}
```

**Workflow:**
```
1. Create Gemini-based coordinator and task agents
2. Initialize Workforce with these agents
3. Register A2A Worker pointing to mock service
4. Submit task: "how much is 10 USD in INR"
5. Workforce routes task to A2A Worker
6. A2A Worker returns "835.00"
7. Result is aggregated and printed
```

### Cleanup
```bash
# Stop mock service
lsof -ti:10000 | xargs kill -9 2>/dev/null || true
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CAMEL-AI Workforce                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Coordinator Agent (Gemini)                            │   │
│  │  - Analyze tasks                                       │   │
│  │  - Route to appropriate workers                        │   │
│  └──────────────────┬──────────────────────────────────────┘   │
│                     │                                           │
│  ┌──────────────────▼──────────────────────────────────────┐   │
│  │  A2A Worker                                            │   │
│  │  - Communicates via JSON-RPC 2.0                       │   │
│  │  - Forwards tasks to remote agents                     │   │
│  │  - Aggregates results                                  │   │
│  └──────────────────┬──────────────────────────────────────┘   │
└─────────────────────┼──────────────────────────────────────────┘
                      │ HTTP/JSON-RPC
                      ▼
         ┌────────────────────────────┐
         │  Mock A2A Service          │
         │  (localhost:10000)         │
         │  - Agent Card              │
         │  - Message Processing      │
         │  - Dynamic Query Handling   │
         └────────────────────────────┘
```

## Token Usage

**Note:** The full integration test (`a2a_example.py`) uses Gemini API tokens for:
- Coordinator agent analysis (understanding tasks)
- Task agent verification (validating results)

To avoid token consumption, use the basic connectivity test (`test_a2a_mock.py`) or modify the example to use local models.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 10000 already in use | `lsof -ti:10000 \| xargs kill -9` |
| Connection refused | Ensure `mock_a2a.py` is running in another terminal |
| Validation errors | Check JSON-RPC response format matches schema |
| Token consumption | Use `test_a2a_mock.py` instead of `a2a_example.py` |

## Future Enhancements

- [ ] Support for more currency pairs
- [ ] Add error handling and retries
- [ ] Implement streaming message support
- [ ] Add authentication mechanisms
- [ ] Support for file uploads/downloads
- [ ] Performance benchmarking

