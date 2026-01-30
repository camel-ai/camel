#!/usr/bin/env python3
"""
Browser Log to HTML Visualization Converter

将 hybrid_browser_toolkit 的日志文件转换为可视化的 HTML 文件。

用法:
    python browser_log_to_html.py <input_log_path> [output_html_path]

示例:
    python browser_log_to_html.py browser_log/hybrid_browser_toolkit_ws_20251011_171154_498057c3.log
    python browser_log_to_html.py browser_log/hybrid_browser_toolkit_ws_20251011_171154_498057c3.log /path/to/output.html
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Any


def parse_log_file(log_path: str) -> list[dict[str, Any]]:
    """解析日志文件，返回操作列表。"""
    actions = []
    with open(log_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 日志文件可能包含多个 JSON 对象（每行一个或连续的对象）
    decoder = json.JSONDecoder()
    pos = 0
    content = content.strip()

    while pos < len(content):
        # 跳过空白字符
        while pos < len(content) and content[pos] in ' \t\n\r':
            pos += 1
        if pos >= len(content):
            break

        try:
            obj, end_pos = decoder.raw_decode(content, pos)
            actions.append(obj)
            # raw_decode 返回的 end_pos 是绝对位置
            pos = end_pos
        except json.JSONDecodeError:
            # 尝试找到下一个 { 字符
            next_brace = content.find('{', pos + 1)
            if next_brace == -1:
                break
            pos = next_brace

    return actions


def escape_html(text: str) -> str:
    """转义 HTML 特殊字符。"""
    if not isinstance(text, str):
        text = str(text)
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


def format_json(obj: Any, max_length: int = 500, truncate: bool = True) -> str:
    """格式化 JSON 对象为字符串。"""
    try:
        formatted = json.dumps(obj, indent=2, ensure_ascii=False)
        if truncate and len(formatted) > max_length:
            formatted = formatted[:max_length] + '\n... (truncated)'
        return formatted
    except Exception:
        return str(obj)


def format_snapshot(snapshot: str) -> str:
    """格式化 snapshot 字符串，保留换行。"""
    if not snapshot:
        return ''
    # 将 \n 转换为实际换行，已经是换行的保持不变
    return snapshot.replace('\\n', '\n')


def format_outputs(outputs: Any) -> str:
    """格式化 outputs，snapshot 不截断并渲染换行。"""
    if isinstance(outputs, str):
        # outputs 本身就是 snapshot 字符串
        return outputs

    if isinstance(outputs, dict):
        # 先序列化为 JSON
        json_str = json.dumps(outputs, indent=2, ensure_ascii=False)
        # 将 JSON 中的 \\n 转换为实际换行（在 snapshot 值中）
        # 这样 snapshot 内容会正确换行显示
        json_str = json_str.replace('\\n', '\n')
        return json_str

    if isinstance(outputs, list):
        return json.dumps(outputs, indent=2, ensure_ascii=False)

    return str(outputs)


def get_action_icon(action: str) -> str:
    """根据操作类型返回对应的图标。"""
    icons = {
        'open_browser': '🌐',
        'visit_page': '🔗',
        'click': '👆',
        'type': '⌨️',
        'scroll': '📜',
        'get_page_snapshot': '📸',
        'get_som_screenshot': '🖼️',
        'get_tab_info': '📑',
        'switch_tab': '🔄',
        'back': '⬅️',
        'forward': '➡️',
        'enter': '↩️',
        'press_key': '🔤',
        'select': '☑️',
        'console_exec': '💻',
        'console_view': '📋',
        'close': '❌',
    }
    return icons.get(action, '🔧')


def get_action_color(action: str) -> str:
    """根据操作类型返回对应的颜色。"""
    colors = {
        'open_browser': '#3b82f6',  # blue
        'visit_page': '#8b5cf6',    # purple
        'click': '#10b981',         # green
        'type': '#f59e0b',          # amber
        'scroll': '#6366f1',        # indigo
        'get_page_snapshot': '#ec4899',  # pink
        'get_som_screenshot': '#f43f5e', # rose
        'get_tab_info': '#14b8a6',  # teal
        'switch_tab': '#06b6d4',    # cyan
        'back': '#64748b',          # slate
        'forward': '#64748b',       # slate
        'enter': '#84cc16',         # lime
        'press_key': '#a855f7',     # purple
        'select': '#22c55e',        # green
        'console_exec': '#ef4444',  # red
        'console_view': '#f97316',  # orange
        'close': '#dc2626',         # red
    }
    return colors.get(action, '#6b7280')


def parse_ref_info(snapshot: str, ref_id: str) -> dict | None:
    """从 snapshot 中解析指定 ref 的 aria-label 和值。

    格式示例：
    - button "Book 已保存" [ref=f1e72]: 123
    - combobox "从哪里出发？" [ref=e145]: 伦敦
    - textbox "出发时间" [ref=e177]
    - generic [ref=e105]: 航班
    """
    if not snapshot or not ref_id:
        return None


    # 找到包含该 ref 的行
    lines = snapshot.split('\n')
    target_line = None
    for line in lines:
        if f'[ref={ref_id}]' in line:
            target_line = line
            break

    if not target_line:
        return None

    # 解析该行
    # 格式: - element_type "aria-label" [...] [ref=xxx] [...]: value
    # 或: - element_type [...] [ref=xxx] [...]: value
    # 或: - element_type "aria-label" [...] [ref=xxx]
    # 或: - element_type [...] [ref=xxx]

    result = {
        'element_type': None,
        'aria_label': None,
        'value': None
    }

    # 提取元素类型
    element_match = re.match(r'^\s*-\s+(\w+)', target_line)
    if element_match:
        result['element_type'] = element_match.group(1)

    # 提取 aria-label（引号中的内容，在 [ref=xxx] 之前）
    ref_pos = target_line.find(f'[ref={ref_id}]')
    before_ref = target_line[:ref_pos] if ref_pos > 0 else target_line

    label_match = re.search(r'"([^"]+)"', before_ref)
    if label_match:
        result['aria_label'] = label_match.group(1)

    # 提取值（[ref=xxx] 之后，冒号后面的内容，但不包含子元素）
    after_ref = target_line[ref_pos + len(f'[ref={ref_id}]'):] if ref_pos >= 0 else ''

    # 查找冒号后的值，但值不能以 "- " 开头（那是子元素）
    value_match = re.search(r'\]:\s*([^:\[\]]+?)$', target_line)
    if value_match:
        value = value_match.group(1).strip()
        # 排除子元素标记
        if value and not value.startswith('-'):
            # 清理值中可能的多余内容
            value = re.sub(r'\s*\[.*$', '', value).strip()
            if value and value != ':':
                result['value'] = value

    return result if any(result.values()) else None


def find_ref_info_recursive(actions: list, current_idx: int, ref_id: str) -> dict | None:
    """递归向上查找 ref 的信息，从当前操作的前一个开始。"""
    for i in range(current_idx - 1, -1, -1):
        action = actions[i]
        outputs = action.get('outputs', {})

        # 获取 snapshot
        snapshot = None
        if isinstance(outputs, dict):
            snapshot = outputs.get('snapshot', '')
        elif isinstance(outputs, str):
            snapshot = outputs

        if snapshot:
            ref_info = parse_ref_info(snapshot, ref_id)
            if ref_info:
                return ref_info

    return None


def get_url_base(url: str) -> str:
    """获取 URL 的基础部分（忽略查询参数）。"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        # 简单处理：去掉问号后面的内容
        if '?' in url:
            return url.split('?')[0]
        return url


# 颜色库 - 差异较大的颜色
URL_COLORS = [
    '#2196F3',  # Blue
    '#4CAF50',  # Green
    '#FF5722',  # Deep Orange
    '#9C27B0',  # Purple
    '#00BCD4',  # Cyan
    '#FF9800',  # Orange
    '#E91E63',  # Pink
    '#009688',  # Teal
    '#673AB7',  # Deep Purple
    '#F44336',  # Red
    '#3F51B5',  # Indigo
    '#8BC34A',  # Light Green
    '#CDDC39',  # Lime
    '#FFC107',  # Amber
    '#795548',  # Brown
    '#607D8B',  # Blue Grey
    '#1565C0',  # Blue 800
    '#2E7D32',  # Green 800
    '#C62828',  # Red 800
    '#6A1B9A',  # Purple 800
    '#00838F',  # Cyan 800
    '#EF6C00',  # Orange 800
    '#AD1457',  # Pink 800
    '#00695C',  # Teal 800
    '#4527A0',  # Deep Purple 800
    '#283593',  # Indigo 800
    '#558B2F',  # Light Green 800
    '#9E9D24',  # Lime 800
    '#FF8F00',  # Amber 800
    '#4E342E',  # Brown 800
]


def extract_urls(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从操作列表中提取 URL 区域信息（排除 get_tab_info）。"""
    url_regions = []
    current_url = None
    current_actions = []

    for idx, action in enumerate(actions):
        action_type = action.get('action', '')

        # 跳过 get_tab_info 操作
        if action_type == 'get_tab_info':
            continue

        inputs = action.get('inputs', {})
        outputs = action.get('outputs', {})

        # 检测 URL 变化
        new_url = None

        if action_type == 'open_browser':
            args = inputs.get('args', [])
            if args:
                new_url = args[0]
        elif action_type == 'visit_page':
            args = inputs.get('args', [])
            if args:
                new_url = args[0]

        if new_url and new_url != current_url:
            # 保存之前的区域
            if current_url and current_actions:
                url_regions.append({
                    'url': current_url,
                    'actions': current_actions,
                    'action_count': len(current_actions)
                })
            current_url = new_url
            current_actions = [idx]
        else:
            current_actions.append(idx)

    # 保存最后一个区域
    if current_url and current_actions:
        url_regions.append({
            'url': current_url,
            'actions': current_actions,
            'action_count': len(current_actions)
        })

    return url_regions


def get_url_color(url: str, url_color_map: dict) -> str:
    """根据 URL 基础部分获取颜色。"""
    base_url = get_url_base(url)
    if base_url not in url_color_map:
        color_idx = len(url_color_map) % len(URL_COLORS)
        url_color_map[base_url] = URL_COLORS[color_idx]
    return url_color_map[base_url]


def shorten_url(url: str, max_length: int = 50) -> str:
    """缩短 URL 显示。"""
    if len(url) <= max_length:
        return url
    # 保留协议和域名，截断路径
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        path = parsed.path
        if len(domain) + len(path) > max_length:
            remaining = max_length - len(domain) - 3
            if remaining > 10:
                path = path[:remaining] + '...'
            else:
                path = '/...'
        return domain + path
    except Exception:
        return url[:max_length-3] + '...'


def generate_html(actions: list[dict[str, Any]], session_id: str, log_filename: str) -> str:
    """生成 HTML 可视化内容。"""

    # 过滤掉 get_tab_info 操作
    filtered_actions = [a for a in actions if a.get('action') != 'get_tab_info']

    # 计算统计信息
    total_time = sum(a.get('execution_time_ms', 0) for a in filtered_actions)
    action_counts = {}
    success_count = 0
    failed_count = 0

    for a in filtered_actions:
        action_type = a.get('action', 'unknown')
        action_counts[action_type] = action_counts.get(action_type, 0) + 1

        outputs = a.get('outputs', {})
        if isinstance(outputs, dict):
            if outputs.get('success') is False or 'error' in str(outputs).lower():
                failed_count += 1
            else:
                success_count += 1
        else:
            success_count += 1

    # 提取 URL 区域
    url_regions = extract_urls(actions)

    # 构建 URL 颜色映射（相同基础 URL 使用相同颜色）
    url_color_map = {}

    # 判断每个区域是否由 open_browser 开始
    def region_starts_with_open_browser(region_actions, all_actions):
        if not region_actions:
            return False
        first_action_idx = region_actions[0]
        return all_actions[first_action_idx].get('action') == 'open_browser'

    # 构建 URL 流程图（按 open_browser 分行）
    flow_nodes_html = []
    current_row = []

    for idx, region in enumerate(url_regions):
        url = region['url']
        short_url = shorten_url(url, 40)
        action_count = region['action_count']
        color = get_url_color(url, url_color_map)

        # 检查是否需要开始新行（open_browser 开始的区域）
        is_new_session = region_starts_with_open_browser(region['actions'], actions)

        if is_new_session and current_row:
            # 结束当前行，开始新行
            flow_nodes_html.append(f'<div class="flow-row">{"".join(current_row)}</div>')
            current_row = []

        # 添加箭头（如果不是行首）
        if current_row:
            current_row.append('<div class="flow-arrow">→</div>')

        # 添加节点（带高亮功能）
        node_html = f'''
            <div class="flow-node" onclick="highlightRegion({idx})" title="{escape_html(url)}" style="background: linear-gradient(135deg, {color}, {color}dd);" data-region-idx="{idx}">
                <div class="flow-node-id">Region {idx + 1}</div>
                <div class="flow-node-url">{escape_html(short_url)}</div>
                <div class="flow-node-count">{action_count} actions</div>
            </div>
        '''
        current_row.append(node_html)

    # 添加最后一行
    if current_row:
        flow_nodes_html.append(f'<div class="flow-row">{"".join(current_row)}</div>')

    # 构建 Action Flow（每个 action 显示为一个节点）
    action_flow_html = []
    action_flow_row = []

    for idx, action in enumerate(actions):
        action_type = action.get('action', 'unknown')

        # 跳过 get_tab_info
        if action_type == 'get_tab_info':
            continue

        inputs = action.get('inputs', {})
        args = inputs.get('args', [])

        # 检查是否需要开始新行（open_browser）
        if action_type == 'open_browser' and action_flow_row:
            action_flow_html.append(f'<div class="action-flow-row">{"".join(action_flow_row)}</div>')
            action_flow_row = []

        # 获取 ref 信息
        ref_label = ''
        ref_value = ''
        arg_display = ''

        if args:
            first_arg = str(args[0])
            if action_type in ['click', 'type', 'select', 'scroll']:
                ref_id = first_arg
                ref_info = find_ref_info_recursive(actions, idx, ref_id)
                if ref_info:
                    if ref_info.get('aria_label'):
                        ref_label = ref_info['aria_label']
                    if ref_info.get('value'):
                        ref_value = ref_info['value']
                # 对于 type，第二个 arg 是输入的值
                if action_type == 'type' and len(args) > 1:
                    type_value = str(args[1])
                    if len(type_value) > 30:
                        arg_display = type_value[:27] + '...'
                    else:
                        arg_display = type_value
                # 只有 ref 的情况不显示 arg
            else:
                # 其他 action 显示 arg（截断长度），但排除 False
                if first_arg.lower() != 'false':
                    if len(first_arg) > 30:
                        arg_display = first_arg[:27] + '...'
                    else:
                        arg_display = first_arg

        # 检查是否失败
        outputs = action.get('outputs', {})
        is_failed = False
        if isinstance(outputs, dict):
            result = outputs.get('result', '')
            if 'failed' in str(result).lower() or 'error' in str(result).lower():
                is_failed = True
            if outputs.get('success') is False:
                is_failed = True

        # 获取 action 颜色
        action_color = get_action_color(action_type)
        action_icon = get_action_icon(action_type)
        failed_class = 'action-flow-failed' if is_failed else ''

        # 构建节点内容
        warning_icon = '<div class="action-flow-warning">⚠️</div>' if is_failed else ''
        node_content = f'{warning_icon}<div class="action-flow-type">{action_icon} {escape_html(action_type)}</div>'
        if arg_display:
            node_content += f'<div class="action-flow-arg">{escape_html(arg_display)}</div>'
        if ref_label:
            node_content += f'<div class="action-flow-label">"{escape_html(ref_label)}"</div>'
        if ref_value:
            node_content += f'<div class="action-flow-value">{escape_html(ref_value)}</div>'

        # 添加箭头（如果不是行首）
        if action_flow_row:
            action_flow_row.append('<div class="action-flow-arrow">→</div>')

        # 添加节点（带点击跳转和 region 标记）
        # 找到当前 action 所属的 region
        current_region_idx = -1
        for ri, region in enumerate(url_regions):
            if idx in region['actions']:
                current_region_idx = ri
                break

        action_flow_row.append(f'''
            <div class="action-flow-node {failed_class}" style="border-color: {action_color};"
                 title="Action {idx + 1}"
                 data-action-idx="{idx}"
                 data-region-idx="{current_region_idx}"
                 data-action-type="{action_type}"
                 id="action-flow-{idx}"
                 onclick="scrollToAction({idx})">
                {node_content}
            </div>
        ''')

    # 添加最后一行
    if action_flow_row:
        action_flow_html.append(f'<div class="action-flow-row">{"".join(action_flow_row)}</div>')

    # 构建区域和时间线 HTML
    regions_html = []
    for region_idx, region in enumerate(url_regions):
        url = region['url']
        action_indices = region['actions']

        actions_html = []
        for idx in action_indices:
            action = actions[idx]
            action_type = action.get('action', 'unknown')

            # 跳过 get_tab_info 操作
            if action_type == 'get_tab_info':
                continue
            timestamp = action.get('timestamp', '')
            exec_time = action.get('execution_time_ms', 0)
            inputs = action.get('inputs', {})
            outputs = action.get('outputs', {})

            # 格式化时间
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime('%H:%M:%S.%f')[:-3]
            except Exception:
                time_str = timestamp

            # 获取简短描述
            args = inputs.get('args', [])
            description = ''
            if args:
                first_arg = str(args[0])
                if len(first_arg) > 80:
                    first_arg = first_arg[:77] + '...'
                description = first_arg

            # 如果是有 ref 的操作（click, type 等），查找 ref 信息
            ref_info_html = ''
            arg_info_html = ''

            if args and action_type in ['click', 'type', 'select', 'scroll']:
                ref_id = str(args[0])
                # 递归向上查找 ref 信息
                ref_info = find_ref_info_recursive(actions, idx, ref_id)
                if ref_info:
                    element_type = ref_info.get('element_type', '')
                    aria_label = ref_info.get('aria_label', '')
                    value = ref_info.get('value', '')

                    ref_parts = []
                    if element_type:
                        ref_parts.append(f'<span class="ref-element-type">{escape_html(element_type)}</span>')
                    if aria_label:
                        ref_parts.append(f'<span class="ref-aria-label">"{escape_html(aria_label)}"</span>')
                    if value:
                        ref_parts.append(f'<span class="ref-value">: {escape_html(value)}</span>')

                    if ref_parts:
                        ref_info_html = f'<div class="ref-info"><span class="ref-id">[{escape_html(ref_id)}]</span> {" ".join(ref_parts)}</div>'

                # 对于 type，显示输入的值
                if action_type == 'type' and len(args) > 1:
                    type_value = str(args[1])
                    arg_info_html = f'<div class="arg-info"><span class="arg-label">Input:</span> <span class="arg-value">{escape_html(type_value)}</span></div>'

            elif args:
                # 其他 action 显示 arg（排除 False）
                first_arg = str(args[0])
                if first_arg.lower() != 'false':
                    if action_type in ['open_browser', 'visit_page']:
                        arg_info_html = f'<div class="arg-info"><span class="arg-label">URL:</span> <span class="arg-value arg-url">{escape_html(first_arg)}</span></div>'
                    elif action_type == 'scroll':
                        arg_info_html = f'<div class="arg-info"><span class="arg-label">Direction:</span> <span class="arg-value">{escape_html(first_arg)}</span></div>'
                    else:
                        arg_info_html = f'<div class="arg-info"><span class="arg-label">Arg:</span> <span class="arg-value">{escape_html(first_arg)}</span></div>'

            # 检查是否成功
            is_success = True
            if isinstance(outputs, dict):
                if outputs.get('success') is False or 'error' in str(outputs).lower():
                    is_success = False

            icon = get_action_icon(action_type)
            color = get_action_color(action_type)
            status_class = 'success' if is_success else 'error'

            # 输出内容预览
            output_preview = ''
            if isinstance(outputs, dict):
                if 'message' in outputs:
                    output_preview = str(outputs['message'])[:100]
                elif 'result' in outputs:
                    output_preview = str(outputs['result'])[:100]
                elif 'snapshot' in outputs:
                    output_preview = '(Page snapshot captured)'
            elif isinstance(outputs, list):
                output_preview = f'({len(outputs)} items)'
            elif isinstance(outputs, str):
                output_preview = outputs[:100] if len(outputs) > 100 else outputs

            # 是否是导航操作
            is_navigation = action_type in ['open_browser', 'visit_page', 'back', 'forward']
            nav_class = 'action-navigation' if is_navigation else ''
            nav_badge = '<span class="navigation-badge">NAVIGATION</span>' if is_navigation else ''

            actions_html.append(f'''
            <div class="action-item {status_class} {nav_class}" data-index="{idx}" data-type="{action_type}" data-action-idx="{idx}" id="action-{idx}">
                <div class="action-number">{idx + 1}</div>
                <div class="action-header">
                    <div class="action-left">
                        <span class="action-icon" style="background: {color};">{icon}</span>
                        <span class="action-type">{escape_html(action_type)}</span>
                        {nav_badge}
                        <span class="execution-time">{exec_time:.1f}ms</span>
                    </div>
                    <div class="action-right">
                        <span class="action-time">{time_str}</span>
                        <span class="status-badge {status_class}">{'✓' if is_success else '✗'}</span>
                    </div>
                </div>
                {ref_info_html}
                {arg_info_html}
                {f'<div class="action-description">{escape_html(description)}</div>' if description and not ref_info_html and not arg_info_html else ''}
                {f'<div class="output-info"><div class="output-summary">{escape_html(output_preview)}</div></div>' if output_preview else ''}
                <details class="inputs-outputs">
                    <summary>View Details</summary>
                    <div class="detail-section">
                        <div class="detail-title">📥 Inputs</div>
                        <pre class="json-view">{escape_html(format_json(inputs, 3000))}</pre>
                    </div>
                    <div class="detail-section">
                        <div class="detail-title">📤 Outputs</div>
                        <pre class="json-view">{escape_html(format_outputs(outputs))}</pre>
                    </div>
                </details>
            </div>
            ''')

        region_color = get_url_color(url, url_color_map)
        regions_html.append(f'''
        <div class="region" id="region-{region_idx}" style="background: {region_color}22;">
            <div class="region-header" onclick="toggleRegion({region_idx})" style="border-left-color: {region_color};">
                <div class="region-title">
                    <span class="region-badge" style="background: {region_color};">Region {region_idx + 1}</span>
                    <span class="region-url">{escape_html(shorten_url(url, 60))}</span>
                    <span class="collapse-indicator">▼</span>
                </div>
                <div class="region-stats">
                    <span class="region-action-count">{len(actions_html)} actions</span>
                </div>
            </div>
            <div class="region-actions" id="region-actions-{region_idx}">
                {''.join(actions_html)}
            </div>
        </div>
        ''')

    # 构建统计卡片（可点击切换显示）
    stats_html = []
    for action_type, count in sorted(action_counts.items(), key=lambda x: -x[1]):
        icon = get_action_icon(action_type)
        color = get_action_color(action_type)
        stats_html.append(f'''
        <div class="stat-chip" style="border-color: {color};" data-action-type="{escape_html(action_type)}" onclick="toggleActionType('{escape_html(action_type)}')">
            <span class="chip-icon">{icon}</span>
            <span class="chip-label">{escape_html(action_type)}</span>
            <span class="chip-count">{count}</span>
            <span class="chip-toggle">✓</span>
        </div>
        ''')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Browser Log Visualization - {escape_html(session_id)}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}

        body {{
            background: #f5f5f5;
            color: #333;
            min-height: 100vh;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}

        header {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}

        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }}

        .summary {{
            background: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
        }}

        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}

        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border: 2px solid #2196F3;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}

        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            color: #2196F3;
        }}

        .stat-label {{
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }}

        /* Flow Diagram */
        .flow-section {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .flow-section h2 {{
            margin-bottom: 15px;
            color: #333;
        }}

        .flow-diagram {{
            display: flex;
            flex-direction: column;
            gap: 20px;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
            border: 2px solid #ddd;
            overflow-x: auto;
        }}

        .flow-row {{
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
        }}

        .flow-node {{
            background: linear-gradient(135deg, #2196F3, #1976D2);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
            min-width: 180px;
            text-align: center;
            box-shadow: 0 3px 10px rgba(33, 150, 243, 0.3);
        }}

        .flow-node:hover {{
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(33, 150, 243, 0.4);
            background: linear-gradient(135deg, #1976D2, #1565C0);
        }}

        .flow-node-id {{
            font-size: 12px;
            opacity: 0.9;
            margin-bottom: 5px;
        }}

        .flow-node-url {{
            font-size: 11px;
            font-family: 'Courier New', monospace;
            word-break: break-all;
            line-height: 1.4;
        }}

        .flow-node-count {{
            font-size: 10px;
            margin-top: 8px;
            opacity: 0.8;
            background: rgba(255,255,255,0.2);
            padding: 3px 8px;
            border-radius: 10px;
        }}

        .flow-arrow {{
            color: #999;
            font-size: 28px;
            font-weight: bold;
        }}

        /* Action Flow */
        .action-flow-diagram {{
            display: flex;
            flex-direction: column;
            gap: 15px;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
            border: 2px solid #ddd;
            overflow-x: auto;
        }}

        .action-flow-row {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            padding: 10px 0;
            border-bottom: 1px dashed #ddd;
        }}

        .action-flow-row:last-child {{
            border-bottom: none;
        }}

        .action-flow-node {{
            background: white;
            border: 2px solid;
            border-radius: 8px;
            padding: 8px 12px;
            min-width: 80px;
            text-align: center;
            font-size: 11px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .action-flow-node:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}

        .action-flow-type {{
            font-weight: bold;
            color: #333;
            white-space: nowrap;
        }}

        .action-flow-label {{
            color: #1565c0;
            font-size: 10px;
            margin-top: 4px;
            max-width: 120px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .action-flow-value {{
            color: #2e7d32;
            font-size: 10px;
            background: #e8f5e9;
            padding: 2px 6px;
            border-radius: 3px;
            margin-top: 4px;
            max-width: 120px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .action-flow-arrow {{
            color: #bbb;
            font-size: 16px;
            flex-shrink: 0;
        }}

        .action-flow-arg {{
            color: #666;
            font-size: 9px;
            font-family: 'Courier New', monospace;
            background: #f5f5f5;
            padding: 2px 5px;
            border-radius: 3px;
            margin-top: 3px;
            max-width: 140px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .action-flow-node {{
            cursor: pointer;
        }}

        .action-flow-node.highlighted {{
            background: #fff3e0 !important;
            box-shadow: 0 0 10px rgba(255, 152, 0, 0.5) !important;
            transform: scale(1.05);
        }}

        .action-item.highlighted {{
            background: #fff3e0 !important;
            border: 3px solid #FF9800 !important;
            box-shadow: 0 0 15px rgba(255, 152, 0, 0.4) !important;
        }}

        .flow-node.active {{
            box-shadow: 0 0 20px rgba(255, 255, 255, 0.8) !important;
            transform: scale(1.08);
        }}

        .action-flow-failed {{
            background: #ffebee !important;
        }}

        .action-flow-warning {{
            font-size: 14px;
            text-align: center;
            margin-bottom: 2px;
        }}

        /* Action Stats */
        .stats-section {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .stats-chips {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }}

        .stat-chip {{
            display: flex;
            align-items: center;
            gap: 8px;
            background: #f5f5f5;
            border: 2px solid;
            border-radius: 25px;
            padding: 8px 16px;
            transition: transform 0.2s;
        }}

        .stat-chip:hover {{
            transform: scale(1.05);
        }}

        .stat-chip {{
            cursor: pointer;
            user-select: none;
            position: relative;
        }}

        .stat-chip.disabled {{
            opacity: 0.4;
            background: #eee;
        }}

        .stat-chip.disabled .chip-toggle {{
            display: none;
        }}

        .chip-toggle {{
            color: #4CAF50;
            font-size: 12px;
            margin-left: 5px;
        }}

        .filter-hint {{
            font-size: 12px;
            color: #999;
            font-weight: normal;
        }}

        .action-flow-node.hidden {{
            display: none;
        }}

        .action-flow-arrow.hidden {{
            display: none;
        }}

        .chip-icon {{
            font-size: 1.1rem;
        }}

        .chip-label {{
            font-size: 0.85rem;
            color: #333;
        }}

        .chip-count {{
            background: rgba(0, 0, 0, 0.1);
            border-radius: 12px;
            padding: 2px 10px;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        /* Filter Buttons */
        .filter-buttons {{
            background: white;
            border-radius: 10px;
            padding: 15px 20px;
            margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .filter-btn {{
            padding: 8px 16px;
            margin: 5px;
            border: none;
            border-radius: 5px;
            background: #e0e0e0;
            cursor: pointer;
            transition: all 0.3s;
        }}

        .filter-btn:hover {{
            background: #bdbdbd;
        }}

        .filter-btn.active {{
            background: #4CAF50;
            color: white;
        }}

        /* Region Styles */
        .region {{
            margin: 20px 0;
            border-radius: 10px;
            background: #e3f2fd;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        .region-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            background: rgba(255,255,255,0.8);
            border-left: 5px solid #2196F3;
            cursor: pointer;
            user-select: none;
            transition: background 0.2s;
        }}

        .region-header:hover {{
            background: rgba(255,255,255,0.95);
        }}

        .region-title {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .region-badge {{
            background: #2196F3;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-weight: bold;
            font-size: 14px;
        }}

        .region-url {{
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #333;
            font-weight: 600;
        }}

        .collapse-indicator {{
            color: #666;
            font-size: 12px;
            transition: transform 0.3s;
        }}

        .region.collapsed .collapse-indicator {{
            transform: rotate(-90deg);
        }}

        .region-stats {{
            color: #666;
            font-size: 13px;
        }}

        .region-action-count {{
            background: rgba(0,0,0,0.1);
            padding: 4px 12px;
            border-radius: 12px;
        }}

        .region-actions {{
            padding: 15px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .region.collapsed .region-actions {{
            display: none;
        }}

        /* Action Item Styles */
        .action-item {{
            position: relative;
            padding: 15px 15px 15px 70px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            transition: all 0.2s;
        }}

        .action-item:hover {{
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transform: translateX(3px);
        }}

        .action-item.error {{
            background: #ffebee;
            border: 2px solid #f44336;
        }}

        .action-navigation {{
            border: 3px solid #FF5722 !important;
            box-shadow: 0 0 10px rgba(255, 87, 34, 0.2);
        }}

        .navigation-badge {{
            display: inline-block;
            background: #FF5722;
            color: white;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: bold;
            margin-left: 8px;
        }}

        .action-number {{
            position: absolute;
            left: 15px;
            top: 15px;
            width: 40px;
            height: 40px;
            background: #4CAF50;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
        }}

        .action-item.error .action-number {{
            background: #f44336;
        }}

        .action-navigation .action-number {{
            background: #FF5722;
        }}

        .action-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .action-left {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .action-icon {{
            width: 28px;
            height: 28px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            color: white;
        }}

        .action-type {{
            font-size: 15px;
            font-weight: bold;
            color: #2196F3;
        }}

        .action-time {{
            font-size: 12px;
            color: #666;
        }}

        .execution-time {{
            display: inline-block;
            background: #FFC107;
            color: #333;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 500;
        }}

        .action-right {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .status-badge {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
        }}

        .status-badge.success {{
            background: #e8f5e9;
            color: #4CAF50;
        }}

        .status-badge.error {{
            background: #ffebee;
            color: #f44336;
        }}

        .action-description {{
            margin-top: 10px;
            color: #555;
            font-size: 13px;
            font-family: 'Courier New', monospace;
            background: #f9f9f9;
            padding: 8px 12px;
            border-radius: 5px;
            word-break: break-all;
        }}

        .ref-info {{
            margin-top: 10px;
            background: #e8f4fd;
            border: 1px solid #90caf9;
            border-left: 4px solid #2196F3;
            padding: 10px 15px;
            border-radius: 5px;
            font-size: 13px;
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .ref-id {{
            background: #2196F3;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            font-size: 12px;
        }}

        .ref-element-type {{
            background: #e1bee7;
            color: #7b1fa2;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 12px;
        }}

        .ref-aria-label {{
            color: #1565c0;
            font-weight: 600;
        }}

        .ref-value {{
            color: #2e7d32;
            font-family: 'Courier New', monospace;
            background: #e8f5e9;
            padding: 2px 8px;
            border-radius: 4px;
        }}

        .arg-info {{
            margin-top: 10px;
            background: #fff8e1;
            border: 1px solid #ffcc80;
            border-left: 4px solid #FF9800;
            padding: 10px 15px;
            border-radius: 5px;
            font-size: 13px;
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
        }}

        .arg-label {{
            background: #FF9800;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 12px;
        }}

        .arg-value {{
            color: #e65100;
            font-family: 'Courier New', monospace;
            word-break: break-all;
        }}

        .arg-url {{
            color: #1565c0;
            text-decoration: underline;
        }}

        .output-info {{
            background: #f0f7ff;
            padding: 10px;
            border-left: 3px solid #2196F3;
            margin-top: 10px;
            border-radius: 5px;
        }}

        .output-summary {{
            color: #333;
            font-size: 13px;
            line-height: 1.5;
        }}

        .action-item.error .output-info {{
            background: #ffcdd2;
            border-left-color: #f44336;
        }}

        /* Details */
        .inputs-outputs {{
            margin-top: 10px;
        }}

        .inputs-outputs summary {{
            cursor: pointer;
            color: #666;
            font-weight: bold;
            padding: 8px 12px;
            background: #f0f0f0;
            border-radius: 5px;
            font-size: 13px;
        }}

        .inputs-outputs summary:hover {{
            background: #e0e0e0;
        }}

        .detail-section {{
            margin-top: 10px;
        }}

        .detail-title {{
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
            font-weight: 600;
        }}

        .json-view {{
            background: #263238;
            color: #aed581;
            padding: 12px;
            border-radius: 5px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-word;
        }}

        /* Footer */
        footer {{
            text-align: center;
            padding: 30px;
            color: #666;
            font-size: 13px;
        }}

        footer a {{
            color: #2196F3;
            text-decoration: none;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .flow-diagram {{
                flex-direction: column;
            }}

            .flow-arrow {{
                transform: rotate(90deg);
            }}

            .action-header {{
                flex-direction: column;
                align-items: flex-start;
            }}

            .region-header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🌐 Browser Log Visualization</h1>
            <div class="summary">
                <strong>Log File:</strong> {escape_html(log_filename)}<br>
                <strong>Session ID:</strong> {escape_html(session_id)}<br>
                <strong>Total Actions:</strong> {len(filtered_actions)} |
                <strong>URL Regions:</strong> {len(url_regions)}
            </div>
        </header>

        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{len(filtered_actions)}</div>
                <div class="stat-label">Total Actions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(url_regions)}</div>
                <div class="stat-label">URL Regions</div>
            </div>
            <div class="stat-card" style="border-color: #4CAF50;">
                <div class="stat-value" style="color: #4CAF50;">{success_count}</div>
                <div class="stat-label">Success</div>
            </div>
            <div class="stat-card" style="border-color: #f44336;">
                <div class="stat-value" style="color: #f44336;">{failed_count}</div>
                <div class="stat-label">Failed</div>
            </div>
            <div class="stat-card" style="border-color: #FF9800;">
                <div class="stat-value" style="color: #FF9800;">{total_time/1000:.1f}s</div>
                <div class="stat-label">Total Time</div>
            </div>
        </div>

        <!-- URL Flow Diagram -->
        <div class="flow-section">
            <h2>🔗 URL Flow</h2>
            <div class="flow-diagram">
                {''.join(flow_nodes_html)}
            </div>
        </div>

        <!-- Action Distribution (Filter) -->
        <div class="stats-section">
            <h2>📊 Action Distribution <span class="filter-hint">(click to toggle visibility in flow)</span></h2>
            <div class="stats-chips">
                {''.join(stats_html)}
            </div>
        </div>

        <!-- Action Flow -->
        <div class="flow-section">
            <h2>⚡ Action Flow</h2>
            <div class="action-flow-diagram">
                {''.join(action_flow_html)}
            </div>
        </div>

        <!-- Filter Buttons -->
        <div class="filter-buttons">
            <button class="filter-btn active" onclick="filterActions('all')">All</button>
            <button class="filter-btn" onclick="filterActions('click')">Click</button>
            <button class="filter-btn" onclick="filterActions('type')">Type</button>
            <button class="filter-btn" onclick="filterActions('visit_page')">Visit Page</button>
            <button class="filter-btn" onclick="filterActions('get_page_snapshot')">Snapshot</button>
            <button class="filter-btn" onclick="filterActions('navigation')" style="background: #ffccbc;">Navigation</button>
            <button class="filter-btn" onclick="filterActions('error')" style="background: #ffcdd2;">Failed</button>
            <button class="filter-btn" onclick="expandAll()">Expand All</button>
            <button class="filter-btn" onclick="collapseAll()">Collapse All</button>
        </div>

        <!-- Timeline Regions -->
        <div class="timeline">
            {''.join(regions_html)}
        </div>

        <footer>
            <p>Generated from: {escape_html(log_filename)}</p>
            <p>Powered by <a href="https://github.com/camel-ai/camel">CAMEL-AI</a> Hybrid Browser Toolkit</p>
        </footer>
    </div>

    <script>
        // Toggle region collapse
        function toggleRegion(idx) {{
            const region = document.getElementById('region-' + idx);
            region.classList.toggle('collapsed');
        }}

        // Scroll to region
        function scrollToRegion(idx) {{
            const region = document.getElementById('region-' + idx);
            if (region) {{
                region.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                // Expand if collapsed
                region.classList.remove('collapsed');
            }}
        }}

        // Filter actions
        function filterActions(type) {{
            // Update active button
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.classList.remove('active');
                if (btn.textContent.toLowerCase().includes(type) ||
                    (type === 'all' && btn.textContent === 'All') ||
                    (type === 'navigation' && btn.textContent === 'Navigation') ||
                    (type === 'error' && btn.textContent === 'Failed')) {{
                    btn.classList.add('active');
                }}
            }});

            // Filter action items
            document.querySelectorAll('.action-item').forEach(item => {{
                const itemType = item.dataset.type;
                const isNavigation = item.classList.contains('action-navigation');
                const isError = item.classList.contains('error');

                let show = false;
                if (type === 'all') {{
                    show = true;
                }} else if (type === 'navigation') {{
                    show = isNavigation;
                }} else if (type === 'error') {{
                    show = isError;
                }} else {{
                    show = itemType === type;
                }}

                item.style.display = show ? 'block' : 'none';
            }});
        }}

        // Expand all regions
        function expandAll() {{
            document.querySelectorAll('.region').forEach(region => {{
                region.classList.remove('collapsed');
            }});
        }}

        // Collapse all regions
        function collapseAll() {{
            document.querySelectorAll('.region').forEach(region => {{
                region.classList.add('collapsed');
            }});
        }}

        // Scroll to specific action and highlight it
        function scrollToAction(actionIdx) {{
            const actionElement = document.getElementById('action-' + actionIdx);
            if (actionElement) {{
                // 展开所在的 region
                const region = actionElement.closest('.region');
                if (region) {{
                    region.classList.remove('collapsed');
                }}

                // 滚动到 action
                actionElement.scrollIntoView({{ behavior: 'smooth', block: 'center' }});

                // 高亮 action
                clearAllHighlights();
                actionElement.classList.add('highlighted');

                // 3秒后移除高亮
                setTimeout(() => {{
                    actionElement.classList.remove('highlighted');
                }}, 3000);
            }}
        }}

        // Highlight all actions in a region
        function highlightRegion(regionIdx) {{
            clearAllHighlights();

            // 高亮 URL flow 节点
            document.querySelectorAll('.flow-node').forEach(node => {{
                node.classList.remove('active');
                if (node.dataset.regionIdx == regionIdx) {{
                    node.classList.add('active');
                }}
            }});

            // 高亮 Action flow 中对应的节点，并找到第一个节点用于滚动
            let firstActionFlowNode = null;
            document.querySelectorAll('.action-flow-node').forEach(node => {{
                if (node.dataset.regionIdx == regionIdx) {{
                    node.classList.add('highlighted');
                    if (!firstActionFlowNode) {{
                        firstActionFlowNode = node;
                    }}
                }}
            }});

            // 滚动到 Action Flow 中的第一个对应节点
            if (firstActionFlowNode) {{
                firstActionFlowNode.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            }}

            // 5秒后移除高亮
            setTimeout(() => {{
                clearAllHighlights();
            }}, 5000);
        }}

        // Clear all highlights
        function clearAllHighlights() {{
            document.querySelectorAll('.highlighted').forEach(el => {{
                el.classList.remove('highlighted');
            }});
            document.querySelectorAll('.flow-node.active').forEach(el => {{
                el.classList.remove('active');
            }});
        }}

        // Toggle action type visibility in flow
        const hiddenActionTypes = new Set();

        function toggleActionType(actionType) {{
            const chip = document.querySelector(`.stat-chip[data-action-type="${{actionType}}"]`);

            if (hiddenActionTypes.has(actionType)) {{
                // Show
                hiddenActionTypes.delete(actionType);
                chip.classList.remove('disabled');
            }} else {{
                // Hide
                hiddenActionTypes.add(actionType);
                chip.classList.add('disabled');
            }}

            // Update action flow visibility
            updateActionFlowVisibility();
        }}

        function updateActionFlowVisibility() {{
            document.querySelectorAll('.action-flow-row').forEach(row => {{
                const nodes = row.querySelectorAll('.action-flow-node');
                const arrows = row.querySelectorAll('.action-flow-arrow');

                // First pass: determine visibility
                let visibleCount = 0;
                nodes.forEach(node => {{
                    const actionType = node.dataset.actionType;
                    if (hiddenActionTypes.has(actionType)) {{
                        node.classList.add('hidden');
                    }} else {{
                        node.classList.remove('hidden');
                        visibleCount++;
                    }}
                }});

                // Second pass: update arrows visibility
                let lastVisibleIdx = -1;
                const allElements = Array.from(row.children);

                allElements.forEach((el, idx) => {{
                    if (el.classList.contains('action-flow-node')) {{
                        if (!el.classList.contains('hidden')) {{
                            // Show arrow before this node if there was a previous visible node
                            if (lastVisibleIdx >= 0 && idx > 0) {{
                                // Find arrow between lastVisibleIdx and idx
                                for (let i = lastVisibleIdx + 1; i < idx; i++) {{
                                    if (allElements[i].classList.contains('action-flow-arrow')) {{
                                        allElements[i].classList.remove('hidden');
                                        break;
                                    }}
                                }}
                            }}
                            lastVisibleIdx = idx;
                        }}
                    }} else if (el.classList.contains('action-flow-arrow')) {{
                        // Hide all arrows first, they'll be shown as needed
                        el.classList.add('hidden');
                    }}
                }});

                // Re-show arrows between visible nodes
                let prevVisible = null;
                allElements.forEach((el, idx) => {{
                    if (el.classList.contains('action-flow-node') && !el.classList.contains('hidden')) {{
                        if (prevVisible !== null) {{
                            // Show arrow between prevVisible and current
                            for (let i = prevVisible + 1; i < idx; i++) {{
                                if (allElements[i].classList.contains('action-flow-arrow')) {{
                                    allElements[i].classList.remove('hidden');
                                    break;
                                }}
                            }}
                        }}
                        prevVisible = idx;
                    }}
                }});
            }});
        }}
    </script>
</body>
</html>
'''
    return html


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = sys.argv[1]

    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    # 解析日志文件
    print(f"Parsing log file: {input_path}")
    actions = parse_log_file(input_path)
    print(f"Found {len(actions)} actions")

    if not actions:
        print("Error: No actions found in log file")
        sys.exit(1)

    # 获取 session_id
    session_id = actions[0].get('session_id') or 'unknown'
    log_filename = os.path.basename(input_path)

    # 确定输出路径
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        # 默认在同目录生成 _visualization.html 后缀的文件
        base_name = os.path.splitext(log_filename)[0]
        output_path = os.path.join(
            os.path.dirname(input_path) or '.',
            f"{base_name}_visualization.html"
        )

    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 生成 HTML
    print("Generating HTML visualization...")
    html_content = generate_html(actions, session_id, log_filename)

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✓ HTML visualization saved to: {output_path}")
    print(f"  - Session ID: {session_id}")
    print(f"  - Actions: {len(actions)}")


if __name__ == '__main__':
    main()
