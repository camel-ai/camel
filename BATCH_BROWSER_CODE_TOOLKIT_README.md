# Batch Browser Code Toolkit 使用说明

## 概述

`batch_browser_code_toolkit.py` 是一个基于 `BrowserCodeToolkit` 的批处理脚本，可以从 JSONL 文件中加载任务并批量处理。

## 主要特性

1. **批量任务处理**: 从 JSONL 文件加载并顺序处理多个任务
2. **自动验证**: 使用独立的验证 Agent 检查任务完成质量
3. **结果保存**: 每个任务结果单独保存，同时生成汇总文件
4. **统计分析**: 自动生成成功率等统计信息
5. **灵活配置**: 支持任务索引范围和关键词过滤

## 与 batch_google_flights.py 的区别

| 特性 | batch_google_flights.py | batch_browser_code_toolkit.py |
|------|------------------------|------------------------------|
| 工具包 | HybridBrowserToolkit | BrowserCodeToolkit |
| 浏览器控制方式 | 直接工具调用 | 通过 Python 代码执行 |
| 代码执行 | 不支持 | 支持编写 Python 代码控制浏览器 |
| 系统提示 | 简单提示 | 详细的代码编写指导 |
| 截图上下文注入 | 支持 | **自动支持** ✨ |

## ✨ 新功能：截图上下文自动注入

**重要更新**：现在当 Agent 在代码中调用 `browser.get_screenshot()` 时，生成的截图会**自动注入到 Agent 的上下文中**！

### 工作原理

```python
# Agent 写的代码
code = '''
browser.open()
browser.visit_page("https://www.google.com")

# 获取截图 - 这会自动注入到上下文中
screenshot = browser.get_screenshot()
print("Screenshot captured!")
'''

# 执行后，截图会自动添加到 Agent 的上下文中
# Agent 在后续交互中可以"看到"截图内容
```

### 优势

1. **视觉验证**：Agent 可以看到页面的实际状态，而不只是文本快照
2. **自动工作**：无需任何额外配置，调用 `browser.get_screenshot()` 即可
3. **增强决策**：Agent 可以基于视觉内容做出更准确的判断
4. **更好的调试**：出现问题时，Agent 可以看到实际的页面状态

### 使用示例

在批处理任务中，Agent 可以：

```python
# 完成搜索任务
browser.type(ref="5", text="flight search")
browser.click(ref="10")

# 截图验证结果
screenshot = browser.get_screenshot()

# Agent 在下次交互时可以描述：
# "我看到搜索结果页面显示了3个航班选项..."
```

### 日志输出

当捕获截图时，你会在日志中看到：

```
🤖 AGENT CODE EXECUTION
==========================================
...
📸 Captured 1 screenshot(s) - will be added to context
==========================================
```

详细的实现说明请查看：`SCREENSHOT_CONTEXT_INJECTION_IMPLEMENTATION.md`

## 配置参数

在 `main()` 函数中可以修改以下参数：

```python
START_INDEX = 428  # 起始任务索引
END_INDEX = None   # 结束任务索引 (None = 处理到文件末尾)
FILTER_KEYWORD = 'google.com/travel/flights'  # 网站过滤关键词 (None = 不过滤)
```

### 示例配置

1. **处理所有 Google Flights 任务 (从索引 428 开始)**:
```python
START_INDEX = 428
END_INDEX = None
FILTER_KEYWORD = 'google.com/travel/flights'
```

2. **处理特定范围的任务 (索引 0-100)**:
```python
START_INDEX = 0
END_INDEX = 100
FILTER_KEYWORD = None
```

3. **处理所有 Amazon 相关任务**:
```python
START_INDEX = 0
END_INDEX = None
FILTER_KEYWORD = 'amazon'
```

## 使用方法

### 1. 安装依赖

确保已安装所需的包：
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件并配置 Azure OpenAI 凭据：
```
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### 3. 修改 JSONL 文件路径

在脚本中修改 `JSONL_PATH` 变量：
```python
JSONL_PATH = '/path/to/your/data.jsonl'
```

### 4. 运行脚本

```bash
python batch_browser_code_toolkit.py
```

## 输出结构

脚本会在 `batch_browser_code_results/` 目录下生成以下文件：

```
batch_browser_code_results/
├── task_428_result.json      # 单个任务结果
├── task_429_result.json
├── ...
├── all_results_summary.json  # 所有任务汇总
└── statistics.json           # 统计信息
```

### 单个任务结果格式

```json
{
  "task_index": 428,
  "website": "https://www.google.com/travel/flights/",
  "question": "搜索从爱丁堡到曼彻斯特的航班...",
  "task_prompt": "完整的任务提示词...",
  "response": "Agent 的回复...",
  "verification": {
    "verified": true,
    "verification_text": "验证结果...",
    "timestamp": "2025-12-16T10:30:00"
  },
  "error": null,
  "timestamp": "2025-12-16T10:25:00"
}
```

### 汇总文件格式

```json
{
  "configuration": {
    "start_index": 428,
    "end_index": null,
    "filter_keyword": "google.com/travel/flights",
    "jsonl_path": "/path/to/data.jsonl"
  },
  "total_tasks": 50,
  "processed_tasks": 50,
  "results": [...]
}
```

### 统计文件格式

```json
{
  "total_tasks": 50,
  "successful": 45,
  "failed": 5,
  "success_rate": 0.9,
  "timestamp": "2025-12-16T12:00:00"
}
```

## 自定义工具

可以通过修改 `custom_tools` 列表来启用/禁用特定的浏览器工具：

```python
custom_tools = [
    "browser_open",           # 打开浏览器
    "browser_close",          # 关闭浏览器
    "browser_visit_page",     # 访问页面
    "browser_back",           # 后退
    "browser_forward",        # 前进
    "browser_click",          # 点击元素
    "browser_type",           # 输入文本
    "browser_enter",          # 按回车
    "browser_get_page_snapshot",    # 获取页面快照
    "browser_get_som_screenshot",   # 获取标注截图
    # "browser_scroll",       # 滚动页面 (可选)
    # "browser_console_exec", # 执行控制台命令 (高级功能)
]
```

## 日志和调试

### 修改日志级别

在脚本开头修改日志配置：
```python
logging.basicConfig(
    level=logging.DEBUG,  # 改为 DEBUG 可看到更详细的日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()],
)
```

### 查看浏览器操作日志

每个任务执行时，BrowserCodeToolkit 会在 `camel_logs/` 目录下生成详细的日志文件。

## 性能优化建议

1. **调整任务间隔**: 在 `main()` 函数中可以调整任务之间的延迟：
```python
# 在每个任务之间等待 2 秒
await asyncio.sleep(2)
```

2. **控制并发**: 当前脚本是顺序处理，如需并发处理需要修改代码结构

3. **资源清理**: 每个任务完成后会自动清理浏览器资源，避免内存泄漏

## 常见问题

### Q1: 任务失败如何重试？
A: 可以从失败的索引重新开始，修改 `START_INDEX` 即可。

### Q2: 如何只处理失败的任务？
A: 可以编写脚本读取 `all_results_summary.json`，提取失败任务的索引，然后单独处理。

### Q3: 浏览器窗口太多怎么办？
A: 将 `headless=True` 可以使用无头模式运行浏览器。

### Q4: 验证总是失败怎么办？
A: 可以修改验证提示词或跳过验证步骤（注释掉验证相关代码）。

## 进阶用法

### 自定义验证逻辑

可以修改 `verify_response()` 函数来实现自定义的验证逻辑：

```python
async def verify_response(question: str, response: str) -> dict:
    # 自定义验证规则
    if "价格" in question and "$" not in response:
        return {
            "verified": False,
            "verification_text": "响应中缺少价格信息",
            "timestamp": datetime.now().isoformat()
        }
    # ... 更多自定义规则
```

### 添加错误重试机制

在 `process_single_task()` 中可以添加重试逻辑：

```python
max_retries = 3
for attempt in range(max_retries):
    try:
        response = await agent.astep(task_prompt)
        break  # 成功则跳出
    except Exception as e:
        if attempt < max_retries - 1:
            print(f"重试 {attempt + 1}/{max_retries}...")
            await asyncio.sleep(5)
        else:
            raise
```

## 相关文件

- `examples/toolkits/browser_code_toolkit_example.py` - 单任务示例
- `batch_google_flights.py` - HybridBrowserToolkit 批处理示例
- `camel/toolkits/browser_code_toolkit.py` - BrowserCodeToolkit 源代码

## 许可证

Apache License 2.0
