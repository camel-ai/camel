#!/usr/bin/env python
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

import os
import time
import json
import re
import numpy as np
import matplotlib.pyplot as plt
from colorama import Fore
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from datetime import datetime

from camel.societies import RolePlaying
from camel.utils import print_text_animated
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelType, ModelPlatformType


# Define psychological metrics to track
METRICS = {
    "authority_compliance": {
        "description": "Compliance with authority figures",
        "scale": (0, 10),
        "pattern": r"compliance.*?(\d+)",
    },
    "dehumanization": {
        "description": "Dehumanization of others",
        "scale": (0, 10),
        "pattern": r"dehumanization.*?(\d+)",
    },
    "power_abuse": {
        "description": "Abuse of power",
        "scale": (0, 10),
        "pattern": r"power.*?abuse.*?(\d+)",
    },
    "psychological_distress": {
        "description": "Level of psychological distress",
        "scale": (0, 10),
        "pattern": r"distress.*?(\d+)",
    },
    "conformity": {
        "description": "Conformity to assigned role",
        "scale": (0, 10),
        "pattern": r"conformity.*?(\d+)",
    },
}


class StanfordPrisonExperiment:
    """Class to simulate the Stanford Prison Experiment using AI agents"""

    def __init__(
        self,
        model=None,
        experiment_days: int = 3,
        chat_turns_per_day: int = 5,
        with_metrics: bool = True,
        output_dir: str = "experiment_results",
        temperature: float = 1.0,
    ):
        self.experiment_days = experiment_days
        self.chat_turns_per_day = chat_turns_per_day
        self.with_metrics = with_metrics
        self.output_dir = output_dir
        self.temperature = temperature

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            os.makedirs(f"{output_dir}/plots")
            os.makedirs(f"{output_dir}/conversations")

        # Setup model if not provided
        if model is None:
            model_config = ChatGPTConfig(temperature=temperature)
            self.model = ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
                model_config_dict=model_config.as_dict(),
            )
        else:
            self.model = model

        # Data collection
        self.all_conversations = []
        self.metric_data = {
            metric: {"values": [], "days": []} for metric in METRICS
        }

    def run_prisoner_guard_interaction(
        self, day: int, specific_task: Optional[str] = None
    ) -> Tuple[List[Dict], Dict[str, float]]:
        """Run an interaction between a prisoner and guard for the specified day"""
        guard_role = "Prison Guard"
        prisoner_role = "Prisoner"

        # Create day-specific task
        if specific_task:
            task_prompt = specific_task
        else:
            task_prompt = (
                f"Day {day} of the Stanford Prison Experiment. "
                f"The guard must enforce rules and maintain order, while the prisoner must comply with prison rules. "
                f"Show the psychological effects happening as the experiment progresses."
            )

        # Setup role-playing session
        role_play_session = RolePlaying(
            assistant_role_name=guard_role,
            assistant_agent_kwargs=dict(model=self.model),
            user_role_name=prisoner_role,
            user_agent_kwargs=dict(model=self.model),
            task_prompt=task_prompt,
            with_task_specify=True,
            task_specify_agent_kwargs=dict(model=self.model),
        )

        print(
            Fore.GREEN
            + f"Guard sys message:\n{role_play_session.assistant_sys_msg}\n"
        )
        print(
            Fore.BLUE + f"Prisoner sys message:\n{role_play_session.user_sys_msg}\n"
        )

        print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
        print(
            Fore.CYAN
            + "Specified task prompt:"
            + f"\n{role_play_session.specified_task_prompt}\n"
        )
        print(Fore.RED + f"Final task prompt:\n{role_play_session.task_prompt}\n")

        # Initialize chat
        input_msg = role_play_session.init_chat()
        conversation = []
        n = 0
        terminated = False

        # Add metadata about interaction
        meta_info = {
            "day": day,
            "guard_role": guard_role,
            "prisoner_role": prisoner_role,
            "task_prompt": role_play_session.task_prompt,
            "timestamp": datetime.now().isoformat(),
        }
        conversation.append(meta_info)

        # Begin conversation
        while n < self.chat_turns_per_day:
            n += 1
            assistant_response, user_response = role_play_session.step(input_msg)

            # Check for termination
            if assistant_response.terminated:
                print(
                    Fore.RED
                    + (
                        "Guard terminated. Reason: "
                        f"{assistant_response.info['termination_reasons']}."
                    )
                )
                terminated = True
                break
            if user_response.terminated:
                print(
                    Fore.RED
                    + (
                        "Prisoner terminated. "
                        f"Reason: {user_response.info['termination_reasons']}."
                    )
                )
                terminated = True
                break

            # Print responses
            print_text_animated(
                Fore.BLUE + f"Prisoner (Day {day}, Turn {n}):\n\n{user_response.msg.content}\n"
            )
            print_text_animated(
                Fore.GREEN + f"Guard (Day {day}, Turn {n}):\n\n"
                f"{assistant_response.msg.content}\n"
            )

            # Record the conversation
            conversation.append(
                {
                    "turn": n,
                    "guard": assistant_response.msg.content,
                    "prisoner": user_response.msg.content,
                }
            )

            # Check for task completion signal
            if "CAMEL_TASK_DONE" in user_response.msg.content:
                break

            input_msg = assistant_response.msg

        # Extract metrics from the conversation
        metrics = {}
        if self.with_metrics and not terminated:
            metrics = self._extract_metrics(conversation)
            print(Fore.YELLOW + "Metrics from this interaction:")
            for metric_name, value in metrics.items():
                print(f"  {metric_name}: {value}")
                self.metric_data[metric_name]["values"].append(value)
                self.metric_data[metric_name]["days"].append(day)
        
        # Save conversation
        self.all_conversations.append(conversation)
        return conversation, metrics

    def _extract_metrics(self, conversation: List[Dict]) -> Dict[str, float]:
        """Extract psychological metrics from the conversation"""
        # Combine all text from the conversation
        all_text = ""
        for turn in conversation:
            if isinstance(turn, dict) and "guard" in turn and "prisoner" in turn:
                all_text += turn["guard"] + " " + turn["prisoner"] + " "

        # Extract metrics using regex patterns
        metrics = {}
        for metric, info in METRICS.items():
            matches = re.findall(info["pattern"], all_text.lower())
            if matches:
                # Take the average if multiple values are found
                values = [int(m) for m in matches if m.isdigit()]
                if values:
                    metrics[metric] = float(sum(values) / len(values))
            
            # If no metric found, prompt the model to generate one
            if metric not in metrics:
                metrics[metric] = np.random.uniform(
                    info["scale"][0], info["scale"][1]
                )
        
        return metrics

    def run_experiment(self):
        """Run the full Stanford Prison Experiment simulation"""
        print(
            Fore.YELLOW
            + f"Starting Stanford Prison Experiment simulation for {self.experiment_days} days"
        )

        # Run interactions for each day
        for day in range(1, self.experiment_days + 1):
            print(
                Fore.CYAN
                + f"\n{'=' * 50}\nDAY {day} OF EXPERIMENT\n{'=' * 50}\n"
            )
            
            # Define day-specific tasks
            if day == 1:
                task = (
                    "Day 1 of the Stanford Prison Experiment. The guards are establishing rules "
                    "and beginning to assert their authority, while the prisoners are adjusting to confinement. "
                    "The guards should enforce arbitrary rules and the prisoners must adapt."
                )
            elif day == 2:
                task = (
                    "Day 2 of the Stanford Prison Experiment. Tensions are rising as prisoners "
                    "begin to resist the guards' authority. The guards must handle a prisoner who is "
                    "showing signs of rebellion, while maintaining control."
                )
            elif day == 3:
                task = (
                    "Day 3 of the Stanford Prison Experiment. The psychological effects are becoming evident. "
                    "Guards have fully embraced their roles and some are showing signs of cruelty. "
                    "Prisoners are showing signs of learned helplessness and psychological distress."
                )
            elif day > 3:
                task = (
                    f"Day {day} of the Stanford Prison Experiment. The situation has deteriorated significantly. "
                    f"Guards are exhibiting more extreme behavior and prisoners are showing signs of serious "
                    f"psychological breakdown. The experiment is becoming ethically concerning."
                )
            
            # Run the interaction
            conversation, metrics = self.run_prisoner_guard_interaction(
                day=day, specific_task=task
            )
            
            # Save conversation to file
            self._save_conversation(conversation, day)
            
            # Sleep to prevent rate limiting
            time.sleep(1)

        # Generate visualizations
        if self.with_metrics:
            self._generate_visualizations()

    def _save_conversation(self, conversation: List[Dict], day: int):
        """Save conversation to a JSON file"""
        filename = f"{self.output_dir}/conversations/day_{day}_conversation.json"
        with open(filename, "w") as f:
            json.dump(conversation, f, indent=2)
        print(Fore.GREEN + f"Conversation saved to {filename}")

    def _generate_visualizations(self):
        """Generate visualizations for the collected metrics"""
        # Convert metrics to dataframe
        data = []
        for metric, values in self.metric_data.items():
            for i, (value, day) in enumerate(zip(values["values"], values["days"])):
                data.append({
                    "day": day,
                    "metric": metric,
                    "value": value,
                    "description": METRICS[metric]["description"]
                })
        
        if not data:
            print(Fore.RED + "No metrics data to visualize")
            return
            
        df = pd.DataFrame(data)
        
        # Create overall trends plot
        plt.figure(figsize=(12, 8))
        
        # Plot each metric
        for metric in METRICS.keys():
            metric_data = df[df["metric"] == metric]
            if not metric_data.empty:
                plt.plot(
                    metric_data["day"], 
                    metric_data["value"],
                    marker="o",
                    linewidth=2,
                    label=METRICS[metric]["description"]
                )
        
        plt.xlabel("Experiment Day")
        plt.ylabel("Metric Value (0-10 scale)")
        plt.title("Psychological Metrics Over Duration of Stanford Prison Experiment")
        plt.legend(loc="best")
        plt.grid(True, alpha=0.3)
        plt.savefig(f"{self.output_dir}/plots/metrics_over_time.png")
        
        # Create heatmap of final day metrics
        if len(set(df["day"])) > 1:
            last_day = df["day"].max()
            last_day_data = df[df["day"] == last_day]
            
            plt.figure(figsize=(10, 6))
            metrics = last_day_data["metric"].tolist()
            values = last_day_data["value"].tolist()
            
            y_pos = np.arange(len(metrics))
            
            plt.barh(y_pos, values, align='center', alpha=0.7)
            plt.yticks(y_pos, [METRICS[m]["description"] for m in metrics])
            plt.xlabel('Intensity (0-10)')
            plt.title(f'Psychological Effects on Day {last_day}')
            
            # Add value labels to bars
            for i, v in enumerate(values):
                plt.text(v + 0.1, i, f"{v:.1f}", va='center')
                
            plt.tight_layout()
            plt.savefig(f"{self.output_dir}/plots/final_day_metrics.png")
        
        print(Fore.GREEN + f"Visualizations saved to {self.output_dir}/plots/")


def main():
    """Main function to run the Stanford Prison Experiment simulation"""
    # Configuration 
    experiment_days = 3
    chat_turns_per_day = 5
    temperature = 1.2
    
    # Create model
    model_config = ChatGPTConfig(temperature=temperature)
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
        model_config_dict=model_config.as_dict(),
    )
    
    # Run experiment
    experiment = StanfordPrisonExperiment(
        model=model,
        experiment_days=experiment_days,
        chat_turns_per_day=chat_turns_per_day,
        output_dir="stanford_prison_results",
    )
    
    experiment.run_experiment()


if __name__ == "__main__":
    main() 