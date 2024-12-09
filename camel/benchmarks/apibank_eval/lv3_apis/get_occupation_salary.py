from apis.api import API

class GetOccupationSalary(API):
    description = "API for querying the salary of a given occupation."
    input_parameters = {
        'occupation': {'type': 'str', 'description': 'The occupation to query.'},
    }
    output_parameters = {
        'salary': {'type': 'float', 'description': 'The salary of the given occupation.'}
    }

    def __init__(self):
        self.salary_info = {
            'Financial Analyst': 100000,
            'Software Engineer': 120000,
            'Data Scientist': 150000,
            'Product Manager': 130000,
            'Doctor': 200000,
        }

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
        return response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception'] and response['input'] == groundtruth['input']

    def call(self, occupation: str) -> dict:
        input_parameters = {
            'occupation': occupation,
        }
        try:
            salary = self.query_salary(occupation)
            output_parameters = {
                'salary': salary,
            }
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': output_parameters,
                    'exception': None}

    def query_salary(self, occupation: str) -> float:
        """
        Queries the salary of the given occupation.

        Parameters:
        - occupation (str): the occupation to query.

        Returns:
        - salary (float): the salary of the given occupation.
        """
        if occupation not in self.salary_info:
            raise Exception("The occupation is not in the database.")
        return self.salary_info[occupation]

