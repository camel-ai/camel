# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
import datetime
import sys
import threading
import time
from queue import Queue

from colorama import Fore

from camel.societies import RolePlaying

# Global variables for keyboard input handling
keyboard_input_queue = Queue()
should_exit = threading.Event()
keyboard_listener_active = False
interrupt_printing = threading.Event()
human_interrupt_requested = threading.Event()
original_terminal_settings = None
h_pressed = False
print_lock = threading.Lock()


def print_text_animated(text):
    interrupt_printing.clear()
    try:
        for char in text:
            if interrupt_printing.is_set():
                print(Fore.MAGENTA + "\n[Output interrupted]")
                return
            print(char, end="", flush=True)
            time.sleep(0.01)
    except Exception as e:
        print(Fore.RED + f"\nError during animated printing: {e}")
        print(text)


def start_keyboard_listener():
    global keyboard_listener_active, original_terminal_settings

    if keyboard_listener_active:
        return True

    try:

        def unix_listener():
            print(
                Fore.MAGENTA + "Keyboard listener started. Type 'h' and press "
                "Enter to enter human intervention mode."
            )

            try:
                while not should_exit.is_set():
                    import select

                    readable, _, _ = select.select([sys.stdin], [], [], 0.1)
                    if readable:
                        user_input = sys.stdin.readline().strip()
                        if (
                            user_input == 'h'
                            and not human_interrupt_requested.is_set()
                        ):
                            interrupt_printing.set()
                            human_interrupt_requested.set()
                            print(
                                Fore.MAGENTA
                                + "\n[Human intervention triggered]\n"
                            )
                    time.sleep(0.01)
            except Exception as e:
                print(Fore.RED + f"Keyboard listener error: {e}")

        listener_thread = threading.Thread(target=unix_listener, daemon=True)
        listener_thread.start()
        keyboard_listener_active = True
        return True

    except Exception as e:
        print(Fore.RED + f"Keyboard listener init failed: {e}")
        return False


def stop_keyboard_listener():
    r"""Stop the keyboard listener thread"""
    global keyboard_listener_active
    should_exit.set()
    keyboard_listener_active = False


def clear_keyboard_queue():
    interrupt_printing.clear()
    human_interrupt_requested.clear()


def print_checkpoints(checkpoints):
    r"""Print the list of available checkpoints"""
    print(Fore.YELLOW + "\nAvailable checkpoints:")
    for i, checkpoint in enumerate(checkpoints):
        timestamp = datetime.datetime.fromtimestamp(
            checkpoint["timestamp"]
        ).strftime("%H:%M:%S")
        print(
            f"{i+1}: {checkpoint['name']} (Turn {checkpoint['turn']}, "
            f"Time {timestamp}, User Message: {checkpoint['user_message']})"
        )


def human_intervention_handler(role_play_session):
    r"""Handle the human intervention process"""

    print(Fore.MAGENTA + "\n--- Human Intervention Mode Activated ---")
    print(Fore.MAGENTA + "Preparing to rollback to a historical checkpoint...")

    checkpoints = role_play_session.list_checkpoints()
    print_checkpoints(checkpoints)

    print(Fore.MAGENTA + "Enter checkpoint number to rollback to: ")

    try:
        checkpoint_idx = int(input().strip()) - 1
        if 0 <= checkpoint_idx < len(checkpoints):
            checkpoint_name = checkpoints[checkpoint_idx]["name"]
            success = role_play_session.rollback_to_checkpoint(checkpoint_name)
            if success:
                print(
                    Fore.MAGENTA
                    + f"\nSuccessfully rolled back to checkpoint: "
                    f"{checkpoint_name}"
                )

                print(
                    Fore.MAGENTA
                    + "Enter your new message to replace AI user: "
                )

                human_message = input().strip()

                human_msg = role_play_session.human_intervene(human_message)

                print_text_animated(
                    Fore.RED + f"Human User:\n\n{human_msg.content}\n"
                )

                assistant_response, _ = role_play_session.step(human_msg)

                if assistant_response.terminated:
                    print(
                        Fore.GREEN
                        + (
                            "AI Assistant terminated. Reason: "
                            f"{assistant_response.info['termination_reasons']}."
                        )
                    )
                    return None

                print_text_animated(
                    Fore.GREEN + "AI Assistant:\n\n"
                    f"{assistant_response.msg.content}\n"
                )

                human_interrupt_requested.clear()

                return assistant_response.msg
            else:
                print(Fore.RED + "Rollback failed!")
        else:
            print(Fore.RED + "Invalid checkpoint number!")
    except ValueError:
        print(Fore.RED + "Please enter a valid number!")

    clear_keyboard_queue()

    if keyboard_listener_active:
        try:
            import tty

            fd = sys.stdin.fileno()
            tty.setraw(fd)
        except Exception as e:
            print(Fore.RED + f"Failed to restore keyboard mode: {e}")

    return None


def main(model=None, chat_turn_limit=50) -> None:
    task_prompt = "Develop a trading bot for the stock market"
    role_play_session = RolePlaying(
        assistant_role_name="Python Programmer",
        assistant_agent_kwargs=dict(model=model),
        user_role_name="Stock Trader",
        user_agent_kwargs=dict(model=model),
        task_prompt=task_prompt,
        with_task_specify=True,
        task_specify_agent_kwargs=dict(model=model),
        with_human_on_the_loop=True,
        human_role_name="Human Trader",
    )

    print(
        Fore.GREEN
        + f"AI Assistant sys message:\n{role_play_session.assistant_sys_msg}\n"
    )
    print(
        Fore.BLUE + f"AI User sys message:\n{role_play_session.user_sys_msg}\n"
    )

    print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
    print(
        Fore.CYAN
        + "Specified task prompt:"
        + f"\n{role_play_session.specified_task_prompt}\n"
    )
    print(Fore.RED + f"Final task prompt:\n{role_play_session.task_prompt}\n")

    keyboard_mode = start_keyboard_listener()

    try:
        n = 0
        input_msg = role_play_session.init_chat()

        while n < chat_turn_limit:
            n += 1
            clear_keyboard_queue()

            assistant_response, user_response = role_play_session.step(
                input_msg
            )

            if assistant_response.terminated or user_response.terminated:
                print(Fore.GREEN + "Conversation terminated.")
                break

            print_text_animated(
                Fore.BLUE + f"AI User:\n\n{user_response.msg.content}\n"
            )
            print_text_animated(
                Fore.GREEN
                + f"AI Assistant:\n\n{assistant_response.msg.content}\n"
            )

            if human_interrupt_requested.is_set():
                human_intervention_handler(role_play_session)
                human_interrupt_requested.clear()

            if "CAMEL_TASK_DONE" in user_response.msg.content:
                break

            input_msg = assistant_response.msg

            if keyboard_mode:
                print(
                    Fore.MAGENTA
                    + "Continuing conversation... (press 'h' to intervene "
                    + "at any time)",
                    end="\r",
                )
                sys.stdout.flush()

    finally:
        if keyboard_mode:
            stop_keyboard_listener()


if __name__ == "__main__":
    main()
