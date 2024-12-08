from apis.api import API

class OrganizationMembers(API):
    description = "API to retrieve the list of members in the organization."
    input_parameters = {
        'organization': {'type': 'str', 'description': "Name of the organization."},
    }
    output_parameters = {
        'members': {'type': 'list', 'description': 'List of organization members.'}
    }


    def __init__(self):
        self.database = {
            'Alibaba': [
                'John',
                'Mary',
                'Peter',
            ],
            'Tencent': [
                'Tom',
                'Jerry',
            ],
            'Baidu': [
                'Jack',
                'Rose',
            ],
            'ByteDance': [
                'Bob',
                'Alice',
            ],
            'JD': [
                'Mike',
                'Jane',
            ],
        }


    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response.

        Returns:
        - is_correct (bool): whether the response is correct.
        """
        assert response['api_name'] == groundtruth['api_name'], "The API name is not correct."
        if response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception'] and response['input'] == groundtruth['input']:
            return True
        else:
            return False


    def call(self, organization: str) -> dict:
        input_parameters = {
            'organization': organization
        }
        try:
            members = self.get_organization_members(organization)
            output_parameters = {
                'members': members
            }
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}     
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': output_parameters,
                    'exception': None}


    def get_organization_members(self, organization):
        return self.database[organization]
    
