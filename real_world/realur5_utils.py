from socket import socket, AF_INET, SOCK_STREAM
import threading
from threading import Thread
from time import time, sleep
import struct
from abc import ABC, abstractmethod, abstractproperty
import numpy as np

class Gripper(ABC):
    @abstractmethod
    def close(self, blocking=True):
        pass 

    @abstractmethod
    def open(self, blocking=True):
        pass

    @abstractproperty
    def ee_tip_z_offset(self) -> float:
        # in meters
        pass

    @abstractproperty
    def current_width(self) -> float:
        # in meters
        pass

    @property
    def tool_offset(self):
        # in meters
        return [0, 0, self.ee_tip_z_offset, 0, 0, 0]

    @property
    def mass(self):
        # in kg
        return 1.2


def connect(ip, port):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect((ip, port))
    return sock


def setup_thread(target):
    print('SETUP THREAD',target)
    print(list(map(lambda t:t.name,threading.enumerate())))
    thread = Thread(target=target)
    thread.daemon = True
    thread.start()
    print('started', thread.name)
    return thread

# Helper function to skip to specific package byte index in TCP message


def skip_to_package_index(state_data, pkg_type):
    byte_index = 1
    while byte_index < len(state_data):
        package_size = struct.unpack(
            "!i", state_data[byte_index:(byte_index + 4)])[0]
        byte_index += 4
        package_index = int(struct.unpack(
            '!B', state_data[(byte_index + 0):(byte_index + 1)])[0])
        if package_index == pkg_type:
            byte_index += 1
            break
        byte_index += package_size - 4
    return byte_index

# Define functions to parse TCP message for each type of requested info


def tcp_parse_timestamp(state_data):
    byte_index = skip_to_package_index(state_data, pkg_type=0)
    timestamp = struct.unpack(
        '!Q', state_data[(byte_index + 0):(byte_index + 8)])[0]
    return timestamp


def tcp_parse_actual_j_pos(state_data):
    byte_index = skip_to_package_index(state_data, pkg_type=1)
    actual_j_pos = [0, 0, 0, 0, 0, 0]
    for i in range(6):
        actual_j_pos[i] = struct.unpack(
            '!d', state_data[(byte_index + 0):(byte_index + 8)])[0]
        byte_index += 41
    return actual_j_pos


def tcp_parse_actual_j_vel(state_data):
    byte_index = skip_to_package_index(state_data, pkg_type=1) + 16
    actual_j_vel = [0, 0, 0, 0, 0, 0]
    for i in range(6):
        actual_j_vel[i] = struct.unpack(
            '!d', state_data[(byte_index + 0):(byte_index + 8)])[0]
        byte_index += 41
    return actual_j_vel


def tcp_parse_actual_j_currents(state_data):
    byte_index = skip_to_package_index(state_data, pkg_type=1) + 24
    actual_j_currents = [0, 0, 0, 0, 0, 0]
    for i in range(6):
        actual_j_currents[i] = struct.unpack(
            '!f', state_data[(byte_index + 0):(byte_index + 4)])[0]
        byte_index += 41
    return actual_j_currents


def tcp_parse_actual_tool_pose(state_data):
    byte_index = skip_to_package_index(state_data, pkg_type=4)
    actual_tool_pose = [0, 0, 0, 0, 0, 0]
    for i in range(6):
        actual_tool_pose[i] = struct.unpack(
            '!d', state_data[(byte_index + 0):(byte_index + 8)])[0]
        byte_index += 8
    return actual_tool_pose


def tcp_parse_tool_analog_input2(state_data):
    byte_index = skip_to_package_index(state_data, pkg_type=2) + 2
    try: 
        tool_analog_input2 = struct.unpack(
            '!d', state_data[(byte_index + 0):(byte_index + 8)])[0]
    except Exception as e:
        print("[IGNORING!!!] ", e)
        return 0.4
    return tool_analog_input2


def tcp_parse_analog_input1(state_data):
    byte_index = skip_to_package_index(state_data, pkg_type=3) + 14
    analog_input1 = struct.unpack(
        '!d', state_data[(byte_index + 0):(byte_index + 8)])[0]
    return analog_input1


# https://www.universal-robots.com/articles/ur/real-time-data-exchange-rtde-guide/

# Map requested info to parsing function and sub-package type
tcp_parse_func = {'timestamp': tcp_parse_timestamp,
                  'actual_j_pos': tcp_parse_actual_j_pos,
                  'actual_j_vel': tcp_parse_actual_j_vel,
                  'actual_j_currents': tcp_parse_actual_j_currents,
                  'actual_tool_pose': tcp_parse_actual_tool_pose,
                  'tool_analog_input2': tcp_parse_tool_analog_input2,
                  'analog_input1': tcp_parse_analog_input1}

# Define functions to parse RTC message for each type of requested info


def rtc_parse_timestamp(rtc_state_data):
    byte_index = 0
    timestamp = struct.unpack(
        '!d', rtc_state_data[(byte_index + 0):(byte_index + 8)])[0]
    return timestamp


def rtc_parse_actual_j_pos(rtc_state_data):
    byte_index = 8 + 48 * 5
    actual_j_pos = [0, 0, 0, 0, 0, 0]
    for i in range(6):
        actual_j_pos[i] = struct.unpack(
            '!d', rtc_state_data[(byte_index + 0):(byte_index + 8)])[0]
        byte_index += 8
    return actual_j_pos


def rtc_parse_actual_j_vel(rtc_state_data):
    byte_index = 8 + 48 * 6
    actual_j_vel = [0, 0, 0, 0, 0, 0]
    for i in range(6):
        actual_j_vel[i] = struct.unpack(
            '!d', rtc_state_data[(byte_index + 0):(byte_index + 8)])[0]
        byte_index += 8
    return actual_j_vel


def rtc_parse_actual_j_currents(rtc_state_data):
    byte_index = 8 + 48 * 7
    actual_j_currents = [0, 0, 0, 0, 0, 0]
    for i in range(6):
        actual_j_currents[i] = struct.unpack(
            '!d', rtc_state_data[(byte_index + 0):(byte_index + 8)])[0]
        byte_index += 8
    return actual_j_currents


def rtc_parse_actual_tool_pose(rtc_state_data):
    byte_index = 8 + 48 * 8 + 24 + 120 + 48
    actual_tool_pose = [0, 0, 0, 0, 0, 0]
    for i in range(6):
        actual_tool_pose[i] = struct.unpack(
            '!d', rtc_state_data[(byte_index + 0):(byte_index + 8)])[0]
        byte_index += 8
    return actual_tool_pose


def rtc_parse_actual_tool_vel(rtc_state_data):
    byte_index = 8 + 48 * 8 + 24 + 120 + 48 * 2
    actual_tool_vel = [0, 0, 0, 0, 0, 0]
    for i in range(6):
        actual_tool_vel[i] = struct.unpack(
            '!d', rtc_state_data[(byte_index + 0):(byte_index + 8)])[0]
        byte_index += 8
    return actual_tool_vel


# Map requested info to parsing function and sub-package type
rtc_parse_func = {'timestamp': rtc_parse_timestamp,
                  'actual_j_pos': rtc_parse_actual_j_pos,
                  'actual_j_vel': rtc_parse_actual_j_vel,
                  'actual_j_currents': rtc_parse_actual_j_currents,
                  'actual_tool_pose': rtc_parse_actual_tool_pose,
                  'actual_tool_vel': rtc_parse_actual_tool_vel}


class UR5State:
    def __init__(self, create_tcp_sock_fn, create_rtc_sock_fn):
        self.clear()
        self.create_tcp_sock_fn = create_tcp_sock_fn
        self.create_rtc_sock_fn = create_rtc_sock_fn
        self.thread = setup_thread(target=self.get_rtc_state_data)
        while self.get_j_pos() is None:
            sleep(0.01)

    def clear(self):
        self.state = {
            'timestamp': None,
            'actual_j_pos': None,
            'actual_j_vel': None,
            'actual_j_currents': None,
            'actual_tool_pose': None,
            'actual_tool_vel': None
        }

    def get_j_pos(self):
        rv = self.state['actual_j_pos']
        while rv is None:
            sleep(0.1)
            rv = self.state['actual_j_pos']
        return np.array(rv)

    def get_j_vel(self):
        return np.array(self.state['actual_j_vel'])

    def get_ee_pose(self):
        return np.array(self.state['actual_tool_pose'])

    # def tcp_get_state_data(self):
    #     while True:
    #         self.update_state_tcp()
    #         sleep(0.01)

    def update_state_tcp(self, timeout=1):
        sock = self.create_tcp_sock_fn()
        max_tcp_msg_size = 2048
        t0 = time()
        while True:
            if (time() - t0) < 3:
                message_size_bytes = bytearray(sock.recv(4))
                message_size = struct.unpack("!i", message_size_bytes)[0]
                # This is hacky but it can work for multiple versions
                if message_size <= 55 or message_size >= max_tcp_msg_size:
                    continue
                else:
                    state_data = sock.recv(message_size - 4)
                if message_size < max_tcp_msg_size \
                        and message_size - 4 == len(state_data):
                    break
            else:
                raise Exception('Timeout: retrieving TCP RTC message ',
                                'exceeded 3 seconds. Restarting connection.')
        
        tool_voltage = tcp_parse_tool_analog_input2(state_data)
        # print("tool voltage: ", tool_voltage)
        return tool_voltage
        # for key in self.state.keys():
        #     print(time())
        #     self.state[key] = tcp_parse_func[key](state_data)
        # print("self.state: ", self.state)

    def get_rtc_state_data(self):
        while True:
            self.update_state_rtc(sock=self.create_rtc_sock_fn())
            sleep(0.01)

    def update_state_rtc(self, sock, timeout=1):
        max_tcp_msg_size = 2048
        t0 = time()
        while True:
            if (time() - t0) < timeout:
                message_size_bytes = bytearray(sock.recv(4))
                message_size = struct.unpack("!i", message_size_bytes)[0]
                if message_size <= 0:
                    continue
                else:
                    rtc_state_data = sock.recv(message_size - 4)
                if message_size < max_tcp_msg_size\
                        and message_size - 4 == len(rtc_state_data):
                    break
            else:
                msg = 'Timeout: retrieving TCP RTC message ' +\
                    f'exceeded {timeout} seconds. Restarting connection.'
                print(msg)
                raise Exception(msg)
        for key in self.state.keys():
            self.state[key] = \
                rtc_parse_func[key](rtc_state_data)
