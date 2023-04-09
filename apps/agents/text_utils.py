import re


def split_markdown_code(string: str) -> str:
    """ Split a multiline block of markdown code (triple-quotes) into
    line-sized sub-blocks to make newlines stay where they belong.
    This transformation is a workaround to a known Gradio bug:
    https://github.com/gradio-app/gradio/issues/3531

    Args:
        string (str): markdown string incompatible with gr.Chatbot

    Returns:
        str: markdown string which is compatible with gr.Chatbot
    """
    substr_list = string.split("```")
    out = []
    for i_subs, subs in enumerate(substr_list):
        if i_subs % 2 == 0:  # outsize code, don't change
            out.append(subs)
        else:  # inside code
            br_done = re.sub(r"<br>", "\n", subs)

            def repl(m):
                return "```{}```".format(m.group(0))

            new_subs = re.sub(r"\n+", repl, br_done)
            out.append(new_subs)
    out_str = "```".join(out)
    out_str_cleanup = re.sub(r"``````", "", out_str)
    return out_str_cleanup
