from camel.types import ModelType
from camel.agents import CodeReviewAgent
from camel.agents.code_review_agent import ChangeMode
from camel.models import BaseModelBackend, ModelFactory
from camel.types import (
    ModelPlatformType,
    ModelType,
    OpenAIBackendRole,
    RoleType,
)

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.O1_MINI,  
    model_config_dict={"temperature": 0.2},
    )


review_request = """请重点关注以下几个方面：

1. 该变更引入了对外部 API 的调用，请检查是否存在潜在的安全问题，例如参数校验或异常处理不足。

2. 我尝试优化了原有的循环结构，请评估这部分代码在性能上的提升是否合理。

3. 此次改动重构了部分函数命名和模块拆分，麻烦检查是否提升了代码的可读性和可维护性。

4. 我尽量保持代码风格与项目一致，如有不规范的地方请指出。

最后，如果你认为某些代码已经写得很不错，也可以指出并说明原因 🙏
"""

agent = CodeReviewAgent(model=model, github_token=git_tok, repo_full_name=repo_full_name, change_model=ChangeMode(2) ,output_language="zh")
result = agent.step(input_message=review_request, pr_number=pr_number, commit_sha=commit_sha)

print(result)