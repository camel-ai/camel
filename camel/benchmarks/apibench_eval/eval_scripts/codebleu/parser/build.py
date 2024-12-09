# Copyright (c) Microsoft Corporation. 
# Licensed under the MIT license.

from tree_sitter import Language, Parser
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
tree_sitter_python_path = os.path.join(current_dir, 'tree-sitter-python')

Language.build_library(
  # Store the library in the `build` directory
  'my-languages.so',

  # Include one or more languages
  [ tree_sitter_python_path,
  ]
)

