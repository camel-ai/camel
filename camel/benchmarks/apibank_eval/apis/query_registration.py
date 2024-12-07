from apis.api import API
import datetime

class QueryRegistration(API):
    
    description = 'This API queries the registration of a patient, given patient ID.'
    input_parameters = {
        "patient_name": {'type': 'str', 'description': 'The name of patient.'},
        "date": {'type': 'str', 'description': 'The date of appointment. Format be like %Y-%m-%d'},
    }
    output_parameters = {
        "appointments": {'type': 'list', 'description': 'The dict where from appointment_id to a list like ["patient_name":xxx, "date":xxx, "doctor_name":xxx]'},
    }
    database_name = 'Appointments'

    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, patient_name: str, date: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - patient_name (str): the name of patient.
        - date (str): the date of appointment.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'patient_name': patient_name,
            'date': date,
        }
        try:
            appointments = self.query_registration(patient_name, date)
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
                'output': appointments,
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
        
    def query_registration(self, patient_name: str, date: str) -> list:
        """
        Queries the registration of a patient given patient ID and date.

        Parameters:
        - patient_name (str): the name of patient.
        - date (str): the date of appointment.

        Returns:
        - appointments (dict): the dict where from appointment_id to a list like ["patient_name":xxx, "date":xxx, "doctor_name":xxx]
        """
        patient_name = patient_name.strip()
        date = self.format_check(date)
        if isinstance(date, Exception):
            raise date
        
        appointments = {}
        for appointment in self.database:
            if self.database[appointment]['patient_name'] == patient_name:
                if self.format_check(self.database[appointment]['date']) == date:
                    appointments[appointment] = self.database[appointment]
        if len(appointments) == 0:
            raise Exception("No appointments found.")
        return appointments
        
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        """
        Checks the correctness of the API call.

        Parameters:
        - response (dict): the response from the API call.
        - groundtruth (dict): the groundtruth of the API call.

        Returns:
        - correctness (bool): the correctness of the API call.
        """
        response_patient_name = response['input']['patient_name']
        groundtruth_patient_name = groundtruth['input']['patient_name']
        response_patient_name = response_patient_name.strip()
        groundtruth_patient_name = groundtruth_patient_name.strip()

        response_date = response['input']['date']
        groundtruth_date = groundtruth['input']['date']
        response_date = self.format_check(response_date)
        groundtruth_date = self.format_check(groundtruth_date)

        if response_patient_name != groundtruth_patient_name:
            return False
        if response_date != groundtruth_date:
            return False
        if response['output'] != groundtruth['output']:
            return False
        if response['exception'] != groundtruth['exception']:
            return False
        return True