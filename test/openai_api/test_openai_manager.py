import pytest
from camel.openai_api.openai_manager import OpenAIManager
from openai.types.beta import Assistant, AssistantDeleted, assistant_create_params
from openai.types.beta.assistants import AssistantFile, FileDeleteResponse
from openai.pagination import SyncCursorPage
from camel.types.enums import ModelType

class TestOpenAIManager:
    @pytest.fixture
    def openai_manager(self):
        return OpenAIManager()

    def test_create_assistant(self, openai_manager):
        name = "Test Assistant"
        model = "gpt-3.5-turbo"
        file_ids = ["file1", "file2"]
        instructions = "Test instructions"
        tools = [assistant_create_params.Tool(type="code_interpreter", name="Python")]
        description = "Test assistant description"

        assistant = openai_manager.create_assistant(name, model, file_ids, instructions, tools, description)

        assert isinstance(assistant, Assistant)

    def test_update_assistant(self, openai_manager):
        name = "Test Assistant"
        assistant_id = "assistant1"
        description = "Updated description"
        instructions = "Updated instructions"
        file_ids = ["file1", "file2"]
        tools = [assistant_create_params.Tool(type="retrieval", name="Search")]

        assistant = openai_manager.update_assistant(name, assistant_id, description, instructions, file_ids, tools)

        assert isinstance(assistant, Assistant)

    def test_list_assistants(self, openai_manager):
        assistants = openai_manager.list_assistants()

        assert isinstance(assistants, SyncCursorPage)

    def test_retrieve_assistant(self, openai_manager):
        assistant_id = "assistant1"

        assistant = openai_manager.retrieve_assitant(assistant_id)

        assert isinstance(assistant, Assistant)

    def test_delete_assistant(self, openai_manager):
        assistant_id = "assistant1"

        response = openai_manager.delete_assistant(assistant_id)

        assert isinstance(response, AssistantDeleted)

    def test_create_assistant_file(self, openai_manager):
        file_id = "file1"
        assistant_id = "assistant1"

        assistant_file = openai_manager.create_assistant_file(file_id, assistant_id)

        assert isinstance(assistant_file, AssistantFile)

    def test_retrieve_assistant_file(self, openai_manager):
        file_id = "file1"
        assistant_id = "assistant1"

        assistant_file = openai_manager.retrieve_assistant_file(file_id, assistant_id)

        assert isinstance(assistant_file, AssistantFile)

    def test_list_assistant_files(self, openai_manager):
        assistant_id = "assistant1"

        files = openai_manager.list_assistant_files(assistant_id)

        assert isinstance(files, SyncCursorPage)

    def test_delete_assistant_file(self, openai_manager):
        file_id = "file1"
        assistant_id = "assistant1"

        response = openai_manager.delete_assistant_file(file_id, assistant_id)

        assert isinstance(response, FileDeleteResponse)