#!/bin/bash

# Install test dependencies
pip install pytest==8.4.1 psutil==7.0.0

# Run the tests
pytest $TEST_DIR/test_outputs.py -v -rA