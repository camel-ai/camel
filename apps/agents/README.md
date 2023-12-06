# Agents app showcases Role Playing API as a Gradio web app

Run the app:
```
python agents.py --api-key=YOUR-OPENAI-API-KEY
```

# Deploy the app to Huggingface

This app in Camel repo does not get deployed to Huggingface automatically. The process of deployment is manual at the moment.
1. Make changes in Camel (this) repo, and thoroughly debug them on a dev machine.
2. Tag the commit that you want to deploy with tag hf_spaces_{X+1} where X must be looked up in [HF repo sync script](https://huggingface.co/spaces/camel-ai/camel-agents/blob/main/sync.sh). Do not forget to `git push --tags`.
3. Clone [HF repo](https://huggingface.co/spaces/camel-ai/camel-agents/) locally.
4. Update the tag.
5. Synchronize the changes by running [HF repo sync script](https://huggingface.co/spaces/camel-ai/camel-agents/blob/main/sync.sh)
6. Commit and push to HF.
7. HF will deploy the app automatically. Make sure that the app is built well on HF and is up and running.
