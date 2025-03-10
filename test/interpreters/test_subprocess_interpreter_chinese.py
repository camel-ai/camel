import sys
from pathlib import Path
from camel.interpreters import SubprocessInterpreter

def test_subprocess_interpreter():
    # 创建解释器实例，关闭确认提示，打开输出显示
    interpreter = SubprocessInterpreter(
        require_confirm=False,
        print_stdout=True,
        print_stderr=True,
    )
    
    print(f"\nPython 版本: {sys.version}")
    print(f"运行路径: {sys.executable}")
    print("临时文件位置:", Path(sys.executable).parent / "Temp")
    
    try:
        # 测试用例1：简单中文输出
        code1 = '''
print("=== 测试1：基本中文输出 ===")
print("测试中文输出")
print("Test English output")
'''
        print("\n运行测试1...")
        result1 = interpreter.run(code1, "python")
        print(f"结果1: {result1}")

        # 测试用例2：中文文件操作
        code2 = '''
print("=== 测试2：文件操作 ===")
import os
test_file = "测试.txt"
print(f"当前目录: {os.getcwd()}")
print(f"创建文件: {test_file}")
with open(test_file, "w", encoding="utf-8") as f:
    f.write("测试文件写入")
print("文件已创建")
'''
        print("\n运行测试2...")
        result2 = interpreter.run(code2, "python")
        print(f"结果2: {result2}")

        # 测试用例3：复杂的中文处理（列表推导和字符串操作）
        code3 = '''
print("=== 测试3：复杂中文处理 ===")
# 创建一个包含中文的列表
words = ["你好", "世界", "测试", "Python"]
# 使用列表推导
lengths = [len(word) for word in words]
print(f"中文词列表: {words}")
print(f"长度列表: {lengths}")
# 字符串拼接
result = "，".join(words)
print(f"拼接结果: {result}")
'''
        print("\n运行测试3...")
        result3 = interpreter.run(code3, "python")
        print(f"结果3: {result3}")

    except Exception as e:
        print(f"\n错误: {type(e).__name__}: {str(e)}")
        import traceback
        print("\n详细错误信息:")
        traceback.print_exc()

if __name__ == "__main__":
    test_subprocess_interpreter()
