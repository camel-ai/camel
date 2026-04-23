# Feature: Interactive Browser Instruction UI

## 1) Objective
Build an easy-to-use interactive UI for the browser-instruction workflow.

Today, log visualization is done by converting a log file to static HTML using:
`examples/toolkits/browser/browser_instruction/utils/browser_log_to_html.py`

The new UI should replace this static workflow with a live, interactive experience.

## 2) References
- Existing task runner example:
	`examples/toolkits/browser/browser_instruction/cli/run_simple_task.py`
- Existing log visualization logic:
	`examples/toolkits/browser/browser_instruction/utils/browser_log_to_html.py`
- Browser integration reference:
	`camel/toolkits/hybrid_browser_toolkit`

## 3) Required Features
You may use a lightweight framework such as Streamlit or vue.js.

1. Instruction input and task execution
- Provide an input area where users can enter a browser instruction.
- Start a session and run the existing browser-instruction agent flow (reuse backend logic; do not reimplement core execution).

1. Session log persistence and real-time visualization
- For each session, save logs to a session-specific folder/file structure.
- Show step-by-step log updates in real time while the session is running.
- For each step, display the screenshot referenced by `pre_capture_screenshot_path` when available.
- Reuse the parsing/formatting ideas from `browser_log_to_html.py`, but render directly in the UI.

1. Live Playwright browser view in UI
- Integrate the Playwright-driven browser so users can observe browser actions in real time from the UI.
- Follow existing behavior/patterns in `camel/toolkits/hybrid_browser_toolkit`.

## 4) In Scope
- UI for browser instruction execution.
- Real-time log and screenshot visualization.
- Real-time browser action visibility via Playwright integration.

## 5) Out of Scope
- Rewriting or replacing existing backend/browser-instruction business logic.
- Unrelated product features outside this browser-instruction UI.

## 6) Deliverables
- A runnable UI entry point under the browser_instruction example area.
- Clear start instructions (single command) in a short README note or doc section.
- Session artifacts saved per run (logs and referenced screenshots).

## 7) Acceptance Criteria
- User can enter an instruction and start a task from the UI.
- A new session is created, and logs are persisted.
- Logs update in real time in the UI while the task runs.
- Step screenshots (`pre_capture_screenshot_path`) are shown in the corresponding log steps.
- User can observe browser actions in real time through the integrated Playwright view.
- Existing backend logic remains unchanged except for minimal integration wiring needed by the UI.
