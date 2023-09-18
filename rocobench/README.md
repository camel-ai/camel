# RoCoBench: Task Suite for Multi-Robot Collaboration 

<img src="../teaser.jpg" alt="RoCoBench" width="700"/>

## Overview

RoCoBench is a multi-robot collaboration benchmark built on [MuJoCo](https://github.com/deepmind/mujoco) simulation. The current version contains 6 tasks, and support 4 types of robots: a Franka Panda robot arm, a UR5E arm with Robotiq 2f85 gripper, a UR5E arm with suction gripper, and a torso-only humanoid robot. 

## RoCoBench-Text
This text-based dataset is designed to evaluated an LLM's agent representation and task reasoning ability. The dataset is based on the above RoCoBench tasks, but requires no robotic environment interaction. The questions are more open-ended and go beyond simply finding the next best action plan.

## Acknowledgement
The Franak Panda, UR5E arm, and Robotiq gripper models are from the open-source [MuJoCo Menagerie](https://github.com/deepmind/mujoco_menagerie) project. Some of the object assets are borrowed from [Robosuite](https://robosuite.ai/) and [object sim](https://github.com/vikashplus/object_sim) repo. The suction gripper mesh is built on top of the gripper assets from the [Ravens](https://github.com/google-research/ravens/tree/master) benchmark. Special thanks to [Huy Ha](https://cs.columbia.edu/~huy) for helping with various aspects in the motion planning and simulation code. 