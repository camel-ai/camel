import logging
import numpy as np
from tqdm import tqdm
from copy import deepcopy
from itertools import islice
from time import time
from typing import Callable, List, Optional, Tuple, Union, Dict, Set, Any, FrozenSet

DistanceFunc = Callable[[np.ndarray, np.ndarray], float]
SampleFunc = Callable[[], np.ndarray]
ExtendFunc = Callable[[np.ndarray, np.ndarray], List[np.ndarray]]
CollisionFunc = Callable[[np.ndarray], bool]


def irange(start, stop=None, step=1):  # np.arange
    if stop is None:
        stop = start
        start = 0
    while start < stop:
        yield start
        start += step

def argmin(function, sequence):
    values = list(sequence)
    scores = [function(x) for x in values]
    return values[scores.index(min(scores))]

def pairs(lst):
    return zip(lst[:-1], lst[1:])

def merge_dicts(*args):
    result = {}
    for d in args:
        result.update(d)
    return result
    # return dict(reduce(operator.add, [d.items() for d in args]))
 
def flatten(iterable_of_iterables):
    return (item for iterables in iterable_of_iterables for item in iterables)
 
def randomize(sequence, np_random: np.random.RandomState):
    np_random.shuffle(sequence)
    return sequence
 
def take(iterable, n: Optional[int] = None):
    if n is None:
        n = 0  # NOTE - for some of the uses
    return islice(iterable, n)
 
def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    enums["names"] = sorted(enums.keys(), key=lambda k: enums[k])
    return type("Enum", (), enums)
 
def smooth_path(
    path: List[np.ndarray],
    extend_fn: ExtendFunc,
    collision_fn: CollisionFunc,
    np_random: np.random.RandomState,
    iterations: int = 50,
):
    smoothed_path = path
    for _ in range(iterations):
        if len(smoothed_path) <= 2:
            return smoothed_path
        i = np_random.randint(0, len(smoothed_path) - 1)
        j = np_random.randint(0, len(smoothed_path) - 1)
        if abs(i - j) <= 1:
            continue
        if j < i:
            i, j = j, i
        shortcut = list(extend_fn(smoothed_path[i], smoothed_path[j]))
        if (len(shortcut) < (j - i)) and all(not collision_fn(q) for q in shortcut):
            smoothed_path = smoothed_path[: i + 1] + shortcut + smoothed_path[j + 1 :]
    return smoothed_path


class TreeNode(object):
    def __init__(self, config, parent=None):
        # configuration
        self.config = config
        # parent configuration
        self.parent = parent

    def retrace(self):
        """
        Get a list of nodes from start to itself
        :return: a list of nodes
        """
        sequence = []
        node = self
        while node is not None:
            sequence.append(node)
            node = node.parent
        return sequence[::-1]

    def __str__(self):
        return "TreeNode(" + str(self.config) + ")"

    __repr__ = __str__


def configs(nodes) -> Optional[List[np.ndarray]]:
    """
    Get the configurations of nodes
    :param nodes: array type of nodes
    :return: a list of configurations
    """
    return [n.config for n in nodes] if nodes is not None else None


def closest_node_to_goal(distance_fn, target, nodes: List[TreeNode]) -> TreeNode:
    return nodes[np.argmin([distance_fn(node.config, target) for node in nodes])]


def rrt(
    start_conf: np.ndarray,
    goal_conf: np.ndarray,  # TODO extend functionality to multiple goal confs
    distance_fn: DistanceFunc,
    sample_fn: SampleFunc,
    extend_fn: ExtendFunc,
    collision_fn: CollisionFunc,
    np_random: np.random.RandomState,
    iterations: int = 2000,
    goal_probability: float = 0.2,
    greedy: bool = True,
) -> Optional[List[np.ndarray]]:
    """
    RRT algorithm
    :param start_conf: start_conf configuration.
    :param goal_conf: goal configuration.
    :param distance_fn: distance_fn function distance_fn(q1, q2). Takes two
                    confugurations, returns a number of distance_fn.
    :param sample_fn: sampling function sample_fn(). Takes nothing, returns a sample
                of configuration.
    :param extend_fn: extend_fn function extend_fn(q1, q2). Extends the tree from q1
                towards q2.
    :param collision_fn: collision checking function. Check whether
                    collision exists for configuration q. 
    :param iterations: number of iterations to extend tree towards an sample
    :param goal_probability: bias probability to set the sample to goal
    :param visualize: whether draw nodes and lines for the tree
    :return: a list of configurations
    """
    if collision_fn(start_conf):
        logging.error("rrt fails, start_conf configuration has collision")
        return None

    nodes = [TreeNode(start_conf)]
    for i in irange(iterations):
        goal = np_random.random() < goal_probability or i == 0
        current_target = goal_conf if goal else sample_fn()
        last = closest_node_to_goal(
            distance_fn=distance_fn, target=current_target, nodes=nodes
        )
        for q in extend_fn(last.config, current_target):
            if collision_fn(q):
                break
            last = TreeNode(q, parent=last)
            nodes.append(last)
            if (last.config == goal_conf).all():
                logging.debug("Success")
                return configs(last.retrace())
            if not greedy:
                break
        else:
            if goal:
                logging.error("Impossible")
                return configs(last.retrace())
    return None


def rrt_connect(
    q1: np.ndarray,
    q2: np.ndarray,
    distance_fn: DistanceFunc,
    sample_fn: SampleFunc,
    extend_fn: ExtendFunc,
    collision_fn: CollisionFunc,
    iterations: int,
    greedy: bool,
    timeout: float,
    debug: bool = False,
    skip_start_collision_check: bool = True,
):    
    if not skip_start_collision_check:
        if collision_fn(q1):
            return None, f"ReasonCollisionAtStart_time0_iter0"
    if collision_fn(q2):
        return None, f"ReasonCollisionAtGoal_time0_iter0"

    root1, root2 = TreeNode(q1), TreeNode(q2)
    nodes1, nodes2 = [root1], [root2]
    loop = irange(iterations)
    if debug:
        tqdm(loop, total=iterations)
    
    start_time = time()
    for loop_idx in loop:
        duration = float(time() - start_time)
        if duration > timeout:
            logging.debug("Timeout")
            info = f"ReasonTimeout_time{duration}_iter{loop_idx+1}"
            return None, info

        if len(nodes1) > len(nodes2):
            nodes1, nodes2 = nodes2, nodes1

        current_target = sample_fn()
        
        last1 = closest_node_to_goal(
            distance_fn=distance_fn, target=current_target, nodes=nodes1
        )
        for q in extend_fn(last1.config, current_target):
            if collision_fn(q): 
                break
            last1 = TreeNode(q, parent=last1)
            nodes1.append(last1)
            if not greedy:
                break

        last2 = closest_node_to_goal(
            distance_fn=distance_fn, target=last1.config, nodes=nodes2
        )

        for q in extend_fn(last2.config, last1.config):
            if collision_fn(q):
                break
            last2 = TreeNode(q, parent=last2)
            nodes2.append(last2)
            if not greedy:
                break
        if (last2.config == last1.config).all():
            path1, path2 = last1.retrace(), last2.retrace()
            if path1[0] != root1:
                path1, path2 = path2, path1
            duration = float(time() - start_time)
            return configs(path1[:-1] + path2[::-1]), f"ReasonSuccess_time{duration}_iter{loop_idx+1}"

    duration = float(time() - start_time)
    info = f"ReasonMaxIteration_time{duration}_iter{iterations}"
    return None, info


def direct_path(
    q1: np.ndarray, q2: np.ndarray, extend_fn: ExtendFunc, collision_fn: CollisionFunc
):
    if collision_fn(q1) or collision_fn(q2):
        return None
    path = [q1]
    for q in extend_fn(q1, q2):
        if collision_fn(q):
            return None
        path.append(q)
    return path


def birrt(
    start_conf: np.ndarray,
    goal_conf: np.ndarray,
    distance_fn: DistanceFunc,
    sample_fn: SampleFunc,
    extend_fn: ExtendFunc,
    collision_fn: CollisionFunc,
    np_random: np.random.RandomState,
    iterations: int, 
    greedy: bool,
    timeout: float, 
    smooth_iterations: int,
    smooth_extend_fn: Optional[ExtendFunc] = None,
    skip_direct_path: bool = False,
    skip_smooth_path: bool = False,
) -> Tuple:

    if not skip_direct_path:
        start_time = time()
        path = direct_path(start_conf, goal_conf, extend_fn, collision_fn)
        if path is not None:
            return path, f"ReasonDirect_time{time() - start_time}_iter1"

    path, info = rrt_connect(
        q1=start_conf,
        q2=goal_conf,
        distance_fn=distance_fn,
        sample_fn=sample_fn,
        extend_fn=extend_fn,
        collision_fn=collision_fn,
        iterations=iterations,
        greedy=greedy,
        timeout=timeout,
    )
    if path is not None and not skip_smooth_path:
        path = smooth_path(
            path=path,
            extend_fn=smooth_extend_fn if smooth_extend_fn is not None else extend_fn,
            collision_fn=collision_fn,
            np_random=np_random,
            iterations=smooth_iterations,
        )
        info += '_smoothed'
    return path, info 
 

class RRTSampler:
    def __init__(
        self,
        start_conf: np.ndarray,
        goal_conf: np.ndarray,
        min_values: np.ndarray,
        max_values: np.ndarray,
        numpy_random: np.random.RandomState,
        init_samples: Optional[List[np.ndarray]] = None,
    ):
        self.start_conf = start_conf
        self.goal_conf = goal_conf
        self.min_values = min_values
        self.max_values = max_values
        self.value_range = self.max_values - self.min_values
        self.numpy_random = numpy_random
        self.init_samples = init_samples
        self.curr_sample_idx = 0

    def __call__(self):
        if self.init_samples is not None and self.curr_sample_idx < len(
            self.init_samples
        ):
            self.curr_sample_idx += 1 
            return self.init_samples[self.curr_sample_idx - 1]
        return self.numpy_random.uniform(low=self.min_values, high=self.max_values)


class NearJointsNormalSampler(RRTSampler):
    def __init__(self, bias: float, **kwargs):
        self.bias = bias
        super().__init__(**kwargs)

    def __call__(self):
        if self.numpy_random.random() > 0.5:
            return super().__call__()
        center = self.goal_conf if self.numpy_random.random() > 0.5 else self.start_conf
        sample = (
            center
            + self.numpy_random.randn(len(center))
            * (self.max_values - self.min_values)
            * self.bias
        )
        return np.clip(sample, a_min=self.min_values, a_max=self.max_values)


class NearJointsUniformSampler(RRTSampler):
    def __init__(self, bias: float, **kwargs):
        self.bias = bias
        super().__init__(**kwargs)

    def __call__(self):
        # NOTE: always goes through init samples to work
        if self.init_samples is not None and self.curr_sample_idx < len(
            self.init_samples
        ):
            self.curr_sample_idx += 1 
            print(f'init-sampling! {self.curr_sample_idx}')
            return self.init_samples[self.curr_sample_idx - 1]
        # if self.curr_sample_idx < len(self.init_samples):
        #     self.curr_sample_idx += 1
        #     print(f'init-sampling! {self.curr_sample_idx}')
        #     return self.init_samples[self.curr_sample_idx - 1]
        if self.numpy_random.random() > 0.8:
            return super().__call__()
        center = self.goal_conf if self.numpy_random.random() > 0.5 else self.start_conf
        sample = center + self.numpy_random.uniform(
            low=np.clip(
                center - self.bias * self.value_range,
                a_min=self.min_values,
                a_max=self.max_values,
            ),
            high=np.clip(
                center + self.bias * self.value_range,
                a_min=self.min_values,
                a_max=self.max_values,
            ),
        )
        return sample

class CenterWaypointsUniformSampler(RRTSampler):
    def __init__(self, bias: float, **kwargs):
        self.bias = bias
        super().__init__(**kwargs)

    def __call__(self):
        # NOTE: always goes through init samples to work
        if self.init_samples is not None and self.curr_sample_idx < len(
            self.init_samples
        ):
            self.curr_sample_idx += 1 
            print(f'init-sampling! {self.curr_sample_idx}')
            return self.init_samples[self.curr_sample_idx - 1]
        
        # if self.numpy_random.random() > 0.8 and len(self.init_samples) > 0:
        #     idx = np.random.choice(len(self.init_samples))
        #     center = self.init_samples[idx]
        # else:
        #     center = self.goal_conf if self.numpy_random.random() > 0.5 else self.start_conf

        center = self.goal_conf if self.numpy_random.random() > 0.5 else self.start_conf
        
        sample = center + self.numpy_random.uniform(
            low=np.clip(
                center - self.bias * self.value_range,
                a_min=self.min_values,
                a_max=self.max_values,
            ),
            high=np.clip(
                center + self.bias * self.value_range,
                a_min=self.min_values,
                a_max=self.max_values,
            ),
        )
        return sample
  