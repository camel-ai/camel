---
name: enter-destination-location
id: 18
description: "Enter and confirm the destination city for flight search. Execution page: https://www.google.com/travel/flights"
start_index: 25
end_index: 31
url_start: "https://www.google.com/travel/flights?tfs=CBwQARoOagwIAhIIL20vMDRqcGxAAUgBcAGCAQsI____________AZgBAg&tfu=KgIIAw"
url_end: "https://www.google.com/travel/flights?tfs=CBwQARoOagwIAxIIL20vMDV5d2dAAUgBcAGCAQsI____________AZgBAg&tfu=KgIIAw"
variables:
  destination_city:
    type: string
    default_value: "Tokyo"
    description: "Name of the destination city (e.g., 'Tokyo', 'Sapporo')"
    action_index: 28
    arg_position: 1
source:
  log_file: "../../session_logs/session_20251230_184816/complete_browser_log.log"
  task_description: "Find a one-way flight from Prague to a city in Japan on Jan 20, 2026, which city in Japan is cheaper to go to, Tokyo or a certain city in Hokkaido?"
---
# Enter Destination Location

Enter and confirm the destination city for flight search. Execution page: https://www.google.com/travel/flights

## Usage

This skill is automatically invoked when the agent needs to perform this action.

## Variables

- **destination_city** (default: `Tokyo`): Name of the destination city (e.g., 'Tokyo', 'Sapporo')

## Execution Context

- **Start URL**: https://www.google.com/travel/flights?tfs=CBwQARoOagwIAhIIL20vMDRqcGxAAUgBcAGCAQsI____________AZgBAg&tfu=KgIIAw
- **End URL**: https://www.google.com/travel/flights?tfs=CBwQARoOagwIAxIIL20vMDV5d2dAAUgBcAGCAQsI____________AZgBAg&tfu=KgIIAw
