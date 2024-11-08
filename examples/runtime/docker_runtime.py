from camel.toolkits import MATH_FUNCS
from camel.toolkits import CodeExecutionToolkit
from camel.runtime import DockerRuntime


if __name__ == "__main__":
    runtime = (
        DockerRuntime("xukunliu/camel")
        .add(MATH_FUNCS, "camel.toolkits.MATH_FUNCS")
        .add(CodeExecutionToolkit().get_tools(), "camel.toolkits.CodeExecutionToolkit")
    )

    with runtime as r: # using with statement to automatically close the runtime
        print("Waiting for runtime to be ready...")
        while not r.ok:
            r.wait()
        print("Runtime is ready.")

        tools = r.get_tools()

        add, sub, mul = tools[:3]
        code_exec = tools[3]

        # without kwargs
        print(f"Add 1 + 2: {add.func(1, 2)}")
        print(f"Subtract 5 - 3: {sub.func(5, 3)}")
        print(f"Multiply 2 * 3: {mul.func(2, 3)}")
        print(f"Execute code: {code_exec.func('1 + 2')}")

        # with kwargs
        print(f"Add 1 + 2: {add.func(a=1, b=2)}")
        print(f"Subtract 5 - 3: {sub.func(a=5, b=3)}")
        print(f"Multiply 2 * 3: {mul.func(a=2, b=3)}")
        print(f"Execute code: {code_exec.func(code='1 + 2')}")
        
    # you can also use the runtime without the with statement
    # runtime.build()
    # runtime.stop()

"""
Add 1 + 2: 3
Subtract 5 - 3: 2
Multiply 2 * 3: 6
Execute code: Executed the code below:
```py
1 + 2
```
> Executed Results:
3
"""
