import os 
import json
from glob import glob
from os.path import join
from natsort import natsorted

def compose_js_code( 
    container_idx=0,
    data=None, 
    json_fname=None,
    include_function=True,
):
    assert data is not None or json_fname is not None, "Must provide data or json_fname"
    if data is None:
        # Load the local JSON data
        with open(json_fname) as json_file:
            data = json.load(json_file)

    # Generate the JavaScript code
    js_code = f"const jsonData{container_idx} = {json.dumps(data)};"
    if include_function:
        js_code += """
function createChatBubble(sender, message) {
    const bubbleWrapper = document.createElement("div");
    bubbleWrapper.className = "bubble-wrapper";

    const nameBox = document.createElement("div");
    nameBox.className = "user-name-box";
    nameBox.innerText = sender;

    const bubble = document.createElement("div");
    bubble.className = `.chat-bubble ${sender}-bubble`;
    bubble.innerText = message;

    bubbleWrapper.appendChild(nameBox);
    bubbleWrapper.appendChild(bubble);
    return bubbleWrapper;
    }  
        """

    container_name = f"chat-container-{container_idx}"
    js_code += f"""
// Get the chat container element
const chatContainer{container_idx} = document.getElementById("{container_name}");
    """

    js_code += f"""
// Iterate over the JSON data and generate chat bubbles
jsonData{container_idx}.forEach(
    """

    js_code += """
    data => {
    const { sender, message } = data;
    const bubble = createChatBubble(sender, message);
    """

    js_code += f"""
    chatContainer{container_idx}.appendChild(bubble);
    """

    js_code += """
});
    """

    return js_code


def compose_html_block(  
    container_name="chat-container",
    include_video=True,
    video_fname="execute.mp4",
):
    # assert os.path.exists(video_fname), f"video {video_fname} does not exist"  
    if not include_video:
        html_block = f"""
    <div id="{container_name}"></div> 
    """
    elif "gif" in video_fname:
        vid_alt = video_fname.replace(".gif", "")
        html_block = f"""
    <div id="{container_name}"></div>
    <div id="video-container">
      <span class="image fit" style="max-width: 70%; border: 0px solid; border-color: #888888; margin-left: auto; margin-right: auto">
	    <img src="{video_fname}" alt="{vid_alt}"></img>
	  </span>
        
    </div>

    """
    else:
        html_block = f"""
    <div id="{container_name}"></div>
    <div id="video-container">
        <video src="{video_fname}" controls></video>
    </div>
        
    """
    
    return html_block

def compose_html_file( 
    js_fname,
    css_code,
    html_blocks,
):
    # assert os.path.exists(js_fname), f"js_fname {js_fname} does not exist"
    # assert os.path.exists(css_fname), f"css_fname {css_fname} does not exist"
    assert len(html_blocks) > 0, "Must provide at least one html block"
    div_code = "\n".join(html_blocks)
    
    html_code = f"""
<!DOCTYPE html>
<html>
<head>
  <title>Chat Messages</title>
  <style>
    {css_code}
  </style>
</head>
<body>   
    {div_code}
    <script src="{js_fname}"></script>
</body>
</html>
    """
    return html_code

CSS_CODE = """  
        /* styles.css */
        /* Chat message styles */
        #chat-container {
        padding: 20px;
        background-color: #f9f9f9;
        border: 1px solid #ddd;
        border-radius: 8px;
        }

        .bubble-wrapper {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        }

        .user-name-box {
        font-size: 14px;
        background-color: #f2f2f2;
        padding: 4px 8px;
        border-radius: 4px;
        margin-right: 8px;
        width: 80px;
        }

        .chat-bubble {
        background-color: #dcf8c6;
        padding: 12px;
        margin: 10px;
        font-size: 8px; 
        border-radius: 5px;
        display: inline-block;
        }

        .SystemPrompt-bubble {
        background-color: #c0d8ae;
        } 
        .UserPrompt-bubble {
        background-color: #deefd0;
        } 
        .Feedback-bubble {
        background-color: #c3f2db;
        }
        .Action-bubble {
        background-color: #fff3a8;
        }
        .Alice-bubble {
        background-color: #efa0d0; 
        }
        .Bob-bubble {
        background-color: #7db6f7;
        }
        .Chad-bubble {
        background-color: #facf92;
        }
        .Dave-bubble {
        background-color: #918d84;
        } 
        .Solution-bubble {
        background-color: #fff3a8;
        }
        .Response-bubble {
        background-color: #7db6f7;
        }
        /* Video container styles */
        #video-container {
        width: 500px;
        margin: 5px auto;
        }

        #video-container video {
        width: 100%;
        }
"""


def save_episode_html(
    episode_path,
    html_fname="display",
    video_fname="execute.mp4",
    video_include_steps=False,
    sender_keys=["Alice", "Bob", "Chad", "Dave", "SystemPrompt", "UserPrompt", "Feedback", "Action"],
    ):
    # dumps css, js, and html files to save_dir
    step_dirs = natsorted(
        glob(
            f"{episode_path}/step_*"
        )
    )
    assert len(step_dirs) > 0, "No steps found in episode path"
    all_js_blocks = []
    all_html_blocks = []
    for step, step_dir in enumerate(step_dirs):
        json_files = natsorted(
            glob(
                f"{step_dir}/prompts/*.json"
            )
        )

        # the json filename should be in the format of replan{replan_idx}_call{n_calls}_agent{agent_name}_{timestamp}.json'
        # sort them by replan first, then by call number 

        json_data = []
        for json_file in json_files:
            _data = json.load(open(json_file, 'r'))
            if isinstance(_data, dict):
                _data = [_data]
            else:
                assert isinstance(_data, list), "json data must be a list or dict"
            filter_data = [
                di for di in _data if di.get("sender", None) in sender_keys
            ]
            json_data.extend(filter_data)

        all_js_blocks.append(
            compose_js_code(
                container_idx=step,
                data=json_data,
                include_function=(step == 0)
            )
        )
        relative_step_dir = step_dir.split("/")[-1]
        if video_include_steps:
            video_fname = f"video_step_{step}.m4v"
        else:
            video_fname = f"{relative_step_dir}/{video_fname}"
        all_html_blocks.append(
            compose_html_block(
                container_name=f"chat-container-{step}",
                video_fname=video_fname,
            )
        )
    js_code = "\n".join(all_js_blocks)
    js_fname = f"{episode_path}/script.js"
    with open(js_fname, 'w') as f:
        f.write(js_code)

    # directly write style on top of html  
    # css_fname = f"{episode_path}/style.css"
    # with open(css_fname, 'w') as f:
    #     f.write(CSS_CODE)

    html_code = compose_html_file(
        js_fname=js_fname.split("/")[-1],
        html_blocks=all_html_blocks,
        css_code=CSS_CODE,
    )
    html_fname = f"{episode_path}/{html_fname}.html"
    with open(html_fname, 'w') as f:
        f.write(html_code)
    print(f"Saved episode html to {html_fname}")
    return

def save_qa_data_html(
    dataset_dir,
    html_fname="qa_display",
    sender_keys=["Alice", "Bob", "Chad", "Dave", "SystemPrompt", "UserPrompt", "Solution", "Feedback", "Action", "Response"],
    ):
    data_dirs = natsorted(
        glob(
            f"{dataset_dir}/*"
        )   
    ) 
    for i, data_dir in enumerate(data_dirs):
        json_files = natsorted(
            glob(
                f"{data_dir}/question*.json"
            )
        )
        num_questions = len(json_files)
        json_data = []
        for json_file in json_files:
            _data = json.load(open(json_file, 'r'))
            if isinstance(_data, dict):
                _data = [_data]
            else:
                assert isinstance(_data, list), "json data must be a list or dict"
            filter_data = [
                di for di in _data if di.get("sender", None) in sender_keys
            ]
            json_data.extend(filter_data)
        
        js_code = compose_js_code(
                container_idx=i,
                data=json_data,
                include_function=True
            )
        relative_step_dir = data_dir.split("/")[-1]
        html_block = compose_html_block(
                container_name=f"chat-container-{i}",
                include_video=False,
            ) 
         
        js_fname = f"{data_dir}/script.js"
        with open(js_fname, 'w') as f:
            f.write(js_code)
 
        html_code = compose_html_file(
            js_fname=js_fname.split("/")[-1],
            html_blocks=[html_block],
            css_code=CSS_CODE,
        )
        html_path = f"{data_dir}/{html_fname}.html"
        with open(html_path, 'w') as f:
            f.write(html_code)
        print(f"Found {num_questions} questions. Saved html to {html_path}")
    return 

    


if __name__ == "__main__":
    # path = "data/sandwich_dialogTemp0FullChat/run_0"
    path = "data/qa_data/dataset_capability/"
    save_qa_data_html(path)
    exit()
    path = "data/qa_data/task_cabinet/run_19"
    save_episode_html(
        path,
        html_fname="full_prompt_and_response", 
        sender_keys=["Alice", "Bob", "Chad", "Dave", "SystemPrompt", "UserPrompt", "Feedback", "Action", 'Solution', 'Response'],
    )
    exit()        

    from glob import glob
    # paths = glob("data/task_*_method*")
    paths = glob('../../project-roco.github.io/demos/*')
    for path in paths:
        save_episode_html(
            path, 
            # html_fname="full_prompt_and_response", 
            # sender_keys=["Alice", "Bob", "Chad", "Dave", "SystemPrompt", "UserPrompt", "Feedback", "Action", 'Solution'],
            video_include_steps=True,
            sender_keys=["Alice", "Bob", "Chad", "Dave", "Feedback", "Action"],
            html_fname="response_only", 
        )
    
