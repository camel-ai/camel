from camel.models import ModelScopeModel

model = ModelScopeModel(
    model_type="Shanghai_AI_Laboratory/internlm3-8b-instruct",
    model_config_dict={
        # "temperature": 0.5,
        # "trust_remote_code": True,
    },)

model.run([{"role": "user", "content": "Hello"}])

