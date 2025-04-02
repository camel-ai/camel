import asyncio
from typing import List, Type, Tuple

from .models import Action, Observation, StepResult
from .multi_step import MultiStepEnv

class BatchedMultiStepEnv:
    def __init__(self, env_cls: Type[MultiStepEnv], n: int, *args, **kwargs):
        self.num_envs = n
        self.envs = [env_cls(*args, **kwargs) for _ in range(n)]
        self._done_flags = [False] * n

    async def setup(self):
        await asyncio.gather(*(env.setup() for env in self.envs))

    async def reset(self) -> List[Observation]:
        self._done_flags = [False] * self.num_envs
        return await asyncio.gather(*(env.reset() for env in self.envs))

    async def step(self, actions: List[Action]) -> List[Tuple[int, StepResult]]:
        results = []
        tasks = []

        for action in actions:
            idx = action.idx
            if idx < 0 or idx >= self.num_envs:
                raise IndexError(f"Invalid env index: {idx}")
            if self._done_flags[idx]:
                continue  # Skip finished envs
            tasks.append((idx, self.envs[idx].step(action)))

        step_results = await asyncio.gather(*(t[1] for t in tasks))
        for (idx, _), result in zip(tasks, step_results):
            if result.done:
                self._done_flags[idx] = True
            results.append((idx, result))

        return results

    async def close(self):
        await asyncio.gather(*(env.close() for env in self.envs))

    def get_done_flags(self) -> List[bool]:
        return self._done_flags.copy()
