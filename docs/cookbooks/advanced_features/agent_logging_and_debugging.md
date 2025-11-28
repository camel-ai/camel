# HTML Log Viewer for Terminal Bench

This guide explains how to use the HTML log viewer to visualize and analyze agent-LLM interactions during Terminal Bench evaluations.

## Overview

The HTML log viewer provides an interactive way to view agent conversation histories. It consists of two components:

1. **PromptLogger**: Automatically logs all LLM prompts during task execution
2. **llm_log_to_html.py**: Converts log files to interactive HTML

## Features

- 🎨 **Interactive Visualization**: Collapsible sections for easy navigation
- 🔍 **Search Functionality**: Quickly find specific messages or content
- 📊 **Statistics Dashboard**: View total prompts, messages, and iterations
- 🎨 **Color-Coded Roles**: Different colors for system, user, assistant, and tool messages
- 📱 **Responsive Design**: Works on desktop and mobile devices

## Installation

No additional dependencies required! Both tools use Python standard library only.

## Usage

### Step 1: Enable Logging During Task Execution

The PromptLogger is integrated into the Terminal Bench runner. When you run a task, logs are automatically saved to:

```
output/<run_id>/<task_name>/sessions/session_logs/llm_prompts.log
```

### Step 2: Convert Log to HTML

After the task completes, convert the log file to HTML:

```bash
python llm_log_to_html.py <log_file_path> [output_file_path]
```

**Examples:**

```bash
# Auto-generate output filename
python llm_log_to_html.py sessions/session_logs/llm_prompts.log

# Specify custom output filename
python llm_log_to_html.py sessions/session_logs/llm_prompts.log my_analysis.html
```

The script will create an HTML file that you can open in any web browser.

### Step 3: View the HTML

Open the generated HTML file in your browser:

```bash
# macOS
open llm_prompts_viewer.html

# Linux
xdg-open llm_prompts_viewer.html

# Windows
start llm_prompts_viewer.html
```

## HTML Viewer Features

### Navigation

- **Click on prompt headers** to expand/collapse individual prompts
- **Click on message headers** to expand/collapse message content
- **Use the search box** to filter prompts by content
- **Use control buttons** to expand or collapse all sections at once

### Color Coding

Messages are color-coded by role:
- 🔵 **System** messages: Light blue background
- 💜 **User** messages: Light purple background
- 💚 **Assistant** messages: Light green background
- 🟠 **Tool** messages: Light orange background

### Statistics

The viewer displays real-time statistics:
- Total number of prompts logged
- Total number of messages across all prompts
- Maximum iteration number reached

## Log File Format

The log file uses a structured format:

```
================================================================================
PROMPT #1 - gpt-4 (iteration 0)
Timestamp: 2024-11-25T10:30:00.123456
================================================================================
[
  {
    "role": "system",
    "content": "You are a helpful assistant..."
  },
  {
    "role": "user",
    "content": "Hello!"
  }
]
================================================================================
```

## Integration Examples

### Example 1: Basic Integration

Here's how to integrate PromptLogger in your own code:

```python
from prompt_logger import PromptLogger

# Initialize logger
logger = PromptLogger("path/to/llm_prompts.log")

# Log prompts during execution
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Solve this task..."}
]
logger.log_prompt(messages, model_info="gpt-4", iteration=1)

# Get statistics
stats = logger.get_stats()
print(f"Logged {stats['total_prompts']} prompts to {stats['log_file']}")
```

### Example 2: Real-World Integration (Terminal Bench)

**See `run_tbench_task_example.py` for a complete, production-ready example.**

This example file demonstrates:

1. **Import PromptLogger** (line 35-36)
   ```python
   from prompt_logger import PromptLogger
   ```

2. **Initialize before agent creation** (line 105-107)
   ```python
   prompt_log_path = session_log_dir / "llm_prompts.log"
   prompt_logger = PromptLogger(str(prompt_log_path))
   print(f"✅ LLM prompts will be logged to: {prompt_log_path}")
   ```

3. **Monkey-patch ChatAgent** to capture all prompts automatically (line 109-173)
   ```python
   def patch_chat_agent_for_prompt_logging():
       from camel.agents.chat_agent import ChatAgent

       original_get_model_response = ChatAgent._get_model_response

       def logged_get_model_response(self, openai_messages, num_tokens,
                                     current_iteration=0, **kwargs):
           if prompt_logger:
               model_info = f"{self.model_backend.model_type}"
               prompt_logger.log_prompt(openai_messages,
                                       model_info=model_info,
                                       iteration=current_iteration)
           return original_get_model_response(self, openai_messages,
                                            num_tokens, current_iteration,
                                            **kwargs)

       ChatAgent._get_model_response = logged_get_model_response

   patch_chat_agent_for_prompt_logging()
   ```

4. **Use agent normally** - logging happens automatically (line 200+)
   ```python
   # All agent interactions are now automatically logged
   response = camel_agent.step(usr_msg)
   ```

5. **Display statistics and next steps** (line 280+)
   ```python
   stats = prompt_logger.get_stats()
   print(f"Total prompts logged: {stats['total_prompts']}")
   print(f"Convert to HTML: python llm_log_to_html.py {prompt_log_path}")
   ```

**Key Points:**
- ✅ **Zero code changes** to agent logic after patching
- ✅ **Automatic logging** for all LLM interactions
- ✅ **Works with sync and async** agent methods
- ✅ **Minimal performance overhead** (~20ms per log entry)

**This is just an example file showing the integration pattern.** Adapt it to your specific use case.

## Troubleshooting

### Issue: HTML file is very large

**Solution**: The HTML file includes all prompt data inline. For very long conversations, the file may be several MB. This is normal and browsers handle it well.

### Issue: Search is slow

**Solution**: Search is debounced by 300ms to improve performance. Wait a moment after typing for results to appear.

### Issue: Some messages appear truncated

**Solution**: Click on the message header to expand and see the full content. Preview text is limited to 100 characters.

## Best Practices

1. **Regular Conversion**: Convert logs to HTML after each task run for easier analysis
2. **Organized Storage**: Keep HTML files organized by task and run ID
3. **Browser Bookmarks**: Bookmark frequently accessed log viewers for quick access
4. **Search Usage**: Use search to quickly locate specific errors or tool calls
5. **Collapse Unnecessary Sections**: Keep only relevant prompts expanded for focused analysis

## Technical Details

### Performance

- Log writing: ~20ms per prompt (synchronous)
- HTML conversion: ~1-2 seconds for 100 prompts
- File size: ~5-10KB per prompt (depends on content length)

### Browser Compatibility

The HTML viewer works on all modern browsers:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

### Limitations

- No server required (static HTML file)
- All data embedded in HTML (no external dependencies)
- Search is client-side (works offline)

## Example Workflow

Here's a complete workflow example:

```bash
# 1. Run a Terminal Bench task
python run_tbench_task.py --task play-zork --run_id experiment_001

# 2. Wait for task completion

# 3. Convert the log to HTML
python llm_log_to_html.py output/experiment_001/play-zork/sessions/session_logs/llm_prompts.log

# 4. Open in browser
open output/experiment_001/play-zork/sessions/session_logs/llm_prompts_viewer.html

# 5. Analyze agent behavior, search for specific tool calls, etc.
```

## Additional Resources

- Terminal Bench Documentation: [Link to docs]
- CAMEL Framework: https://github.com/camel-ai/camel
- Report Issues: [Link to issues page]

## Contributing

Found a bug or have a feature request? Please open an issue on the CAMEL GitHub repository.

---

**Note**: This viewer is designed for debugging and analysis purposes. For production monitoring, consider using dedicated observability tools.
