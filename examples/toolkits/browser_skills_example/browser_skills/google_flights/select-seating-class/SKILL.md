---
name: select-seating-class
id: 17
description: "Change the seating class for the flight search (e.g., Economy, Business, First). Execution page: https://www.google.com/travel/flights"
start_index: 49
end_index: 51
url_start: "https://www.google.com/travel/flights?tfs=CBwQARooEgoyMDI2LTAxLTE5agwIAxIIL20vMDdxenZyDAgDEggvbS8wN19wZhooEgoyMDI2LTAxLTI2agwIAxIIL20vMDdfcGZyDAgDEggvbS8wN3F6dkABSAFwAYIBCwj___________8BmAEB&tfu=KgIIAw"
url_end: "https://www.google.com/travel/flights?tfs=CBwQARooEgoyMDI2LTAxLTE5agwIAxIIL20vMDdxenZyDAgDEggvbS8wN19wZhooEgoyMDI2LTAxLTI2agwIAxIIL20vMDdfcGZyDAgDEggvbS8wN3F6dkABSARwAYIBCwj___________8BmAEB&tfu=KgIIAw"
variables:
  seating_class:
    type: string
    default_value: "First"
    description: "Desired seating class to select (e.g., 'First', 'Business', 'Economy')"
    action_index: 51
    arg_position: 0
source:
  log_file: "../../session_logs/session_20251230_175829/complete_browser_log.log"
  task_description: "Search for a flight on January 19, 2026 and return on January 26, 2026 from Tel Aviv to Venice and Select First Class."
---
# Select Seating Class

Change the seating class for the flight search (e.g., Economy, Business, First). Execution page: https://www.google.com/travel/flights

## Variables

- **seating_class** (default: `First`): Desired seating class to select (e.g., 'First', 'Business', 'Economy')

## Execution Context

- **Start URL**: https://www.google.com/travel/flights?tfs=CBwQARooEgoyMDI2LTAxLTE5agwIAxIIL20vMDdxenZyDAgDEggvbS8wN19wZhooEgoyMDI2LTAxLTI2agwIAxIIL20vMDdfcGZyDAgDEggvbS8wN3F6dkABSAFwAYIBCwj___________8BmAEB&tfu=KgIIAw
- **End URL**: https://www.google.com/travel/flights?tfs=CBwQARooEgoyMDI2LTAxLTE5agwIAxIIL20vMDdxenZyDAgDEggvbS8wN19wZhooEgoyMDI2LTAxLTI2agwIAxIIL20vMDdfcGZyDAgDEggvbS8wN3F6dkABSARwAYIBCwj___________8BmAEB&tfu=KgIIAw
