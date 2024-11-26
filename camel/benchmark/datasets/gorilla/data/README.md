# Gorilla API Store 

Teach Gorilla how to use your API! Learn about the entire workflow, and how to contribute to Gorilla API Store! Gorilla API Store intends to enhance LLM's capability to use tools through API calls. We appreciate everyone's effort and contributions! THIS WILL ALWAYS REMAIN OPEN SOURCE.

## How to Contribute?

Contribute to Gorilla API Store is very easy! 

1. **JSON Contribution**: It only takes two steps

- Step 1: Submit an API JSON file or a URL JSON file following our format. 
- Step 2: Raise a Pull Request.

2. **Website Assisted** [Coming Soon]: If you need help writing an API json, we will provide a website and you only need to type in your API documentation url. We will return a draft API JSON file (you guessed it, using an LLM) and you can either choose to **Submit** or **Edit & Submit**. 

## Repository Organization
 
Post merge, your APIs will reside under your username, organized as follows: 

```
gorilla
├── data
│   ├── apibench (Evaluating LLM models) v-1.0
│   │   ├── {api_name}_train.jsonl, {api_name}_eval.jsonl
│   ├── apizoo (Contributed by our Community)
│   |   ├── username1.json
│   │   ├── username2.json
│   │   ├── username3.json
│   │   ├── ...
```

## Two ways to contribute APIs

We make the contribution to Gorilla API Store as easy as possible. We provide two alternatives: You could either submit following the API JSON format {or} URL JSON format. 

### Option 1: API JSON (Preferred)
 
Community members can submit to Gorilla API Zoo using the following JSON list format:

| Field      |  Type  | Description/Options     | Required |
| :---       | :----: |          :----         |   :---:   |
| user_name     | String       | Name of User   | ✅ |
| api_name      | String       | Name of API (maximum 20 words)   | ✅ |
| api_call | String | One line of code that starts with the function call, followed by a full list of argument names and values | ✅ |
| api_version | String | Version of API | ✅ |
| api_arguments | JSON | JSON of all the restricted keywords in the arguments list | ✅ |
| functionality | String | Short description of the function (maximum 20 words) | ✅ |
| env_requirements | List[String] | List of all the library dependencies | [Optional]:fire: |
| example_code | String | A string containing example code to use the API | [Optional]:fire: |
| meta_data | JSON | A JSON file of containing additional information about the API | [Optional]:fire: |
| Questions | List[String] | A question describing a real-life scenario that uses this API. Please do not include specific API name. | [Optional]:fire: |

**Example Submission**:

```python
[ 
  {
    "user_name": "example_username_api",
    "api_name": "Torch Hub Model snakers4-silero",
    "api_call": "torch.hub.load(repo_or_dir=['snakers4/silero-models'], model=['silero_stt'], *args, source, trust_repo, force_reload, verbose, skip_validation, **kwargs)", 
    "api_version": 2.0, 
    "api_arguments": {
      "repo_or_dir": "snakers4/silero-models", 
      "model": "silero_stt", 
      "language": ["en", "de", "es"]
    },
    "functionality": "Speech to Text",
    "env_requirements": ["torchaudio", "torch", "omegaconf", "soundfile"],
    "example_code": "import torch \n \
                    model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True) \n \
                    imgs = ['https://ultralytics.com/images/zidane.jpg'] \n \
                    results = model(imgs)",
    "meta_data": {
      "description": "Silero Speech-To-Text models provide enterprise grade STT in a compact form-factor for several commonly spoken languages. The models are robust to a variety of dialects, codecs, domains, noises, and lower sampling rates. They consume a normalized audio in the form of samples and output frames with token probabilities. A decoder utility is provided for simplicity.", 
      "performance": {"dataset": "imagenet", "accuracy": "80.4\%"}
    },
    "questions": [
      "I am a doctor and I want to dictate what my patient is saying and put it into a text doc in my computer.",
      "My students in math class is having trouble following up my content. He needs an API to write down what I am saying for reviewing.",
    ],
  },
  ...
]
```

### Option 2: URL JSON

We also provide you with a much simpler approach for you to contribute! Provide a simple url to your API documentation, we'll process it for you. Keep in mind, there might be some errors that can creep in with this process and hence we recommend the approach above, or at least come back to verify if the api documentation we generated for these url's are accurate! They API document generated from the urls will be stored as mentioned in the directory structure above.

Submit a json file containing the list of json objects: 

| Field      |  Type  | Description/Options     | Required |
| :---       | :----: |          :----         |   :---:   |
| user_name     | String       | Name of User   | ✅ |
| api_name      | String       | Name of API (maximum 20 words)   | ✅ |
| api_url      | String       | URL to API documentation   | ✅ |
| Questions | List[String] | A question describing a real-life scenario that uses this API. Please do not include specific API name. | [Optional]:fire: |

**Example Submission**:

```python
[
  {
    "user_name": "example_username_url",
    "api_name": "Torch Hub ultralytics_yolov5",
    "url": "https://pytorch.org/hub/ultralytics_yolov5/",
    "questions": [
      "I am a doctor and I want to dictate what my patient is saying and put it into a text doc in my computer.",
      "My students in math class is having trouble following up my content. He needs an API to write down what I am saying for reviewing.",
    ],
  },
...
]
```

**LLM assistance for LLM API dataset :wink:**:

Visit our website [Coming Soon!], where you can type in the API URL and we'll output an API submission for you! You can choose to submit or edit before and submitting. Easy and quick!

## Citation

If you use Gorilla or APIBench, please cite our paper:

```text
@article{patil2023gorilla,
  title={Gorilla: Large Language Model Connected with Massive APIs},
  author={Shishir G. Patil and Tianjun Zhang and Xin Wang and Joseph E. Gonzalez},
  year={2023},
  journal={arXiv preprint arXiv:2305.15334},
} 
```