🐫 **Welcome to CAMEL!** 🐫

Thank you for your interest in contributing to the CAMEL project! 🎉 We're excited to have your support. As an open-source initiative in a rapidly evolving and open-ended field, we wholeheartedly welcome contributions of all kinds. Whether you want to introduce new features, enhance the infrastructure, improve documentation, asking issues, add more examples, implement state-of-the-art research ideas, or fix bugs, we appreciate your enthusiasm and efforts. 🙌  You are welcome to join our [slack](https://join.slack.com/t/camel-kwr1314/shared_invite/zt-1vy8u9lbo-ZQmhIAyWSEfSwLCl2r2eKA) for more efficient communication. 💬

## Guidelines 📝

### Contributing to the Code 👨‍💻👩‍💻

If you're eager to contribute to this project, that's fantastic! We're thrilled to have your support. Just remember to follow the [Fork-and-Pull-Request](https://docs.github.com/en/get-started/quickstart/contributing-to-projects) workflow when opening your pull requests. Make sure to mention any related issues and tag the relevant maintainers too. 💪

Before your pull request can be merged, it must pass the formatting, linting, and testing checks. You can find instructions on running these checks locally under the **Common Tasks** section below. 🔍

Ensuring excellent documentation and thorough testing is absolutely crucial. Here are some guidelines to follow based on the type of contribution you're making:

- If you fix a bug:
  - Add a relevant unit test when possible. These can be found in the `test` directory.
- If you make an improvement:
  - Update any affected example console scripts in the `examples` directory, Gradio demos in the `apps` directory, and documentation in the `docs` directory.
  - Update unit tests when relevant.
- If you add a feature:
  - Include unit tests in the `test` directory. 
  - Add a demo script in the `examples` directory.
 

We're a small team focused on building great things. If you have something in mind that you'd like to add or modify, opening a pull request is the ideal way to catch our attention. 🚀

### Issues 🐛🆙🌟

Our [issues](https://github.com/camel-ai/camel/issues) page on GitHub is regularly updated with bugs, improvements, and feature requests. We have a handy set of labels to help you sort through and find issues that interest you. Feel free to use these labels to keep things organized.

When you start working on an issue, please assign it to yourself so that others know it's being taken care of.

When creating a new issue, it's best to keep it focused on a specific bug, improvement, or feature. If two issues are related or blocking each other, it's better to link them instead of merging them into one.

We do our best to keep these issues up to date, but considering the fast-paced nature of this field, some may become outdated. If you come across any such issues, please give us a heads-up so we can address them promptly. 👀

### Getting Help 🆘

Our aim is to make the developer setup as straightforward as possible. If you encounter any challenges during the setup process, don't hesitate to reach out to a maintainer. We're here to assist you and ensure that the experience is smooth not just for you but also for future contributors. 😊

In line with this, we do have specific guidelines for code linting, formatting, and documentation in the codebase. If you find these requirements difficult or even just bothersome to work with, please feel free to get in touch with a maintainer. We don't want these guidelines to hinder the integration of good code into the codebase, so we're more than happy to provide support and find a solution that works for you. 🤝

## Quick Start 🚀

To get started with CAMEL, follow these steps:

```bash
# Create a conda virtual environment
conda create --name camel python=3.10

# Activate the camel conda environment
conda activate camel

# Clone the GitHub repo
git clone https://github.com/camel-ai/camel.git

# Change to the project directory
cd camel

# Install CAMEL from source
pip install -e .

# Install pre-commit within the camel environment (only needed for opening pull requests)
pip install pre-commit
pre-commit install
```

These commands will install all the necessary dependencies for running the package, examples, linting, formatting, tests, and coverage.

To verify that everything is set up correctly, run `pytest .` This will ensure that all tests pass successfully. ✅

## Common Actions 🔄

### Linting & Formatting ✨

```bash
flake8
isort .
```

For extra validation of type hints:

```bash
mypy --namespace-packages -p camel
mypy --namespace-packages -p test
mypy --namespace-packages -p examples
mypy --namespace-packages -p apps
```

### Coverage 📊

Code coverage measures the extent to which unit tests cover the code, helping identify both robust and less robust areas of the codebase.

To generate a report showing the current code coverage, execute one of the following commands.

To include all source files into coverage:
```
coverage erase
coverage run --source=. -m pytest .
coverage html
# Open htmlcov/index.html
```

To include only tested files:
```bash
pytest --cov --cov-report=html
```

The coverage report will be generated at `htmlcov/index.html`.

#### Tests 🧪

Unit tests cover modular logic that doesn't require calls to outside APIs. Currently, the test setup requires an OpenAI API key to test the framework, making them resemble integration tests.

To run all tests including those that use OpenAI API, use the following command:

```bash
pytest .
```

To quickly run only local isolated unit and integration tests:
```bash
pytest -m "not model_backend and not slow" .
```

If you're developing with VSCode, make sure to create a `.env` file in the repository root and include your OpenAI API key:

```
OPENAI_API_KEY=sk-XXXXXXXX
```

## Documentation 📚

### Contribute to Documentation 📝

The documentation is primarily generated automatically by [Sphinx](https://www.sphinx-doc.org/en/master/) using the code.

We kindly request that you provide comprehensive documentation for all classes and methods to ensure high-quality documentation coverage.

### Build Documentation Locally 🛠️

To build the documentation locally, follow these steps:

```bash
cd docs
make html
```

More guidelines about building and hosting documentations locally can be found [here](https://github.com/camel-ai/camel/blob/master/docs/README.md).

## Versioning and Release 🚀

As of now, CAMEL is actively in development and not published to PyPI yet.

CAMEL follows the [semver](https://semver.org/) versioning standard. As pre-1.0 software, even patch releases may contain [non-backwards-compatible changes](https://semver.org/#spec-item-4). Currently, the major version is 0, and the minor version is incremented. Releases are made once the maintainers feel that a significant body of changes has accumulated.


## License 📜

The source code of the CAMEL project is licensed under Apache 2.0. Your contributed code will be also licensed under Apache 2.0 by default. To add license to you code, you can manually copy-paste it from `license_template.txt` to the head of your files or run the `update_license.py` script to automate the process:

```bash
python licenses/update_license.py . licenses/license_template.txt
```

This script will add licenses to all the `*.py` files or update the licenses if the existing licenses are not the same as `license_template.txt`.

## Giving Credit 🎉

If your contribution has been included in a release, we'd love to give you credit on Twitter, but only if you're comfortable with it!

If you have a Twitter account that you would like us to mention, please let us know either in the pull request or through another communication method. We want to make sure you receive proper recognition for your valuable contributions. 😄
