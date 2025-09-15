<a id="camel.toolkits.video_analysis_toolkit"></a>

<a id="camel.toolkits.video_analysis_toolkit.VideoAnalysisToolkit"></a>

## VideoAnalysisToolkit

```python
class VideoAnalysisToolkit(BaseToolkit):
```

A class for analysing videos with vision-language model.

**Parameters:**

- **working_directory** (Optional[str], optional): The directory where the video will be downloaded to. If not provided, video will be stored in a temporary directory and will be cleaned up after use. (default: :obj:`None`)
- **model** (Optional[BaseModelBackend], optional): The model to use for visual analysis. (default: :obj:`None`)
- **use_audio_transcription** (bool, optional): Whether to enable audio transcription using OpenAI's audio models. Requires a valid OpenAI API key. When disabled, video analysis will be based solely on visual content. (default: :obj:`False`)
- **use_ocr** (bool, optional): Whether to enable OCR for extracting text from video frames. (default: :obj:`False`)
- **frame_interval** (float, optional): Interval in seconds between frames to extract from the video. (default: :obj:`4.0`)
- **output_language** (str, optional): The language for output responses. (default: :obj:`"English"`)
- **cookies_path** (Optional[str]): The path to the cookies file for the video service in Netscape format. (default: :obj:`None`)
- **timeout** (Optional[float]): The timeout value for API requests in seconds. If None, no timeout is applied. (default: :obj:`None`)

<a id="camel.toolkits.video_analysis_toolkit.VideoAnalysisToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    working_directory: Optional[str] = None,
    model: Optional[BaseModelBackend] = None,
    use_audio_transcription: bool = False,
    use_ocr: bool = False,
    frame_interval: float = 4.0,
    output_language: str = 'English',
    cookies_path: Optional[str] = None,
    timeout: Optional[float] = None
):
```

<a id="camel.toolkits.video_analysis_toolkit.VideoAnalysisToolkit.__del__"></a>

### __del__

```python
def __del__(self):
```

Clean up temporary directories and files when the object is
destroyed.

<a id="camel.toolkits.video_analysis_toolkit.VideoAnalysisToolkit._extract_text_from_frame"></a>

### _extract_text_from_frame

```python
def _extract_text_from_frame(self, frame: Image.Image):
```

Extract text from a video frame using OCR.

**Parameters:**

- **frame** (Image.Image): PIL image frame to process.

**Returns:**

  str: Extracted text from the frame.

<a id="camel.toolkits.video_analysis_toolkit.VideoAnalysisToolkit._process_extracted_text"></a>

### _process_extracted_text

```python
def _process_extracted_text(self, text: str):
```

Clean and format OCR-extracted text.

**Parameters:**

- **text** (str): Raw extracted OCR text.

**Returns:**

  str: Cleaned and formatted text.

<a id="camel.toolkits.video_analysis_toolkit.VideoAnalysisToolkit._extract_audio_from_video"></a>

### _extract_audio_from_video

```python
def _extract_audio_from_video(self, video_path: str, output_format: str = 'mp3'):
```

Extract audio from the video.

**Parameters:**

- **video_path** (str): The path to the video file.
- **output_format** (str): The format of the audio file to be saved. (default: :obj:`"mp3"`)

**Returns:**

  str: The path to the audio file.

<a id="camel.toolkits.video_analysis_toolkit.VideoAnalysisToolkit._transcribe_audio"></a>

### _transcribe_audio

```python
def _transcribe_audio(self, audio_path: str):
```

Transcribe the audio of the video.

<a id="camel.toolkits.video_analysis_toolkit.VideoAnalysisToolkit._extract_keyframes"></a>

### _extract_keyframes

```python
def _extract_keyframes(self, video_path: str):
```

Extract keyframes from a video based on scene changes and
regular intervals,and return them as PIL.Image.Image objects.

**Parameters:**

- **video_path** (str): Path to the video file.

**Returns:**

  List[Image.Image]: A list of PIL.Image.Image objects representing
the extracted keyframes.

<a id="camel.toolkits.video_analysis_toolkit.VideoAnalysisToolkit._normalize_frames"></a>

### _normalize_frames

```python
def _normalize_frames(self, frames: List[Image.Image], target_width: int = 512):
```

Normalize the size of extracted frames.

**Parameters:**

- **frames** (List[Image.Image]): List of frames to normalize.
- **target_width** (int): Target width for normalized frames.

**Returns:**

  List[Image.Image]: List of normalized frames.

<a id="camel.toolkits.video_analysis_toolkit.VideoAnalysisToolkit.ask_question_about_video"></a>

### ask_question_about_video

```python
def ask_question_about_video(self, video_path: str, question: str):
```

Ask a question about the video.

**Parameters:**

- **video_path** (str): The path to the video file. It can be a local file or a URL (such as Youtube website).
- **question** (str): The question to ask about the video.

**Returns:**

  str: The answer to the question.

<a id="camel.toolkits.video_analysis_toolkit.VideoAnalysisToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects representing
the functions in the toolkit.
