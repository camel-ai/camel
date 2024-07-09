from text_to_persona import text_to_persona
from persona_to_persona import persona_to_persona

# Example usage
if __name__ == "__main__":
    example_text = """
    Clinical Guideline: Administration of Injections in Pediatric Patients
    Purpose: To provide standardized care for pediatric patients requiring injections, ensuring safety, ...
    """

    inferred_persona = text_to_persona(example_text, action="read")
    print(f"Inferred Persona:\n{inferred_persona}\n")

    related_personas = persona_to_persona(inferred_persona)
    print(f"Related Personas:\n{related_personas}")
