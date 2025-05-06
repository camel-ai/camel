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
from queue import Empty, Queue

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


def print_text_animated(text, *args, **kwargs):
    """Interruptible streaming output function that checks for interrupt
    requests during printing"""
    interrupt_printing.clear()

    if keyboard_listener_active:
        for char in text:
            if interrupt_printing.is_set():
                print(Fore.MAGENTA + "[Output interrupted]")
                return

            try:
                while not keyboard_input_queue.empty():
                    key = keyboard_input_queue.get_nowait()
                    if key == 'h':
                        interrupt_printing.set()
                        human_interrupt_requested.set()
                        print(
                            Fore.MAGENTA
                            + "[Output interrupted, entering human "
                            + "intervention mode]"
                        )
                        return
            except Empty:
                pass

            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(0.01)  # Adjust printing speed
    else:
        print_text_animated(text, *args, **kwargs)


def start_keyboard_listener():
    """Start the keyboard listener thread"""
    global keyboard_listener_active, original_terminal_settings, h_pressed

    if keyboard_listener_active:
        return True

    try:
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        original_terminal_settings = termios.tcgetattr(fd)

        def unix_listener():
            """Unix/Mac non-blocking keyboard listener"""
            global h_pressed
            print(
                Fore.MAGENTA
                + "Keyboard listener started, press 'h' to enter human "
                + "intervention mode at any time"
            )

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)

                while not should_exit.is_set():
                    try:
                        if (
                            sys.stdin
                            in select.select([sys.stdin], [], [], 0.1)[0]
                        ):
                            char = sys.stdin.read(1)

                            if (
                                char == 'h'
                                and not human_interrupt_requested.is_set()
                            ):
                                keyboard_input_queue.put(char)
                                termios.tcsetattr(
                                    fd, termios.TCSADRAIN, old_settings
                                )
                                print(
                                    Fore.MAGENTA + "\nKeyboard 'h' detected!"
                                )
                                tty.setraw(fd)
                            elif ord(char) == 3:  # Ctrl+C
                                should_exit.set()
                    except Exception as e:
                        try:
                            termios.tcsetattr(
                                fd, termios.TCSADRAIN, old_settings
                            )
                            print(
                                Fore.RED + f"\nError in keyboard listener: {e}"
                            )
                            tty.setraw(fd)
                        except Exception as terminal_err:
                            print(
                                Fore.RED
                                + f"Terminal reset error: {terminal_err}"
                            )

                    time.sleep(0.01)
            finally:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except Exception as term_err:
                    print(
                        Fore.RED
                        + f"Failed to restore terminal settings: {term_err}"
                    )

        listener_thread = threading.Thread(target=unix_listener)
        listener_thread.daemon = True
        listener_thread.start()
        keyboard_listener_active = True
        return True

    except (ImportError, AttributeError) as e:
        print(
            Fore.MAGENTA + f"Keyboard listener functionality unavailable: {e}"
        )
        print(Fore.MAGENTA + "Using periodic polling instead")
        return False


def stop_keyboard_listener():
    """Stop the keyboard listener thread"""
    global keyboard_listener_active
    should_exit.set()
    keyboard_listener_active = False
    restore_terminal()


def clear_keyboard_queue():
    """Clear the keyboard input queue"""
    global h_pressed

    h_pressed = False

    human_interrupt_requested.clear()
    interrupt_printing.clear()

    while not keyboard_input_queue.empty():
        try:
            keyboard_input_queue.get_nowait()
        except Empty:
            break


def restore_terminal():
    """Restore the terminal to normal state"""
    global original_terminal_settings
    if original_terminal_settings is not None:
        try:
            import termios

            fd = sys.stdin.fileno()
            termios.tcsetattr(
                fd, termios.TCSADRAIN, original_terminal_settings
            )
        except (ImportError, IOError, AttributeError):
            pass


def print_checkpoints(checkpoints):
    """Print the list of available checkpoints"""
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
    """Handle the human intervention process"""
    restore_terminal()

    print(Fore.MAGENTA + "\n--- Human Intervention Mode Activated ---")
    print(Fore.MAGENTA + "Preparing to rollback to a historical checkpoint...")

    checkpoints = role_play_session.list_checkpoints()
    print_checkpoints(checkpoints)

    print(Fore.MAGENTA + "Enter checkpoint number to rollback to: ")
    restore_terminal()

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
                restore_terminal()
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
        with_human_on_the_loop=True,  # Enable human intervention feature
        human_role_name="Human Trader",  # Set human role name
        output_language="zh-CN",
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

            if assistant_response.terminated:
                print(
                    Fore.GREEN
                    + (
                        "AI Assistant terminated. Reason: "
                        f"{assistant_response.info['termination_reasons']}."
                    )
                )
                break
            if user_response.terminated:
                print(
                    Fore.GREEN
                    + (
                        "AI User terminated. "
                        f"Reason: {user_response.info['termination_reasons']}."
                    )
                )
                break

            print_text_animated(
                Fore.BLUE + f"AI User:\n\n{user_response.msg.content}\n"
            )

            if human_interrupt_requested.is_set():
                result = human_intervention_handler(role_play_session)
                if result is not None:
                    input_msg = result
                    if keyboard_mode:
                        try:
                            import tty

                            fd = sys.stdin.fileno()
                            tty.setraw(fd)
                        except Exception as e:
                            print(
                                Fore.RED
                                + f"Failed to restore keyboard mode: {e}"
                            )
                    continue

            print_text_animated(
                Fore.GREEN + "AI Assistant:\n\n"
                f"{assistant_response.msg.content}\n"
            )

            if human_interrupt_requested.is_set():
                result = human_intervention_handler(role_play_session)
                if result is not None:
                    input_msg = result
                    if keyboard_mode:
                        try:
                            import tty

                            fd = sys.stdin.fileno()
                            tty.setraw(fd)
                        except Exception as e:
                            print(
                                Fore.RED
                                + f"Failed to restore keyboard mode: {e}"
                            )
                    continue

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
        restore_terminal()


if __name__ == "__main__":
    main()
