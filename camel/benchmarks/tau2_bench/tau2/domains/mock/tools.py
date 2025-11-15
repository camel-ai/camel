from tau2.domains.mock.data_model import MockDB, Task, TaskStatus, User
from tau2.environment.toolkit import ToolKitBase, ToolType, is_tool


class MockTools(ToolKitBase):
    """Simple tools for the mock domain."""

    db: MockDB

    def __init__(self, db: MockDB) -> None:
        super().__init__(db)

    @is_tool(ToolType.WRITE)
    def create_task(self, user_id: str, title: str, description: str = None) -> Task:
        """
        Create a new task for a user.

        Args:
            user_id: The ID of the user creating the task
            title: The title of the task
            description: Optional description of the task

        Returns:
            The created task

        Raises:
            ValueError: If the user is not found
        """
        if user_id not in self.db.users:
            raise ValueError(f"User {user_id} not found")

        task_id = f"task_{len(self.db.tasks) + 1}"
        task = Task(
            task_id=task_id, title=title, description=description, status="pending"
        )

        self.db.tasks[task_id] = task
        self.db.users[user_id].tasks.append(task_id)

        return task

    @is_tool(ToolType.READ)
    def get_users(self) -> list[User]:
        """
        Get all users in the database.
        """
        return list(self.db.users.values())

    @is_tool(ToolType.WRITE)
    def update_task_status(self, task_id: str, status: TaskStatus) -> Task:
        """
        Update the status of a task.

        Args:
            task_id: The ID of the task to update
            status: The new status of the task

        Returns:
            The updated task

        Raises:
            ValueError: If the task is not found
        """
        if task_id not in self.db.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.db.tasks[task_id]
        task.status = status
        return task

    def assert_number_of_tasks(self, user_id: str, expected_number: int) -> bool:
        """
        Check if the number of tasks for a user is as expected.

        Args:
            user_id: The ID of the user
            expected_number: The expected number of tasks

        Returns:
            True if the number of tasks is as expected, False otherwise
        """
        if user_id not in self.db.users:
            raise ValueError(f"User {user_id} not found")
        return len(self.db.users[user_id].tasks) == expected_number

    def assert_task_status(self, task_id: str, expected_status: TaskStatus) -> bool:
        """
        Check if the status of a task is as expected.
        """
        if task_id not in self.db.tasks:
            raise ValueError(f"Task {task_id} not found")
        return self.db.tasks[task_id].status == expected_status

    @is_tool(ToolType.GENERIC)
    def transfer_to_human_agents(self, summary: str) -> str:
        """
        Transfer the user to a human agent, with a summary of the user's issue.
        Only transfer if
         -  the user explicitly asks for a human agent
         -  given the policy and the available tools, you cannot solve the user's issue.

        Args:
            summary: A summary of the user's issue.

        Returns:
            A message indicating the user has been transferred to a human agent.
        """
        return "Transfer successful"

    # @is_tool(ToolType.THINK)
    # def think(self, thought: str) -> str:
    #     """
    #     Use the tool to think about something.
    #     It will not obtain new information or change the database, but just append the thought to the log.
    #     Use it when complex reasoning or some cache memory is needed.

    #     Args:
    #         thought: A thought to think about.

    #     Returns:
    #         Empty string
    #     """
    #     return ""
