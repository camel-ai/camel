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
        'system': 'rgba(0, 240, 255, 0.1)',
        'user': 'rgba(255, 42, 109, 0.1)',
        'assistant': 'rgba(255, 208, 10, 0.1)',
        'tool': 'rgba(0, 240, 255, 0.15)',
    }
    return colors.get(role, 'rgba(255, 255, 255, 0.05)')


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
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Orbitron:wght@700;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0e27;
            --bg-secondary: #151932;
            --bg-tertiary: #1a1f3a;
            --accent-cyan: #00f0ff;
            --accent-pink: #ff2a6d;
            --accent-yellow: #ffd60a;
            --text-primary: #e0e6ff;
            --text-secondary: #8892b0;
            --border-glow: rgba(0, 240, 255, 0.4);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        @keyframes flicker {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.97; }
        }

        @keyframes glitch {
            0%, 100% { transform: translateX(0); }
            33% { transform: translateX(-2px); }
            66% { transform: translateX(2px); }
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        body {
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            background: var(--bg-primary);
            background-image:
                repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 240, 255, 0.03) 2px, rgba(0, 240, 255, 0.03) 4px),
                repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(255, 42, 109, 0.03) 2px, rgba(255, 42, 109, 0.03) 4px);
            padding: 20px;
            min-height: 100vh;
            position: relative;
            animation: flicker 3s infinite;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: var(--bg-secondary);
            border: 1px solid rgba(0, 240, 255, 0.2);
            border-radius: 2px;
            box-shadow:
                0 0 40px rgba(0, 240, 255, 0.1),
                inset 0 0 100px rgba(0, 0, 0, 0.5);
            overflow: hidden;
            animation: fadeInUp 0.6s ease-out;
        }

        .header {
            background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-secondary) 100%);
            border-bottom: 2px solid var(--accent-cyan);
            padding: 40px 30px;
            position: relative;
            overflow: hidden;
        }

        .header::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg,
                transparent,
                var(--accent-pink),
                var(--accent-cyan),
                var(--accent-yellow),
                transparent
            );
            animation: glitch 0.3s infinite;
        }

        .header h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 3em;
            font-weight: 900;
            margin-bottom: 10px;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-pink));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-transform: uppercase;
            letter-spacing: 4px;
            text-shadow: 0 0 30px rgba(0, 240, 255, 0.5);
            animation: glitch 5s infinite;
        }

        .header p {
            font-size: 0.9em;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 2px;
        }

        .stats {
            display: flex;
            justify-content: space-around;
            padding: 30px 20px;
            background: rgba(0, 0, 0, 0.3);
            border-bottom: 1px solid rgba(0, 240, 255, 0.1);
            gap: 20px;
        }

        .stat-item {
            text-align: center;
            padding: 15px;
            background: var(--bg-tertiary);
            border: 1px solid rgba(0, 240, 255, 0.2);
            border-radius: 2px;
            flex: 1;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .stat-item::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(0, 240, 255, 0.1), transparent);
            transition: left 0.5s;
        }

        .stat-item:hover::before {
            left: 100%;
        }

        .stat-item:hover {
            border-color: var(--accent-cyan);
            box-shadow: 0 0 20px rgba(0, 240, 255, 0.3);
            transform: translateY(-2px);
        }

        .stat-value {
            font-size: 2.5em;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent-cyan), var(--accent-yellow));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-family: 'Orbitron', sans-serif;
        }

        .stat-label {
            color: var(--text-secondary);
            margin-top: 8px;
            font-size: 0.75em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .prompts-container {
            padding: 30px 20px;
        }

        .prompt-section {
            margin-bottom: 25px;
            border: 1px solid rgba(0, 240, 255, 0.3);
            border-radius: 2px;
            overflow: hidden;
            transition: all 0.4s ease;
            background: var(--bg-tertiary);
            animation: fadeInUp 0.5s ease-out backwards;
        }

        .prompt-section:nth-child(1) { animation-delay: 0.1s; }
        .prompt-section:nth-child(2) { animation-delay: 0.2s; }
        .prompt-section:nth-child(3) { animation-delay: 0.3s; }
        .prompt-section:nth-child(4) { animation-delay: 0.4s; }
        .prompt-section:nth-child(5) { animation-delay: 0.5s; }

        .prompt-section:hover {
            box-shadow:
                0 0 30px rgba(0, 240, 255, 0.2),
                inset 0 0 50px rgba(0, 240, 255, 0.05);
            border-color: var(--accent-cyan);
            transform: translateX(5px);
        }

        .prompt-header {
            background: linear-gradient(135deg,
                rgba(0, 240, 255, 0.1) 0%,
                rgba(255, 42, 109, 0.1) 100%
            );
            border-bottom: 1px solid rgba(0, 240, 255, 0.2);
            color: var(--text-primary);
            padding: 20px 25px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            user-select: none;
            position: relative;
            overflow: hidden;
        }

        .prompt-header::before {
            content: '>';
            position: absolute;
            left: 10px;
            color: var(--accent-cyan);
            font-size: 1.2em;
            font-weight: bold;
            opacity: 0.7;
        }

        .prompt-header:hover {
            background: linear-gradient(135deg,
                rgba(0, 240, 255, 0.2) 0%,
                rgba(255, 42, 109, 0.2) 100%
            );
        }

        .prompt-header:hover::before {
            animation: glitch 0.5s infinite;
        }

        .prompt-title {
            font-size: 1em;
            font-weight: 700;
            color: var(--accent-cyan);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .prompt-meta {
            display: flex;
            gap: 20px;
            font-size: 0.75em;
            color: var(--text-secondary);
            margin-top: 8px;
        }

        .prompt-meta span {
            padding: 4px 8px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(0, 240, 255, 0.2);
            border-radius: 2px;
        }

        .toggle-icon {
            font-size: 1.2em;
            color: var(--accent-pink);
            transition: transform 0.3s ease;
        }

        .prompt-section.collapsed .toggle-icon {
            transform: rotate(-90deg);
        }

        .prompt-content {
            max-height: 3000px;
            overflow: hidden;
            transition: max-height 0.4s ease;
        }

        .prompt-section.collapsed .prompt-content {
            max-height: 0;
        }

        .messages {
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .message {
            border: 1px solid rgba(0, 240, 255, 0.2);
            border-radius: 2px;
            overflow: hidden;
            background: var(--bg-secondary);
            transition: all 0.3s ease;
        }

        .message:hover {
            border-color: var(--accent-pink);
            box-shadow: 0 0 15px rgba(255, 42, 109, 0.2);
        }

        .message-header {
            padding: 15px 20px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 500;
            user-select: none;
            transition: all 0.3s ease;
            position: relative;
        }

        .message-header::before {
            content: '$';
            position: absolute;
            left: 8px;
            color: var(--accent-yellow);
            font-weight: bold;
            opacity: 0.5;
        }

        .message-header:hover {
            background: rgba(0, 240, 255, 0.05);
        }

        .message-role {
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--text-primary);
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .message-preview {
            font-size: 0.8em;
            color: var(--text-secondary);
            font-weight: normal;
            max-width: 600px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            margin-left: 15px;
            font-style: italic;
        }

        .message-body {
            padding: 20px;
            background: rgba(0, 0, 0, 0.3);
            border-top: 1px solid rgba(0, 240, 255, 0.1);
            max-height: 600px;
            overflow: auto;
            display: none;
        }

        .message-body::-webkit-scrollbar {
            width: 8px;
        }

        .message-body::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }

        .message-body::-webkit-scrollbar-thumb {
            background: var(--accent-cyan);
            border-radius: 2px;
        }

        .message.expanded .message-body {
            display: block;
            animation: fadeInUp 0.3s ease-out;
        }

        .message.expanded .message-toggle {
            transform: rotate(180deg);
            color: var(--accent-cyan);
        }

        .message-toggle {
            transition: transform 0.3s ease, color 0.3s ease;
            color: var(--accent-pink);
            font-size: 0.9em;
        }

        .message-content {
            white-space: pre-wrap;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85em;
            line-height: 1.8;
            color: var(--text-primary);
        }

        .tool-calls {
            background: rgba(255, 208, 10, 0.1);
            border-left: 3px solid var(--accent-yellow);
            padding: 15px;
            margin-top: 15px;
            border-radius: 2px;
            color: var(--text-secondary);
        }

        .tool-calls strong {
            color: var(--accent-yellow);
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .controls {
            position: fixed;
            bottom: 30px;
            right: 30px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            z-index: 1000;
        }

        .control-btn {
            font-family: 'JetBrains Mono', monospace;
            background: var(--bg-tertiary);
            color: var(--accent-cyan);
            border: 1px solid var(--accent-cyan);
            padding: 12px 20px;
            border-radius: 2px;
            cursor: pointer;
            font-size: 0.85em;
            font-weight: 500;
            box-shadow: 0 0 20px rgba(0, 240, 255, 0.2);
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
            position: relative;
            overflow: hidden;
        }

        .control-btn::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            background: rgba(0, 240, 255, 0.3);
            border-radius: 50%;
            transform: translate(-50%, -50%);
            transition: width 0.4s, height 0.4s;
        }

        .control-btn:hover::before {
            width: 300px;
            height: 300px;
        }

        .control-btn:hover {
            background: var(--accent-cyan);
            color: var(--bg-primary);
            transform: translateX(-5px);
            box-shadow: 0 0 30px rgba(0, 240, 255, 0.5);
        }

        .control-btn:active {
            transform: translateX(-5px) scale(0.95);
        }

        .search-box {
            padding: 25px 20px;
            background: rgba(0, 0, 0, 0.3);
            border-bottom: 1px solid rgba(0, 240, 255, 0.2);
            position: relative;
        }

        .search-box::before {
            content: '>';
            position: absolute;
            left: 30px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--accent-yellow);
            font-weight: bold;
            font-size: 1.2em;
        }

        .search-input {
            width: 100%;
            padding: 15px 20px 15px 40px;
            font-size: 0.9em;
            font-family: 'JetBrains Mono', monospace;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid rgba(0, 240, 255, 0.3);
            border-radius: 2px;
            outline: none;
            transition: all 0.3s ease;
        }

        .search-input::placeholder {
            color: var(--text-secondary);
            opacity: 0.6;
        }

        .search-input:focus {
            border-color: var(--accent-cyan);
            box-shadow:
                0 0 20px rgba(0, 240, 255, 0.3),
                inset 0 0 30px rgba(0, 240, 255, 0.05);
            background: var(--bg-secondary);
        }

        .highlight {
            background: var(--accent-yellow);
            color: var(--bg-primary);
            padding: 2px 4px;
            border-radius: 2px;
            font-weight: bold;
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.8em;
                letter-spacing: 2px;
            }

            .stats {
                flex-direction: column;
                gap: 15px;
            }

            .prompt-meta {
                flex-direction: column;
                gap: 8px;
            }

            .controls {
                bottom: 20px;
                right: 20px;
                gap: 8px;
            }

            .control-btn {
                padding: 10px 16px;
                font-size: 0.75em;
            }

            .message-preview {
                max-width: 200px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>LLM LOG VISUALIZATION</h1>
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
            <input type="text" class="search-input" placeholder="grep -i 'search query' ./messages/*" id="searchInput">
        </div>

        <div class="prompts-container">
            {prompts_html}
        </div>
    </div>

    <div class="controls">
        <button class="control-btn" onclick="expandAll()">&gt;_ EXPAND ALL</button>
        <button class="control-btn" onclick="collapseAll()">&gt;_ COLLAPSE ALL</button>
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
