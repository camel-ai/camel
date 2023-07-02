# How to update the documentation

To update the RST files:
```bash
sphinx-apidoc -o docs camel/
```

Helpful article [here](https://towardsdatascience.com/documenting-python-code-with-sphinx-554e1d6c4f6d).

# Building Documentation

To build the documentation:

1. [Install CAMEL](https://github.com/camel-ai/camel/blob/master/README.md) from source.

2. Install Sphinx, Sphinx theme and `recommonmark` (Sphinx extension that enables Markdown support) by running the following command in your terminal or command prompt:
```bash
pip install sphinx
pip install sphinx_book_theme
pip install recommonmark
```

3. Navigate to the `docs` directory, and run the `make` command:
```bash
cd docs
make html
```

4. Launch the HTML documentation from the terminal using a local HTTP server
```bash
cd _build/html
python -m http.server
```
This command starts a local HTTP server on port 8000 by default. Once the server is running, open your web browser and enter the following URL:
```bash
http://localhost:8000
```
This will load the HTML documentation in your web browser from the local server.

You can navigate through the documentation using the links and interact with it as you would with any other web page.

To stop the local server, go back to the terminal or command prompt where it is running and press `Ctrl+C` to terminate the server.