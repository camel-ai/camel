#!/bin/bash

pip install pytest==8.4.1

python -m pytest $TEST_DIR/test_outputs.py -rA