#!/usr/bin/env python3
"""
LLM Prompts Log to HTML Converter

Converts LLM prompts log files into interactive HTML with collapsible sections.

Usage:
    python llm_log_to_html.py <log_file_path> [output_file_path]

Example:
    python llm_log_to_html.py /path/to/llm_prompts.log
    python llm_log_to_html.py /path/to/llm_prompts.log output.html
"""

import json
import re
import sys
from pathlib import Path
from html import escape
from typing import Any, Dict, List, Union


def parse_log_file(log_path: Path) -> List[Dict[str, Any]]:
    """Parse the LLM prompts log file and extract all prompts."""
    with open(log_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by prompt sections
    prompt_pattern = r'={80,}\nPROMPT #(\d+) - ([^\s]+) \(iteration (\d+)\)\nTimestamp: ([^\n]+)\n={80,}\n(.*?)(?=\n={80,}\n|\Z)'

    prompts = []
    matches = re.finditer(prompt_pattern, content, re.DOTALL)

    for match in matches:
        prompt_num = match.group(1)
        model = match.group(2)
        iteration = match.group(3)
        timestamp = match.group(4)
        json_content = match.group(5).strip()

        # Parse JSON content
        try:
            messages = json.loads(json_content)
            prompts.append({
                'number': prompt_num,
                'model': model,
                'iteration': iteration,
                'timestamp': timestamp,
                'messages': messages
            })
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON for prompt #{prompt_num}: {e}", file=sys.stderr)
            continue

    return prompts


def truncate_content(content: str, max_length: int = 500) -> str:
    """Truncate long content for preview."""
    if len(content) > max_length:
        return content[:max_length] + "..."
    return content


def format_message_content(content: Union[str, list, Any]) -> str:
    """Format message content with proper escaping and structure."""
    if isinstance(content, str):
        return escape(content)
    elif isinstance(content, list):
        # Handle structured content (tool calls, etc.)
        formatted = []
        for item in content:
            if isinstance(item, dict):
                formatted.append(json.dumps(item, indent=2))
            else:
                formatted.append(str(item))
        return escape('\n'.join(formatted))
    else:
        return escape(str(content))


def get_role_color(role: str) -> str:
    """Get color for different message roles."""
    colors = {
        'system': 'rgba(0, 240, 255, 0.1)',
        'user': 'rgba(255, 42, 109, 0.1)',
        'assistant': 'rgba(255, 208, 10, 0.1)',
        'tool': 'rgba(0, 240, 255, 0.15)',
    }
    return colors.get(role, 'rgba(255, 255, 255, 0.05)')


def get_role_icon(role: str) -> str:
    """Get emoji icon for different roles."""
    icons = {
        'system': '⚙️',
        'user': '👤',
        'assistant': '🤖',
        'tool': '🔧',
    }
    return icons.get(role, '📝')


def generate_html(prompts: List[Dict[str, Any]], output_path: Path) -> None:
    """Generate HTML file from parsed prompts."""

    # Load HTML template from file
    template_path = Path(__file__).parent / 'templates' / 'log_viewer.html'
    with open(template_path, 'r', encoding='utf-8') as f:
        html_template = f.read()

    # Generate prompts HTML
    prompts_html = []
    total_messages = 0
    max_iteration = 0

    for prompt in prompts:
        max_iteration = max(max_iteration, int(prompt['iteration']))
        messages_html = []

        for msg in prompt['messages']:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')

            # Get preview
            preview = truncate_content(str(content), 100)

            # Format content
            formatted_content = format_message_content(content)

            # Handle tool calls
            tool_calls_html = ''
            if 'tool_calls' in msg:
                tool_calls_html = f'<div class="tool-calls"><strong>Tool Calls:</strong><pre>{escape(json.dumps(msg["tool_calls"], indent=2))}</pre></div>'

            messages_html.append(f'''
                <div class="message">
                    <div class="message-header" onclick="toggleMessage(this)" style="background-color: {get_role_color(role)};">
                        <div class="message-role">
                            <span>{get_role_icon(role)}</span>
                            <strong>{role.upper()}</strong>
                            <span class="message-preview">{escape(preview)}</span>
                        </div>
                        <span class="message-toggle">▼</span>
                    </div>
                    <div class="message-body">
                        <div class="message-content">{formatted_content}</div>
                        {tool_calls_html}
                    </div>
                </div>
            ''')
            total_messages += 1

        prompts_html.append(f'''
            <div class="prompt-section">
                <div class="prompt-header" onclick="togglePrompt(this)">
                    <div>
                        <div class="prompt-title">Prompt #{prompt['number']} (Iteration {prompt['iteration']})</div>
                        <div class="prompt-meta">
                            <span>🤖 Model: {prompt['model']}</span>
                            <span>📅 {prompt['timestamp']}</span>
                            <span>💬 Messages: {len(prompt['messages'])}</span>
                        </div>
                    </div>
                    <span class="toggle-icon">▼</span>
                </div>
                <div class="prompt-content">
                    <div class="messages">
                        {''.join(messages_html)}
                    </div>
                </div>
            </div>
        ''')

    # Fill in template by replacing placeholders
    html = html_template.replace('{total_prompts}', str(len(prompts)))
    html = html.replace('{total_messages}', str(total_messages))
    html = html.replace('{max_iteration}', str(max_iteration))
    html = html.replace('{prompts_html}', ''.join(prompts_html))

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ HTML file generated: {output_path}")
    print(f"📊 Stats: {len(prompts)} prompts, {total_messages} messages, max iteration: {max_iteration}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python llm_log_to_html.py <log_file_path> [output_file_path]")
        print("\nExample:")
        print("  python llm_log_to_html.py /path/to/llm_prompts.log")
        print("  python llm_log_to_html.py /path/to/llm_prompts.log output.html")
        sys.exit(1)

    log_path = Path(sys.argv[1])

    if not log_path.exists():
        print(f"Error: Log file not found: {log_path}")
        sys.exit(1)

    # Determine output path
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = log_path.parent / f"{log_path.stem}_viewer.html"

    print(f"📖 Parsing log file: {log_path}")
    prompts = parse_log_file(log_path)

    if not prompts:
        print("⚠️  Warning: No prompts found in the log file!")
        sys.exit(1)

    print(f"✅ Found {len(prompts)} prompts")
    print(f"🔨 Generating HTML...")

    generate_html(prompts, output_path)

    print(f"\n🎉 Done! Open the file in your browser:")
    print(f"   {output_path.absolute()}")


if __name__ == '__main__':
    main()
