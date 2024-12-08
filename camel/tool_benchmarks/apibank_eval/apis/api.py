class API:
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks if the response from the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth response.

        Returns:
        - is_correct (bool): whether the response is correct.
        """
        raise NotImplementedError
    def call(self, **kwargs) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - kwargs (dict): the parameters to call the API with.

        Returns:
        - response (dict): the response from the API call.
        """
        raise NotImplementedError