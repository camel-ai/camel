from pydantic import BaseModel, Field
import pydantic
import openai


# pydantic basemodel as input params format
class JokeResponse(BaseModel):
    joke: str = Field(description="a joke")
    funny_level: str = Field(description="Funny level, from 1 to 10")

def return_json_format_response(joke: str, funny_level: str):
    return {"joke": joke, "funny_level": funny_level}

def output_parse_json(pydantic_params: BaseModel):
    json_schema = parse_pydantic_as_json(pydantic_params)
    # print(json_schema)
    tools =[json_schema]
    query = f"Tell a jokes."
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": query}],
        tools=tools, 
    )
    response_message = response.choices[0].message.tool_calls[0].function. \
    arguments
    # response_output_json_format = \
    # response_message['function_call']['arguments']
    return response_message


def parse_pydantic_as_json(pydantic_params: BaseModel):
    source_dict = {
        "type": "function",
        "function": {
            "name": "return_json_format_response",
            "description": "Return the respnse of json format",
            "parameters": {
                "type": "object",
                "properties": {},
                },
                "required": [],
        }
    }

    pydantic_params_schema = get_pydantic_object_schema(pydantic_params)
    source_dict["function"]["parameters"]["properties"] = \
    pydantic_params_schema["properties"]
    source_dict["function"]["required"] = \
    pydantic_params_schema["required"]

    return source_dict

def get_pydantic_object_schema(pydantic_params: BaseModel):
    PYDANTIC_MAJOR_VERSION = get_pydantic_major_version()
    if PYDANTIC_MAJOR_VERSION == 2:
            if issubclass(pydantic_params, pydantic.BaseModel):
                return pydantic_params.model_json_schema()
            elif issubclass(pydantic_params, pydantic.v1.BaseModel):
                return pydantic_params.schema()
    return pydantic_params.schema()

def get_pydantic_major_version() -> int:
    """Get the major version of Pydantic."""
    try:
        import pydantic

        return int(pydantic.__version__.split(".")[0])
    except ImportError:
        return 0


if __name__ == "__main__":
    
    res = output_parse_json(JokeResponse)
    print(res)