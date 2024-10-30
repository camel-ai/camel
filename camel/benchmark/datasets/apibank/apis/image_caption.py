from apis.api import API

class ImageCaption(API):
    description = 'This API generates a caption for a given image.'
    input_parameters = {
        "url": {'type': 'str', 'description': 'The url to download the image. It should end with .jpg, .jpeg or .png.'},
    }
    output_parameters = {
        "caption": {'type': 'str', 'description': 'The generated caption.'},
    }
    database_name = 'ImageCaptioning'

    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, url: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - url (str): the url to download the image. It should end with .jpg, .jpeg or .png.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'url': url,
        }
        try:
            caption = self.generate_caption(url)
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
            'output': caption,
            'exception': None,
        }
    
    def generate_caption(self, url: str) -> str:
        """
        Generate a caption for a given image.

        Parameters:
        - url (str): the url to download the image. It should end with .jpg, .jpeg or .png.

        Returns:
        - caption (str): the generated caption.
        """

        url = url.strip()
        if not url.endswith('.jpg') and not url.endswith('.jpeg') and not url.endswith('.png'):
            raise Exception('The url should end with .jpg, .jpeg or .png.')
        
        for item in self.database:
            if item['url'] == url:
                return item['caption']
            
        raise Exception('The image of this url failed to be processed.')

        
    def check_api_call_correctness(self, response, groundtruth):
        """
        Check if the API call is correct.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth.

        Returns:
        - correctness (bool): whether the API call is correct.
        """
        if response['input'] != groundtruth['input']:
            return False
        if response['output'] != groundtruth['output']:
            return False
        if response['exception'] != groundtruth['exception']:
            return False
        return True
    
