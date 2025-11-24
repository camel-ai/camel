# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

sys.path.insert(0, os.path.abspath('..'))

project = 'CAMEL'
copyright = '2024, CAMEL-AI.org'
author = 'CAMEL-AI.org'
release = '0.2.80a3'

html_favicon = (
    'https://raw.githubusercontent.com/camel-ai/camel/master/misc/favicon.png'
)

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

source_suffix = ['.rst', '.md']

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'myst_parser',
    'nbsphinx',
    'sphinxext.rediraffe',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_book_theme'

html_theme_options = {
    "logo": {
        "text": f"CAMEL {release}",
        "image_light": "https://raw.githubusercontent.com/camel-ai/camel/master/misc/logo_light.png",
        "image_dark": "https://raw.githubusercontent.com/camel-ai/camel/master/misc/logo_light.png",
    },
    "show_toc_level": 2,
    "show_nav_level": 2,
    "navigation_with_keys": True,
    "toc_title": "On this page",
    "show_navbar_depth": 2,
    "repository_url": "https://github.com/camel-ai/camel",
    "use_repository_button": True,
    "use_issues_button": True,
    "use_edit_page_button": True,
}

html_static_path = ['_static']
html_css_files = ['custom.css']

nbsphinx_execute = 'never'
nbsphinx_allow_errors = True
nbsphinx_prolog = r"""
{% set docname = env.doc2path(env.docname, base=None) %}

.. raw:: html

    <style>
    div.nbinput div.prompt,
    div.nboutput div.prompt {
        display: none;
    }
    </style>
"""

# ruff: noqa: E501
rediraffe_redirects = {
    "cookbooks/create_your_first_agent": "cookbooks/basic_concepts/create_your_first_agent",
    "cookbooks/create_your_first_agents_society": "cookbooks/basic_concepts/create_your_first_agents_society",
    "cookbooks/embodied_agents": "cookbooks/advanced_features/embodied_agents",
    "cookbooks/critic_agents_and_tree_search": "cookbooks/advanced_features/critic_agents_and_tree_search",
    "cookbooks/agents_society": "cookbooks/basic_concepts/create_your_first_agents_society",
    "cookbooks/agents_message": "cookbooks/basic_concepts/agents_message",
    "cookbooks/agents_with_tools": "cookbooks/advanced_features/agents_with_tools",
    "cookbooks/agents_with_memory": "cookbooks/advanced_features/agents_with_memory",
    "cookbooks/agents_with_rag": "cookbooks/advanced_features/agents_with_rag",
    "cookbooks/agents_prompting": "cookbooks/basic_concepts/agents_prompting",
    "cookbooks/task_generation": "cookbooks/multi_agent_society/task_generation",
    "cookbooks/knowledge_graph": "cookbooks/advanced_features/agents_with_graph_rag",
    "cookbooks/roleplaying_scraper": "cookbooks/applications/roleplaying_scraper",
    "cookbooks/video_analysis": "cookbooks/data_processing/video_analysis",
    "cookbooks/agents_tracking": "cookbooks/advanced_features/agents_tracking",
    "cookbooks/workforce_judge_committee": "cookbooks/multi_agent_society/workforce_judge_committee",
    "cookbooks/ingest_data_from_websites_with_Firecrawl": "cookbooks/data_processing/ingest_data_from_websites_with_Firecrawl",
    "cookbooks/sft_data_generation_and_unsloth_finetuning": "cookbooks/data_generation/sft_data_generation_and_unsloth_finetuning_Qwen2_5_7B",
    "cookbooks/customer_service_Discord_bot_with_agentic_RAG": "cookbooks/applications/customer_service_Discord_bot_using_SambaNova_with_agentic_RAG",
    "cookbooks/agent_with_chunkr_for_pdf_parsing": "cookbooks/data_processing/agent_with_chunkr_for_pdf_parsing",
    "cookbooks/data_gen_with_real_function_calls_and_hermes_format": "cookbooks/data_generation/data_gen_with_real_function_calls_and_hermes_format",
    "cookbooks/cot_data_gen_sft_qwen_unsolth_upload_huggingface": "cookbooks/data_generation/cot_data_gen_sft_qwen_unsolth_upload_huggingface",
    "cookbooks/customer_service_Discord_bot_using_local_model_with_agentic_RAG": "cookbooks/applications/customer_service_Discord_bot_using_local_model_with_agentic_RAG",
    "cookbooks/model_training/cot_data_gen_sft_qwen_unsolth_upload_huggingface": "cookbooks/data_generation/cot_data_gen_sft_qwen_unsolth_upload_huggingface",
}
