import re


def split_markdown_code(string: str) -> str:
    substr_list = string.split("```")
    out = []
    for i_subs, subs in enumerate(substr_list):
        if i_subs % 2 == 0:
            out.append(subs)
        else:  # inside code
            rx = r"\n+"
            repl = lambda m: "```{}```".format(m.group(0))
            new_subs = re.sub(rx, repl, subs)
            out.append(new_subs)
    out_str = "```".join(out)
    out_str_cleanup = re.sub(r"``````", "", out_str)
    return out_str_cleanup
