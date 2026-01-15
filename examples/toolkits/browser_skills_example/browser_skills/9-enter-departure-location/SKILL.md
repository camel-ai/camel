---
name: enter-departure-location
id: 9
description: "Enter and confirm the departure city for flight search. Execution page: https://www.google.com/travel/flights"
start_index: 5
end_index: 11
url_start: "https://www.google.com/travel/flights"
url_end: "https://www.google.com/travel/flights"
variables:
  departure_city:
    type: string
    default_value: "Edinburgh"
    description: "Name of the departure city (e.g., 'Edinburgh')"
    action_index: 9
    arg_position: 1
source:
  log_file: "../../session_logs/session_20251230_142623/complete_browser_log.log"
  task_description: "Book a journey with return option on same day from Edinburg to Manchester on January 28th, 2026 and show me the lowest price option available."
---
# Enter Departure Location

Enter and confirm the departure city for flight search. Execution page: https://www.google.com/travel/flights

## Usage

This skill is automatically invoked when the agent needs to perform this action.

## Variables

- **departure_city** (default: `Edinburgh`): Name of the departure city (e.g., 'Edinburgh')

## Execution Context

- **Start URL**: https://www.google.com/travel/flights
- **End URL**: https://www.google.com/travel/flights
