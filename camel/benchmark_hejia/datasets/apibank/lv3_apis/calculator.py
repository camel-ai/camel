from apis.api import API

class Calculator(API):
    description = 'This API provides basic arithmetic operations: addition, subtraction, multiplication, and division.'
    input_parameters = {
        'formula': {'type': 'str', 'description': 'The formula that needs to be calculated. Only integers are supported. Valid operators are +, -, *, /, and (, ). For example, \'(1 + 2) * 3\'.'},
    }
    output_parameters = {
        'result': {'type': 'float', 'description': 'The result of the formula.'},
    }
    def __init__(self) -> None:
        pass

    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response.

        Returns:
        - is_correct (bool): whether the response is correct.
        """
        re_formula = response['input']['formula'].replace(' ', '')
        gt_formula = groundtruth['input']['formula'].replace(' ', '')

        if re_formula == gt_formula and response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception']:
            return True
        else:
            return False

    def call(self, formula: str) -> float:
        """
        Calculates the result of the formula.

        Parameters:
        - formula (str): the formula that needs to be calculated. Valid operators are +, -, *, /, and (, ). For example, '(1 + 2) * 3'.

        Returns:
        - result (float): the result of the formula.
        - formula (str): the formula that was calculated.
        """
        input_parameters = {
            'formula': formula,
        }
        try:
            result = self.calculate(formula)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None, 'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': result, 'exception': None}
    
    def calculate(self, formula: str) -> float:
        """
        Calculates the result of the formula.

        Parameters:
        - formula (str): the formula that needs to be calculated. Valid operators are +, -, *, /, and (, ). For example, '(1 + 2) * 3'.

        Returns:
        - result (float): the result of the formula.
        """
        # Remove all spaces from the formula
        formula = formula.replace(' ', '')

        # Check if the formula is valid
        if not self.is_valid_formula(formula):
            raise Exception('invalid formula')

        # Convert the formula to a list
        formula = self.convert_formula_to_list(formula)

        # Calculate the result
        result = self.calculate_formula(formula)

        return result
    
    def is_valid_formula(self, formula: str) -> bool:
        """
        Checks if the formula is valid.

        Parameters:
        - formula (str): the formula that needs to be checked.

        Returns:
        - is_valid (bool): True if the formula is valid, False otherwise.
        """
        # Check if the formula is empty
        if len(formula) == 0:
            return False

        # Check if the formula contains invalid characters
        for c in formula:
            if c not in '0123456789+-*/()':
                return False

        # Check if the formula contains an invalid number of parentheses
        if formula.count('(') != formula.count(')'):
            return False

        # Check if the formula contains an invalid number of operators
        if formula.count('+') + formula.count('-') + formula.count('*') + formula.count('/') == 0:
            return False

        # Check if the formula contains an invalid number of operands
        if formula.count('+') + formula.count('-') + formula.count('*') + formula.count('/') + 1 == len(formula):
            return False

        return True
    
    def convert_formula_to_list(self, formula: str) -> list:
        """
        Converts the formula to a list.

        Parameters:
        - formula (str): the formula that needs to be converted.

        Returns:
        - formula_list (list): the formula converted to a list.
        """
        formula_list = []
        number = ''
        for c in formula:
            if c in '0123456789':
                number += c
            else:
                if number != '':
                    formula_list.append(float(number))
                    number = ''
                formula_list.append(c)
        if number != '':
            formula_list.append(float(number))

        return formula_list
    
    def calculate_formula(self, formula: list) -> float:
        """
        Calculates the result of the formula.

        Parameters:
        - formula (list): the formula that needs to be calculated.

        Returns:
        - result (float): the result of the formula.
        """
        # Calculate the result of the parentheses
        while '(' in formula:
            left_parenthesis_index = formula.index('(')
            right_parenthesis_index = formula.index(')')
            formula[left_parenthesis_index:right_parenthesis_index + 1] = [self.calculate_formula(formula[left_parenthesis_index + 1:right_parenthesis_index])]

        # Calculate the result of the multiplication and division
        while '*' in formula or '/' in formula:
            if '*' in formula and '/' in formula:
                if formula.index('*') < formula.index('/'):
                    index = formula.index('*')
                else:
                    index = formula.index('/')
            elif '*' in formula:
                index = formula.index('*')
            else:
                index = formula.index('/')
            formula[index - 1:index + 2] = [self.calculate_operation(formula[index - 1], formula[index], formula[index + 1])]

        # Calculate the result of the addition and subtraction
        while '+' in formula or '-' in formula:
            if '+' in formula and '-' in formula:
                if formula.index('+') < formula.index('-'):
                    index = formula.index('+')
                else:
                    index = formula.index('-')
            elif '+' in formula:
                index = formula.index('+')
            else:
                index = formula.index('-')
            formula[index - 1:index + 2] = [self.calculate_operation(formula[index - 1], formula[index], formula[index + 1])]

        return formula[0]
    
    def calculate_operation(self, operand1: float, operator: str, operand2: float) -> float:
        """
        Calculates the result of the operation.

        Parameters:
        - operand1 (float): the first operand.
        - operator (str): the operator.
        - operand2 (float): the second operand.

        Returns:
        - result (float): the result of the operation.
        """
        if operator == '+':
            return operand1 + operand2
        elif operator == '-':
            return operand1 - operand2
        elif operator == '*':
            return operand1 * operand2
        elif operator == '/':
            return operand1 / operand2
        
if __name__ == '__main__':
    # Create the API
    api = Calculator()
    response = api.call('(1 + 2) * 3')
    print(response)