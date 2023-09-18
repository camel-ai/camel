import numpy as np
import cv2
from copy import deepcopy
from real_world.realur5 import UR5RTDE
from real_world.kinect import KinectClient

WS_CROP_X = (180, -120)
WS_CROP_Y = (300, -380)

# Table workspace surface is 0.0 without suction gripper and -0.025 with the suction gripper
WORKSPACE_SURFACE = -0.027
BIN_TOP = 0.1
tool_orientation = [2.22, -2.22, 0.0]

if __name__ == "__main__":
    bin_cam = KinectClient('128.59.23.32', '8080')
    robot = UR5RTDE(ip='192.168.0.113', gripper='suction', home_joint=np.array([-180, -90, 90, -90, -90, 0]) / 180 * np.pi)
    robot.home()
     
    input("Running touch script. Press Enter to continue...")

    bin_cam_pose = np.loadtxt('real_world/cam_pose/cam2ur_pose.txt')
    bin_cam_depth_scale = np.loadtxt('real_world/cam_pose/camera_depth_scale.txt')
    print("bin_cam_pose: ", bin_cam_pose)
    print("bin_cam_depth_scale: ", bin_cam_depth_scale)

    # Callback function for clicking on OpenCV window
    click_point_pix = ()
    color_im, depth_im = bin_cam.get_camera_data()

    def mouseclick_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            global click_point_pix
            click_point_pix = (x, y)
            
            # Get click point in camera coordinates
            click_z = depth_im[y, x] * bin_cam_depth_scale
            click_x = (x-bin_cam.color_intr[0, 2]) * \
                click_z/bin_cam.color_intr[0, 0]
            click_y = (y-bin_cam.color_intr[1, 2]) * \
                click_z/bin_cam.color_intr[1, 1]
            if click_z == 0:
                return
            pick_point = np.asarray([click_x, click_y, click_z])
            pick_point = np.append(pick_point, 1.0).reshape(4, 1)

            # Convert camera coordinates to robot coordinates
            pick_pos = np.dot(bin_cam_pose, pick_point)
            pick_pos = pick_pos[0:3, 0]

            print("Grasp:", robot.check_grasp())

            # Move robot to target position for pick if it is currently grasping nothing
            if robot.check_grasp() == False:
                robot.open_suction_sys()
                # Move robot to target position only if it is above the table
                pick_pos[2] = max(pick_pos[2], WORKSPACE_SURFACE)
            
                robot.open_gripper()
                print("Moving robot to target position for pick...")
                postpick_pos = deepcopy(pick_pos)
                postpick_pos[2] += 0.2
                print("Pick position: ", pick_pos)
                robot.movel(list(pick_pos) + tool_orientation, 0.5, 0.1, blocking=True)
                robot.close_gripper()
                print("Current grasp: ", robot.check_grasp())
                while not robot.check_grasp():
                    pick_pos[2] -= 0.01
                    if pick_pos[2] < WORKSPACE_SURFACE:
                        print("Reached workspace surface; cannot go lower")
                        robot.open_gripper()
                        break
                    robot.movel(list(pick_pos) + tool_orientation, 0.05, 0.05, blocking=True)
                print("Current grasp: ", robot.check_grasp())
                robot.movel(list(postpick_pos) + tool_orientation, 0.5, 0.1, blocking=True)
            
            # This script is for testing purpose only
            # Replace bin with the output from owl-vit detection each time
            bin = [391.05106, 175.80579, 506.1133 , 281.53677]
            place_pix = [int((bin[0] + bin[2])/2), int((bin[1] + bin[3])/2)]
            place_pix = place_pix[0] + WS_CROP_Y[0] - 5, place_pix[1] + WS_CROP_X[0]
            
            # Get place point in camera coordinates
            z = depth_im[place_pix[1], place_pix[0]] * bin_cam_depth_scale
            x = (place_pix[0]-bin_cam.color_intr[0, 2]) * \
                z/bin_cam.color_intr[0, 0]
            y = (place_pix[1]-bin_cam.color_intr[1, 2]) * \
                z/bin_cam.color_intr[1, 1]
            if z == 0:
                return
            place_point = np.asarray([x, y, z])
            place_point = np.append(place_point, 1.0).reshape(4, 1)

            # Convert camera coordinates to robot coordinates
            place_pos = np.dot(bin_cam_pose, place_point)
            place_pos = place_pos[0:3, 0]
            
            # Move robot to target position only if it is above the table
            place_pos[2] = max(place_pos[2], BIN_TOP)

            # Move robot to target position for place if it is currently grasping something
            if robot.check_grasp() == True:
                print("Moving robot to target position for place...")
                prepostplace_pos = deepcopy(place_pos)
                prepostplace_pos[2] += 0.1
                print("Place position: ", place_pos)
                robot.movel(list(prepostplace_pos) + tool_orientation, 0.5, 0.1, blocking=True)
                robot.movel(list(place_pos) + tool_orientation, 0.5, 0.1, blocking=True)
                robot.open_gripper()
                print("Current grasp: ", robot.check_grasp())
                robot.movel(list(prepostplace_pos) + tool_orientation, 0.5, 0.1, blocking=True)
                robot.close_suction_sys()
                robot.home()

    # Show color and depth frames
    cv2.namedWindow('color')
    cv2.setMouseCallback('color', mouseclick_callback)

    while True:
        color_im, depth_im = bin_cam.get_camera_data()
        bgr_data = cv2.cvtColor(color_im, cv2.COLOR_RGB2BGR)
        if len(click_point_pix) != 0:
            bgr_data = cv2.circle(bgr_data, click_point_pix, 7, (0, 0, 255), 2)
        cv2.imshow('color', bgr_data)

        if cv2.waitKey(1) == ord('q'):
            robot.close_suction_sys()
            robot.home()
            break
