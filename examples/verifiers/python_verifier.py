import asyncio
from camel.verifiers import PythonVerifier, Response

async def test_verifier():
    verifier = PythonVerifier(required_packages=["numpy", "pandas"])
    await verifier.setup()

    result = await verifier.verify(Response(llm_response="print('Hello, world!')"))

    print(result.status)  # SUCCESS
    print(result)  # "Hello, world!"

    await verifier.teardown()

async def test_verifier_np():
    verifier = PythonVerifier(required_packages=["numpy", "pandas"])
    await verifier._setup()  # Ensure the virtual environment is set up

    # Example numpy script to verify installation and functionality
    numpy_test_code = """
import numpy as np
a = np.array([1, 2, 3])
b = np.array([4, 5, 6])
result = np.dot(a, b)
result
"""

    # Create a response object with the numpy script
    response = Response(llm_response=numpy_test_code)
    result = await verifier._verify_implementation(response)

    # Print verification results
    print(f"Status: {result}")

    await verifier._teardown()  # Clean up the virtual environment

# Properly run the async function
asyncio.run(test_verifier())


# Properly run the async function
asyncio.run(test_verifier_np())
