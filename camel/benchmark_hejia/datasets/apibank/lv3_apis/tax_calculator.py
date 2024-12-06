from apis.api import API
class TaxCalculator(API):
    description = "API for calculating tax deductions based on the given salary."
    input_parameters = {
        'salary': {'type': 'float', 'description': 'The salary to calculate tax deductions for.'},
    }
    output_parameters = {
        'salary_after_tax': {'type': 'float', 'description': 'The salary after tax deductions.'}
    }

    def __init__(self, tax_rates=None):
        if tax_rates is not None:
            self.tax_rates = tax_rates
        else:
            self.tax_rates = {
                0: 0.0,     # 0% tax rate
                1000: 0.1,  # 10% tax rate for income up to 1000
                3000: 0.2,  # 20% tax rate for income up to 3000
                5000: 0.3,  # 30% tax rate for income up to 5000
                float('inf'): 0.4  # 40% tax rate for income above 5000
            }

    def calculate_tax_deductions(self, salary):
        tax_rate = next(rate for threshold, rate in sorted(self.tax_rates.items(), reverse=True) if salary >= threshold)
        tax_deduction = salary * tax_rate
        salary_after_tax = salary - tax_deduction
        return salary_after_tax

    def check_api_call_correctness(self, response, groundtruth):
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response.

        Returns:
        - is_correct (bool): whether the response is correct.
        """
        assert response['api_name'] == groundtruth['api_name'], "The API name is not correct."
        if response['input']['salary'] == groundtruth['input']['salary'] and \
           response['output']['salary_after_tax'] == groundtruth['output']['salary_after_tax'] and \
           response['exception'] == groundtruth['exception']:
            return True
        else:
            return False

    def call(self, salary):
        input_parameters = {'salary': salary}
        try:
            salary_after_tax = self.calculate_tax_deductions(salary)
            output_parameters = {'salary_after_tax': salary_after_tax}
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters,
                    'output': output_parameters, 'exception': None}

if __name__ == '__main__':
    tax_calculator = TaxCalculator()
    response = tax_calculator.call(100000)
    print(response)