<a id="camel.toolkits.video_download_toolkit"></a>

<a id="camel.toolkits.video_download_toolkit._capture_screenshot"></a>

## _capture_screenshot

```python
def _capture_screenshot(video_file: str, timestamp: float):
```

Capture a screenshot from a video file at a specific timestamp.

**Parameters:**

- **video_file** (str): The path to the video file.
- **timestamp** (float): The time in seconds from which to capture the screenshot.

**Returns:**

  Image.Image: The captured screenshot in the form of Image.Image.

<a id="camel.toolkits.video_download_toolkit.VideoDownloaderToolkit"></a>

## VideoDownloaderToolkit

```python
class VideoDownloaderToolkit(BaseToolkit):
```

A class for downloading videos and optionally splitting them into
chunks.

**Parameters:**

- **working_directory** (Optional[str], optional): The directory where the video will be downloaded to. If not provided, video will be stored in a temporary directory and will be cleaned up after use. (default: :obj:`None`)
- **cookies_path** (Optional[str], optional): The path to the cookies file for the video service in Netscape format. (default: :obj:`None`)

<a id="camel.toolkits.video_download_toolkit.VideoDownloaderToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    working_directory: Optional[str] = None,
    cookies_path: Optional[str] = None,
    timeout: Optional[float] = None
):
```

<a id="camel.toolkits.video_download_toolkit.VideoDownloaderToolkit.__del__"></a>

### __del__

```python
def __del__(self):
```

Deconstructor for the VideoDownloaderToolkit class.

Cleans up the downloaded video if they are stored in a temporary
directory.

<a id="camel.toolkits.video_download_toolkit.VideoDownloaderToolkit.download_video"></a>

### download_video

```python
def download_video(self, url: str):
```

Download the video and optionally split it into chunks.

yt-dlp will detect if the video is downloaded automatically so there
is no need to check if the video exists.

**Parameters:**

- **url** (str): The URL of the video to download.

**Returns:**

  str: The path to the downloaded video file.

<a id="camel.toolkits.video_download_toolkit.VideoDownloaderToolkit.get_video_bytes"></a>

### get_video_bytes

```python
def get_video_bytes(self, video_path: str):
```

Download video by the path, and return the content in bytes.

**Parameters:**

- **video_path** (str): The path to the video file.

**Returns:**

  bytes: The video file content in bytes.

<a id="camel.toolkits.video_download_toolkit.VideoDownloaderToolkit.get_video_screenshots"></a>

### get_video_screenshots

```python
def get_video_screenshots(self, video_path: str, amount: int):
```

Capture screenshots from the video at specified timestamps or by
dividing the video into equal parts if an integer is provided.

**Parameters:**

- **video_path** (str): The local path or URL of the video to take screenshots.
- **amount** (int): the amount of evenly split screenshots to capture.

**Returns:**

  List[Image.Image]: A list of screenshots as Image.Image.

<a id="camel.toolkits.video_download_toolkit.VideoDownloaderToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects representing
the functions in the toolkit.
