---
name: set-round-trip-dates
id: 11
description: "Enter and confirm both departure and return dates for round-trip flight search. Execution page: https://www.google.com/travel/flights"
start_index: 19
end_index: 29
url_start: "https://www.google.com/travel/flights?tfs=CBwQARoOagwIAxIIL20vMDJtNzcaDnIMCAMSCC9tLzAybTc3QAFIAXABggELCP___________wGYAQE&tfu=KgIIAw"
url_end: "https://www.google.com/travel/flights?tfs=CBwQARooEgoyMDI2LTAxLTI4agwIAxIIL20vMDJtNzdyDAgDEggvbS8wNTJidxooEgoyMDI2LTAxLTI4agwIAxIIL20vMDUyYndyDAgDEggvbS8wMm03N0ABSAFwAYIBCwj___________8BmAEB&tfu=KgIIAw"
variables:
  departure_date:
    type: string
    default_value: "28 Jan 2026"
    description: "Date of departure (e.g., '28 Jan 2026')"
    action_index: 21
    arg_position: 1
  return_date:
    type: string
    default_value: "28 Jan 2026"
    description: "Date of return (e.g., '28 Jan 2026')"
    action_index: 23
    arg_position: 1
source:
  log_file: "../../session_logs/session_20251230_142623/complete_browser_log.log"
  task_description: "Book a journey with return option on same day from Edinburg to Manchester on January 28th, 2026 and show me the lowest price option available."
---
# Set Round-Trip Dates

Enter and confirm both departure and return dates for round-trip flight search. Execution page: https://www.google.com/travel/flights

## Variables

- **departure_date** (default: `28 Jan 2026`): Date of departure (e.g., '28 Jan 2026')
- **return_date** (default: `28 Jan 2026`): Date of return (e.g., '28 Jan 2026')

## Execution Context

- **Start URL**: https://www.google.com/travel/flights?tfs=CBwQARoOagwIAxIIL20vMDJtNzcaDnIMCAMSCC9tLzAybTc3QAFIAXABggELCP___________wGYAQE&tfu=KgIIAw
- **End URL**: https://www.google.com/travel/flights?tfs=CBwQARooEgoyMDI2LTAxLTI4agwIAxIIL20vMDJtNzdyDAgDEggvbS8wNTJidxooEgoyMDI2LTAxLTI4agwIAxIIL20vMDUyYndyDAgDEggvbS8wMm03N0ABSAFwAYIBCwj___________8BmAEB&tfu=KgIIAw
