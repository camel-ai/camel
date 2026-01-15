---
name: enter-destination-location
id: 10
description: "Enter and confirm the destination city for flight search. Execution page: https://www.google.com/travel/flights"
start_index: 13
end_index: 17
url_start: "https://www.google.com/travel/flights"
url_end: "https://www.google.com/travel/flights?tfs=CBwQARoOagwIAxIIL20vMDJtNzcaDnIMCAMSCC9tLzAybTc3QAFIAXABggELCP___________wGYAQE&tfu=KgIIAw"
variables:
  destination_city:
    type: string
    default_value: "Manchester"
    description: "Name of the destination city (e.g., 'Manchester')"
    action_index: 15
    arg_position: 1
source:
  log_file: "../../session_logs/session_20251230_142623/complete_browser_log.log"
  task_description: "Book a journey with return option on same day from Edinburg to Manchester on January 28th, 2026 and show me the lowest price option available."
---
# Enter Destination Location

Enter and confirm the destination city for flight search. Execution page: https://www.google.com/travel/flights

## Usage

This skill is automatically invoked when the agent needs to perform this action.

## Variables

- **destination_city** (default: `Manchester`): Name of the destination city (e.g., 'Manchester')

## Execution Context

- **Start URL**: https://www.google.com/travel/flights
- **End URL**: https://www.google.com/travel/flights?tfs=CBwQARoOagwIAxIIL20vMDJtNzcaDnIMCAMSCC9tLzAybTc3QAFIAXABggELCP___________wGYAQE&tfu=KgIIAw
