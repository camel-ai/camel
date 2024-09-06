from camel.agents.chat_agent import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.messages.base import BaseMessage
from camel.models.model_factory import ModelFactory
from camel.prompts.prompt_templates import PromptTemplateGenerator
from camel.toolkits.search_toolkit import SearchToolkit
from camel.toolkits.video_toolkit import VideoDownloaderToolkit
from camel.types.enums import ModelPlatformType, ModelType, RoleType, TaskType


def detect_image_obj(image_list) -> None:
    sys_msg = PromptTemplateGenerator().get_prompt_from_key(
        TaskType.OBJECT_RECOGNITION, RoleType.ASSISTANT
    )
    print("=" * 20 + " SYS MSG " + "=" * 20)
    print(sys_msg)
    print("=" * 49)

    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content=sys_msg,
    )
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig().as_dict(),
    )
    agent = ChatAgent(
        assistant_sys_msg,
        model=model,
    )

    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content="Please start the object detection for the following images!",
        image_list=image_list,
        image_detail="high",
    )
    assistant_response = agent.step(user_msg)
    print("=" * 20 + " RESULT " + "=" * 20)
    print(assistant_response.msgs[0].content)
    print("=" * 48)


def main() -> None:
    # Create an instance of the SearchToolkit
    search_toolkit = SearchToolkit()

    # Example query for DuckDuckGo video search
    query = "What big things are happening in 2024?"

    # Perform a DuckDuckGo search with the query, setting source to 'videos'
    results = search_toolkit.search_duckduckgo(
        query=query, source="videos", max_results=5
    )

    # Try to download videos from the search results
    for result in results:
        video_url = result['embed_url']
        if not video_url:
            print(f"No valid video URL provided for result: {result}")
            continue

        print(f"Trying to download video from: {video_url}")
        try:
            # Initialize the downloader with the found video URL
            downloader = VideoDownloaderToolkit(
                video_url=video_url, split_into_chunks=False
            )
            # Try to get screenshots (assuming the method raises an exception on failure)
            image_list = downloader.get_video_screenshots(3)
            if image_list and len(image_list) > 0:
                print(
                    f"Successfully downloaded video and captured screenshots from: {video_url}"
                )
                # Proceed with object detection if screenshots are successfully captured
                detect_image_obj(image_list)
                print("Stopping further downloads as we found valid images.")
                break
            else:
                print(f"Failed to capture screenshots from video: {video_url}")
        except Exception as e:
            print(f"Failed to download video from {video_url}: {str(e)}")

    print("Exited the video download loop.")


if __name__ == "__main__":
    main()
