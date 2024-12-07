from apis.api import API
import datetime
import random

class AppointmentRegistration(API):
    description = 'This API registers an appointment of hospital.'
    input_parameters = {
        "patient_name": {'type': 'str', 'description': 'The name of patient.'},
        "date": {'type': 'str', 'description': 'The date of appointment. Format be like %Y-%m-%d'},
        "doctor_name": {'type': 'str', 'description': 'The name of appointed doctor.'},
    }
    output_parameters = {
        "appointment_id": {'type': 'str', 'description': 'The ID of appointment.'},
    }
    database_name = 'Appointments'
    
    def __init__(self, init_database=None) -> None:
        if init_database != None:
            self.database = init_database
        else:
            self.database = {}

    def call(self, patient_name: str, date: str, doctor_name: str) -> dict:
        """
        Calls the API with the given parameters.

        Parameters:
        - patient_name (str): the name of patient.
        - date (str): the date of appointment.
        - doctor_name (str): the name of appointed doctor.

        Returns:
        - response (dict): the response from the API call.
        """
        input_parameters = {
            'patient_name': patient_name,
            'date': date,
            'doctor_name': doctor_name,
        }
        try:
            appointment_id = self.register_appointment(patient_name, date, doctor_name)
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
                'output': appointment_id,
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
    
    def register_appointment(self, patient_name: str, date: str, doctor_name: str) -> None:
        """
        Registers an appointment of hospital.

        Parameters:
        - patient_name (str): the name of patient.
        - date (str): the date of appointment.
        - doctor_name (str): the name of appointed doctor.

        Returns:
        - None
        """
        patient_name = patient_name.strip()
        doctor_name = doctor_name.strip()
        if patient_name == '' or doctor_name == '':
            raise Exception('Patient name or doctor name cannot be empty.')
        
        date = self.format_check(date)
        if isinstance(date, Exception):
            raise date

        """
        database = {
            'id1': {
                'patient_name': 'patient_name1',
                'date': '2020-01-01',
                'doctor_name': 'doctor_name1',
            },
            'id2': {
                'patient_name': 'patient_name2',
                'date': '2020-01-01',
                'doctor_name': 'doctor_name2',
            },
            'id3': {
                'patient_name': 'patient_name3',
                'date': '2020-01-01',
                'doctor_name': 'doctor_name3',
            },
        }
        """

        # 要有一个去重的功能，如果已经有了，就不要再添加了，还要报错
        for appointment in self.database:
            if self.database[appointment]['patient_name'] == patient_name:
                if self.format_check(self.database[appointment]['date']) == date:
                    if self.database[appointment]['doctor_name'] == doctor_name:
                        raise Exception('This appointment has already been registered.')
                    else:
                        raise Exception('This patient has already been registered in this day.')

        appointment_id = str(random.randint(10000000, 99999999))
        while appointment_id in self.database:
            appointment_id = str(random.randint(10000000, 99999999))
        
        
        self.database[appointment_id] = {
            'patient_name': patient_name,
            'date': date,
            'doctor_name': doctor_name,
        }

        return appointment_id
    
    def check_api_call_correctness(self, response, groundtruth) -> bool:
        response_patient_name = response['input']['patient_name'].strip()
        response_date = self.format_check(response['input']['date'])
        response_doctor_name = response['input']['doctor_name'].strip()
        response_appointment_id = response['output']
        response_exception = response['exception']
        groundtruth_patient_name = groundtruth['input']['patient_name'].strip()
        groundtruth_date = self.format_check(groundtruth['input']['date'])
        groundtruth_doctor_name = groundtruth['input']['doctor_name'].strip()
        groundtruth_appointment_id = groundtruth['output']
        groundtruth_exception = groundtruth['exception']
        if response_patient_name != groundtruth_patient_name:
            return False
        if response_date != groundtruth_date:
            return False
        if response_doctor_name != groundtruth_doctor_name:
            return False
        if groundtruth_appointment_id == None and response_appointment_id != None:
            return False
        if response_exception != groundtruth_exception:
            return False
        return True