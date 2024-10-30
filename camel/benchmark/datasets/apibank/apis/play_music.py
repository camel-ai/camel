from apis.api import API

class PlayMusic(API):
    description = 'This API triggers a music player to play music.'
    input_parameters = {
        "music_name": {'type': 'str', 'description': 'The name of the music to play.'},
    }
    output_parameters = {
        "status": {'type': 'str', 'description': 'The corresponding url scheme to trigger the music player.'},
    }

    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, music_name: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - music_name (str): the name of the music to play.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'music_name': music_name,
        }
        try:
            status = self.play_music(music_name)
        except Exception as e:
            exception = str(e)
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': None,
                'exception': exception,
            }
        return {
            'api_name': self.__class__.__name__,
            'input': input_parameters,
            'output': status,
            'exception': None,
        }
    
    def play_music(self, music_name: str) -> str:
        """
        Plays the music.

        Parameters:
        - music_name (str): the name of the music to play.

        Returns:
        - status (str): the corresponding url scheme to trigger the music player.
        """

        music_name = music_name.lower().strip()
        if music_name == '':
            raise Exception('The music name cannot be empty.')
        
        return "music://{}".format(music_name)
    
    def check_api_call_correctness(self, response, groundtruth):
        """
        Checks the correctness of the API call.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth of the API call.

        Returns:
        - correctness (bool): whether the API call is correct.
        """
        if response['output'] == groundtruth['output']:
            return True
        else:
            return False