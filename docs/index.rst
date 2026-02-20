.. CAMEL documentation master file, created by
   sphinx-quickstart on Sun May 14 13:51:36 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to CAMEL's documentation!
=================================
| **Finding the Scaling Law of Agents: The First and the Best Multi-Agent Framework.**

| **CAMEL** was the first `LLM-based multi-agent framework <https://arxiv.org/pdf/2303.17760.pdf>`_ and has since evolved into a general-purpose framework for building and deploying LLM-based agents to solve real-world tasks. We believe that studying these agents at scale offers valuable insights into their behaviors, capabilities, and potential risks. To facilitate research in this field, we support a wide range of agents, tasks, prompts, models, and simulated environments.

Main Documentation
------------------
.. toctree::
   :maxdepth: 1
   :caption: Get Started
   :name: getting_started

   get_started/installation.md
   get_started/setup.md

.. toctree::
   :maxdepth: 1
   :caption: Agents
   :name: agents

   cookbooks/create_your_first_agent.ipynb
   cookbooks/create_your_first_agents_society.ipynb
   cookbooks/embodied_agents.ipynb
   cookbooks/critic_agents_and_tree_search.ipynb

.. toctree::
   :maxdepth: 1
   :caption: Key Modules
   :name: key_modules

   key_modules/agents.md
   key_modules/datagen.md
   key_modules/models.md
   key_modules/messages.md
   key_modules/memory.md
   key_modules/tools.md
   key_modules/prompts.md
   key_modules/runtimes.md
   key_modules/tasks.md
   key_modules/loaders.md
   key_modules/storages.md
   key_modules/society.md
   key_modules/embeddings.md
   key_modules/retrievers.md
   key_modules/workforce.md
   key_modules/benchmark.md

.. toctree::
   :maxdepth: 2
   :caption: Cookbooks
   :name: cookbooks

   cookbooks/basic_concepts/index
   cookbooks/advanced_features/index
   cookbooks/multi_agent_society/index
   cookbooks/data_generation/index
   cookbooks/applications/index
   cookbooks/data_processing/index
   cookbooks/loong/index
   cookbooks/mcp/index

.. toctree::
   :maxdepth: 1
   :caption: API References
   :name: api_references

   modules

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Get Involved
------------------
We are always excited to collaborate with others and push the boundaries of multi-agent systems.

**For Research Aficionados**: Rigorous and in-depth research takes time and resources. With access to nearly unlimited advanced GPU compute and a team of world-class researchers and engineers, we’re eager to explore the frontier with patience and curiosity. Whether you’d like to contribute to ongoing projects or test a new idea, we’d love to hear from you.

**For Coding Enthusiasts**: Whether you're introducing new features, enhancing the infrastructure, improving documentation, reporting issues, adding examples, implementing state-of-the-art ideas, or fixing bugs — every contribution matters. Get started by reviewing our `Contributing Guidelines <https://github.com/camel-ai/camel/wiki/Contributing-Guidlines>`_ on GitHub.

**For Interested Humans**: Connect with us on `Discord <https://discord.camel-ai.org>`_, `WeChat <https://ghli.org/camel/wechat.png>`_, or `Slack <https://join.slack.com/t/camel-ai/shared_invite/zt-2g7xc41gy-_7rcrNNAArIP6sLQqldkqQ>`_.
