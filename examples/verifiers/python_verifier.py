import asyncio
from camel.verifiers import PythonVerifier, Response

async def test_verifier():
    verifier = PythonVerifier()
    await verifier.setup()

    result = await verifier.verify(Response(llm_response="print('Hello, world!')"))

    print(result.status)  # SUCCESS
    print(result)  # "Hello, world!"

    await verifier.teardown()

# Properly run the async function
asyncio.run(test_verifier())
