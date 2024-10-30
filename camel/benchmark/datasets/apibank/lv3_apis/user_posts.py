from apis.api import API

class UserPosts(API):
    description = "API to retrieve the post IDs for a specific user."
    input_parameters = {
        'user_id': {'type': 'int', 'description': "User's ID."},
    }
    output_parameters = {
        'post_ids': {'type': 'list', 'description': 'List of post IDs.'},
    }


    def __init__(self):
        self.database = {
            1: [1, 2, 3],
            2: [4, 5, 6],
            3: [7, 8, 9],
            4: [10, 11, 12],
            5: [13, 14, 15],
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
        return response['output'] == groundtruth['output'] and response['exception'] == groundtruth['exception'] and response['input'] == groundtruth['input']


    def call(self, user_id: int) -> dict:
        input_parameters = {
            'user_id': user_id,
        }
        try:
            post_ids = self.retrieve_user_post_ids(user_id)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None, 'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': {'post_ids': post_ids}, 'exception': None}

    def retrieve_user_post_ids(self, user_id: int) -> list:
        return self.database[user_id]
