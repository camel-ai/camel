import os
import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import seaborn as sns
import torch

from typing import Dict
from pydantic import dataclasses, validator

from real_world.utils.generic import AllowArbitraryTypes
from real_world.kinect import KinectClient
from transformers import OwlViTProcessor, OwlViTForObjectDetection

WS_CROP_X = (180, -120)
WS_CROP_Y = (300, -380)

TASK = 'block_in_cup'
ALL_OBJECTS = ["blue cup", "yellow cup", "purple cup", "red hexagonal block", "yellow block", "strawberry toy", "wooden bin"]
TASK_OBJECTS = ["red hexagonal block", "yellow block", "strawberry toy"]

@dataclasses.dataclass(config=AllowArbitraryTypes, frozen=True)
class EnvState:
    color_im: np.ndarray # shape: (H, W, 3)
    depth_im: np.ndarray # shape: (H, W)
    objects: Dict[str, np.ndarray] # shape: (4,) (xmin, ymin, xmax, ymax)

    @validator("color_im")
    @classmethod
    def color_im_shape(cls, v: np.ndarray):
        if v.shape[2] != 3:
            raise ValueError("color_im must have shape (H, W, 3)")
        return v
    
    @validator("depth_im")
    @classmethod
    def depth_im_shape(cls, v: np.ndarray, values):
        if v.shape != values["color_im"].shape[:2]:
            raise ValueError("color_im and depth_im must have same (H, W)")
        return v
    
    @validator("objects")
    @classmethod
    def objects_shape(cls, v: Dict[str, np.ndarray]):
        for obj in v:
            if v[obj].shape != (4,):
                raise ValueError("objects must have shape (4,)")
        return v

class Task():
    def __init__(
        self,
        bin_cam):

        self.bin_cam = bin_cam
        self.task = TASK
        self.all_objects = ALL_OBJECTS
        self.task_objects = TASK_OBJECTS
        self.output_name = f"real_world/outputs/{self.task}/"
        os.makedirs(self.output_name, exist_ok=True)

        # Load OWL-ViT model
        self.model = OwlViTForObjectDetection.from_pretrained("google/owlvit-base-patch32")
        self.processor = OwlViTProcessor.from_pretrained("google/owlvit-base-patch32")

        self.timestep = 0
    
    def get_obs(self) -> EnvState:
        # Get color and depth images from the kinect
        color_im, depth_im = bin_cam.get_camera_data()
        bgr_data = cv2.cvtColor(color_im, cv2.COLOR_RGB2BGR)
        ws_color_im = color_im[WS_CROP_X[0]:WS_CROP_X[1], WS_CROP_Y[0]:WS_CROP_Y[1]]
        ws_depth_im = depth_im[WS_CROP_X[0]:WS_CROP_X[1], WS_CROP_Y[0]:WS_CROP_Y[1]]

        image = Image.fromarray(ws_color_im)
        text = ALL_OBJECTS

        inputs = self.processor(text=[text], images=image, return_tensors="pt")
        outputs = self.model(**inputs)

        # Target image sizes (height, width) to rescale box predictions [batch_size, 2]
        target_sizes = torch.Tensor([image.size[::-1]])

        # Convert outputs (bounding boxes and class logits) to COCO API
        results = self.processor.post_process(outputs=outputs, target_sizes=target_sizes)

        # Get prediction scores
        pred_scores = results[0]["scores"].detach().numpy()

        # Get prediction labels and boundary boxes
        pred_labels, pred_boxes = results[0]["labels"].detach().numpy(), results[0]["boxes"].detach().numpy()

        objects = {}
        for label in np.unique(pred_labels):
            max_score_idx = np.argmax(pred_scores[np.where(pred_labels == label)])
            max_score = pred_scores[np.where(pred_labels == label)][max_score_idx]
            max_box = pred_boxes[np.where(pred_labels == label)][max_score_idx]
            # print(f"Detected {text[label]} with confidence {round(max_score.item(), 3)} at location {max_box}")
            objects[text[label]] = max_box
        
        self.timestep += 1
        image.save(f"{self.output_name}/img_{self.timestep}.png")
        obs = EnvState(
            color_im=ws_color_im,
            depth_im=ws_depth_im,
            objects=objects,
        )
        return obs

    def plot_preds(self, color_im, objects, save=False):
        fig, ax = plt.subplots(figsize=(12, 12 * color_im.shape[0] / color_im.shape[1]))
        ax.imshow(color_im)
        colors = sns.color_palette('muted', len(objects))
        for label, c in zip(objects, colors):
            (xmin, ymin, xmax, ymax) = objects[label]
            ax.add_patch(
                plt.Rectangle((xmin, ymin), xmax - xmin, ymax - ymin, fill=False, color=c, linewidth=3))
            if label in self.task_objects:
                ax.text(xmin-30, ymax+15, label, fontsize=22, bbox=dict(facecolor='white', alpha=0.8))
            else:
                ax.text(xmin, ymin-10, label, fontsize=22, bbox=dict(facecolor='white', alpha=0.8))
        plt.axis('off')
        fig.tight_layout()
        plt.show()

        if save:
            fig.savefig(f"{self.output_name}/pred_{self.timestep}.png", bbox_inches='tight', pad_inches=0)
        
    def plot_preds_rotated(self, color_im, objects, save=False):
        fig, ax = plt.subplots(figsize=(12, 12 * color_im.shape[0] / color_im.shape[1]))
        from scipy import ndimage
        # ax.imshow(ndimage.rotate(color_im, 180))
        colors = sns.color_palette('muted', len(objects))
        for label, c in zip(objects, colors):
            (xmin, ymin, xmax, ymax) = objects[label]
            xmin = color_im.shape[1] - xmin
            xmax = color_im.shape[1] - xmax
            ymin = color_im.shape[0] - ymin
            ymax = color_im.shape[0] - ymax
            ax.add_patch(
                plt.Rectangle((xmin, ymin), xmax - xmin, ymax - ymin, fill=False, color=c, linewidth=3))
            if label in self.task_objects:
                ax.text(xmax-45, ymin+15, label, fontsize=22, bbox=dict(facecolor='white', alpha=0.8))
            else:
                ax.text(xmax, ymax-10, label, fontsize=22, bbox=dict(facecolor='white', alpha=0.8))
        plt.axis('off')
        fig.tight_layout()
        plt.show()

        if save:
            fig.savefig(f"{self.output_name}/pred_{self.timestep}.png", bbox_inches='tight', pad_inches=0)
    
    def describe_scene(
        self,
        objects,
        cup="cup",
        bin="wooden bin",
        ):
        scene_desp = "[Scene description]\n" 

        assert bin in objects, f"{bin} not detected"
        bin_box = objects[bin]
        bin_center = (bin_box[0]+bin_box[2])/2, (bin_box[1]+bin_box[3])/2
        bin_size = (bin_box[2]-bin_box[0])/2

        for obj in self.task_objects:
            obj_box = objects[obj]
            obj_center = (obj_box[0]+obj_box[2])/2, (obj_box[1]+obj_box[3])/2
            dist = ((obj_center[0]-bin_center[0])**2 + (obj_center[1]-bin_center[1])**2)**0.5
            if dist < bin_size:
                # determine if the object is inside the wooden bin
                scene_desp += f"{obj}: in {bin}\n"
            
            elif cup not in obj:
                # determine if the object is inside a cup
                inside_sth = False
                for other_obj in objects:
                    if cup in other_obj:
                        other_obj_box = objects[other_obj]
                        other_obj_center = (other_obj_box[0]+other_obj_box[2])/2, (other_obj_box[1]+other_obj_box[3])/2
                        dist_to_cup = ((obj_center[0]-other_obj_center[0])**2 + (obj_center[1]-other_obj_center[1])**2)**0.5
                        cup_size = (other_obj_box[2]-other_obj_box[0])/2
                        if dist_to_cup < cup_size:
                            scene_desp += f"{obj}: in {other_obj}\n"
                            inside_sth = True
                if not inside_sth:
                    # determine if the object is on the table
                    scene_desp += f"{obj}: on table\n"
        
        return scene_desp

if __name__ == "__main__":
    # Set up top-down kinect and task environment
    bin_cam = KinectClient(ip='128.59.23.32', port=8080)
    env = Task(bin_cam=bin_cam)

    while True:
        obs = env.get_obs()
        env.plot_preds(obs.color_im, obs.objects, False)
        env.plot_preds_rotated(obs.color_im, obs.objects, True)
        scene_desp = env.describe_scene(obs.objects)
        print(scene_desp)
        breakpoint()