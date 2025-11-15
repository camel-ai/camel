# Tau2 Domains

This folder contains the domains for the Tau2 project.

## Domain Structure

Each domain has its own folder with the following structure:

- `data_model.py`: Defines the data models for the domain. 
    - This implements the `DB` class, which is a base class for all domain databases.
- `user_data_model.py`: Defines the data models for the user data for the domain. (Optional)
    - This implements the `DB` class, which is a base class for all domain user databases.
- `tools.py`: Defines the tools for the domain. 
    - Implements `ToolKitBase` class, which is a base class for all domain toolkits. 
- `user_tools.py`: Defines the user tools for the domain. (Optional)
    - Implements `ToolKitBase` class, which is a base class for all domain toolkits. 
- `environment.py`: Defines the environment for the domain. 
    - Implements `get_environment()` functions that returns an `Environment` instance for the domain.
    - Implements `get_tasks()` functions that returns a list of tasks for the domain.
- `utils.py`: Defines the utility functions for the domain.

## Data Storage

All the data for the domain is stored in `data/tau2/domains/<domain_name>` folder.
Should contain:
- `tasks.json`: A JSON file containing the tasks for the domain.
- `split_tasks.json`: A JSON file containing the task splits for the domain.
    - The task splits are defined as a list of task IDs.
    - The task IDs are defined in the `tasks.json` file.
    - It must at minimum implement a task split called `base`. This will be the default task split.
- `policy.md`: A markdown file containing the policy for the domain.
- `db.json` or `db.toml`: A JSON or TOML file containing the database for the domain.
- `user_db.json` or `user_db.toml`: A JSON or TOML file containing the user database for the domain. (Optional)


## Tests
All the tests for the domain are stored in the `tests/domain_tests/<domain_name>` folder.
- `test_tools_<domain_name>.py`: Contains tests for the tools for the domain.
- `test_user_tools_<domain_name>.py`: Contains tests for the user tools for the domain (if any)


To run tests:
```sh
pytest tests/domain_tests/<domain_name>
```

## Registering your domain
To make it easy for people to use your domain, you need to register your `get_environment` function in Tau2 `registry.py` file.

In `registry.py`:
```python
from tau2.your_domain.environment import get_environment as your_domain_get_environment
...
registry.register_domain(your_domain_get_environment, "your_domain_name")
registry.register_tasks(your_domain_get_tasks, "your_domain_name")
```

