#!/usr/bin/env python3
import asyncio
import psutil
import time
import subprocess
from datetime import datetime
from camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit_ts import HybridBrowserToolkit
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ],
)

logging.getLogger('camel.agents').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)
logging.getLogger('camel.toolkits.hybrid_browser_toolkit').setLevel(logging.DEBUG)

BROWSER_COUNT = 3
CDP_PORT_START = 9222
USER_DATA_DIR_PREFIX = "/tmp/chrome-cdp-parallel"

model_backend = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
    model_config_dict={"temperature": 0.0, "top_p": 1},
)

custom_tools = [
    "browser_open",
    "browser_visit_page",
    "browser_click",
    "browser_type",
    "browser_enter",
]

TASK_PROMPT = r"""
open browser,visit file:///Users/puzhen/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_pv2qqr16e4k622_c24e/msg/file/2025-09/mock_website-1.html
 you can see a form, please fill this form with random string
"""

async def monitor_memory():
    """监控内存使用情况"""
    memory_data = []
    start_time = time.time()
    
    while True:
        memory = psutil.virtual_memory()
        data = {
            'timestamp': time.time() - start_time,
            'total_mb': memory.total / 1024 / 1024,
            'available_mb': memory.available / 1024 / 1024,
            'used_mb': memory.used / 1024 / 1024,
            'percent': memory.percent
        }
        memory_data.append(data)
        
        if data['timestamp'] > 120:
            break
            
        await asyncio.sleep(1)

    return memory_data

def launch_chrome_with_cdp(port):
    """启动带CDP的Chrome浏览器"""
    user_data_dir = f"{USER_DATA_DIR_PREFIX}-{port}"
    cmd = [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        f'--remote-debugging-port={port}',
        '--no-first-run',
        '--no-default-browser-check',
        f'--user-data-dir={user_data_dir}'
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    return process, user_data_dir

async def run_browser_agent(index, cdp_port):
    """在单个浏览器实例上运行agent"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 启动Agent #{index + 1} (CDP端口: {cdp_port})")
    
    web_toolkit = HybridBrowserToolkit(
        headless=False,
        cdp_url=f"http://localhost:{cdp_port}",
        browser_log_to_file=True,
        enabled_tools=custom_tools,
        stealth=True,
        viewport_limit=True,
        default_start_url="about:blank",
    )
    
    agent = ChatAgent(
        model=model_backend,
        tools=[*web_toolkit.get_tools()],
        toolkits_to_register_agent=[web_toolkit],
        max_iteration=10,
    )
    
    try:
        start_task_time = time.time()
        response = await agent.astep(TASK_PROMPT)
        end_task_time = time.time()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Agent #{index + 1} 任务完成，耗时: {end_task_time - start_task_time:.2f}秒")
        
        result_content = response.msgs[0].content if response.msgs else "<no response>"
        with open(f'agent_{index + 1}_result.md', 'w') as f:
            f.write(f"# Agent #{index + 1} 结果\n\n")
            f.write(f"CDP端口: {cdp_port}\n")
            f.write(f"任务耗时: {end_task_time - start_task_time:.2f}秒\n\n")
            f.write("## 任务结果:\n\n")
            f.write(result_content)
        
        return {
            'index': index,
            'success': True,
            'duration': end_task_time - start_task_time,
            'result': result_content
        }
        
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Agent #{index + 1} 执行失败: {e}")
        return {
            'index': index,
            'success': False,
            'error': str(e)
        }
    
    finally:
        try:
            await web_toolkit.browser_close()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Agent #{index + 1} 浏览器连接已关闭")
        except:
            pass

async def main():
    print(f"========== 并行浏览器Agent测试开始 ==========")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"计划启动浏览器实例数: {BROWSER_COUNT}")
    print(f"任务提示词: {TASK_PROMPT[:100]}...")
    print()
    
    initial_memory = psutil.virtual_memory()
    print(f"初始内存状态:")
    print(f"  总内存: {initial_memory.total / 1024 / 1024:.2f} MB")
    print(f"  可用内存: {initial_memory.available / 1024 / 1024:.2f} MB")
    print(f"  已用内存: {initial_memory.used / 1024 / 1024:.2f} MB")
    print(f"  使用率: {initial_memory.percent:.1f}%")
    print()
    
    print("========== 第一阶段：启动Chrome实例 ==========")
    chrome_processes = []
    for i in range(BROWSER_COUNT):
        port = CDP_PORT_START + i
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 启动Chrome实例 #{i + 1} (CDP端口: {port})")
        process, user_data_dir = launch_chrome_with_cdp(port)
        chrome_processes.append((process, port, user_data_dir))

    print("\n等待所有Chrome实例完全启动...")
    await asyncio.sleep(5)
    
    memory_task = asyncio.create_task(monitor_memory())
    
    print("\n========== 第二阶段：并行执行Agent任务 ==========")
    agent_tasks = []
    for i in range(BROWSER_COUNT):
        port = CDP_PORT_START + i
        task = asyncio.create_task(run_browser_agent(i, port))
        agent_tasks.append(task)
        await asyncio.sleep(1)
    
    results = await asyncio.gather(*agent_tasks)
    
    successful_agents = [r for r in results if r.get('success', False)]
    failed_agents = [r for r in results if not r.get('success', False)]
    
    print(f"\n========== 任务执行结果统计 ==========")
    print(f"成功完成任务的Agent数: {len(successful_agents)}/{BROWSER_COUNT}")
    print(f"失败的Agent数: {len(failed_agents)}/{BROWSER_COUNT}")
    
    if successful_agents:
        avg_duration = sum(r['duration'] for r in successful_agents) / len(successful_agents)
        print(f"平均任务耗时: {avg_duration:.2f}秒")
    
    memory_data = await memory_task
    
    print("\n========== 清理阶段 ==========")
    print("终止所有Chrome进程...")
    for i, (process, port, user_data_dir) in enumerate(chrome_processes):
        try:
            process.terminate()
            process.wait(timeout=5)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Chrome进程 #{i + 1} (端口: {port}) 已终止")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 终止Chrome进程 #{i + 1} 时出错: {e}")
            try:
                process.kill()
            except:
                pass
    
    print("\n清理临时目录...")
    for _, _, user_data_dir in chrome_processes:
        try:
            subprocess.run(['rm', '-rf', user_data_dir], capture_output=True)
        except:
            pass
    
    await asyncio.sleep(5)
    
    final_memory = psutil.virtual_memory()
    print(f"\n最终内存状态:")
    print(f"  总内存: {final_memory.total / 1024 / 1024:.2f} MB")
    print(f"  可用内存: {final_memory.available / 1024 / 1024:.2f} MB")
    print(f"  已用内存: {final_memory.used / 1024 / 1024:.2f} MB")
    print(f"  使用率: {final_memory.percent:.1f}%")
    
    print(f"\n========== 内存使用分析 ==========")
    
    max_used = max(memory_data, key=lambda x: x['used_mb'])
    min_available = min(memory_data, key=lambda x: x['available_mb'])
    
    print(f"最大内存使用: {max_used['used_mb']:.2f} MB (在 {max_used['timestamp']:.1f}秒时)")
    print(f"最小可用内存: {min_available['available_mb']:.2f} MB (在 {min_available['timestamp']:.1f}秒时)")
    print(f"内存增长: {max_used['used_mb'] - memory_data[0]['used_mb']:.2f} MB")
    
    if len(successful_agents) > 0:
        print(f"平均每个浏览器占用: {(max_used['used_mb'] - memory_data[0]['used_mb']) / len(successful_agents):.2f} MB")
    

    print(f"========== 测试完成 ==========")

if __name__ == "__main__":
    asyncio.run(main())