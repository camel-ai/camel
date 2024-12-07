from apis.api import API

class CancelRegistration(API):
    description = 'This API cancels the registration of a patient given appointment ID.'
    input_parameters = {
        "appointment_id": {'type': 'str', 'description': 'The ID of appointment.'},
    }
    output_parameters = {
        "status": {'type': 'str', 'description': 'The status of cancellation.'},
    }
    database_name = 'Appointments'

    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, appointment_id: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - appointment_id (str): the ID of appointment.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'appointment_id': appointment_id,
        }
        try:
            status = self.cancel_registration(appointment_id)
        except Exception as e:
            exception = str(e)
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': None,
                'exception': exception,
            }
        else:
            return {
                'api_name': self.__class__.__name__,
                'input': input_parameters,
                'output': status,
                'exception': None,
            }
        
    def cancel_registration(self, appointment_id: str) -> str:
        """
        Cancels the registration of a patient given appointment ID.

        Parameters:
        - appointment_id (str): the ID of appointment.

        Returns:
        - status (str): the status of cancellation.
        """
        appointment_id = appointment_id.strip()
        if appointment_id in self.database:
            del self.database[appointment_id]
            return 'success'
        else:
            raise Exception('The appointment ID is incorrect.')
        
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        response_id = response['input']['appointment_id'].strip()
        groundtruth_id = groundtruth['input']['appointment_id'].strip()
        response_status = response['output']
        groundtruth_status = groundtruth['output']
        response_exception = response['exception']
        groundtruth_exception = groundtruth['exception']
        if response_id != groundtruth_id:
            return False
        if response_status != groundtruth_status:
            return False
        if response_exception != groundtruth_exception:
            return False
        return True