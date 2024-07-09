from openai import OpenAI
import os

# Set up your OpenAI API key from environment variable
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def persona_to_persona(persona):
    """
    Derives additional personas based on interpersonal relationships from an initial persona.

    Args:
    persona (str): The initial persona description.

    Returns:
    dict: A dictionary of related personas with their relationship types.
    """
    system_prompt = "You are a helpful assistant."
    user_prompt = f"Given the following persona: \"{persona}\", who is likely to be in a close relationship with this persona? Describe the related personas and their relationships."

    response = client.chat.completions.create(model="gpt-4",
    temperature=0.7,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])

    related_personas = response.choices[0].message.content
    return related_personas


# Example usage
if __name__ == "__main__":
    inferred_persona = """
    A pediatric nurse, who is responsible for administering injections to children and ensuring their safety and comfort during the procedure.
    """
    related_personas = persona_to_persona(inferred_persona)
    print(f"Related Personas:\n{related_personas}")
