import random
import numpy as np

# print with colors (modified from Huihan's lflf)
def print_color(message, color=None, logger=None):
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m'
    }
    print(f"{colors.get(color, '')}{message}\033[0m")  # Default to no color if invalid color is provided

    if logger is not None:
        logger.log(message)


def extract_int(txt):
    return [int(s) for s in txt.split() if s.isdigit()]

def extract_action(response, n_actions, separator="#"):
    if n_actions is None:  # free form action
        action = response.split(separator)[1]
        return action
    try:
        action = response.split(separator)[1]
        if not action.isnumeric():
            action = extract_int(action)[0]
        action = int(action)
        if action>=0 and action<n_actions:
            return action
        else:
            print("Action {} is out of range [0, {}].\n".format(action, n_actions-1))
    except IndexError:
        pass
    print("Cannot find the action in the response, so take a random action.\n\tResponse: {}.\n".format(response))
    return random.randint(0,n_actions-1)

class ReplayBuffer:
    """ A basic replay buffer based on list. """

    def __init__(self, buffer_size):
        self.buffer_size = buffer_size
        self.buffer = []

    def reset(self):
        self.buffer = []

    def append(self, **kwargs):
        self.buffer.append(dict(**kwargs))
        if len(self.buffer) > self.buffer_size:
            self.buffer.pop(0)

    def update(self, **kwargs):
        # update the last item
        if len(self.buffer)>0:
            self.buffer[-1].update(**kwargs)

    def __len__(self):
        return len(self.buffer)

    def __getitem__(self, item):
        return self.buffer[item]

    def __iter__(self):
        return self.buffer.__iter__()

def set_seed(seed, env=None):
    # torch.manual_seed(seed)
    # if torch.cuda.is_available():
    #     torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)
    #if env is not None:
    #    env.reset(seed)

def rollout(agent, env, *, horizon, return_full_information=False, log_data=False, seed=None):
    """ A basic agent evaluation loop. """

    if return_full_information:
        assert hasattr(env,'get_full_information')

    observation = env.reset(seed=seed)

    default_docstring = 'This is an interactive decision making problem with language feedback.'

    docstring = getattr(env, 'docstring', observation if isinstance(observation, str) else default_docstring)

    agent.reset(docstring)

    info = {}
    sum_of_rewards = 0.0
    data = dict(observations=[observation], actions=[], rewards=[], dones=[], infos=[])

    for i in range(horizon):

        feedback = info.get('feedback', None)

        if return_full_information:  # Oracle: the agent gets privileged information
            full_information = info.get('full_information', env.get_full_information())
            action = agent.act(observation, feedback, full_information=full_information)
        else:                       # Regular agent
            action = agent.act(observation, feedback)

        new_observation, reward, terminated, truncated, info = env.step(action)

        observation = new_observation

        if log_data:
            for k in data.keys():
                data[k].append(locals()[k[:-1]])  # removing s at the end
        sum_of_rewards += reward

        if terminated or truncated or info['success']:
            print("EPISODE DONE! Terminated: {}, truncated: {}, success: {}".format(terminated, truncated, info['success']))
            break

    return sum_of_rewards, data


def evaluate_agent(agent, env, *, horizon, n_episodes, return_full_information=False, log_data=False,
                   n_workers=1, seed=None):
    """ Evaluate an agent with n_episodes rollouts. """

    _rollout = lambda: rollout(agent, env,
                               horizon=horizon,
                               log_data=log_data,
                               return_full_information=return_full_information,
                               seed=seed)

    if n_workers > 1:
        import ray
        ray_rollout = ray.remote(_rollout)
        results = [ray_rollout.remote() for _ in range(n_episodes)]
        results = ray.get(results)
    else:
        results = [_rollout() for _ in range(n_episodes)]

    # Extract the scores and data
    scores = [score for score, _ in results]
    scores = np.array(scores)
    data = [data for _, data in results]
    return (scores, data) if log_data else scores
