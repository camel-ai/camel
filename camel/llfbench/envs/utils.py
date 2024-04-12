import numpy as np

from typing import Dict, Any, Tuple, Union, List, Callable

def format(prompts : List[str], method : Union[str, int] = 'random', **kwargs : Dict[str,str]):
    """ A helper method for selecting from a set of paraphrased prompts.

        Args:
            prompts: A list of prompt templates to select from. The first one is
            the default.

            method: The method to use in selecting the prompt. It can be either
            'random' or an integer.

            If it is 'random', a template would be randomly selected from `prompts`.

            If it is an integer, it is used as the index to select from the template in `prompts`.

            **kwargs: The keyword arguments to be used in formatting the template.

    """

    if method=='random':
        return np.random.choice(prompts).format(**kwargs)
    else:
        assert type(method)==int, "The method must be either 'random', 'llm', a callable, or an integer."
        idx = method
        return prompts[idx % len(prompts)].format(**kwargs)
