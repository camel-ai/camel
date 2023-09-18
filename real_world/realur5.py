import numpy as np
import real_world.realur5_utils as realur5_utils
import rtde_control
import rtde_io
import rtde_receive

class UR5MoveTimeoutException(Exception):
    def __init__(self):
        super().__init__('UR5 Move Timeout')

class UR5RTDE:
    def __init__(self, ip, gripper=None, home_joint=None):
        self.rtde_c = rtde_control.RTDEControlInterface(ip)
        self.rtde_r = rtde_receive.RTDEReceiveInterface(ip)
        
        self.gripper = gripper
        if self.gripper == 'suction':
            self.rtde_io = rtde_io.RTDEIOInterface(ip)
            self.rtde_c.setTcp([-0.005, -0.103, 0.305, 0, 0, 0])
            self.rtde_c.setPayload(1.5, (0, 0, 0.1))
        else:
            self.rtde_c.setTcp([0, 0, 0, 0, 0, 0])
        
        if home_joint is not None:
            self.home_joint = home_joint
        else:
            self.home_joint = np.array([-180, -90, 90, -90, -90, 0]) / 180 * np.pi
        
        tcp_port=30002
        rtc_port=30003
        self.create_tcp_sock_fn = lambda: realur5_utils.connect(ip, tcp_port)
        self.create_rtc_sock_fn = lambda: realur5_utils.connect(ip, rtc_port)
        self.state = realur5_utils.UR5State(
            self.create_tcp_sock_fn,
            self.create_rtc_sock_fn)

    def home(self, speed=0.75, acceleration=0.1, blocking=True):
        self.rtde_c.moveJ(self.home_joint, speed, acceleration, not blocking)

    def movej(self, q, speed=0.1, acceleration=0.1, blocking=True):
        self.rtde_c.moveJ(q, speed, acceleration, not blocking)
    
    def movel(self, p, speed=0.1, acceleration=0.1, blocking=True):
        if isinstance(p[0], float):
            self.rtde_c.moveL(p, speed, acceleration, not blocking)
        elif isinstance(p[0], list):
            for x in p:
                x.extend([speed, acceleration, 0])
            self.rtde_c.moveL(p, not blocking)
    
    def open_suction_sys(self):
        if self.gripper == 'suction':
            self.rtde_io.setStandardDigitalOut(6, True)
        else:
            raise NotImplementedError
    
    def close_suction_sys(self):
        if self.gripper == 'suction':
            self.rtde_io.setStandardDigitalOut(6, False)
        else:
            raise NotImplementedError

    def open_gripper(self):
        if self.gripper == 'suction':
            self.rtde_io.setStandardDigitalOut(7, True)
        else:
            raise NotImplementedError
        
    def close_gripper(self):
        if self.gripper == 'suction':
            self.rtde_io.setStandardDigitalOut(7, False)
        else:
            raise NotImplementedError
    
    def check_grasp(self):
        analog_in_0 = self.rtde_r.getStandardAnalogInput0()
        if analog_in_0 < 2.0:
            return False
        else:
            return True
        
    # TODO: update reachable workspace for robot
    def check_pose_reachable(self, pose):
        x, y, z = pose
        if x < 0.3 or x > 0.7 or y < -0.3 or y > 0.3 or z < 0.1 or z > 0.5:
            return False
        else:
            return True 
    