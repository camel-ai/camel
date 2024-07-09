from openai import OpenAI
import os

# Set up your OpenAI API key from environment variable
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def text_to_persona(text, action="read"):
    """
    Infers a specific persona who is likely to [read|write|like|dislike|...] the given text.

    Args:
    text (str): The input text for which to infer a persona.
    action (str): The action associated with the persona (default is "read").

    Returns:
    str: The inferred persona description.
    """
    # System prompt for the assistant
    system_prompt = "You are a helpful assistant."

    # User prompt template
    user_prompt = f"Who is likely to {action} the following text? Provide a detailed and specific persona description.\n\nText: {text}"

    # Get response from the model
    response = client.chat.completions.create(model="gpt-4",
    temperature=0.7,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])

    # Extract and return the persona description
    persona_description = response.choices[0].message.content
    return persona_description


# Example usage
# if __name__ == "__main__":
#     example_text = """
#     Clinical Guideline: Administration of Injections in Pediatric Patients
#     Purpose: To provide standardized care for pediatric patients requiring injections, ensuring safety, ...
#     """
#     inferred_persona = text_to_persona(example_text, action="read")
#     print(inferred_persona)
