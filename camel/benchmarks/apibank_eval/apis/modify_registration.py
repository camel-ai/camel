from apis.api import API
import datetime

class ModifyRegistration(API):
    
    description = 'This API modifies the registration of a patient given appointment ID.'
    input_parameters = {
        "appointment_id": {'type': 'str', 'description': 'The ID of appointment.'},
        "new_appointment_date": {'type': 'str', 'description': 'The new appointment date. Format: %Y-%m-%d.'},
        "new_appointment_doctor": {'type': 'str', 'description': 'The new appointment doctor.'},
    }
    output_parameters = {
        "status": {'type': 'str', 'description': 'The status of modification.'},
    }
    database_name = 'Appointments'

    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, appointment_id: str, new_appointment_date: str = None, new_appointment_doctor: str = None) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - appointment_id (str): the ID of appointment.
        - new_appointment_date (str): the new appointment date.
        - new_appointment_doctor (str): the new appointment doctor.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'appointment_id': appointment_id,
            'new_appointment_date': new_appointment_date,
            'new_appointment_doctor': new_appointment_doctor,
        }
        try:
            status = self.modify_registration(appointment_id, new_appointment_date, new_appointment_doctor)
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
        
    def format_check(self, date):
        date = date.strip()
        split_date = date.split('-')
        if len(split_date) == 3:
            if len(split_date[0]) == 4:
                pass
            else:
                split_date[0] = split_date[0].zfill(4)
            date = '-'.join(split_date)
        try:
            date = datetime.datetime.strptime(date, '%Y-%m-%d').strftime('%Y-%m-%d')
        except Exception as e:
            date = e
        return date
    
    def modify_registration(self, appointment_id: str, new_appointment_date: str = None, new_appointment_doctor: str = None) -> str:
        """
        Modifies the registration of a patient given appointment ID.

        Parameters:
        - appointment_id (str): the ID of appointment.
        - new_appointment_date (str): the new appointment date.
        - new_appointment_doctor (str): the new appointment doctor.

        Returns:
        - status (str): the status of modification.
        """
        # Check formats of input parameters.
        appointment_id = appointment_id.strip()
        if appointment_id not in self.database:
            raise Exception('The appointment ID does not exist.')
        if new_appointment_date != None:
            new_appointment_date = self.format_check(new_appointment_date)
        if new_appointment_doctor != None:
            new_appointment_doctor = new_appointment_doctor.strip()
            if new_appointment_doctor == '':
                raise Exception('Fail because the doctor name is empty.')

        # Check if the input parameters are valid.
        if isinstance(new_appointment_date, Exception):
            raise new_appointment_date
        if new_appointment_date == None and new_appointment_doctor == None:
            raise Exception('Fail because no modification is made.')
        if new_appointment_date == None:
            assert new_appointment_doctor != None
            if new_appointment_doctor == self.database[appointment_id]['doctor_name']:
                raise Exception('Fail because doctor is not changed.')
            self.database[appointment_id]['doctor_name'] = new_appointment_doctor
        else: # new_appointment_date != None
            if new_appointment_doctor == None:
                if new_appointment_date == self.database[appointment_id]['date']:
                    raise Exception('Fail because date is not changed.')
                self.database[appointment_id]['date'] = new_appointment_date
            else: # new_appointment_date != None and new_appointment_doctor != None
                if new_appointment_date == self.database[appointment_id]['date'] and new_appointment_doctor == self.database[appointment_id]['doctor_name']:
                    raise Exception('Fail because no modification is made.')
                if new_appointment_date == self.database[appointment_id]['date']:
                    raise Exception('Fail because date is not changed.')
                if new_appointment_doctor == self.database[appointment_id]['doctor_name']:
                    raise Exception('Fail because doctor is not changed.')
                self.database[appointment_id]['date'] = new_appointment_date
                self.database[appointment_id]['doctor_name'] = new_appointment_doctor
        return 'success'
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks the correctness of the API call.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth of the API call.

        Returns:
        - correctness (bool): the correctness of the API call.
        """
        response_appointment_id = str(response['input']['appointment_id'])
        groundtruth_appointment_id = groundtruth['input']['appointment_id']
        response_new_appointment_date = response['input']['new_appointment_date']
        groundtruth_new_appointment_date = groundtruth['input']['new_appointment_date']
        response_new_appointment_doctor = response['input']['new_appointment_doctor']
        groundtruth_new_appointment_doctor = groundtruth['input']['new_appointment_doctor']

        # Check formats of input parameters.
        response_appointment_id = response_appointment_id.strip()
        groundtruth_appointment_id = groundtruth_appointment_id.strip()
        
        if response_new_appointment_date != None:
            response_new_appointment_date = self.format_check(response_new_appointment_date)
        if groundtruth_new_appointment_date != None:
            groundtruth_new_appointment_date = self.format_check(groundtruth_new_appointment_date)
        
        if response_new_appointment_doctor != None:
            response_new_appointment_doctor = response_new_appointment_doctor.strip()
        if groundtruth_new_appointment_doctor != None:
            groundtruth_new_appointment_doctor = groundtruth_new_appointment_doctor.strip()
        
        response_output = response['output']
        groundtruth_output = groundtruth['output']
        response_exception = response['exception']
        groundtruth_exception = groundtruth['exception']

        if response_appointment_id != groundtruth_appointment_id:
            return False
        if response_new_appointment_date != groundtruth_new_appointment_date:
            return False
        if response_new_appointment_doctor != groundtruth_new_appointment_doctor:
            return False
        if response_output != groundtruth_output:
            return False
        if response_exception != groundtruth_exception:
            return False
        return True
    
