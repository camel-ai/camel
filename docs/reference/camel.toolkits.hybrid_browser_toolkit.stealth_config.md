<a id="camel.toolkits.hybrid_browser_toolkit.stealth_config"></a>

Stealth configuration for browser automation to avoid bot detection.

This module contains all the configuration needed to make the browser
appear as a regular user browser rather than an automated one.

<a id="camel.toolkits.hybrid_browser_toolkit.stealth_config.StealthConfig"></a>

## StealthConfig

```python
class StealthConfig:
```

Configuration class for stealth browser settings.

<a id="camel.toolkits.hybrid_browser_toolkit.stealth_config.StealthConfig.get_launch_args"></a>

### get_launch_args

```python
def get_launch_args():
```

**Returns:**

  List[str]: Chrome command line arguments to avoid detection.

<a id="camel.toolkits.hybrid_browser_toolkit.stealth_config.StealthConfig.get_context_options"></a>

### get_context_options

```python
def get_context_options():
```

**Returns:**

  Dict[str, Any]: Browser context configuration options.

<a id="camel.toolkits.hybrid_browser_toolkit.stealth_config.StealthConfig.get_http_headers"></a>

### get_http_headers

```python
def get_http_headers():
```

**Returns:**

  Dict[str, str]: HTTP headers to appear more like a real browser.

<a id="camel.toolkits.hybrid_browser_toolkit.stealth_config.StealthConfig.get_all_config"></a>

### get_all_config

```python
def get_all_config():
```

**Returns:**

  Dict[str, Any]: Complete stealth configuration.
