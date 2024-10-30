from apis.api import API

class LikeCount(API):
    description = "API to retrieve the number of likes for a given post ID."
    input_parameters = {
        'post_id': {'type': 'int', 'description': "Post ID."},
    }
    output_parameters = {
        'like_count': {'type': 'int', 'description': 'Number of likes for the post.'},
    }

    def __init__(self):
        self.database = {
            1: 10,
            2: 20,
            3: 30,
            4: 40,
            5: 50,
            6: 60,
            7: 70,
            8: 80,
            9: 90,
            10: 100,
            11: 110,
            12: 120,
            13: 130,
            14: 140,
            15: 150,
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
    
    def call(self, post_id: int) -> dict:
        input_parameters = {
            'post_id': post_id,
        }
        try:
            like_count = self.retrieve_like_count(post_id)
        except Exception as e:
            exception = str(e)
            return {'api_name': self.__class__.__name__, 'input': input_parameters, 'output': None,
                    'exception': exception}
        else:
            return {'api_name': self.__class__.__name__, 'input': input_parameters,
                    'output': {'like_count': like_count}, 'exception': None}

    def retrieve_like_count(self, post_id: int) -> int:
        if post_id not in self.database:
            raise Exception(f"Post with ID {post_id} does not exist.")

        return self.database[post_id]

