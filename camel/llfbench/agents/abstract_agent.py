class Agent:
    """ An agent that interacts with an environment with language feedback. """

    NAME = "AbstractAgent"

    def __init__(self, *args, **kwargs):
        # TODO: pass env_spec
        self.docstring = None

    def reset(self, docstring):
        self.docstring = docstring

    def act(self, *args, **kwargs):
        raise NotImplementedError
