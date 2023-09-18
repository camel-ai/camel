import requests
import pickle
import time
import numpy as np
import matplotlib.pyplot as plt
import cv2  
from PIL import Image

# See https://github.com/columbia-ai-robotics/PyKinect

WS_PC = [180, -120, 300, -380]

def get_workspace_crop(img):
    retval = img[WS_PC[0]:WS_PC[1], WS_PC[2]:WS_PC[3], ...]
    return retval

class KinectClient:
    def __init__(self, ip, port, fielt_bg=False):
        self.ip = ip
        self.port = port
        self.fielt_bg = fielt_bg
    
    @property
    def color_intr(self):
        return self.get_intr()

    def get_intr(self):
        return pickle.loads(requests.get(f'http://{self.ip}:{self.port}/intr').content)

    def get_camera_data(self, n=1, fielt_bg=None):
        cam_data = pickle.loads(requests.get(f'http://{self.ip}:{self.port}/pickle').content)
        color_img = cam_data['color_img']
        depth_img = cam_data['depth_img']
        depth_img *= 0.973 # camera's depth offset
        if fielt_bg is None:
            fielt_bg = self.fielt_bg
        if fielt_bg:
            mask = (cv2.cvtColor(color_img, cv2.COLOR_RGB2HSV)[:, :, 2] > 150)
            color_img = color_img * mask[:, :, np.newaxis] + (1 - mask[:, :, np.newaxis]) * np.array([90, 89, 89])
            color_img = color_img.astype(np.uint8)
        
        return color_img, depth_img

if __name__ == '__main__':

    ip = "128.59.23.32"
    port = 8080
    kinect = KinectClient(ip, port)
    
    counter = 0
    limit = 100
    sleep = 0.05

    all_rgbs = []
    while counter < limit:
        img, depth = kinect.get_camera_data()
        im = Image.fromarray(img)
        
        print("img shape: ", img.shape)
        print("depth shape: ", depth.shape)
        counter += 1
        time.sleep(sleep)
        print('Step counter at {}'.format(counter))
        all_rgbs.append(img)

        fig, ax = plt.subplots(2, 2, figsize=(10, 5))
        ax[0][0].imshow(img)
        ax[0][1].imshow(depth)
        ax[1][0].imshow(get_workspace_crop(img))
        ax[1][1].imshow(get_workspace_crop(depth))
        plt.show()