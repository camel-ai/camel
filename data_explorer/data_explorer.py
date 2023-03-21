import gradio as gr
from loader import load_data

data = load_data()

with gr.Blocks() as demo:
    assistant_roles = data['assistant_roles']
    user_roles = data['user_roles']
    with gr.Row():
        assistant_dd = gr.Dropdown(assistant_roles, label="ASSISTANT",
                                   value=assistant_roles[0])
        user_dd = gr.Dropdown(user_roles, label="USER", value=user_roles[0])
    with gr.Row():
        with gr.Column(scale=0.3):
            original_task_ta = gr.TextArea(label="Original task", lines=2)
        with gr.Column(scale=0.7):
            specified_task_ta = gr.TextArea(label="Specified task", lines=2)
    chatbot = gr.Chatbot().style(height=400)

    def assistant_dd_change(assistant_role, user_role):
        matrix = data['matrix']
        if (assistant_role, user_role) in matrix:
            record = matrix[(assistant_role, user_role)]
            original_task = record['original_task']
            specified_task = record['specified_task']
            messages = record['messages']
            history = []
            curr_qa = (None, None)
            for k in sorted(messages.keys()):
                msg = messages[k]
                content = msg['content']
                if msg['role_type'] == "USER":
                    if curr_qa[0] is not None:
                        history.append(curr_qa)
                        curr_qa = (content, None)
                    else:
                        curr_qa = (content, None)
                elif msg['role_type'] == "ASSISTANT":
                    curr_qa = (curr_qa[0], content)
                    history.append(curr_qa)
                    curr_qa = (None, None)
                else:
                    pass
        else:
            original_task = "N/A"
            specified_task = "N/A"
            history = []
        return original_task, specified_task, history

    args = (assistant_dd_change, [assistant_dd, user_dd],
            [original_task_ta, specified_task_ta, chatbot])
    assistant_dd.change(*args)
    user_dd.change(*args)

    assistant_dd.value = assistant_dd.value

if __name__ == "__main__":
    demo.launch(share=True, server_port=8080, inbrowser=True)
