import json
from typing import Dict, List, Optional, Self, Union
from camel.agents.chat_agent import ChatAgent
from camel.data_collector.base import BaseDataCollector
from camel.messages.base import BaseMessage
from camel.messages.func_message import FunctionCallingMessage
from camel.toolkits.function_tool import FunctionTool
from camel.types.enums import OpenAIBackendRole, RoleType


class ShareGPTDataCollector(BaseDataCollector):

    def __init__(self):
        super().__init__()
        self.system_message: Optional[BaseMessage] = None
        self.agent_name: Optional[str] = None
        self.tools: List[FunctionTool] = []

    def inject(
        self,
        agent: Union[List[ChatAgent], ChatAgent],
        name: Optional[Union[str, List[str]]] = None,
    ) -> Self:
        if len(self.agents) > 1:
            raise ValueError("ShareGPTDataCollector only supports one agent")
        if isinstance(agent, list):
            if len(agent) != 1:
                raise ValueError("ShareGPTDataCollector only supports one agent")
            agent = agent[0]
        if isinstance(name, list):
            name = name[0]

        self.agent_name = name or agent.role_name
        self.system_message = agent._system_message
        self.tools = list(agent.tool_dict.values())

        self._inject(agent, name)
        return self

    def convert(self) -> Dict[str, str]:
        if self.agent_name is None:
            raise ValueError("No agent injected")
        if history := self.history.get(self.agent_name):
            data = dict(
                system=self.system_message.content if self.system_message else "",
                tools=json.dumps(
                    [t.get_openai_tool_schema()["function"] for t in self.tools]
                ),
                conversations=[],
            )
            for _, role, message in history:
                if role == OpenAIBackendRole.USER:
                    data["conversations"].append(
                        {"from": "human", "value": message.content}
                    )
                elif role == OpenAIBackendRole.ASSISTANT:
                    if isinstance(message, FunctionCallingMessage):
                        tmp = dict(
                            name=message.func_name,
                            arguments=message.args,
                        )
                        data["conversations"].append(
                            {"from": "function_call", "value": json.dumps(tmp)}
                        )
                    else:
                        data["conversations"].append(
                            {"from": "gpt", "value": message.content}
                        )
                elif role == OpenAIBackendRole.FUNCTION:
                    data["conversations"].append(
                        {"from": "observation", "value": json.dumps(message.result)}
                    )

            self.data.append(data)
            return data
        raise ValueError("No data collected")
