---
name: set-one-way-departure-date
id: 19
description: "Select and confirm the departure date for a one-way flight search. Execution page: https://www.google.com/travel/flights"
start_index: 35
end_index: 44
url_start: "https://www.google.com/travel/flights?tfs=CBwQARoOagwIAxIIL20vMDV5d2dAAUgBcAGCAQsI____________AZgBAg&tfu=KgIIAw"
url_end: "https://www.google.com/travel/flights?tfs=CBwQARocagwIAxIIL20vMDV5d2dyDAgDEggvbS8wN2Rma0ABSAFwAYIBCwj___________8BmAEC&tfu=KgIIAw"
variables:
  departure_date:
    type: string
    default_value: "20 Jan 2026"
    description: "Departure date for the one-way flight (e.g., '20 Jan 2026')"
    action_index: 38
    arg_position: 1
source:
  log_file: "../../session_logs/session_20251230_184816/complete_browser_log.log"
  task_description: "Find a one-way flight from Prague to a city in Japan on Jan 20, 2026, which city in Japan is cheaper to go to, Tokyo or a certain city in Hokkaido?"
---
# Set One-Way Departure Date

Select and confirm the departure date for a one-way flight search. Execution page: https://www.google.com/travel/flights

## Usage

This skill is automatically invoked when the agent needs to perform this action.

## Variables

- **departure_date** (default: `20 Jan 2026`): Departure date for the one-way flight (e.g., '20 Jan 2026')

## Execution Context

- **Start URL**: https://www.google.com/travel/flights?tfs=CBwQARoOagwIAxIIL20vMDV5d2dAAUgBcAGCAQsI____________AZgBAg&tfu=KgIIAw
- **End URL**: https://www.google.com/travel/flights?tfs=CBwQARocagwIAxIIL20vMDV5d2dyDAgDEggvbS8wN2Rma0ABSAFwAYIBCwj___________8BmAEC&tfu=KgIIAw
