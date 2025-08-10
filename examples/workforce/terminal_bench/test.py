import docker

client = docker.from_env()
# get container
container = client.containers.get("play-zork-container")

# run ls command
# result = container.exec_run("/bin/sh -c 'pwd ; ls /app'")
# print result
# print(result.output.decode('utf-8'))

# create a tmux session called agent
# result = container.exec_run("/bin/sh -c 'tmux new-session -d -s agent'")
# print(result.output.decode('utf-8'))

# run frotz in the tmux session
# result = container.exec_run("/bin/sh -c 'tmux send-keys -t agent \"cd frotz && ./frotz zork1.z5\" C-m'")

# check if tmux session is running
# result = container.exec_run("/bin/sh -c 'tmux ls'")
# print(result.output.decode('utf-8'))


# # capture the pane of the tmux session and print


# # send keys to the tmux session
# result = container.exec_run("/bin/sh -c 'tmux send-keys -t agent \"look\" C-m'")
# print(result.output.decode('utf-8'))

# # capture the pane of the tmux session and print
# result = container.exec_run("/bin/sh -c 'tmux capture-pane -t agent -p'")
# print(result.output.decode('utf-8'))

# # send keys q to the tmux session to quit the game
# result = container.exec_run("/bin/sh -c 'tmux send-keys -t agent \"Y\" C-m'")
# print(result.output.decode('utf-8'))



# # send keys to agent session to create a new tmux session called windows
command = "/bin/sh -c 'tmux send-keys -t agent \"tmux new-session -d -s windows\" C-m'"
result = container.exec_run(command, stderr=True, stdout=True)
# print the result of creating a new tmux session
print(result.output.decode('utf-8'))

result = container.exec_run("/bin/sh -c 'tmux capture-pane -t agent -p'")
print(result.output.decode('utf-8'))

# print the list of tmux sessions
result = container.exec_run("/bin/sh -c 'tmux ls'")
print(result.output.decode('utf-8'))
