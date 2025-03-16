from models import ResponseFormat, AnswerFormat
from pydantic import BaseModel
import sympy as sp
import re
import math
from sympy.parsing.sympy_parser import parse_expr
from sympy.parsing.latex import parse_latex
from sympy.physics import units

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  

class ResponseFormat(BaseModel):
    reasoning: str
    code: str
    unit: str

class AnswerFormat(BaseModel):
    gt_answer: str
    unit: str

# A dictionary to allow parsing of common unit expressions.
allowed_units = {
    "m": units.meter,
    "meter": units.meter,
    "meters": units.meter,
    "s": units.second,
    "second": units.second,
    "seconds": units.second,
    "kg": units.kilogram,
    "kilogram": units.kilogram,
    "kilograms": units.kilogram,
    "N": units.newton,
    "newton": units.newton,
    "J": units.joule,
    "joule": units.joule,
    "\\circ": units.degree,
    "degree": units.degree,
    "degrees": units.degree,
    "K": units.kelvin,
    "kelvin": units.kelvin,
    "g": units.gram,
    "gram": units.gram,
    "grams": units.gram,
    "cm": units.centimeter,
    "centimeter": units.centimeter,
    # Extend this dictionary as needed.
}

def clean_python_code(raw_code: str) -> str:
    """
    Extracts and cleans Python code from an LLM response.
    
    Parameters:
        llm_response (str): The raw response from an LLM containing Python code
        
    Returns:
        str: Cleaned Python code ready for execution
    """
    # Handle different code formats
    code = raw_code.strip()
    
    # Case 1: Code in markdown blocks with ```python
    if "```" in code:
        parts = code.split("```")
        for i, part in enumerate(parts):
            if part.strip().lower().startswith("python"):
                if i+1 < len(parts):
                    code = parts[i+1].strip()
                    break
    
    # Case 2: Code starts with 'python' without code blocks
    elif code.lower().startswith("python"):
        code = code[len("python"):].strip()
    
    # Case 3: Handle code with escaped newlines \n
    code = code.replace("\\n", "\n")
    
    # Case 4: Remove any surrounding quotes
    if (code.startswith("'") and code.endswith("'")) or (code.startswith('"') and code.endswith('"')):
        code = code[1:-1]
    
    # Remove any stray single quotes around individual code lines
    code = re.sub(r"^'(.*)'$", r"\1", code, flags=re.MULTILINE)
    
    # Handle cases where entire code is wrapped in quotes with commas
    if "'," in code:
        parts = code.split("',")
        cleaned_parts = []
        for part in parts:
            cleaned_part = part.strip()
            if cleaned_part.startswith("'"):
                cleaned_part = cleaned_part[1:]
            cleaned_parts.append(cleaned_part)
        code = "\n".join(cleaned_parts)
    
    return code

def clean_answer(raw_answer: str) -> str:
    """
    Clean a raw answer string by removing LaTeX formatting.
    
    Parameters:
        raw_answer (str): The raw answer string potentially containing LaTeX formatting
        
    Returns:
        str: The cleaned answer string without LaTeX formatting
    """
    # Remove whitespace
    answer = raw_answer.strip()
    
    # Remove dollar signs that indicate LaTeX math mode
    if answer.startswith("$") and answer.endswith("$"):
        answer = answer[1:-1].strip()
    
    # Replace LaTeX scientific notation format (e.g., 1 \times 10^{14})
    answer = re.sub(r'([\d.]+)\s*\\times\s*10\^\{(\d+)\}', r'\1e\2', answer)
    
    # Remove \mathrm commands
    answer = re.sub(r'\\mathrm\{([^}]*)\}', r'\1', answer)
    
    # Remove other common LaTeX formatting
    answer = answer.replace('\\', '')
    
    return answer

def parse_unit_with_latex(unit_str: str, allowed_units: dict):
    """
    Parse a unit string using sympy's LaTeX parser.
    After parsing, substitute any symbols with their corresponding
    unit objects defined in allowed_units. This function also attempts
    to reassemble composite units that the LaTeX parser splits into separate symbols.
    
    Parameters:
        unit_str (str): The unit string in LaTeX format, e.g. "$\\frac{\\mathrm{kg}}{\\mathrm{m}^{3}}$"
        allowed_units (dict): A dictionary mapping unit names (e.g. "kg", "m", "km", "cm", "mm")
                              to their corresponding sympy unit objects.
    
    Returns:
        A simplified sympy expression representing the unit.
    """
    # Remove any leading/trailing whitespace.
    unit_str = unit_str.strip()
    
    # Remove surrounding dollar signs if present.
    unit_str = unit_str.lstrip("$").rstrip("$")
    
    # Preprocess the string: Replace \mathrm{...} with its inner content.
    unit_str = re.sub(r'\\mathrm\{([^}]*)\}', r'{\\\1}', unit_str)

    # remove random symbols like tilde
    unit_str = unit_str.replace('~', '')
    
    try:
        expr = parse_latex(unit_str)
        logger.info(f"Parsed LaTeX unit: {expr}")
    except Exception as e:
        logger.error(f"Failed to parse LaTeX unit '{unit_str}': {e}")
        return None
    
    # Substitute allowed unit symbols with their corresponding objects.
    for key, unit_obj in allowed_units.items():
        sym = sp.symbols(key)
        expr = expr.subs(sym, unit_obj)
    
    simplified_expr = sp.simplify(expr)
    logger.info(f"Response unit: {simplified_expr}")
    return simplified_expr

def preprocess_unit_string(unit_str: str) -> str:
    """
    Preprocess a unit string to replace '^' with '**' for exponentiation.
    This is used for non-LaTeX strings.
    """
    return unit_str.replace('^', '**').strip()

class PhysicsVerifier:
    def __init__(self, torlerance: float =1e-2):
        # Set the tolerance for float comparisons.
        self.torlerance = torlerance

    def execute_code(self, code: str):
        """
        Executes the generated code from the response in an isolated namespace.
        The environment includes sympy and the necessary physics units.
        The code is expected to define a variable called 'result'.
        """
        namespace = {}
        try:
            exec(code, namespace, namespace)
        except Exception as e:
            logger.info(f"Failed to execute code: {e}")
        if "result" not in namespace:
            logger.info("The executed code did not define a variable called 'result'.")
        return namespace.get("result", None)

    def parse_unit(self, unit_str: str):
        """
        Parses a unit string into a sympy expression.
        If the string looks like LaTeX (e.g. enclosed in $...$ or contains LaTeX commands),
        it uses sympy's LaTeX parser; otherwise, it falls back to using parse_expr.
        """
        if "$" in unit_str or "\\" in unit_str:
            # Likely a LaTeX formatted string.
            return parse_unit_with_latex(unit_str, allowed_units)
        else:
            # Preprocess for caret exponentiation.
            processed_str = preprocess_unit_string(unit_str)
            try:
                expr = parse_expr(processed_str, local_dict=allowed_units, evaluate=True)
                return sp.simplify(expr)
            except Exception as e:
                logger.error(f"Failed to parse unit '{unit_str}' (processed as '{processed_str}'): {e}")

    def verify_unit(self) -> bool:
        """
        Verifies that the unit provided in the response is equivalent
        to the ground truth unit by comparing their simplified sympy expressions.
        """
        try: 
            response_unit_expr = self.parse_unit(self.response.unit)
            logger.info(f'Response unit: {response_unit_expr}')
            answer_unit_expr = self.parse_unit(self.answer.unit)
            logger.info(f'Answer unit: {answer_unit_expr}')
            diff = sp.simplify(response_unit_expr - answer_unit_expr)
            return diff == 0
        except Exception as e:
            logger.error("Failed to compare units:", e)
            return False

    def verify(self, response: ResponseFormat, answer: AnswerFormat) -> tuple[bool, bool]:
        """
        Verifies that:
        - The executed code's output (variable 'result') matches the ground truth answer.
        - The unit provided in the response is equivalent to the ground truth unit.
        
        Returns:
            A tuple (result_match: bool, unit_match: bool)
        """
        self.response = response
        self.answer = answer

        # Clean and execute the code provided in the response
        cleaned_code = clean_python_code(self.response.code)
        output = self.execute_code(cleaned_code)

        # Determine if the output is a float or a symbolic expression
        if isinstance(output, float) or isinstance(output, int):
            # Convert ground truth answer to float and compare using tolerance.
            try:
                gt_value = float(clean_answer(answer.gt_answer))
                logger.info(f'Output value: {output}')
                logger.info(f'Ground truth value: {gt_value}')
            except ValueError:
                logger.error("Failed to convert ground truth answer to float. Error:", e)
                return False, False
            
            tolerance = self.torlerance
            result_match = math.isclose(output, gt_value, rel_tol=tolerance)

        else:
            # For symbolic expressions, convert both the output and the ground truth to LaTeX.
            # (Assumes that answer.gt_answer is provided as a LaTeX string)
            logger.info(f'Output expression: {output}')
            gt_expr = parse_latex(answer.gt_answer.lstrip("$").rstrip("$"))
            logger.info(f'Ground truth expression: {output}')
            
            try:
                result_match = sp.simplify(output - gt_expr) == 0
            except Exception as e:
                logger.error("Failed to compare symbolic expressions. Error:", e)
                return False, False

        if not answer.unit:
            # If the ground truth unit is not provided, only check the result.
            return result_match, True
        
        unit_match = self.verify_unit()
        return result_match, unit_match


# Example usage:
if __name__ == "__main__":
    # Example response with a LaTeX formatted unit string.
    response = ResponseFormat(
        reasoning="Example with LaTeX formatted unit.",
        code="import sympy as sp\n\n# Given values\nradius_km = 1200  # radius in km\nradius_cm = radius_km * 1e5  # convert radius to cm\n\ndensity = 12.8  # density in g/cm^3\nspecific_heat = 0.400  # specific heat in J/g\u00b7K\nDelta_T = 1  # change in temperature in \u00b0C\nflux_density = 1e11  # neutrinos/(s\u00b7cm^2)\nenergy_per_neutrino = 8e-14  # energy per neutrino in J\n\n# Calculate the volume of the inner core\nV = (4/3) * sp.pi * radius_cm**3  # volume in cm^3\n\n# Calculate the mass of the inner core\nmass = density * V  # mass in grams\n\n# Calculate the energy required to heat the inner core by 1\u00b0C\nQ = mass * specific_heat * Delta_T  # energy in J\n\n# Calculate the area of the inner core\nA = 4 * sp.pi * radius_cm**2  # area in cm^2\n\n# Calculate the total energy absorbed per second\nE = flux_density * A * energy_per_neutrino  # energy in J/s\n\n# Calculate the time required to heat the inner core\nt = Q / E  # time in seconds\n\n# Express t in the form 1 x 10^N\nN = sp.log(t, 10).evalf()  # calculate N\n\n# Store the result\nresult = int(N)\n\n# Display the result\nresult",
        unit="s"
    )
    # Ground truth with equivalent unit in a Python-friendly format.
    answer = AnswerFormat(
        gt_answer='$1 \\times 10^{14}$',
        unit="s"
    )
    
    verifier = PhysicsVerifier()
    try:
        result_match, unit_match = verifier.verify(response, answer)
        logger.info("Result Match:", result_match)
        logger.info("Unit Match:", unit_match)
    except Exception as e:
        logger.info("Verification failed:", e)

