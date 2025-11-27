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
from datetime import datetime
from html import escape


def parse_log_file(log_path):
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


def truncate_content(content, max_length=500):
    """Truncate long content for preview."""
    if len(content) > max_length:
        return content[:max_length] + "..."
    return content


def format_message_content(content):
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


def get_role_color(role):
    """Get color for different message roles."""
    colors = {
        'system': '#e3f2fd',
        'user': '#f3e5f5',
        'assistant': '#e8f5e9',
        'tool': '#fff3e0',
    }
    return colors.get(role, '#f5f5f5')


def get_role_icon(role):
    """Get emoji icon for different roles."""
    icons = {
        'system': '⚙️',
        'user': '👤',
        'assistant': '🤖',
        'tool': '🔧',
    }
    return icons.get(role, '📝')


def generate_html(prompts, output_path):
    """Generate HTML file from parsed prompts."""

    html_template = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Prompts Log Viewer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .stats {
            display: flex;
            justify-content: space-around;
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }

        .stat-item {
            text-align: center;
        }

        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }

        .stat-label {
            color: #6c757d;
            margin-top: 5px;
        }

        .prompts-container {
            padding: 20px;
        }

        .prompt-section {
            margin-bottom: 20px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            overflow: hidden;
            transition: all 0.3s ease;
        }

        .prompt-section:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border-color: #667eea;
        }

        .prompt-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            user-select: none;
        }

        .prompt-header:hover {
            background: linear-gradient(135deg, #5568d3 0%, #653a8b 100%);
        }

        .prompt-title {
            font-size: 1.2em;
            font-weight: bold;
        }

        .prompt-meta {
            display: flex;
            gap: 15px;
            font-size: 0.9em;
            opacity: 0.9;
        }

        .toggle-icon {
            font-size: 1.5em;
            transition: transform 0.3s ease;
        }

        .prompt-section.collapsed .toggle-icon {
            transform: rotate(-90deg);
        }

        .prompt-content {
            max-height: 2000px;
            overflow: hidden;
            transition: max-height 0.3s ease;
        }

        .prompt-section.collapsed .prompt-content {
            max-height: 0;
        }

        .messages {
            padding: 20px;
        }

        .message {
            margin-bottom: 15px;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #dee2e6;
        }

        .message-header {
            padding: 12px 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 600;
            user-select: none;
            transition: all 0.2s ease;
        }

        .message-header:hover {
            opacity: 0.8;
        }

        .message-role {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .message-preview {
            font-size: 0.85em;
            color: #6c757d;
            font-weight: normal;
            max-width: 500px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .message-body {
            padding: 15px;
            background: white;
            border-top: 1px solid #dee2e6;
            max-height: 600px;
            overflow: auto;
            display: none;
        }

        .message.expanded .message-body {
            display: block;
        }

        .message.expanded .message-toggle {
            transform: rotate(180deg);
        }

        .message-toggle {
            transition: transform 0.2s ease;
        }

        .message-content {
            white-space: pre-wrap;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9em;
            line-height: 1.6;
            color: #2d3748;
        }

        .tool-calls {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 10px;
            margin-top: 10px;
            border-radius: 4px;
        }

        .controls {
            position: fixed;
            bottom: 30px;
            right: 30px;
            display: flex;
            gap: 10px;
        }

        .control-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
        }

        .control-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.3);
        }

        .search-box {
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }

        .search-input {
            width: 100%;
            padding: 12px 20px;
            font-size: 1em;
            border: 2px solid #dee2e6;
            border-radius: 25px;
            outline: none;
            transition: all 0.3s ease;
        }

        .search-input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .highlight {
            background-color: yellow;
            font-weight: bold;
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.8em;
            }

            .stats {
                flex-direction: column;
                gap: 15px;
            }

            .prompt-meta {
                flex-direction: column;
                gap: 5px;
            }

            .controls {
                bottom: 10px;
                right: 10px;
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 LLM Prompts Log Viewer</h1>
            <p>Interactive visualization of agent conversation history</p>
        </div>

        <div class="stats">
            <div class="stat-item">
                <div class="stat-value">{total_prompts}</div>
                <div class="stat-label">Total Prompts</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{total_messages}</div>
                <div class="stat-label">Total Messages</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{max_iteration}</div>
                <div class="stat-label">Max Iteration</div>
            </div>
        </div>

        <div class="search-box">
            <input type="text" class="search-input" placeholder="🔍 Search in messages..." id="searchInput">
        </div>

        <div class="prompts-container">
            {prompts_html}
        </div>
    </div>

    <div class="controls">
        <button class="control-btn" onclick="expandAll()">📂 Expand All</button>
        <button class="control-btn" onclick="collapseAll()">📁 Collapse All</button>
    </div>

    <script>
        // Toggle prompt sections
        function togglePrompt(element) {
            element.closest('.prompt-section').classList.toggle('collapsed');
        }

        // Toggle message sections
        function toggleMessage(element) {
            element.closest('.message').classList.toggle('expanded');
        }

        // Expand all prompts
        function expandAll() {
            document.querySelectorAll('.prompt-section').forEach(section => {
                section.classList.remove('collapsed');
            });
            document.querySelectorAll('.message').forEach(msg => {
                msg.classList.add('expanded');
            });
        }

        // Collapse all prompts
        function collapseAll() {
            document.querySelectorAll('.prompt-section').forEach(section => {
                section.classList.add('collapsed');
            });
            document.querySelectorAll('.message').forEach(msg => {
                msg.classList.remove('expanded');
            });
        }

        // Search functionality
        let searchTimeout;
        document.getElementById('searchInput').addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const searchTerm = e.target.value.toLowerCase();
                const prompts = document.querySelectorAll('.prompt-section');

                prompts.forEach(prompt => {
                    const text = prompt.textContent.toLowerCase();
                    if (searchTerm === '' || text.includes(searchTerm)) {
                        prompt.style.display = 'block';
                        if (searchTerm !== '') {
                            prompt.classList.remove('collapsed');
                        }
                    } else {
                        prompt.style.display = 'none';
                    }
                });
            }, 300);
        });

        // Initialize: collapse all prompts except the first one
        document.addEventListener('DOMContentLoaded', function() {
            const prompts = document.querySelectorAll('.prompt-section');
            prompts.forEach((prompt, index) => {
                if (index > 0) {
                    prompt.classList.add('collapsed');
                }
            });
        });
    </script>
</body>
</html>'''

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
