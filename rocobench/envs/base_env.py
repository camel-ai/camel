import os
import copy
import time
import cv2 
import numpy as np 
import random
from PIL import Image 
from copy import deepcopy 
import matplotlib.pyplot as plt
from collections import deque, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from numpy.typing import ArrayLike, NDArray
from pydantic import dataclasses, validator

import mujoco
from mujoco import FatalError as mujocoFatalError
import dm_control 
from dm_control import mujoco as dm_mujoco
from dm_control.utils.transformations import mat_to_quat, quat_to_euler
from .env_utils import AllowArbitraryTypes
from .constants import UR5E_ROBOTIQ_CONSTANTS, UR5E_SUCTION_CONSTANTS, PANDA_CONSTANTS


@dataclasses.dataclass(frozen=False)
class MjSite:
    """ To side-step using native mujoco._structs._MjDataSiteViews object """
    name: str 
    xpos: Any 
    xmat: Any 
    xquat: Any 

    @property
    def pose(self) -> np.ndarray:
        return np.concatenate([self.xpos, self.xquat])

@dataclasses.dataclass(frozen=False)
class ObjectState:
    """ object state """
    name: str
    xpos: Any 
    xquat: Any 
    sites: Dict 
    contacts: Set[str] # a set of body names

    @property
    def top_height(self) -> float:
        """ max of all site heights """
        heights = [site.xpos[2] for site in self.sites]
        return max(heights)
    
    @property
    def bottom_height(self) -> float:
        """ min of all site heights """
        heights = [site.xpos[2] for site in self.sites]
        return min(heights)

@dataclasses.dataclass(frozen=True)
class RobotState:
    name: str 
    base_xpos: Any
    ee_xpos: Any
    ee_xmat: Any
    grasp: bool 
    qpos: Any
    qvel: Any
    contacts: Set[str] # a set of body names

    @validator("ee_xpos", "base_xpos")
    def _validate_xpos(cls, v):
        assert len(v) == 3, f"Invalid xpos shape {v.shape}"
        return v
    
    @validator("ee_xmat")
    def _validate_xmat(cls, v):
        assert v.shape == (9,), f"Invalid xmat shape {v.shape}"
        return v
    
    @property
    def ee_xquat(self) -> NDArray:
        """ convert ee_xmat to quat """
        _xquat = mat_to_quat(self.ee_xmat.reshape(3,3))
        return _xquat
    
    @property
    def ee_rot(self) -> NDArray:
        quat = self.ee_xquat
        euler = quat_to_euler(quat)
        return euler
    
    @property
    def ee_pose(self) -> NDArray:
        """ convert ee_xmat to quat """
        return np.concatenate([self.ee_xpos, self.ee_xquat])

@dataclasses.dataclass(config=AllowArbitraryTypes, frozen=True)
class EnvState:
    """
    Notice how the robot states (i.e. ur5e_suction, panda, ur5e_robotiq, humanoid) are optional, 
    because each task may have different number and set of robots. 
    """
    objects: Dict[str, ObjectState] 
    ur5e_suction: Union[RobotState, None] = None
    panda:        Union[RobotState, None] = None
    ur5e_robotiq: Union[RobotState, None] = None
    humanoid:     Union[RobotState, None] = None

    def get_object(self, name: str) -> ObjectState:
        assert name in self.objects, f"Object {name} not found in env state"
        return self.objects[name]
 
@dataclasses.dataclass(frozen=True)
class SimSaveData:
    """ saved at intermediate simulation steps """
    timestep: float # physics.timestep()
    env_state: EnvState
    qpos: Any
    qvel: Any
    ctrl: Any
    xpos: Any
    xquat: Any
    eq_active: Any
    body_pos: Any
    body_quat: Any 

@dataclasses.dataclass(frozen=False)
class SimAction:
    """ action for directly setting ctrl values """
    ctrl_idxs: Any 
    ctrl_vals: Any  
    qpos_idxs: Any  
    qpos_target: Any   
    eq_active_idxs: Any = None
    eq_active_vals: Any = None 

    @validator("ctrl_vals", "qpos_target",)
    def _validate_vals(cls, v):
        if v is None:
            return []  
        assert isinstance(v, List) or isinstance(v, np.ndarray), f"Invalid idxs, got {type(v)}"
        if len(v) > 0:
            assert all([isinstance(i, np.float32) for i in v]), f"Invalid value, got {type(v)}"
        return v 

    @validator("ctrl_idxs", "qpos_idxs")
    def _validate_idxs(cls, v):
        if v is None:
            return [] 
        assert isinstance(v, List) or isinstance(v, np.ndarray), f"Invalid idxs, got {type(v)}"
        if len(v) > 0:
            assert all([isinstance(i, np.int32) for i in v]), f"Invalid idx, got {type(v)}"
        return v

    def __post_init__(self):
        """ validate that all idxs and vals are same length """ 
        _idxs = self.ctrl_idxs
        _vals = self.ctrl_vals
        if _idxs is None or _vals is None:
            _idxs, _vals = [], []
        assert len(_idxs) == len(_vals), f"{prefix}ctrl_idxs and {prefix}ctrl_vals must be same length"
        # set everything to array if not already
        setattr(self, "ctrl_idxs", np.array(_idxs, dtype=np.int32))
        setattr(self, "ctrl_vals", np.array(_vals, dtype=np.float32))

        for prefix in ["qpos",]: # "xpos", "xquat"]:
            _idxs = getattr(self, f"{prefix}_idxs")
            _vals = getattr(self, f"{prefix}_target")
            if _idxs is None or _vals is None:
                _idxs, _vals = [], []
            assert len(_idxs) == len(_vals), f"{prefix}_idxs and {prefix}_target must be same length"
            # set everything to array if not already
            setattr(self, f"{prefix}_idxs", np.array(_idxs, dtype=np.int32))
            setattr(self, f"{prefix}_target", np.array(_vals, dtype=np.float32))
 
    
    def qpos_error(self, qpos):
        """ compute qpos error """
        if len(self.qpos_idxs) == 0:
            return 0
        current_qpos = qpos[self.qpos_idxs]
        assert current_qpos.shape == self.qpos_target.shape, \
            f"qpos shape {qpos.shape} != qpos_target shape {self.qpos_target.shape}"
        return np.linalg.norm(current_qpos - self.qpos_target)

    def compute_error(self, qpos, xpos, xquat) -> Dict:
        """ compute errors, assume input are raw env state values """
        return self.qpos_error(qpos) 

class MujocoSimEnv:
    """ 
    Base environment for all tasks. Loads from a mujoco xml file and accesses the simulation 
    via dm_control Physics engine. Notice how some methods are not implemented, these are
    specific to each task. See task_[task_name].py for more details.
    """

    def __init__(
        self, 
        filepath: str, 
        task_objects: List[str], # key objects for each task
        agent_configs: Dict = dict(ur5e_suction=UR5E_ROBOTIQ_CONSTANTS, panda=PANDA_CONSTANTS), 
        render_cameras: List[str] = ["face_panda", "face_ur5e", "top_cam", "right_cam", "left_cam", "teaser"],
        image_hw: Tuple = (480,480),
        render_freq: int = 20,
        home_qpos: Union[NDArray, None] = None, 
        sim_forward_steps=100,
        sim_save_freq=100,
        home_keyframe_id=0,
        error_threshold=1e-3,
        error_freq=3,
        randomize_init=True,
        np_seed=0,
        render_point_cloud=False, 
        skip_reset=False,
        ):
        # print(filepath)
        self.xml_file_path = filepath
        self.physics = dm_mujoco.Physics.from_xml_path(filepath)
        self.home_qpos = home_qpos 
        self.home_keyframe_id = home_keyframe_id

        # try loading home_qpos to the xml file 
        try:
            copy_physics = dm_mujoco.Physics.from_xml_path(filepath)
            copy_physics.reset() 
            copy_physics.step()
        except ValueError as e:
            print("Error: ", e)
            print("Home qpos is not loaded to the xml file")
        del copy_physics

        self.agent_configs = agent_configs 
        for k, v in self.agent_configs.items():
            assert k in ["ur5e_suction", "panda", "ur5e_robotiq", "humanoid"], f"agent name {k} not supported" 

        self.task_objects = task_objects 

        self.sim_forward_steps = sim_forward_steps
        self.sim_save_freq = sim_save_freq # NOTE: this save intermediate steps during stepping
        self.save_buffer = deque(maxlen=sim_forward_steps//sim_save_freq)
        self.error_threshold = error_threshold
        self.error_freq = error_freq

        # check rendering options
        self.render_point_cloud = render_point_cloud
        self.render_buffers = dict()
        for cam in render_cameras:
            try:
                self.physics.render(camera_id=cam, height=image_hw[0], width=image_hw[1])
            except Exception as e:
                print("Got Error: ", e)
                print("Camera {} does not exist in the xml file".format(cam))
            self.render_buffers[cam] = deque(maxlen=3000)
        self.render_cameras = render_cameras
        self.render_freq = render_freq
        self.image_hw = image_hw

        self.random_state = np.random.RandomState(np_seed)
        self.randomize_init = randomize_init
        if not skip_reset:
            # reset to home pos and record pos values
            if home_keyframe_id is not None:
                self.reset(keyframe_id=home_keyframe_id, home_pos=None, reload=False)
            else:
                assert home_qpos is not None, "home_qpos must be provided if home_keyframe_id is not provided"
                self.reset(keyframe_id=None, home_pos=home_qpos, reload=False)

    def reset_body_pose(self, body_name, pos = None, quat = None):
        try:
            if pos is not None:
                self.physics.model.body(body_name).pos[:] = pos
            if quat is not None:
                self.physics.model.body(body_name).quat[:] = quat
        except KeyError:
            print('Cannot set new body pose for: ', body_name)
        self.physics.forward()

    def reset_qpos(self, jnt_name: str, pos: np.ndarray = None, quat: np.ndarray = None):
        try:
            qpos_slice = self.physics.named.data.qpos._convert_key(jnt_name)
        except KeyError:
            print('Cannot set new qpos for: ', jnt_name)
            breakpoint()
        
        assert int(qpos_slice.stop - qpos_slice.start) == 7, "object qpos must be 7-dim"
        start = qpos_slice.start
        stop = qpos_slice.stop
        if pos is not None:
            self.physics.named.data.qpos[start:start+3] = pos
        if quat is not None:
            self.physics.named.data.qpos[start+3:stop] = quat
        self.physics.forward()

    def seed(self, np_seed):
        self.random_state = np.random.RandomState(np_seed)

    def reset(self, keyframe_id=0, home_pos=None, reload=False, filepath=None):
        if reload:
            if filepath is None:
                filepath = self.xml_file_path
            assert os.path.exists(filepath), f"While attempting to reload from xml file, filepath {filepath} does not exist"
            self.physics = dm_mujoco.Physics.from_xml_path(filepath)
        self.physics.reset(keyframe_id=keyframe_id)
        if home_pos is not None:
            self.ndata.qpos[:] = home_pos
            self.physics.forward()
        if self.randomize_init:
            self.sample_initial_scene()
        # clear out render buffers
        self.clear_camera_buffer()
        self.clear_save_buffer()
        self.render_all_cameras()
        obs = self.get_obs()
        self.timestep = 0
        return obs
    
    def action_spec(self):
        names = [self.model.id2name(i, 'actuator') or str(i) \
                for i in range(self.model.nu)]
        action_spec = dm_mujoco.action_spec(self.physics)
        return action_spec  

    def print_current_qpos(self):
        qpos = self.ndata.qpos[:]
        length = self.ndata.qpos[:].shape[0]
        string = " ".join(["%.4f" % qpos[i] for i in range(length) ] )
        return string

    @property
    def qpos(self):
        return self.physics.named.data.qpos

    @property
    def data(self):
        return self.physics.data
    
    @property
    def ndata(self):
        return self.physics.named.data
    
    @property
    def model(self):
        return self.physics.model
    
    @property
    def nmodel(self):
        return self.physics.named.model

    def clear_camera_buffer(self):
        self.render_buffers = {cam: deque(maxlen=1000) for cam in self.render_cameras}

    def get_robot_reach_range(self, robot_name: str) -> Dict[str, Tuple[float, float]]:
        """ Overwrite this in each task script according to robot's reach range in each scene"""
        return dict(x=(-2, 2), y=(-1.5, 1.5), z=(0.1, 1))
    
    def check_reach_range(self, robot_name, point: Tuple[float, float, float]) -> bool: 
        reach_range = self.get_robot_reach_range(robot_name)
        for i, axis in enumerate(["x", "y", "z"]):
            if point[i] < reach_range[axis][0] or point[i] > reach_range[axis][1]:
                return False
        return True 
     
    def export_render_to_video(self, output_name="task_video", out_type="gif", fps=20, concat=True, video_duration=0):
        render_steps = len(self.render_buffers[self.render_cameras[0]])
        assert render_steps > 0 and all([len(self.render_buffers[cam]) == render_steps for cam in self.render_cameras]), \
            "Render buffers are not all the same length, got lengths: {}".format([len(self.render_buffers[cam]) for cam in self.render_cameras])
        assert out_type in ["gif", "mp4"], "out_type must be either gif or mp4"
        all_imgs = []
        for t in range(render_steps):
            images = [self.render_buffers[cam][t] for cam in self.render_cameras]
            if concat:
                images = np.concatenate(images, axis=1)
            else:
                images = images[0]
            all_imgs.append(images)
        if out_type == "gif":
            all_imgs = [Image.fromarray(img) for img in all_imgs]
            output_name += ".gif" if ".gif" not in output_name else ""
            if video_duration > 0:
                # ignore fps, use video duration instead
                duration = int(video_duration / render_steps * 1000)
            else:
                duration = int(1000 / fps)
            all_imgs[0].save(
                output_name, 
                save_all=True, 
                append_images=all_imgs[1:], 
                duration=duration,
                loop=0
                )
        elif out_type == "mp4":
            output_name += ".mp4" if ".mp4" not in output_name else ""
            w, h = all_imgs[0].shape[:2]
            if video_duration > 0:
                # ignore fps, use video duration instead
                fps = int(render_steps / video_duration)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video = cv2.VideoWriter(
                output_name, fourcc, fps, (h, w))
            for img in all_imgs: 
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) 
                video.write(img)
            video.release() 
        print('Video gif, total {} frames, saved to {}'.format(render_steps, output_name))
  
    def render_camera(self, camera_id, height=480, width=600):
        img_arr = self.physics.render(
            camera_id=camera_id, height=height, width=width,
            )
        self.render_buffers[camera_id].append(img_arr)
        return img_arr

    def render_all_cameras(self, save_img=False, output_name="render.jpg", show = False):
        imgs = []
        for cam_id in self.render_cameras:
            img_arr = self.render_camera(cam_id, height=self.image_hw[0], width=self.image_hw[1])
            imgs.append(img_arr)
        imgs = np.concatenate(imgs, axis=1)
        if show:
            plt.imshow(imgs)
            plt.show()
        if save_img:
            tosave = Image.fromarray(imgs)
            tosave.save(output_name)
        return imgs

    def get_contact(self) -> Dict:
        """ iterates through all contacts and return dict(each_root_body: set(other_body_names))""" 
        model = self.model
        data = self.data 
        ret = defaultdict(set)
        for geom1_id, geom2_id in zip(data.contact.geom1, data.contact.geom2):
            body1 = model.body(model.geom(geom1_id).bodyid) 
            body2 = model.body(model.geom(geom2_id).bodyid)  
            
            obj1 = model.body(body1.rootid)
            obj2 = model.body(body2.rootid)

            ret[obj1.name].add(obj2.name)
            ret[obj1.name].add(body2.name)

            ret[obj2.name].add(obj1.name)
            ret[obj2.name].add(body1.name) 
        # also check eq_active
        active = model.eq_active 
        nbody = model.nbody
        for i in range(len(active)):
            if active[i]:
                if model.eq_obj1id[i] not in range(nbody) or model.eq_obj2id[i] not in range(nbody):
                    # NOTE: special case for the rope composite body
                    continue                 
                body1 = model.body(model.eq_obj1id[i])
                body2 = model.body(model.eq_obj2id[i])
                obj1 = model.body(body1.rootid)
                obj2 = model.body(body2.rootid)
                ret[obj1.name].add(obj2.name)
                ret[obj1.name].add(body2.name)
                ret[obj2.name].add(obj1.name)
                ret[obj2.name].add(body1.name) 
        for k, v in ret.items():
            if 'weld' in k:
                ret.pop(k)
            newset = set()
            for name in v:
                if 'weld' not in name and '_pad' not in name:
                    newset.add(name)
            ret[k] = newset
        return ret

    def get_object_sites(self, obj_name) -> Dict[str, MjSite]:
        nsites = self.model.nsite 
        obj_sites = dict()
        for i in range(nsites):
            try:
                site = self.data.site(i) 
            except:
                AttributeError
                continue
            if obj_name in site.name:
                obj_sites[site.name] = MjSite(
                        name=site.name,
                        xpos=site.xpos,
                        xmat=site.xmat,
                        xquat=mat_to_quat(site.xmat.reshape(3,3),
                        )
                    )
        return obj_sites

    def get_object_states(self, contact_dict) -> List[ObjectState]:
        model = self.model
        data = self.data
        ret = dict()
        for obj in self.task_objects:
            try:
                body = data.body(obj)
                obj_sites = self.get_object_sites(obj)
            except:
                KeyError('Object {} not found'.format(obj))
                continue
            state = ObjectState(
                name=obj, 
                xpos=body.xpos, 
                xquat=body.xquat, 
                sites=obj_sites,
                contacts=contact_dict.get(obj, set()),
                )
            ret[obj] = state
        return ret 
    
    def get_all_body_ids(self, body_name: str) -> List[int]:
        """ get all body ids that contains body_name """
        try:
            rootid = self.physics.model.body(body_name).id 
        except KeyError:
            print('Body {} not found'.format(body_name))
            breakpoint()

        body_ids = [rootid]
        for i in range(self.physics.model.nbody):
            body = self.physics.model.body(i)
            if body.rootid == rootid:
                body_ids.append(body.id)
        return body_ids
 
    def get_agent_state(self, agent_constants, contact_dict):
        """ Agent can be any of the ur5e, panda, or humanoid robots"""
        data = self.data
        name = agent_constants.get('name', None)
        assert 'ur5e' in name or name == 'panda' or name == "humanoid", 'Agent name {} not supported'.format(name)
        if name is None:
            raise ValueError('Agent name not specified in agent_constants')

        ee_site_name = agent_constants['ee_site_name']
        ee_xpos = data.site(ee_site_name).xpos
        ee_xmat = data.site(ee_site_name).xmat
        jnt_names = agent_constants['all_joint_names']
        agent_qpos = self.ndata.qpos[jnt_names]
        agent_qvel = self.ndata.qvel[jnt_names]

        
        agent_state = RobotState(
            name=name,
            base_xpos=data.body(name).xpos,
            ee_xpos=ee_xpos,
            ee_xmat=ee_xmat,
            contacts=contact_dict.get(name, set()),
            qpos=agent_qpos,
            qvel=agent_qvel,
            grasp=False,
        )

        return agent_state

    def get_obs(self) -> EnvState: 
        contacts = self.get_contact() 
        obj_states = self.get_object_states(contact_dict=contacts)
        agent_states = dict()
        for agent_name, agent_constants in self.agent_configs.items():
            agent_state = self.get_agent_state(
                agent_constants, contact_dict=contacts
            ) 
            agent_states[agent_name] = agent_state
        kwargs = dict(
            objects=obj_states,
        )
        kwargs.update(agent_states)
        if self.render_point_cloud:
            raise NotImplementedError # TODO: the point cloud implementation isn't fully working
        obs = EnvState(**kwargs)
        return obs

    def print_qpos(self, key_format=False):
        string = " ".join(
            [f"{x:.4f}" for x in self.physics.data.qpos]
        )
        if key_format:
            string = f"<key name='debug' qpos='{string}'/>"
        return string 

    def clear_save_buffer(self):
        self.save_buffer = []

    def convert_named_data_to_dict(self, attr_name):
        indexer = getattr(self.ndata, attr_name)
        assert isinstance(indexer, dm_control.mujoco.index.FieldIndexer), "indexer is not a FieldIndexer"
        names = indexer._axes.row._names
        values = np.array(indexer)
        # breakpoint()
        # assert values.shape[0] == len(names), f"{attr_name}: values and names have different lengths, {values.shape[0]} != {len(names)}"
        return dict(field_names=names, field_values=values)

    def save_intermediate_state(self):
        obs = self.get_obs()
        kwargs = dict(
            timestep=self.physics.timestep(),
            env_state=obs,
            )
        for attr_name in ['qpos', 'qvel', 'xpos', 'xquat', 'ctrl']:
            # _dict = self.convert_named_data_to_dict(attr_name)
            # kwargs.update(_dict)
            kwargs[attr_name] = deepcopy(getattr(self.ndata, attr_name)) # NOTE: use deepcopy!!
        kwargs['eq_active'] = deepcopy(self.physics.model.eq_active)
        kwargs['body_pos'] = deepcopy(self.physics.model.body_pos)
        kwargs['body_quat'] = deepcopy(self.physics.model.body_quat)
        save_data = SimSaveData(**kwargs)
        self.save_buffer.append(save_data)
        return save_data

    def load_saved_state(self, data: SimSaveData) -> None:
        qpos = data.qpos
        eq_active = data.eq_active
        self.physics.data.qpos[:] = qpos
        self.physics.data.qvel[:] = data.qvel
        self.physics.data.ctrl[:] = data.ctrl
        self.physics.model.eq_active[:] = eq_active
        self.physics.model.body_pos[:] = data.body_pos
        self.physics.model.body_quat[:] = data.body_quat
        self.physics.forward() 

    def step(self, action: SimAction, verbose: bool = False) -> Tuple[EnvState, float, bool, dict]:
        ctrl_vals = action.ctrl_vals
        ctrl_idxs = action.ctrl_idxs 
        assert len(ctrl_vals) == len(ctrl_idxs) and len(ctrl_vals) > 0, f"ctrl_vals: {ctrl_vals}, ctrl_idxs: {ctrl_idxs}"
        eq_active_idxs = action.eq_active_idxs
        eq_active_vals = action.eq_active_vals

        self.clear_save_buffer()
        self.save_intermediate_state() # obs_T
        # NEW: distable contact margins before stepping
        contact_margins = self.physics.model.pair_margin.copy()
        self.physics.model.pair_margin[:] = 0.0
        self.physics.forward()
        for step in range(self.sim_forward_steps): 
            self.data.ctrl[ctrl_idxs] = ctrl_vals 

            if eq_active_idxs is not None and len(eq_active_idxs) > 0:
                self.physics.model.eq_active[eq_active_idxs] = eq_active_vals
            self.physics.step() 
            if step % self.render_freq == 0:
                self.render_all_cameras()
            
            if step % self.sim_save_freq == 0: 
                self.save_intermediate_state() # obs_T+t

            if step % self.error_freq == 0:
                error_dict = action.compute_error(
                    qpos=self.data.qpos, xpos=self.data.xpos, xquat=self.data.xquat) 
                
                #print('error_dict:', {error_dict}, 'step:', {step})
                #if error_dict['error'] < self.error_threshold and step > self.render_freq * 2:
                if error_dict < self.error_threshold and step > self.render_freq * 2:
                    break  
        self.render_all_cameras()
        
        self.physics.model.pair_margin[:] = contact_margins
        self.physics.forward()
        
        next_obs = self.get_obs() # obs_T+1
        if verbose:
            #print(f"Sim Steped {step} steps, Error: {error_dict['error']}")
            print(f"Sim Steped {step} steps, Error: {error_dict}")
        reward, done = self.get_reward_done(next_obs)
        self.timestep += 1
        info = dict() 
        return next_obs, reward, done, info  
    
    def get_sim_robots(self):
        """NOTE this is indexed by agent name, not actual robot names"""
        return self.robots
    
    def get_robot_config(self) -> Dict[str, Dict[str, Any]]:
        return self.agent_configs 

    def get_site_pos_quat(self, site_name):
        site_pos = self.ndata.site_xpos[site_name]
        site_mat = self.ndata.site_xmat[site_name].reshape(3,3)
        site_quat = np.array(mat_to_quat(site_mat))
        return site_pos, site_quat
    
    def get_body_pos_quat(self, body_name):
        body_pos = self.data.body(body_name).pos
        body_quat = self.data.body(body_name).quat
        return body_pos, body_quat

    def get_point_cloud(self):
        raise NotImplementedError # TODO

    # NOTE: everything below is task specific, overwrite in each task script
    def sample_initial_scene(self):
        # task specific!
        return 
    
    @property
    def use_prepick(self):
        """
        If True, hard-code the robot picking trajectory to first hover over an object before picking
        it in top-down fasion.
        """
        return False 
    
    @property
    def use_preplace(self):
        """
        If True, hard-code the robot placing trajectory to hover over a place target before placing an 
        object, so the trajectory looks something like below:
            ^------>
            |      |
            pick  place
        """
        return False 
    
    @property
    def waypoint_std_threshold(self):
        """
        Used for providing feedback to LLM-generated waypoints: a waypoint path is not valid
        unless the steps are evenly paced with variance lower than this threshold.        
        """
        return 1.0

    def get_graspable_objects(self):
        return None
    
    def get_allowed_collision_pairs(self) -> List[Tuple[int, int]]:
        """ for some tasks, allow certain pairs of graspable objects to collide"""
        return []

    def get_target_pos(self, agent_name, target_name) -> Optional[np.ndarray]: 
        """ 
        Find a target object's 3D position, return None if the object isn't in the task environment
        """
        return None
    
    def get_target_quat(self, agent_name, target_name):
        """
        Returns the desired orientation for an object or site. 
        Useful for finding a robot's grasping pose.
        """
        return np.array([1, 0, 0, 0])

    def get_grasp_site(self, obj_name) -> str:
        """ 
        Given a target object, find the site name for grasping. Most objects are defined with a 
        top-down grasp site -- see the task .xml files. Having attached sites to 
        objects is also needed for forward IK with objects in-hand.
        """
        return obj_name 
    
    def get_object_joint_name(self, obj_name) -> str:
        """ 
        Find the free joint that defines the location of each object wrt the worldbody.
        Also needed to compute forward IK with the objects in-hand. 
        """
        return f"{obj_name}_joint"

    def get_reward_done(self, obs): 
        """
        Determines the success and termination condition, must be defined
        specifically for each task.
        """
        return 0, False 

    
    # NOTE: Below are utils required for generating prompts, defined separately in each task script
    def get_action_prompt(self):
        """ Describes the action space for the task """ 
        raise NotImplementedError
    
    def describe_obs(self, obs: EnvState):
        """ Describes the observation for the task at the current time step """
        raise NotImplementedError

    def describe_task_context(self):
        """ Describes overall context of each task in a third-person perspective. This is Not used for dialog agents """
        raise NotImplementedError

    def get_agent_prompt(self, agent_name):
        """ Describes the task from the perspective of each given agent """
        raise NotImplementedError
    
    def get_task_feedback(self, llm_plan, pose_dict) -> str:
        """ Given a plan and a pose dict, checks task-specific conditions and returns feedback string """
        return "" 




    
    


