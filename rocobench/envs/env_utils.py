from __future__ import annotations # this allows to use the class itself as a type hint
import numpy as np 
from itertools import product
from pydantic import dataclasses, validator
from transforms3d import affines, quaternions, euler
from typing import Dict, List, Optional, Sequence, Tuple


class AllowArbitraryTypes:
    # TODO look into numpy.typing.NDArray
    # https://numpy.org/devdocs/reference/typing.html#numpy.typing.NDArray
    arbitrary_types_allowed = True

@dataclasses.dataclass(config=AllowArbitraryTypes, frozen=False)
class Pose:
    position: np.ndarray  # shape: (3, )
    orientation: np.ndarray  # shape: (4, ), quaternion

    def __hash__(self) -> int:
        return hash((*self.position.tolist(), *self.orientation.tolist()))

    @validator("position")
    @classmethod
    def position_shape(cls, v: np.ndarray):
        if v.shape != (3,):
            raise ValueError("position must be 3D")
        return v

    def __post_init__(self):
        self.x = self.position[0]
        self.y = self.position[1]
        self.z = self.position[2]
        self.qx = self.orientation[0]
        self.qy = self.orientation[1]
        self.qz = self.orientation[2]
        self.qw = self.orientation[3]

    @property 
    def pos_string(self):
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"

    @validator("orientation")
    @classmethod
    def orientation_shape(cls, v: np.ndarray):
        if v.shape != (4,):
            raise ValueError("orientation must be a 4D quaternion")
        return v

    @property
    def array(self) -> np.ndarray:
        return np.concatenate([self.position, self.orientation])
        
    @property
    def flattened(self) -> List[float]:
        return list(self.position) + list(self.orientation)

    def __eq__(self, other) -> bool:
        return bool(
            np.allclose(self.position, other.position)
            and np.allclose(self.orientation, other.orientation)
        )

    @property
    def matrix(self) -> np.ndarray:
        return affines.compose(
            T=self.position, R=quaternions.quat2mat(self.orientation), Z=np.ones(3)
        )

    @staticmethod
    def from_matrix(matrix: np.ndarray) -> Pose:
        T, R = affines.decompose(matrix)[:2]
        return Pose(position=T.copy(), orientation=quaternions.mat2quat(R.copy()))

    def transform(self, transform_matrix: np.ndarray) -> Pose:
        assert transform_matrix.shape == (
            4,
            4,
        ), f"expected 4x4 transformation matrix but got {transform_matrix.shape}"
        T, R, _, _ = affines.decompose(transform_matrix @ self.matrix)
        return Pose(position=T, orientation=quaternions.mat2quat(R))

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        pos_str = ",".join(f"{x:.02f}" for x in self.position)
        rot_str = ",".join(f"{x:.02f}" for x in euler.quat2euler(self.orientation))
        return f"Pose(pos=({pos_str}),rot=({rot_str}))"

    def distance(self, other: Pose, orientation_factor: float = 0.05) -> float:
        position_distance = float(np.linalg.norm(self.position - other.position))

        orientation_distance = (
            float(
                quaternions.qnorm(
                    quaternions.qmult(
                        self.orientation,
                        quaternions.qinverse(other.orientation),
                    )
                )
            )
            if not np.allclose(
                euler.quat2euler(other.orientation),
                euler.quat2euler(self.orientation),
                rtol=0.1,
                atol=0.1,
            )
            else 0.0
        )
        dist = position_distance + orientation_factor * orientation_distance
        return dist
 
