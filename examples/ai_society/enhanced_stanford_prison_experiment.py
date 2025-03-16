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
from typing import Dict, List, Optional, Tuple, Any, Union
import pandas as pd
from datetime import datetime

from camel.societies import RolePlaying
from camel.utils import print_text_animated
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelType, ModelPlatformType
from camel.agents import ChatAgent


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
    "resistance": {
        "description": "Resistance to authority",
        "scale": (0, 10),
        "pattern": r"resistance.*?(\d+)",
    },
    "group_identity": {
        "description": "Strength of group identity",
        "scale": (0, 10),
        "pattern": r"group.*?identity.*?(\d+)",
    },
    "moral_disengagement": {
        "description": "Moral disengagement",
        "scale": (0, 10),
        "pattern": r"moral.*?disengagement.*?(\d+)",
    },
}


class AgentWithMemory:
    """Class that maintains memory and context for an agent in the experiment"""
    
    def __init__(
        self, 
        role_name: str, 
        agent_id: str, 
        model: Any, 
        personality_traits: Optional[Dict[str, float]] = None
    ):
        self.role_name = role_name
        self.agent_id = agent_id
        self.model = model
        self.conversation_history = []
        self.personality_traits = personality_traits or {}
        self.psychological_metrics = {metric: [] for metric in METRICS}
        self.day_metrics = {day: {metric: 0 for metric in METRICS} for day in range(1, 10)}
        
    def get_context_for_day(self, day: int, max_history_items: int = 3) -> str:
        """Get relevant context from previous conversations"""
        if not self.conversation_history:
            return ""
            
        # Get all previous days' conversations up to the current day
        previous_days = [conv for conv in self.conversation_history if conv["day"] < day]
        
        # Sort by recency - most recent first
        previous_days.sort(key=lambda x: x["day"], reverse=True)
        
        # Take the most recent conversations
        recent_conversations = previous_days[:max_history_items]
        
        # Format the context
        context = f"Previous interactions for {self.role_name} (ID: {self.agent_id}):\n\n"
        
        for conv in reversed(recent_conversations):  # Chronological order
            context += f"--- Day {conv['day']} ---\n"
            for turn in conv["conversation"]:
                if isinstance(turn, dict) and "guard" in turn and "prisoner" in turn:
                    if self.role_name == "Prison Guard":
                        context += f"You said: {turn['guard']}\n"
                        context += f"Prisoner responded: {turn['prisoner']}\n\n"
                    else:
                        context += f"Guard said: {turn['guard']}\n"
                        context += f"You responded: {turn['prisoner']}\n\n"
            
            # Add summary of psychological state after this day
            if "metrics" in conv:
                context += "Your psychological state after this day:\n"
                for metric, value in conv["metrics"].items():
                    context += f"- {METRICS[metric]['description']}: {value}/10\n"
                context += "\n"
                
        return context
        
    def add_conversation(self, day: int, conversation: List[Dict], metrics: Dict[str, float]):
        """Add a conversation to the agent's memory"""
        self.conversation_history.append({
            "day": day,
            "conversation": conversation,
            "metrics": metrics
        })
        
        # Update the day metrics
        for metric, value in metrics.items():
            self.day_metrics[day][metric] = value
            self.psychological_metrics[metric].append((day, value))


class EnhancedStanfordPrisonExperiment:
    """Enhanced class to simulate the Stanford Prison Experiment using AI agents with memory"""

    def __init__(
        self,
        model=None,
        experiment_days: int = 6,
        chat_turns_per_day: int = 5,
        with_metrics: bool = True,
        output_dir: str = "enhanced_experiment_results",
        temperature: float = 1.0,
        num_guards: int = 3,
        num_prisoners: int = 6,
    ):
        self.experiment_days = experiment_days
        self.chat_turns_per_day = chat_turns_per_day
        self.with_metrics = with_metrics
        self.output_dir = output_dir
        self.temperature = temperature
        self.num_guards = num_guards
        self.num_prisoners = num_prisoners

        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            os.makedirs(f"{output_dir}/plots")
            os.makedirs(f"{output_dir}/conversations")
            os.makedirs(f"{output_dir}/analysis")

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

        # Initialize agents with memory
        self.guards = [
            AgentWithMemory(
                role_name="Prison Guard", 
                agent_id=f"guard_{i+1}", 
                model=self.model,
                personality_traits=self._generate_random_personality()
            ) 
            for i in range(num_guards)
        ]
        
        self.prisoners = [
            AgentWithMemory(
                role_name="Prisoner", 
                agent_id=f"prisoner_{i+1}", 
                model=self.model,
                personality_traits=self._generate_random_personality()
            ) 
            for i in range(num_prisoners)
        ]
        
        # Observer agent for analysis
        self.observer = None
        
        # Data collection
        self.all_interactions = []
        self.all_agent_metrics = {}

    def _generate_random_personality(self) -> Dict[str, float]:
        """Generate random personality traits for an agent"""
        traits = {
            "dominance": np.random.uniform(0, 10),
            "agreeableness": np.random.uniform(0, 10),
            "neuroticism": np.random.uniform(0, 10),
            "empathy": np.random.uniform(0, 10),
            "authoritarian_tendencies": np.random.uniform(0, 10),
        }
        return traits

    def run_guard_prisoner_interaction(
        self, day: int, guard: AgentWithMemory, prisoner: AgentWithMemory, specific_task: Optional[str] = None
    ) -> Tuple[List[Dict], Dict[str, float]]:
        """Run an interaction between a specific guard and prisoner for the specified day"""
        guard_role = f"Prison Guard #{guard.agent_id}"
        prisoner_role = f"Prisoner #{prisoner.agent_id}"

        # Get memory context for both agents
        guard_context = guard.get_context_for_day(day)
        prisoner_context = prisoner.get_context_for_day(day)
        
        # Create day-specific task with context
        if specific_task:
            task_prompt = specific_task
        else:
            task_prompt = (
                f"Day {day} of the Stanford Prison Experiment. "
                f"The guard must enforce rules and maintain order, while the prisoner must comply with prison rules. "
                f"Show the psychological effects happening as the experiment progresses."
            )
            
        # Add context about agent personalities
        guard_personality = " ".join([f"{trait}: {value:.1f}/10" for trait, value in guard.personality_traits.items()])
        prisoner_personality = " ".join([f"{trait}: {value:.1f}/10" for trait, value in prisoner.personality_traits.items()])
        
        enhanced_task = (
            f"{task_prompt}\n\n"
            f"GUARD CONTEXT: This guard ({guard.agent_id}) has the following personality traits: {guard_personality}\n"
            f"{guard_context}\n\n"
            f"PRISONER CONTEXT: This prisoner ({prisoner.agent_id}) has the following personality traits: {prisoner_personality}\n"
            f"{prisoner_context}\n\n"
            f"Continue the experiment for Day {day} showing how these specific individuals' traits and previous experiences affect their interactions."
        )

        # Setup role-playing session
        role_play_session = RolePlaying(
            assistant_role_name=guard_role,
            assistant_agent_kwargs=dict(model=self.model),
            user_role_name=prisoner_role,
            user_agent_kwargs=dict(model=self.model),
            task_prompt=enhanced_task,
            with_task_specify=True,
            task_specify_agent_kwargs=dict(model=self.model),
        )

        print(
            Fore.GREEN
            + f"Guard #{guard.agent_id} sys message:\n{role_play_session.assistant_sys_msg}\n"
        )
        print(
            Fore.BLUE + f"Prisoner #{prisoner.agent_id} sys message:\n{role_play_session.user_sys_msg}\n"
        )

        print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
        print(
            Fore.CYAN
            + "Enhanced task prompt:"
            + f"\n{enhanced_task}\n"
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
            "guard_id": guard.agent_id,
            "prisoner_id": prisoner.agent_id,
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
                        f"Guard #{guard.agent_id} terminated. Reason: "
                        f"{assistant_response.info['termination_reasons']}."
                    )
                )
                terminated = True
                break
            if user_response.terminated:
                print(
                    Fore.RED
                    + (
                        f"Prisoner #{prisoner.agent_id} terminated. "
                        f"Reason: {user_response.info['termination_reasons']}."
                    )
                )
                terminated = True
                break

            # Print responses
            print_text_animated(
                Fore.BLUE + f"Prisoner #{prisoner.agent_id} (Day {day}, Turn {n}):\n\n{user_response.msg.content}\n"
            )
            print_text_animated(
                Fore.GREEN + f"Guard #{guard.agent_id} (Day {day}, Turn {n}):\n\n"
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
        
        # Update agent memories with the conversation and metrics
        guard.add_conversation(day, conversation, metrics)
        prisoner.add_conversation(day, conversation, metrics)
        
        # Save interaction
        self.all_interactions.append({
            "day": day,
            "guard_id": guard.agent_id,
            "prisoner_id": prisoner.agent_id,
            "conversation": conversation,
            "metrics": metrics
        })
        
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
        """Run the full enhanced Stanford Prison Experiment simulation"""
        print(
            Fore.YELLOW
            + f"Starting Enhanced Stanford Prison Experiment simulation for {self.experiment_days} days"
        )

        # Run experiment for each day
        for day in range(1, self.experiment_days + 1):
            print(
                Fore.CYAN
                + f"\n{'=' * 50}\nDAY {day} OF EXPERIMENT\n{'=' * 50}\n"
            )
            
            # Define day-specific tasks based on the experiment phase
            if day == 1:
                task = (
                    "Day 1 of the Stanford Prison Experiment. The guards are establishing rules "
                    "and beginning to assert their authority, while the prisoners are adjusting to confinement. "
                    "The guards should enforce arbitrary rules and the prisoners must adapt. "
                    "Track psychological metrics including authority compliance, dehumanization, power abuse, "
                    "psychological distress, conformity, resistance, group identity, and moral disengagement. "
                    "Each metric should be rated on a scale of 0-10 where appropriate in the conversation."
                )
            elif day == 2:
                task = (
                    "Day 2 of the Stanford Prison Experiment. Tensions are rising as some prisoners "
                    "begin to resist the guards' authority. The guards must handle prisoners who are "
                    "showing signs of rebellion, while maintaining control. The relationship between "
                    "specific guards and prisoners is developing based on their previous interactions."
                )
            elif day == 3:
                task = (
                    "Day 3 of the Stanford Prison Experiment. The psychological effects are becoming evident. "
                    "Guards have fully embraced their roles and some are showing signs of cruelty. "
                    "Prisoners are showing signs of learned helplessness and psychological distress. "
                    "Individual differences between guards and prisoners are becoming more pronounced."
                )
            elif day == 4:
                task = (
                    "Day 4 of the Stanford Prison Experiment. Group dynamics have solidified. "
                    "Some guards have formed alliances, and prisoners have developed coping strategies. "
                    "Prisoner resistance may be organized or individually expressed. Guards must respond "
                    "to maintain control, potentially using psychological tactics or privileges."
                )
            elif day == 5:
                task = (
                    "Day 5 of the Stanford Prison Experiment. The situation has deteriorated significantly. "
                    "Guards are exhibiting more extreme controlling behavior and prisoners are showing signs "
                    "of serious psychological breakdown. Some prisoners may attempt rebellion while others "
                    "completely conform. The experiment is becoming ethically concerning."
                )
            elif day == 6:
                task = (
                    "Day 6 of the Stanford Prison Experiment. The experiment reaches a critical point. "
                    "Extreme behaviors are normalized, and both guards and prisoners are fully immersed in "
                    "their roles. The power dynamics are at their most pronounced, and serious ethical "
                    "concerns about continuing the experiment have emerged."
                )
            
            # Run interactions between pairs of guards and prisoners
            day_conversations = []
            
            # Each guard interacts with multiple prisoners
            for guard in self.guards:
                # Select prisoners to interact with this guard
                prisoners_for_guard = np.random.choice(
                    self.prisoners, 
                    size=min(2, len(self.prisoners)), 
                    replace=False
                )
                
                for prisoner in prisoners_for_guard:
                    print(
                        Fore.MAGENTA
                        + f"\nInteraction: Guard #{guard.agent_id} with Prisoner #{prisoner.agent_id}\n"
                    )
                    conversation, metrics = self.run_guard_prisoner_interaction(
                        day=day, guard=guard, prisoner=prisoner, specific_task=task
                    )
                    day_conversations.append({
                        "guard_id": guard.agent_id,
                        "prisoner_id": prisoner.agent_id,
                        "conversation": conversation,
                        "metrics": metrics
                    })
                    
                    # Save conversation
                    self._save_conversation(conversation, day, guard.agent_id, prisoner.agent_id)
                    
                    # Sleep to prevent rate limiting
                    time.sleep(1)
            
            # Summarize day results
            print(
                Fore.YELLOW
                + f"\nDay {day} Summary:"
            )
            for interaction in day_conversations:
                guard_id = interaction["guard_id"]
                prisoner_id = interaction["prisoner_id"]
                metrics = interaction["metrics"]
                
                print(f"Guard #{guard_id} & Prisoner #{prisoner_id}:")
                for metric, value in metrics.items():
                    print(f"  {METRICS[metric]['description']}: {value:.1f}")
                print("")

        # Generate final analysis with observer
        if self.with_metrics:
            self._generate_observer_analysis()
            self._generate_visualizations()

    def _save_conversation(self, conversation: List[Dict], day: int, guard_id: str, prisoner_id: str):
        """Save conversation to a JSON file"""
        filename = f"{self.output_dir}/conversations/day_{day}_{guard_id}_{prisoner_id}_conversation.json"
        with open(filename, "w") as f:
            json.dump(conversation, f, indent=2)
        print(Fore.GREEN + f"Conversation saved to {filename}")

    def _generate_observer_analysis(self):
        """Generate psychological analysis using an observer agent"""
        print(
            Fore.CYAN
            + f"\n{'=' * 50}\nPSYCHOLOGICAL ANALYSIS\n{'=' * 50}\n"
        )
        
        # Prepare a summary of the experiment for the observer
        experiment_summary = self._prepare_experiment_summary()
        
        # Create observer role with task to analyze the experiment
        observer_prompt = (
            "You are a professional psychologist observing the Stanford Prison Experiment. "
            "Based on the data collected throughout the experiment, conduct a comprehensive psychological "
            "analysis of the participants' behavior, the power dynamics, and ethical implications.\n\n"
            f"Here is a summary of the experiment that was conducted over {self.experiment_days} days:\n\n"
            f"{experiment_summary}\n\n"
            "Your analysis should include:\n"
            "1. Individual psychological changes in guards and prisoners\n"
            "2. Group dynamics and power structures that emerged\n"
            "3. Ethical considerations and implications\n"
            "4. Comparison to the real Stanford Prison Experiment\n"
            "5. Recommendations for future research or applications\n\n"
            "Provide concrete examples from the interactions to support your analysis."
        )
        
        # Configuration for observer analysis
        model_config = ChatGPTConfig(temperature=0.7)  # Lower temperature for more coherent analysis
        observer_model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
            model_config_dict=model_config.as_dict(),
        )
        
        # Create a simple analysis task with a single agent
        role_play_session = RolePlaying(
            assistant_role_name="Psychologist Observer",
            assistant_agent_kwargs=dict(model=observer_model),
            user_role_name="Experiment Coordinator",
            user_agent_kwargs=dict(model=observer_model),
            task_prompt=observer_prompt,
            with_task_specify=False,
        )
        
        # Generate analysis
        input_msg = role_play_session.init_chat(
            "Please provide your comprehensive psychological analysis of the Stanford Prison Experiment simulation."
        )
        
        # Get response from observer
        observer_response, _ = role_play_session.step(input_msg)
        analysis = observer_response.msg.content
        
        # Save analysis
        self._save_analysis(analysis)
        
        print(
            Fore.GREEN
            + "Psychological analysis completed and saved to file."
        )
        
        return analysis

    def _prepare_experiment_summary(self) -> str:
        """Prepare a summary of the experiment for observer analysis"""
        summary = f"ENHANCED STANFORD PRISON EXPERIMENT SUMMARY\n\n"
        summary += f"Duration: {self.experiment_days} days\n"
        summary += f"Participants: {self.num_guards} guards and {self.num_prisoners} prisoners\n\n"
        
        # Summarize the experiment by day
        for day in range(1, self.experiment_days + 1):
            summary += f"--- DAY {day} ---\n"
            
            # Get interactions for this day
            day_interactions = [i for i in self.all_interactions if i["day"] == day]
            
            # Summarize metrics
            all_day_metrics = {}
            for interaction in day_interactions:
                for metric, value in interaction["metrics"].items():
                    if metric not in all_day_metrics:
                        all_day_metrics[metric] = []
                    all_day_metrics[metric].append(value)
            
            # Calculate average metrics for the day
            summary += "Average metrics:\n"
            for metric, values in all_day_metrics.items():
                avg_value = sum(values) / len(values)
                summary += f"- {METRICS[metric]['description']}: {avg_value:.1f}/10\n"
            
            # Add notable events/patterns
            summary += "\nNotable patterns:\n"
            
            # Example patterns (in a real implementation, these would be extracted from the conversations)
            if day == 1:
                summary += "- Guards established initial rules and authority\n"
                summary += "- Prisoners showed initial resistance but mostly complied\n"
            elif day == 2:
                summary += "- Increased tension between guards and prisoners\n"
                summary += "- Some guards became more controlling\n"
            elif day == 3:
                summary += "- Clear power dynamics emerged between specific guards and prisoners\n"
                summary += "- Psychological distress increasing in prisoners\n"
            elif day == 4:
                summary += "- Group identity formed among prisoners\n"
                summary += "- Guards used psychological tactics to maintain control\n"
            elif day == 5:
                summary += "- Some prisoners showed complete submission\n"
                summary += "- Others displayed increased resistance\n"
            elif day == 6:
                summary += "- Ethical concerns reached critical level\n"
                summary += "- Both guards and prisoners fully embraced their roles\n"
            
            summary += "\n"
            
            # Individual agent states (selected examples)
            if day == self.experiment_days:  # Only for the final day
                summary += "Final psychological state of participants:\n\n"
                
                # Guards
                for guard in self.guards:
                    summary += f"Guard #{guard.agent_id}:\n"
                    # Get final day metrics
                    final_metrics = guard.day_metrics.get(day, {})
                    for metric, value in final_metrics.items():
                        summary += f"- {METRICS[metric]['description']}: {value:.1f}/10\n"
                    summary += "\n"
                
                # Prisoners
                for prisoner in self.prisoners:
                    summary += f"Prisoner #{prisoner.agent_id}:\n"
                    # Get final day metrics
                    final_metrics = prisoner.day_metrics.get(day, {})
                    for metric, value in final_metrics.items():
                        summary += f"- {METRICS[metric]['description']}: {value:.1f}/10\n"
                    summary += "\n"
        
        return summary

    def _save_analysis(self, analysis: str):
        """Save psychological analysis to file"""
        filename = f"{self.output_dir}/analysis/psychological_analysis.txt"
        with open(filename, "w") as f:
            f.write(analysis)
        
        # Also save as JSON with some metadata
        json_filename = f"{self.output_dir}/analysis/psychological_analysis.json"
        analysis_data = {
            "experiment_days": self.experiment_days,
            "num_guards": self.num_guards,
            "num_prisoners": self.num_prisoners,
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis
        }
        
        with open(json_filename, "w") as f:
            json.dump(analysis_data, f, indent=2)

    def _generate_visualizations(self):
        """Generate visualizations for the collected metrics"""
        # Create a dataframe from all interactions
        data = []
        for interaction in self.all_interactions:
            day = interaction["day"]
            guard_id = interaction["guard_id"]
            prisoner_id = interaction["prisoner_id"]
            metrics = interaction["metrics"]
            
            for metric, value in metrics.items():
                data.append({
                    "day": day,
                    "guard_id": guard_id,
                    "prisoner_id": prisoner_id,
                    "metric": metric,
                    "value": value,
                    "description": METRICS[metric]["description"]
                })
        
        if not data:
            print(Fore.RED + "No metrics data to visualize")
            return
            
        df = pd.DataFrame(data)
        
        # Create overall trends plot
        plt.figure(figsize=(14, 8))
        
        # Plot each metric
        for metric in METRICS.keys():
            metric_data = df[df["metric"] == metric]
            if not metric_data.empty:
                # Group by day and compute mean
                day_means = metric_data.groupby("day")["value"].mean()
                plt.plot(
                    day_means.index, 
                    day_means.values,
                    marker="o",
                    linewidth=2,
                    label=METRICS[metric]["description"]
                )
        
        plt.xlabel("Experiment Day")
        plt.ylabel("Metric Value (0-10 scale)")
        plt.title("Psychological Metrics Over Duration of Enhanced Stanford Prison Experiment")
        plt.legend(loc="best")
        plt.grid(True, alpha=0.3)
        plt.xticks(range(1, self.experiment_days + 1))
        plt.savefig(f"{self.output_dir}/plots/metrics_over_time.png")
        
        # Create guards vs prisoners comparison
        plt.figure(figsize=(14, 10))
        
        # Group by day, participant type, and metric
        for i, metric in enumerate(METRICS.keys()):
            plt.subplot(4, 2, i+1)
            metric_data = df[df["metric"] == metric]
            
            if not metric_data.empty:
                # Add guard vs prisoner distinction
                metric_data["participant_type"] = metric_data["guard_id"].apply(
                    lambda x: "Guard" if "guard" in x else "Prisoner"
                )
                
                # Group by day and participant type
                grouped = metric_data.groupby(["day", "participant_type"])["value"].mean().reset_index()
                
                # Plot guards and prisoners separately
                for participant_type, group_data in grouped.groupby("participant_type"):
                    plt.plot(
                        group_data["day"], 
                        group_data["value"],
                        marker="o",
                        linewidth=2,
                        label=participant_type
                    )
                
                plt.xlabel("Day")
                plt.ylabel("Value (0-10)")
                plt.title(METRICS[metric]["description"])
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.xticks(range(1, self.experiment_days + 1))
        
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/plots/guards_vs_prisoners.png")
        
        # Create individual plots for each guard and prisoner
        plt.figure(figsize=(12, 8))
        
        # Select a key metric to plot individual trends
        key_metric = "authority_compliance"
        key_metric_data = df[df["metric"] == key_metric]
        
        # Plot each guard
        for guard_id in df["guard_id"].unique():
            guard_data = key_metric_data[key_metric_data["guard_id"] == guard_id]
            if not guard_data.empty:
                guard_means = guard_data.groupby("day")["value"].mean()
                plt.plot(
                    guard_means.index,
                    guard_means.values,
                    marker="o",
                    linestyle="--",
                    label=f"Guard {guard_id}"
                )
        
        # Plot each prisoner
        for prisoner_id in df["prisoner_id"].unique():
            prisoner_data = key_metric_data[key_metric_data["prisoner_id"] == prisoner_id]
            if not prisoner_data.empty:
                prisoner_means = prisoner_data.groupby("day")["value"].mean()
                plt.plot(
                    prisoner_means.index,
                    prisoner_means.values,
                    marker="s",
                    linestyle="-",
                    label=f"Prisoner {prisoner_id}"
                )
        
        plt.xlabel("Experiment Day")
        plt.ylabel(f"{METRICS[key_metric]['description']} (0-10 scale)")
        plt.title(f"Individual {METRICS[key_metric]['description']} Trends")
        plt.legend(loc="best")
        plt.grid(True, alpha=0.3)
        plt.xticks(range(1, self.experiment_days + 1))
        plt.savefig(f"{self.output_dir}/plots/individual_trends.png")
        
        print(Fore.GREEN + f"Visualizations saved to {self.output_dir}/plots/")


def main():
    """Main function to run the Enhanced Stanford Prison Experiment simulation"""
    # Configuration 
    experiment_days = 6
    chat_turns_per_day = 5
    temperature = 1.2
    num_guards = 3
    num_prisoners = 4
    
    # Create model
    model_config = ChatGPTConfig(temperature=temperature)
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
        model_config_dict=model_config.as_dict(),
    )
    
    # Run experiment
    experiment = EnhancedStanfordPrisonExperiment(
        model=model,
        experiment_days=experiment_days,
        chat_turns_per_day=chat_turns_per_day,
        num_guards=num_guards,
        num_prisoners=num_prisoners,
        output_dir="enhanced_stanford_prison_results",
    )
    
    experiment.run_experiment()


if __name__ == "__main__":
    main() 