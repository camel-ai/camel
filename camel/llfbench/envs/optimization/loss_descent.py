import re
import sys
import gym
from jax import grad
import jax.numpy as jnp
import numpy as np
from textwrap import dedent, indent

from gym.utils import seeding
from llfbench.envs.llf_env import Feedback
import string

class LossLandscapeBase(gym.Env):
    def __init__(self, callable_func, x_low, x_high, min_y, optimal_sol,
                 feedback=0, seed=None, precision_digit=2, horizon=10):
        # callable_func: a function that takes in a list
        # we truncate the floating point precision to 2 decimal places

        super().__init__()
        self.x_low = x_low
        self.x_high = x_high

        self.feedback = feedback
        assert self.feedback in {0, 0.5, 1}

        self.action_space = gym.spaces.Text(sys.maxsize, charset=string.printable)
        self.observation_space = gym.spaces.Text(sys.maxsize, charset=string.printable)

        self._np_random = None

        # in addition to text, we also allow a few keywords that means
        # the agent wants to terminate the environment
        self.stop_keywords = ['reach', 'stay', 'stop']

        self.callable_func = callable_func
        self.grad_func = grad(callable_func)

        self.prev_x = None
        self.left_attempts = horizon
        self.min_y = min_y
        self.optimal_sol = optimal_sol
        self.precision_digit = precision_digit

        self.horizon = horizon

        self._seed = self.seed(seed)

        self.reward_range = (self.get_min_reward(), -self.min_y)

        # Note: currently we treat the first line as "instruction"
        self.docstring = dedent("""
        You are trying to minimize the output (y) of a function by choosing input (x). The goal is to choose x such that y is as small as possible.

        You get to observe y once you choose the value of x, where x is a 2-dimensional vector.
        This means x = [x1, x2], where x1 and x2 are real numbers.


        The range of x1 and x2 is [{}, {}].
        Please do not choose x outside of this range.

        Choose x within {} attempts.
        You can choose to stop at any time.

        Output format:
        x = [x1, x2]
        """)

        self.docstring = self.docstring.strip()
        self.docstring = self.docstring.format(self.x_low, self.x_high, self.horizon)

    def get_min_reward(self):
        x_range = [self.x_low, self.x_high]
        y_max = [self.callable_func(np.array([x_range[i], x_range[j]])) for i in range(2) for j in range(2)]
        y_max = max(y_max)
        return -y_max

    def get_optimal_solution(self):
        return self.optimal_sol

    def reset(self, **kwargs):
        if 'seed' in kwargs:
            self._seed = self.seed(kwargs['seed'])
        # we sample the initial state from the uniform distribution
        x = self.np_random.uniform(self.x_low, self.x_high, size=2)
        # we round the floating point precision to 2 decimal places
        x = np.round(x, self.precision_digit)
        self.prev_x = x

        y = self.callable_func(x)

        self.left_attempts = self.horizon

        obs = "x={}\nFunction outputs y = {}\nYou have {} attempts left!\n".format(x.tolist(), y, self.left_attempts)
        obs += "Please output the next x that will make this function output the smallest y.\n"
        obs += "Format: x = [x1, x2]\n"
        obs += "Output:"

        return obs

    def seed(self, seed=None):
        """Seed the PRNG of this space and possibly the PRNGs of subspaces."""
        self._np_random, seed = seeding.np_random(seed)
        return [seed]

    @property
    def np_random(self):
        """Lazily seed the PRNG since this is expensive and only needed if sampling from this space."""
        if self._np_random is None:
            self.seed()
        return self._np_random  # type: ignore  ## self.seed() call guarantees right type.

    def text_extract(self, text):
        # return np.array([x1, x2]), agent decides to stop
        for stop_word in self.stop_keywords:
            if stop_word in text:
                return None, True

        pattern = r'\[(-?\d+\.?\d*(?:e[-+]?\d+)?),\s*(-?\d+\.?\d*(?:e[-+]?\d+)?)\]'
        match = re.search(pattern, text)
        if match is None:
            return None, False
        else:
            numbers = [float(g) for g in match.groups()]
            return np.array(numbers), False

    def step(self, action):
        # observation, reward, terminal, info
        didactic_feedback = Feedback(r="", hp="", hn="", fp="", fn="")

        x, stop = self.text_extract(action)
        if x is None and stop is False:
            didactic_feedback.r = f'You entered an invalid action: {action}'
            didactic_feedback.fp = didactic_feedback.r + f" Please enter a valid action within ({self.x_low, self.x_high})"
            didactic_feedback.fn = didactic_feedback.r + f" Do not enter a valid action outside of ({self.x_low, self.x_high})"
            return None, -1000, True, {'success': False, 'feedback': didactic_feedback}

        if stop:
            success = np.abs(self.callable_func(self.prev_x) - self.min_y) < 1e-2
            didactic_feedback['r'] = f'You have chosen to stop at {self.prev_x}.'
            if success:
                didactic_feedback['r'] += ' You have reached the minimum!'
            else:
                didactic_feedback['r'] += ' You have not reached the minimum!'
            return None, float(self.callable_func(self.prev_x)), True, {'success': success,
                                                                'feedback': didactic_feedback}

        loss = self.callable_func(x)

        if np.abs(loss - self.min_y) < 1e-2:
            # r_pos
            didactic_feedback['r'] = 'You have reached the minimum!'
            return "Function outputs y: {}\nYou have reached the minimum!".format(self.min_y), -self.min_y, True, {
                'original_feedback': 'You have reached the minimum!', 'feedback': didactic_feedback,
                "success": True}

        # r_neg
        obs = "Function outputs y = {}\nYou have {} attempts left!\n".format(loss, self.left_attempts)
        obs += "Please output the next x that will make this function output the smallest y.\n"
        obs += "Format: x = [x1, x2]\n"
        obs += "Output:"

        # TODO: what's the diff between r and observation?
        didactic_feedback['r'] = "You have not reached the minimum!"
        feedback = ""  # y is not minimized yet. Keep going!

        # not changing original feedback
        # not changing observation, which is r_pos, r_neg
        if self.feedback != 0:
            dx = self.grad_func(x)
            dx1, dx2 = dx[0], dx[1]

        if self.feedback == 0.5:
            feedback += '\n\n'
            if np.abs(dx1) > np.abs(dx2):
                feedback += f"You chose {action}. However, try a different number for first number {x[0]} will minimize y more."
            else:
                feedback += f"You chose {action}. However, try a different number for second number {x[1]} will minimize y more."
        elif self.feedback == 1:
            feedback += '\n\n'
            x1_direction = 'smaller' if dx1 > 0 else 'larger'  # take the opposite of gradient
            x2_direction = 'smaller' if dx2 > 0 else 'larger'
            feedback += f"You chose {action}. Output a {x1_direction} number than the first number {x[0]} to minimize y.\n"
            feedback += f"You chose {action}. Output a {x2_direction} number than the second number {x[1]} to minimize y."

        # this should be full each time
        # hp', 'hn', 'fp', 'fn'

        """
        - (hp) hindsight positive: explaination on why the current action is correct
        - (hn) hindsight negative: explaination on why the current action is incorrect
        - (fp) future positive: suggestion of things (future action) to do
        - (fn) future negative: suggestion of things (future action) to avoid
        """
        change_x = x - self.prev_x  # change in x
        change_x1, change_x2 = change_x[0], change_x[1]
        prev_dx = self.grad_func(self.prev_x)
        prev_dx1, prev_dx2 = prev_dx[0], prev_dx[1]
        prev_x1_direction = 'Increasing' if change_x1 > 0 else 'Decreasing'  # take the opposite of gradient
        prev_x2_direction = 'Increasing' if change_x2 > 0 else 'Decreasing'

        if np.sign(change_x1) == np.sign(-prev_dx1):
            didactic_feedback['hp'] += f"You chose {action} from {self.prev_x}. {prev_x1_direction} the first number {self.prev_x[0]} does minimize y.\n"
        else:
            didactic_feedback['hn'] += f"You chose {action} from {self.prev_x}. {prev_x1_direction} the first number {self.prev_x[0]} does not minimize y.\n"

        if np.sign(change_x2) == np.sign(-prev_dx2):
            didactic_feedback['hp'] += f"You chose {action} from {self.prev_x}. {prev_x2_direction} the second number {self.prev_x[1]} does minimize y."
        else:
            didactic_feedback['hn'] += f"You chose {action} from {self.prev_x}. {prev_x2_direction} the second number {self.prev_x[1]} does not minimize y."

        dx = self.grad_func(x)
        dx1, dx2 = dx[0], dx[1]
        x1_direction = 'smaller' if dx1 > 0 else 'larger'  # take the opposite of gradient
        x2_direction = 'smaller' if dx2 > 0 else 'larger'
        if dx1 != 0:
            didactic_feedback['fp'] += f"You chose {action}. Choose a {x1_direction} number than {x[0]} to minimize y.\n"
        if dx2 != 0:
            didactic_feedback['fp'] += f"You chose {action}. Choose a {x2_direction} number than {x[1]} to minimize y.\n"

        flipped_x1_direction = 'smaller' if dx1 < 0 else 'larger'  # take the opposite of gradient
        flipped_x2_direction = 'smaller' if dx2 < 0 else 'larger'

        if dx1 != 0:
            didactic_feedback['fn'] += f"You chose {action}. Do not choose a {flipped_x1_direction} number than {x[0]} to minimize y."
        if dx2 != 0:
            didactic_feedback['fn'] += f"You chose {action}. Do not choose a {flipped_x2_direction} number than {x[1]} to minimize y."

        self.prev_x = x
        self.left_attempts -= 1
        return obs, float(-loss), False, {'feedback': didactic_feedback, 'original_feedback': feedback, "success": False}


# now we wrap all loss functions by inheriting this class
"""
Bowl-Shaped functions:
- [Bohachevsky Functions](https://www.sfu.ca/~ssurjano/boha.html)
- [Rotated Hyper-Ellipsoid Function](https://www.sfu.ca/~ssurjano/rothyp.html)

Plate-Shaped functions:
- [Booth Function](https://www.sfu.ca/~ssurjano/booth.html)
- [Matyas Function](https://www.sfu.ca/~ssurjano/matya.html)
- [McCormick Function](https://www.sfu.ca/~ssurjano/mccorm.html)

Valley shaped functions:
- [Rosenbrock Function](https://www.sfu.ca/~ssurjano/rosen.html)
- [Six-Hump Camel Function](https://www.sfu.ca/~ssurjano/camel6.html)
- [Three-Hump Camel Function](https://www.sfu.ca/~ssurjano/camel3.html)

Suggestion:
Do not use the following functions:
Bohachevsky, RotatedHyperEllipsoid, Matyas, ThreeHumpCamel

Because LLM is quick to guess [0, 0], and that's often the "correct" answer.
"""


class Bohachevsky(LossLandscapeBase):
    def __init__(self, func_choice=1, feedback=0, seed=None, horizon=10):
        assert func_choice in [1, 2, 3], "func_choice must be 1, 2, or 3"
        if func_choice == 1:
            func = lambda x: x[0] ** 2 + 2 * x[1] ** 2 - 0.3 * jnp.cos(3 * jnp.pi * x[0]) - 0.4 * jnp.cos(
                4 * jnp.pi * x[1]) + 0.7
        elif func_choice == 2:
            func = lambda x: x[0] ** 2 + 2 * x[1] ** 2 - 0.3 * jnp.cos(3 * jnp.pi * x[0]) * jnp.cos(
                4 * jnp.pi * x[1]) + 0.3
        else:
            func = lambda x: x[0] ** 2 + 2 * x[1] ** 2 - 0.3 * jnp.cos(3 * jnp.pi * x[0] + 4 * jnp.pi * x[1]) + 0.3

        super().__init__(callable_func=func,
                         x_low=-100, x_high=100, min_y=0, optimal_sol=np.zeros(2),
                         feedback=feedback, seed=seed, horizon=horizon, precision_digit=4)


class RotatedHyperEllipsoid(LossLandscapeBase):
    def __init__(self, feedback=0, seed=None, horizon=10):
        func = lambda x: x[0] ** 2 + (x[0] ** 2 + x[1] ** 2)
        super().__init__(callable_func=func,
                         x_low=-65.536, x_high=65.536, min_y=0, optimal_sol=np.zeros(2),
                         feedback=feedback, seed=seed, horizon=horizon)


class Booth(LossLandscapeBase):
    def __init__(self, feedback=0, seed=None, horizon=10):
        func = lambda x: (x[0] + 2 * x[1] - 7) ** 2 + (2 * x[0] + x[1] - 5) ** 2
        super().__init__(callable_func=func,
                         x_low=-10, x_high=10, min_y=0, optimal_sol=np.array([1, 3]),
                         feedback=feedback, seed=seed, horizon=horizon)


class Matyas(LossLandscapeBase):
    def __init__(self, feedback=0, seed=None, horizon=10):
        func = lambda x: 0.26 * (x[0] ** 2 + x[1] ** 2) - 0.48 * x[0] * x[1]
        super().__init__(callable_func=func,
                         x_low=-10, x_high=10, min_y=0, optimal_sol=np.zeros(2),
                         feedback=feedback, seed=seed, horizon=horizon, precision_digit=4)


class McCormick(LossLandscapeBase):
    def __init__(self, feedback=0, seed=None, horizon=10):
        func = lambda x: jnp.sin(x[0] + x[1]) + (x[0] - x[1]) ** 2 - 1.5 * x[0] + 2.5 * x[1] + 1
        super().__init__(callable_func=func,
                         x_low=-1.5, x_high=4, min_y=-1.9133, optimal_sol=np.array([-0.54719, -1.54719]),
                         feedback=feedback, seed=seed, horizon=horizon, precision_digit=4)


class Rosenbrock(LossLandscapeBase):
    def __init__(self, a=1, b=1, feedback=0, seed=None, horizon=10):  # b = 100
        # https://en.wikipedia.org/wiki/Rosenbrock_function
        # all of them are lambda functions that expect Numpy array of shape (2,)
        two_dim_rosenbrock = lambda x: (a - x[0]) ** 2 + b * (x[1] - x[0] ** 2) ** 2
        super().__init__(callable_func=two_dim_rosenbrock,
                         x_low=-5, x_high=10, min_y=0, optimal_sol=np.ones(2),
                         feedback=feedback, seed=seed, horizon=horizon)


class SixHumpCamel(LossLandscapeBase):
    def __init__(self, feedback=0, seed=None, horizon=10):
        func = lambda x: (4 - 2.1 * x[0] ** 2 + (x[0] ** 4) / 3) * x[0] ** 2 + x[0] * x[1] + (-4 + 4 * x[1] ** 2) * x[
            1] ** 2
        # note that SixHumpCamel has two global minima
        # also the range on x is x1 = [-3, 3], x2 = [-2, 2]
        # but we use x1 = [-2, 2], x2 = [-3, 3] for simplicity
        super().__init__(callable_func=func,
                         x_low=-2, x_high=2, min_y=-1.0316,
                         optimal_sol=[np.array([0.0898, -0.7126]), np.array([-0.0898, 0.7126])],
                         feedback=feedback, seed=seed, horizon=horizon, precision_digit=4)


class ThreeHumpCamel(LossLandscapeBase):
    def __init__(self, feedback=0, seed=None, horizon=10):
        func = lambda x: 2 * x[0] ** 2 - 1.05 * x[0] ** 4 + (x[0] ** 6) / 6 + x[0] * x[1] + x[1] ** 2
        super().__init__(callable_func=func,
                         x_low=-5, x_high=5, min_y=0, optimal_sol=np.array([0, 0]),
                         feedback=feedback, seed=seed, horizon=horizon, precision_digit=4)
