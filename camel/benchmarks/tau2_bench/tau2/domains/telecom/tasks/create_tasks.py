import json
import random
from argparse import ArgumentParser
from collections import defaultdict

from tau2.data_model.tasks import Task
from tau2.domains.telecom.tasks.mms_issues import mms_issue_task_manager
from tau2.domains.telecom.tasks.mobile_data_issues import mobile_data_task_manager
from tau2.domains.telecom.tasks.service_issues import service_issues_task_manager
from tau2.domains.telecom.tasks.utils import get_persona_from_task_id
from tau2.utils import DATA_DIR


def create_tasks(save_tasks: bool = True, max_count_per_bin: int = 3) -> list[Task]:
    tasks: list[Task] = []
    mobile_data_tasks = mobile_data_task_manager.create_tasks(save_tasks=False)
    print(f"Number of mobile data issue tasks: {len(mobile_data_tasks)}")
    tasks.extend(mobile_data_tasks)

    service_tasks = service_issues_task_manager.create_tasks(save_tasks=False)
    print(f"Number of service issue tasks: {len(service_tasks)}")
    tasks.extend(service_tasks)

    mms_tasks = mms_issue_task_manager.create_tasks(save_tasks=False)
    print(f"Number of mms issue tasks: {len(mms_tasks)}")
    tasks.extend(mms_tasks)

    print(f"Number of tasks: {len(tasks)}")

    file = DATA_DIR / "tau2" / "domains" / "telecom" / f"tasks_full.json"
    if save_tasks:
        with open(file, "w") as f:
            json.dump([t.model_dump() for t in tasks], f, indent=2)

    # Build tasks with attributes
    tasks_with_attrs = []
    for intent_tasks, intent in [
        (mobile_data_tasks, "mobile_data"),
        (service_tasks, "service"),
        (mms_tasks, "mms"),
    ]:
        for task in intent_tasks:
            num_subtasks = len(task.id.split("|"))
            tasks_with_attrs.append(
                {
                    "task": task,
                    "intent": intent,
                    "num_subtasks": num_subtasks,
                    "persona": get_persona_from_task_id(task.id),
                }
            )

    file_small = DATA_DIR / "tau2" / "domains" / "telecom" / f"tasks_small.json"
    small_tasks = [t["task"] for t in tasks_with_attrs if t["num_subtasks"] == 1]
    print(f"Number of tasks in small set: {len(small_tasks)}")
    if save_tasks:
        with open(file_small, "w") as f:
            json.dump([t.model_dump() for t in small_tasks], f, indent=2)

    file_sampled = DATA_DIR / "tau2" / "domains" / "telecom" / f"tasks.json"
    tasks_by_bins = defaultdict(list)
    for task in tasks_with_attrs:
        if task["num_subtasks"] < 2:  # We only keep tasks with at least 2 subtasks
            continue
        tasks_by_bins[(task["intent"], task["num_subtasks"], task["persona"])].append(
            task["task"]
        )

    # sample $n$ tasks per intent, difficulty level, and persona
    sampled_tasks = []
    for (intent, num_subtasks, persona), tasks in tasks_by_bins.items():
        num_sampled = min(max_count_per_bin, len(tasks))
        sampled_tasks.extend(random.sample(tasks, num_sampled))
        print(
            f"Sampled {num_sampled} tasks for {intent} with {num_subtasks} subtasks and persona {persona}..."
        )

    print(f"Number of sampled tasks: {len(sampled_tasks)}")
    if save_tasks:
        with open(file_sampled, "w") as f:
            json.dump([t.model_dump() for t in sampled_tasks], f, indent=2)

    return tasks


def main():
    parser = ArgumentParser()
    parser.add_argument("-s", "--seed", type=int, default=42)
    parser.add_argument("-m", "--max-count-per-bin", type=int, default=3)
    args = parser.parse_args()
    random.seed(args.seed)
    create_tasks(max_count_per_bin=args.max_count_per_bin)


if __name__ == "__main__":
    main()
