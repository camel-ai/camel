---
name: set-one-way-departure-date
id: 14
description: "Select and confirm the departure date for a one-way flight search. Execution page: https://www.google.com/travel/flights"
start_index: 35
end_index: 43
url_start: "https://www.google.com/travel/flights?tfs=CBwQARocagwIAxIIL20vMDFfZDRyDAgDEggvbS8wNXF0akABSAFwAYIBCwj___________8BmAEC&tfu=KgIIAw"
url_end: "https://www.google.com/travel/flights?tfs=CBwQARocagwIAxIIL20vMDFfZDRyDAgDEggvbS8wNXF0akABSAFwAYIBCwj___________8BmAEC&tfu=KgIIAw"
variables:
  departure_date:
    type: string
    default_value: "Saturday, January 17, 2026 , 303 British pounds"
    description: "Date of departure for one-way flight (e.g., 'January 17, 2026')"
    action_index: 40
    arg_position: 1
source:
  log_file: "../../session_logs/session_20251230_144040/complete_browser_log.log"
  task_description: "Show me the list of one-way flights on January 17, 2026 from Chicago to Paris."
---
# Set One-Way Departure Date

Select and confirm the departure date for a one-way flight search. Execution page: https://www.google.com/travel/flights

## Usage

This skill is automatically invoked when the agent needs to perform this action.

## Variables

- **departure_date** (default: `Saturday, January 17, 2026 , 303 British pounds`): Date of departure for one-way flight (e.g., 'January 17, 2026')

## Execution Context

- **Start URL**: https://www.google.com/travel/flights?tfs=CBwQARocagwIAxIIL20vMDFfZDRyDAgDEggvbS8wNXF0akABSAFwAYIBCwj___________8BmAEC&tfu=KgIIAw
- **End URL**: https://www.google.com/travel/flights?tfs=CBwQARocagwIAxIIL20vMDFfZDRyDAgDEggvbS8wNXF0akABSAFwAYIBCwj___________8BmAEC&tfu=KgIIAw
