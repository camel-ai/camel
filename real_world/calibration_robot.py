import time
import numpy as np
import cv2
from scipy import optimize
from real_world.realur5 import UR5RTDE
from real_world.kinect import KinectClient

measured_pts, observed_pts, observed_pix, world2camera = [None]*4
DEFAULT_ORN = [2.22, -2.22, 0.0]

def calibrate(
    cam, 
    ur5, 
    workspace_bounds, 
    ee_tip_offset, 
    ee_to_checker=0.158, 
    calib_grid_step=0.05
    ):
    global measured_pts, observed_pts, observed_pix, world2camera

    checkerboard_offset = ee_tip_offset + np.array([0, 0, ee_to_checker])
    print("checkerboard_offset: ", checkerboard_offset)

    # Construct 3D calibration grid across workspace
    gridspace_x = np.linspace(
        workspace_bounds[0, 0],
        workspace_bounds[0, 1],
        1 + int((workspace_bounds[0, 1]-workspace_bounds[0, 0] + 1e-4)/calib_grid_step))
    gridspace_y = np.linspace(
        workspace_bounds[1, 0],
        workspace_bounds[1, 1],
        1+int((workspace_bounds[1, 1]-workspace_bounds[1, 0] + 1e-4)/calib_grid_step))

    print("gridspace_x, gridspace_y: ", gridspace_x, gridspace_y)

    calib_grid_x, calib_grid_y, calib_grid_z = np.meshgrid(
        gridspace_x, gridspace_y, workspace_bounds[2, 0]+0.1)
    num_calib_grid_pts = calib_grid_x.shape[0] * \
        calib_grid_x.shape[1]*calib_grid_x.shape[2]
    calib_grid_x.shape = (num_calib_grid_pts, 1)
    calib_grid_y.shape = (num_calib_grid_pts, 1)
    calib_grid_z.shape = (num_calib_grid_pts, 1)
    calib_grid_pts = np.concatenate(
        (calib_grid_x, calib_grid_y, calib_grid_z), axis=1)
    print("calib_grid_points: ", calib_grid_pts)

    # Move robot to each calibration point in workspace
    measured_pts = list()
    observed_pts = list()
    observed_pix = list()
    print("num_calib_grid_pts: ", num_calib_grid_pts)

    for calib_pt_idx in range(num_calib_grid_pts):
        tool_position = calib_grid_pts[calib_pt_idx, :]
        tool_position[2] = workspace_bounds[2, 1]
        print("tool_position: ", tool_position)
        ur5.movel(list(tool_position) + DEFAULT_ORN)
        time.sleep(1.0)
        while True:
            color_im, depth_im = cam.get_camera_data()
            chckr_size = (3, 3)
            refine_criteria = (cv2.TERM_CRITERIA_EPS +
                               cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            gray_im = color_im[:, :, 0] - np.mean(color_im[:,:,[1,2]], axis=-1)
            gray_im -= np.min(gray_im)
            gray_im /= np.max(gray_im)
            gray_im = (255 - gray_im * 255.0).astype(np.uint8)
            chckr_found, crnrs = cv2.findChessboardCorners(
                gray_im, chckr_size, None, cv2.CALIB_CB_ADAPTIVE_THRESH)
            if chckr_found:
                crnrs_refined = cv2.cornerSubPix(
                    gray_im, crnrs, (3, 3), (-1, -1), refine_criteria)
                block_pix = crnrs_refined[4, 0, :]
                break
            time.sleep(0.01)
        
        # Get observed checkerboard center 3D point in camera space
        block_z = depth_im[
            int(np.round(block_pix[1])),
            int(np.round(block_pix[0]))
        ]
        print(tool_position, f'[{int(np.round(block_pix[1]))}, {int(np.round(block_pix[0]))}], {block_z:.5f}')
        cam_intr = cam.get_intr()
        block_x = np.multiply(
            block_pix[1] - cam_intr[0, 2],
            block_z / cam_intr[0, 0]
        )
        block_y = np.multiply(
            block_pix[0] - cam_intr[1, 2],
            block_z / cam_intr[1, 1]
        )
        if block_z == 0:
            continue

        # Save calibration point and observed checkerboard center
        observed_pts.append([block_x, block_y, block_z])
        tool_position += checkerboard_offset
        measured_pts.append(tool_position)
        observed_pix.append(block_pix)

        # Draw and display the corners
        print('block_pix = ', block_pix)
        vis_im = cv2.circle(
            color_im, (int(block_pix[0]), int(block_pix[1])), 7, (0, 255, 0), 2)
        cv2.imshow('Calibration', cv2.cvtColor(vis_im, cv2.COLOR_RGB2BGR))
        cv2.waitKey(10)

    # Move robot back to home pose
    ur5.home(blocking=True)

    measured_pts = np.asarray(measured_pts)
    observed_pts = np.asarray(observed_pts)
    observed_pix = np.asarray(observed_pix)
    world2camera = np.eye(4)

    # Estimate rigid transform with SVD (from Nghia Ho)
    def get_rigid_transform(A, B):
        assert len(A) == len(B)
        N = A.shape[0]  # Total points
        centroid_A = np.mean(A, axis=0)
        centroid_B = np.mean(B, axis=0)
        AA = A - np.tile(centroid_A, (N, 1))  # Centre the points
        BB = B - np.tile(centroid_B, (N, 1))
        # Dot is matrix multiplication for array
        H = np.dot(np.transpose(AA), BB)
        U, S, Vt = np.linalg.svd(H)
        R = np.dot(Vt.T, U.T)
        if np.linalg.det(R) < 0:  # Special reflection case
            Vt[2, :] *= -1
            R = np.dot(Vt.T, U.T)
        t = np.dot(-R, centroid_A.T) + centroid_B.T
        return R, t

    def get_rigid_transform_error(z_scale):
        global measured_pts, observed_pts, observed_pix, world2camera

        # Apply z offset and compute new observed points
        # using camera intrinsics
        observed_z = observed_pts[:, 2:] * z_scale
        observed_x = np.multiply(
            observed_pix[:, [0]]-cam_intr[0, 2],
            observed_z/cam_intr[0, 0])
        observed_y = np.multiply(
            observed_pix[:, [1]]-cam_intr[1, 2],
            observed_z/cam_intr[1, 1])
        new_observed_pts = np.concatenate(
            (observed_x, observed_y, observed_z), axis=1)

        # Estimate rigid transform between measured points
        # and new observed points
        R, t = get_rigid_transform(np.asarray(
            measured_pts), np.asarray(new_observed_pts))
        t.shape = (3, 1)
        world2camera = np.concatenate(
            (np.concatenate((R, t), axis=1), np.array([[0, 0, 0, 1]])), axis=0)

        # Compute rigid transform error
        registered_pts = np.dot(R, np.transpose(
            measured_pts)) + np.tile(t, (1, measured_pts.shape[0]))
        error = np.transpose(registered_pts) - new_observed_pts
        error = np.sum(np.multiply(error, error))
        rmse = np.sqrt(error/measured_pts.shape[0])
        return rmse

    # Optimize z scale w.r.t. rigid transform error
    print('Calibrating...')
    z_scale_init = 1
    optim_result = optimize.minimize(
        get_rigid_transform_error,
        np.asarray(z_scale_init),
        method='Nelder-Mead')
    camera_depth_offset = optim_result.x

    # Save camera optimized offset and camera pose
    print('Saving calibration files...')
    np.savetxt('real_world/cam_pose/camera_depth_scale.txt',
               camera_depth_offset,
               delimiter=' ')
    print('camera_depth_offset = ', camera_depth_offset)
    get_rigid_transform_error(camera_depth_offset)
    camera_pose = np.linalg.inv(world2camera)
    return camera_pose


if __name__ == "__main__":
    cam = KinectClient('128.59.23.32', '8080')
    ur5 = UR5RTDE(ip='192.168.0.113', home_joint=np.array([-180, -90, 90, -90, -90, 0]) / 180 * np.pi)
    ur5.home()

    np.savetxt('real_world/cam_pose/cam2ur_pose.txt',
                calibrate(cam, ur5, 
                    workspace_bounds = np.array([
                        [0.0, 0.54],
                        [0.38, 0.7],
                        [0.25, 0.25]
                        ]), 
                    ee_tip_offset=[0,0,0], 
                    calib_grid_step=0.1
                    ), 
                delimiter=' ')
    
 


    


