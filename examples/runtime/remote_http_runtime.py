from camel.runtime import RemoteHttpRuntime
from camel.toolkits import MATH_FUNCS

if __name__ == "__main__":
    runtime = RemoteHttpRuntime("localhost").add(MATH_FUNCS, "camel.toolkits.MATH_FUNCS").build()
    print("Waiting for runtime to be ready...")
    runtime.wait()
    print("Runtime is ready.")
    add, sub, mul = runtime.get_tools()
    print(f"Add 1 + 2: {add.func(1, 2)}")
    print(f"Subtract 5 - 3: {sub.func(5, 3)}")
    print(f"Multiply 2 * 3: {mul.func(2, 3)}")

    print("Documents: ", runtime.docs)
    # you can open this url in browser to see the API Endpoints
    # before the runtime is stopped.
    # time.sleep(60)

    # call runtime.stop() if you want to stop the runtime manually
    # atherwise it will be stopped automatically when the program ends


"""
Waiting for runtime to be ready...
Runtime is ready.
Add 1 + 2: 3
Subtract 5 - 3: 2
Multiply 2 * 3: 6
Documents:  http://localhost:8000/docs
"""
