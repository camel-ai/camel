from camel.agents import EmbodiedAgent, HuggingFaceToolAgent
from camel.generators import SystemMessageGenerator
from camel.messages import UserChatMessage
from camel.typing import ModelType, RoleType


def main():
    # Create an embodied agent
    role_name = "Artist"
    meta_dict = dict(role=role_name, task="Drawing")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict,
        role_tuple=(f"{role_name}'s Embodiment", RoleType.EMBODIMENT))
    action_space = [
        HuggingFaceToolAgent(
            'hugging_face_tool_agent',
            model=ModelType.GPT_4.value,
            remote=True,
        )
    ]
    embodied_agent = EmbodiedAgent(
        sys_msg,
        verbose=True,
        action_space=action_space,
    )
    user_msg = UserChatMessage(
        role_name=role_name,
        content=("Draw all the Camelidae species, "
                 "caption the image content, "
                 "save the images by species name."),
    )
    output_message, _, _ = embodied_agent.step(user_msg)
    print(output_message.content)


if __name__ == "__main__":
    main()
