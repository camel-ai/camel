#!/usr/bin/env python
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
"""Observer agent for the Enhanced Stanford Prison Experiment."""

import logging
from typing import Dict, List, Optional, Any, Tuple
import json
import os
import re
from datetime import datetime

from camel.agents import ChatAgent
from camel.messages import BaseMessage


class ObserverAgent:
    """Observer agent for the Enhanced Stanford Prison Experiment.
    
    This agent observes the experiment and provides analysis, ethical evaluations,
    and can extract metrics from conversations.
    """
    
    def __init__(
        self,
        model: Any,
        role: str = "Psychologist Observer",
        logger: Optional[logging.Logger] = None,
        output_dir: str = "enhanced_stanford_prison_results",
    ):
        """Initialize an observer agent.
        
        Args:
            model: Language model to use for the agent
            role: Role of the observer (e.g., "Psychologist Observer", "Ethics Monitor")
            logger: Logger for the agent
            output_dir: Directory to save analysis results
        """
        self.model = model
        self.role = role
        self.logger = logger
        self.output_dir = output_dir
        self.observations = {}
        self.chat_agent = None
        
        if logger:
            logger.info(f"Initialized {role} observer agent")
    
    def initialize_chat_agent(self, system_message: str) -> ChatAgent:
        """Initialize a chat agent for this observer.
        
        Args:
            system_message: System message for the chat agent
            
        Returns:
            Initialized chat agent
        """
        self.chat_agent = ChatAgent(
            system_message=system_message,
            model=self.model,
        )
        return self.chat_agent
    
    def add_observation(self, day: int, observation_type: str, content: Dict):
        """Add an observation to the observer's records.
        
        Args:
            day: Day of the experiment
            observation_type: Type of observation (e.g., "message_analysis")
            content: Content of the observation
        """
        if day not in self.observations:
            self.observations[day] = {}
            
        if observation_type not in self.observations[day]:
            self.observations[day][observation_type] = []
            
        self.observations[day][observation_type].append({
            "timestamp": datetime.now().isoformat(),
            "content": content
        })
        
        if self.logger:
            self.logger.info(f"Added {observation_type} observation for day {day}")
            
    def get_interaction_notes(self) -> str:
        """Get interaction notes.
        
        Returns:
            String containing interaction notes
        """
        notes = "Observer's notes on interactions:\n\n"
        
        for day, day_observations in sorted(self.observations.items()):
            notes += f"Day {day}:\n"
            
            for obs_type, observations in day_observations.items():
                notes += f"  {obs_type.replace('_', ' ').title()}:\n"
                
                for i, obs in enumerate(observations[-3:], 1):  # Only include the last 3 observations
                    if isinstance(obs["content"], dict) and "notes" in obs["content"]:
                        notes += f"    {i}. {obs['content']['notes'][:200]}...\n"
                    elif isinstance(obs["content"], str):
                        notes += f"    {i}. {obs['content'][:200]}...\n"
                    else:
                        notes += f"    {i}. [Complex observation data]\n"
                        
            notes += "\n"
            
        return notes
    
    def extract_metrics_from_conversation(
        self, 
        conversation: List[Dict], 
        metrics_config: Dict,
        day: int,
        guard_id: str,
        prisoner_id: str,
    ) -> Dict[str, float]:
        """Extract psychological metrics from a conversation.
        
        Instead of using regex patterns directly, this method asks the observer
        to analyze the conversation and provide explicit ratings for each metric.
        
        Args:
            conversation: List of conversation turns
            metrics_config: Dictionary of MetricConfig objects
            day: Day of the experiment
            guard_id: ID of the guard in the conversation
            prisoner_id: ID of the prisoner in the conversation
            
        Returns:
            Dictionary of extracted metrics
        """
        if not self.chat_agent:
            system_message = (
                f"You are a {self.role} observing the Stanford Prison Experiment. "
                "Your task is to analyze conversations between guards and prisoners "
                "and extract psychological metrics based on their interactions. "
                "For each metric, provide a rating on a scale of 0-10 and a brief "
                "justification for your rating."
            )
            self.initialize_chat_agent(system_message)
        
        # Prepare the conversation text
        conversation_text = ""
        for turn in conversation:
            if isinstance(turn, dict):
                if "guard" in turn and "prisoner" in turn:
                    conversation_text += f"Guard: {turn['guard']}\n"
                    conversation_text += f"Prisoner: {turn['prisoner']}\n\n"
                elif "content" in turn and "role" in turn:
                    conversation_text += f"{turn['role']}: {turn['content']}\n\n"
        
        # Create the prompt for metric extraction
        metrics_prompt = (
            f"Please analyze the following conversation from Day {day} of the Stanford "
            f"Prison Experiment between Guard #{guard_id} and Prisoner #{prisoner_id}.\n\n"
            f"CONVERSATION:\n{conversation_text}\n\n"
            "Based on this conversation, rate each of the following psychological metrics "
            "on a scale of 0-10, where 0 is the lowest and 10 is the highest. "
            "For each metric, provide a brief justification for your rating.\n\n"
        )
        
        for metric_name, metric_config in metrics_config.items():
            metrics_prompt += f"- {metric_config.description} (0-10): \n"
        
        metrics_prompt += (
            "\nProvide your response in the following format for each metric:\n"
            "METRIC_NAME: RATING\n"
            "JUSTIFICATION: Brief explanation\n\n"
            "For example:\n"
            "authority_compliance: 7\n"
            "JUSTIFICATION: The prisoner showed high compliance with most guard commands...\n"
        )
        
        # Get response from the observer
        response = self.chat_agent.generate_response(metrics_prompt)
        
        # Extract metrics from the response
        metrics = {}
        for metric_name, metric_config in metrics_config.items():
            # Look for the metric in the response
            matches = re.findall(metric_config.pattern, response.msg.content.lower())
            
            if matches:
                # Take the first match
                metrics[metric_name] = float(matches[0])
            else:
                # If no match, look for the metric name in a more flexible way
                for line in response.msg.content.lower().split('\n'):
                    if metric_name.lower() in line and ':' in line:
                        # Try to extract a number from this line
                        number_matches = re.findall(r'(\d+)', line)
                        if number_matches:
                            metrics[metric_name] = float(number_matches[0])
                            break
        
        # For any missing metrics, assign a default value
        for metric_name, metric_config in metrics_config.items():
            if metric_name not in metrics:
                # Use the midpoint of the scale as default
                default_value = (metric_config.scale[0] + metric_config.scale[1]) / 2
                metrics[metric_name] = default_value
                
                if self.logger:
                    self.logger.warning(
                        f"Could not extract {metric_name} from conversation. Using default value {default_value}."
                    )
        
        # Save the full analysis for reference
        analysis_dir = os.path.join(self.output_dir, "analysis")
        if not os.path.exists(analysis_dir):
            os.makedirs(analysis_dir)
            
        analysis_file = os.path.join(
            analysis_dir, 
            f"metrics_analysis_day{day}_{guard_id}_{prisoner_id}.txt"
        )
        
        with open(analysis_file, "w") as f:
            f.write(f"METRICS ANALYSIS FOR DAY {day}\n")
            f.write(f"Guard: {guard_id}, Prisoner: {prisoner_id}\n\n")
            f.write("OBSERVER RESPONSE:\n")
            f.write(response.msg.content)
            f.write("\n\nEXTRACTED METRICS:\n")
            for metric_name, value in metrics.items():
                f.write(f"{metric_name}: {value}\n")
        
        return metrics
    
    def perform_ethics_check(
        self,
        day: int,
        all_interactions: List[Dict],
        all_metrics: Dict[str, Dict[str, float]],
    ) -> Tuple[bool, str, Dict[str, float]]:
        """Perform an ethics check for the experiment.
        
        Args:
            day: Current day of the experiment
            all_interactions: All interactions from the current day
            all_metrics: All metrics from the current day
            
        Returns:
            Tuple of (should_continue, reason, ethics_metrics)
        """
        if not self.chat_agent:
            system_message = (
                f"You are an Ethics Monitor for the Stanford Prison Experiment. "
                "Your task is to evaluate the ethical implications of the experiment "
                "based on the interactions and psychological metrics of participants. "
                "You should determine if the experiment should continue or be terminated "
                "due to ethical concerns."
            )
            self.initialize_chat_agent(system_message)
        
        # Prepare the summary of interactions
        interactions_summary = ""
        for interaction in all_interactions:
            guard_id = interaction.get("guard_id", "unknown")
            prisoner_id = interaction.get("prisoner_id", "unknown")
            
            interactions_summary += f"Interaction between Guard #{guard_id} and Prisoner #{prisoner_id}:\n"
            
            # Add a summary of the conversation
            conversation = interaction.get("conversation", [])
            for turn in conversation:
                if isinstance(turn, dict) and "guard" in turn and "prisoner" in turn:
                    # Just include a brief excerpt to save space
                    guard_excerpt = turn["guard"][:100] + "..." if len(turn["guard"]) > 100 else turn["guard"]
                    prisoner_excerpt = turn["prisoner"][:100] + "..." if len(turn["prisoner"]) > 100 else turn["prisoner"]
                    
                    interactions_summary += f"Guard: {guard_excerpt}\n"
                    interactions_summary += f"Prisoner: {prisoner_excerpt}\n"
            
            interactions_summary += "\n"
        
        # Prepare metrics summary
        metrics_summary = "Psychological Metrics Summary:\n"
        for agent_id, metrics in all_metrics.items():
            metrics_summary += f"Agent {agent_id}:\n"
            for metric, value in metrics.items():
                metrics_summary += f"- {metric}: {value:.1f}/10\n"
            metrics_summary += "\n"
        
        # Create the prompt for ethics evaluation
        ethics_prompt = (
            f"Please evaluate the ethical implications of the Stanford Prison Experiment "
            f"on Day {day}. Review the following information and determine if the experiment "
            f"should continue or be terminated due to ethical concerns.\n\n"
            f"DAY {day} SUMMARY:\n{interactions_summary}\n\n"
            f"METRICS SUMMARY:\n{metrics_summary}\n\n"
            "Based on this information, please provide:\n"
            "1. An ethical assessment of the current state of the experiment\n"
            "2. A clear recommendation on whether the experiment should continue or be terminated\n"
            "3. A rating for each of the following ethical concerns on a scale of 0-10:\n"
            "   - Psychological harm (0-10)\n"
            "   - Dehumanization (0-10)\n"
            "   - Power abuse (0-10)\n"
            "   - Informed consent violations (0-10)\n"
            "   - Overall ethical concern level (0-10)\n\n"
            "Format your response as follows:\n"
            "ASSESSMENT: Your ethical assessment\n"
            "RECOMMENDATION: [CONTINUE/TERMINATE]\n"
            "REASON: Brief explanation for your recommendation\n"
            "RATINGS:\n"
            "psychological_harm: X\n"
            "dehumanization: X\n"
            "power_abuse: X\n"
            "consent_violations: X\n"
            "overall_concern: X"
        )
        
        # Get response from the observer
        response = self.chat_agent.generate_response(ethics_prompt)
        
        # Extract recommendation and ratings
        should_continue = True
        reason = ""
        ethics_metrics = {}
        
        # Check for termination recommendation
        if "RECOMMENDATION: TERMINATE" in response.msg.content:
            should_continue = False
            
        # Extract reason
        reason_match = re.search(r"REASON: (.*?)(?:\n|$)", response.msg.content)
        if reason_match:
            reason = reason_match.group(1).strip()
        
        # Extract ratings
        metrics_to_extract = [
            "psychological_harm", 
            "dehumanization", 
            "power_abuse", 
            "consent_violations", 
            "overall_concern"
        ]
        
        for metric in metrics_to_extract:
            pattern = f"{metric}: (\\d+)"
            matches = re.findall(pattern, response.msg.content.lower())
            
            if matches:
                ethics_metrics[metric] = float(matches[0])
            else:
                # Default value
                ethics_metrics[metric] = 5.0
        
        # Save the ethics check
        analysis_dir = os.path.join(self.output_dir, "analysis")
        if not os.path.exists(analysis_dir):
            os.makedirs(analysis_dir)
            
        ethics_file = os.path.join(analysis_dir, f"ethics_check_day{day}.txt")
        
        with open(ethics_file, "w") as f:
            f.write(f"ETHICS CHECK FOR DAY {day}\n\n")
            f.write("OBSERVER RESPONSE:\n")
            f.write(response.msg.content)
            f.write("\n\nEXTRACTED DECISION:\n")
            f.write(f"Should continue: {should_continue}\n")
            f.write(f"Reason: {reason}\n")
            f.write("Ethics metrics:\n")
            for metric, value in ethics_metrics.items():
                f.write(f"- {metric}: {value}\n")
        
        # Add to observations
        self.add_observation(day, "ethics_check", {
            "should_continue": should_continue,
            "reason": reason,
            "metrics": ethics_metrics,
            "full_response": response.msg.content,
        })
        
        return should_continue, reason, ethics_metrics
    
    def generate_final_analysis(
        self,
        experiment_summary: str,
        experiment_days: int,
        all_agents_data: Dict,
        all_interactions: List[Dict],
        all_ethics_checks: List[Dict],
    ) -> str:
        """Generate a comprehensive final analysis of the experiment.
        
        Args:
            experiment_summary: Summary of the experiment
            experiment_days: Number of days the experiment ran
            all_agents_data: Data for all agents
            all_interactions: All interactions from the experiment
            all_ethics_checks: All ethics checks from the experiment
            
        Returns:
            Final analysis text
        """
        if not self.chat_agent:
            system_message = (
                f"You are a {self.role} analyzing the results of the Stanford Prison Experiment. "
                "Your task is to provide a comprehensive psychological analysis of the experiment, "
                "including individual psychological changes, group dynamics, ethical implications, "
                "and comparisons to the real Stanford Prison Experiment."
            )
            self.initialize_chat_agent(system_message)
        
        # Create the prompt for final analysis
        analysis_prompt = (
            "Please provide a comprehensive psychological analysis of the Enhanced Stanford "
            f"Prison Experiment that was conducted over {experiment_days} days. "
            "Your analysis should be structured into the following sections:\n\n"
            "1. EXECUTIVE SUMMARY: Brief overview of key findings\n"
            "2. INDIVIDUAL PSYCHOLOGICAL CHANGES: Analysis of how individual guards and prisoners changed over time\n"
            "3. GROUP DYNAMICS: Analysis of power structures and group behavior patterns\n"
            "4. ETHICAL IMPLICATIONS: Discussion of ethical issues that arose during the experiment\n"
            "5. COMPARISON TO ORIGINAL EXPERIMENT: Similarities and differences to Zimbardo's original study\n"
            "6. METHODOLOGICAL CONSIDERATIONS: Strengths and limitations of this simulation approach\n"
            "7. RECOMMENDATIONS: Suggestions for future research or applications\n\n"
            f"Here is a summary of the experiment:\n\n{experiment_summary}\n\n"
            "Please provide your analysis with specific examples from the interactions to support your points. "
            "Your analysis should be evidence-based, psychologically informed, and critically reflective."
        )
        
        # Get response from the observer
        response = self.chat_agent.generate_response(analysis_prompt)
        
        # Save the analysis
        analysis_dir = os.path.join(self.output_dir, "analysis")
        if not os.path.exists(analysis_dir):
            os.makedirs(analysis_dir)
            
        analysis_file = os.path.join(analysis_dir, "final_psychological_analysis.txt")
        
        with open(analysis_file, "w") as f:
            f.write("ENHANCED STANFORD PRISON EXPERIMENT\n")
            f.write("FINAL PSYCHOLOGICAL ANALYSIS\n\n")
            f.write(response.msg.content)
        
        # Also save as JSON with metadata
        json_file = os.path.join(analysis_dir, "final_psychological_analysis.json")
        analysis_data = {
            "experiment_days": experiment_days,
            "analysis": response.msg.content,
            "observer_role": self.role,
        }
        
        with open(json_file, "w") as f:
            json.dump(analysis_data, f, indent=2)
        
        return response.msg.content

    async def analyze_message_async(self, message: BaseMessage, context: Dict) -> Dict:
        """Analyze a message asynchronously and extract relevant metrics.
        
        Args:
            message: Message to analyze
            context: Context information for the message
            
        Returns:
            Dictionary containing analysis results
        """
        # Extract required parameters from context
        metrics_config = context.get("metrics_config", {})
        day = context.get("day", 0)
        guard_id = context.get("guard_id")
        prisoner_id = context.get("prisoner_id")
        
        if not all([metrics_config, guard_id, prisoner_id]):
            if self.logger:
                self.logger.warning("Missing required parameters for metrics extraction")
                missing = []
                if not metrics_config:
                    missing.append("metrics_config")
                if not guard_id:
                    missing.append("guard_id")
                if not prisoner_id:
                    missing.append("prisoner_id")
                self.logger.warning(f"Missing parameters: {', '.join(missing)}")
            return {}
        
        # Prepare the message properly based on its type
        conversation = []
        if hasattr(message, 'to_dict'):
            msg_dict = message.to_dict()
            # Ensure we have a consistent format
            if "content" in msg_dict:
                conversation.append(msg_dict)
            else:
                # Create a structured message with content
                conversation.append({
                    "role": msg_dict.get("role", "speaker"),
                    "content": str(message)
                })
        else:
            # Handle any non-standard message format
            conversation.append({
                "role": context.get("speaker_role", "speaker"),
                "content": str(message)
            })
        
        # Extract metrics from the conversation
        try:
            metrics = await self.extract_metrics_from_conversation_async(
                conversation=conversation,
                metrics_config=metrics_config,
                day=day,
                guard_id=guard_id,
                prisoner_id=prisoner_id
            )
            
            # Add observation
            self.add_observation(
                day=day,
                observation_type="message_analysis",
                content={
                    "message": conversation[0],
                    "metrics": metrics,
                    "context": {
                        "guard_id": guard_id,
                        "prisoner_id": prisoner_id
                    }
                }
            )
            
            return metrics
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error extracting metrics: {str(e)}")
            return {}

    async def extract_metrics_from_conversation_async(
        self, 
        conversation: List[Dict], 
        metrics_config: Dict,
        day: int,
        guard_id: str,
        prisoner_id: str,
    ) -> Dict[str, float]:
        """Extract psychological metrics from a conversation asynchronously.
        
        Instead of using regex patterns directly, this method asks the observer
        to analyze the conversation and provide explicit ratings for each metric.
        
        Args:
            conversation: List of conversation turns
            metrics_config: Dictionary of MetricConfig objects
            day: Day of the experiment
            guard_id: ID of the guard in the conversation
            prisoner_id: ID of the prisoner in the conversation
            
        Returns:
            Dictionary of extracted metrics
        """
        if not self.chat_agent:
            system_message = (
                f"You are a {self.role} observing the Stanford Prison Experiment. "
                "Your task is to analyze conversations between guards and prisoners "
                "and extract psychological metrics based on their interactions. "
                "For each metric, provide a rating on a scale of 0-10 and a brief "
                "justification for your rating."
            )
            self.initialize_chat_agent(system_message)
        
        # Prepare the conversation text
        conversation_text = ""
        for turn in conversation:
            if isinstance(turn, dict):
                if "guard" in turn and "prisoner" in turn:
                    conversation_text += f"Guard: {turn['guard']}\n"
                    conversation_text += f"Prisoner: {turn['prisoner']}\n\n"
                elif "content" in turn and "role" in turn:
                    conversation_text += f"{turn['role']}: {turn['content']}\n\n"
                elif "content" in turn:
                    conversation_text += f"{turn.get('role', 'Speaker')}: {turn['content']}\n\n"
        
        # Create the prompt for metric extraction with clearer instructions
        metrics_prompt = (
            f"Please analyze the following conversation from Day {day} of the Stanford "
            f"Prison Experiment between Guard #{guard_id} and Prisoner #{prisoner_id}.\n\n"
            f"CONVERSATION:\n{conversation_text}\n\n"
            "Based on this conversation, rate each of the following psychological metrics "
            "on a scale of 0-10, where 0 is the lowest and 10 is the highest. "
            "For each metric, provide a brief justification for your rating.\n\n"
            "IMPORTANT: You must follow this exact format for each metric:\n"
            "METRIC_NAME: RATING (just the number)\n"
            "JUSTIFICATION: Brief explanation\n\n"
            "For example:\n"
            "power_abuse: 7\n"
            "JUSTIFICATION: The guard showed high levels of power abuse by threatening...\n\n"
            "Make sure to use the exact metric name as provided below and include a space after the colon.\n\n"
            "METRICS TO RATE:\n"
        )
        
        # Add each metric with clear formatting instructions
        for metric_name, metric_config in metrics_config.items():
            metrics_prompt += f"- {metric_name}: Provide a rating for {metric_config.description}\n"
        
        # Get response from the observer
        response = await self.chat_agent.astep(metrics_prompt)
        
        # Extract metrics from the response
        metrics = {}
        for metric_name, metric_config in metrics_config.items():
            # First try to find an exact match with the standard format
            exact_pattern = rf"{metric_name}:\s*(\d+)"
            exact_matches = re.findall(exact_pattern, response.msg.content.lower())
            
            if exact_matches:
                # Use the exact match
                metrics[metric_name] = float(exact_matches[0])
            else:
                # Try the configurable pattern
                matches = re.findall(metric_config.pattern, response.msg.content.lower())
                
                if matches and isinstance(matches[0], tuple) and len(matches[0]) > 1:
                    # Get the second item which should be the number
                    metrics[metric_name] = float(matches[0][1])
                elif matches and not isinstance(matches[0], tuple):
                    # Direct match
                    metrics[metric_name] = float(matches[0])
                else:
                    # If no match, look for the metric name in a more flexible way
                    for line in response.msg.content.lower().split('\n'):
                        if metric_name.lower().replace('_', ' ') in line and ':' in line:
                            # Try to extract a number from this line
                            number_matches = re.findall(r'(\d+)', line)
                            if number_matches:
                                metrics[metric_name] = float(number_matches[0])
                                break
        
        # For any missing metrics, assign a default value
        for metric_name, metric_config in metrics_config.items():
            if metric_name not in metrics:
                # Use the midpoint of the scale as default
                default_value = (metric_config.scale[0] + metric_config.scale[1]) / 2
                metrics[metric_name] = default_value
                
                if self.logger:
                    self.logger.warning(
                        f"Could not extract {metric_name} from conversation. Using default value {default_value}."
                    )
        
        # Save the full analysis for reference
        analysis_dir = os.path.join(self.output_dir, "analysis")
        if not os.path.exists(analysis_dir):
            os.makedirs(analysis_dir)
            
        analysis_file = os.path.join(
            analysis_dir, 
            f"metrics_analysis_day{day}_{guard_id}_{prisoner_id}.txt"
        )
        
        with open(analysis_file, "w") as f:
            f.write(f"METRICS ANALYSIS FOR DAY {day}\n")
            f.write(f"Guard: {guard_id}, Prisoner: {prisoner_id}\n\n")
            f.write("OBSERVER RESPONSE:\n")
            f.write(response.msg.content)
            f.write("\n\nEXTRACTED METRICS:\n")
            for metric_name, value in metrics.items():
                f.write(f"{metric_name}: {value}\n")
        
        return metrics

    async def perform_ethics_check_async(
        self,
        day: int,
        all_interactions: List[Dict],
        all_metrics: Dict[str, Dict[str, float]],
    ) -> Tuple[bool, str, Dict[str, float]]:
        """Perform an ethics check asynchronously.
        
        Args:
            day: Current day of the experiment
            all_interactions: All interactions from the current day
            all_metrics: All metrics from the current day
            
        Returns:
            Tuple of (should_continue, reason, ethics_metrics)
        """
        if not self.chat_agent:
            system_message = (
                f"You are an Ethics Monitor for the Stanford Prison Experiment. "
                "Your task is to evaluate the ethical implications of the experiment "
                "based on the interactions and psychological metrics of participants. "
                "You should determine if the experiment should continue or be terminated "
                "due to ethical concerns."
            )
            self.initialize_chat_agent(system_message)
        
        # Prepare the summary of interactions
        interactions_summary = ""
        for interaction in all_interactions:
            guard_id = interaction.get("guard_id", "unknown")
            prisoner_id = interaction.get("prisoner_id", "unknown")
            
            interactions_summary += f"Interaction between Guard #{guard_id} and Prisoner #{prisoner_id}:\n"
            
            # Add a summary of the conversation
            conversation = interaction.get("conversation", [])
            for turn in conversation:
                if isinstance(turn, dict) and "guard" in turn and "prisoner" in turn:
                    # Just include a brief excerpt to save space
                    guard_excerpt = turn["guard"][:100] + "..." if len(turn["guard"]) > 100 else turn["guard"]
                    prisoner_excerpt = turn["prisoner"][:100] + "..." if len(turn["prisoner"]) > 100 else turn["prisoner"]
                    
                    interactions_summary += f"Guard: {guard_excerpt}\n"
                    interactions_summary += f"Prisoner: {prisoner_excerpt}\n"
            
            interactions_summary += "\n"
        
        # Prepare metrics summary
        metrics_summary = "Psychological Metrics Summary:\n"
        for agent_id, metrics in all_metrics.items():
            metrics_summary += f"Agent {agent_id}:\n"
            for metric, value in metrics.items():
                metrics_summary += f"- {metric}: {value:.1f}/10\n"
            metrics_summary += "\n"
        
        # Create the prompt for ethics evaluation
        ethics_prompt = (
            f"Please evaluate the ethical implications of the Stanford Prison Experiment "
            f"on Day {day}. Review the following information and determine if the experiment "
            f"should continue or be terminated due to ethical concerns.\n\n"
            f"DAY {day} SUMMARY:\n{interactions_summary}\n\n"
            f"METRICS SUMMARY:\n{metrics_summary}\n\n"
            "Based on this information, please provide:\n"
            "1. An ethical assessment of the current state of the experiment\n"
            "2. A clear recommendation on whether the experiment should continue or be terminated\n"
            "3. A rating for each of the following ethical concerns on a scale of 0-10:\n"
            "   - Psychological harm (0-10)\n"
            "   - Dehumanization (0-10)\n"
            "   - Power abuse (0-10)\n"
            "   - Informed consent violations (0-10)\n"
            "   - Overall ethical concern level (0-10)\n\n"
            "Format your response as follows:\n"
            "ASSESSMENT: Your ethical assessment\n"
            "RECOMMENDATION: [CONTINUE/TERMINATE]\n"
            "REASON: Brief explanation for your recommendation\n"
            "RATINGS:\n"
            "psychological_harm: X\n"
            "dehumanization: X\n"
            "power_abuse: X\n"
            "consent_violations: X\n"
            "overall_concern: X"
        )
        
        # Get response from the observer
        response = await self.chat_agent.astep(ethics_prompt)
        
        # Extract recommendation and ratings
        should_continue = True
        reason = ""
        ethics_metrics = {}
        
        # Check for termination recommendation
        if "RECOMMENDATION: TERMINATE" in response.msg.content:
            should_continue = False
            
        # Extract reason
        reason_match = re.search(r"REASON: (.*?)(?:\n|$)", response.msg.content)
        if reason_match:
            reason = reason_match.group(1).strip()
        
        # Extract ratings
        metrics_to_extract = [
            "psychological_harm", 
            "dehumanization", 
            "power_abuse", 
            "consent_violations", 
            "overall_concern"
        ]
        
        for metric in metrics_to_extract:
            pattern = f"{metric}: (\\d+)"
            matches = re.findall(pattern, response.msg.content.lower())
            
            if matches:
                ethics_metrics[metric] = float(matches[0])
            else:
                # Default value
                ethics_metrics[metric] = 5.0
        
        # Save the ethics check
        analysis_dir = os.path.join(self.output_dir, "analysis")
        if not os.path.exists(analysis_dir):
            os.makedirs(analysis_dir)
            
        ethics_file = os.path.join(analysis_dir, f"ethics_check_day{day}.txt")
        
        with open(ethics_file, "w") as f:
            f.write(f"ETHICS CHECK FOR DAY {day}\n\n")
            f.write("OBSERVER RESPONSE:\n")
            f.write(response.msg.content)
            f.write("\n\nEXTRACTED DECISION:\n")
            f.write(f"Should continue: {should_continue}\n")
            f.write(f"Reason: {reason}\n")
            f.write("Ethics metrics:\n")
            for metric, value in ethics_metrics.items():
                f.write(f"- {metric}: {value}\n")
        
        # Add to observations
        self.add_observation(day, "ethics_check", {
            "should_continue": should_continue,
            "reason": reason,
            "metrics": ethics_metrics,
            "full_response": response.msg.content,
        })
        
        return should_continue, reason, ethics_metrics

    async def get_interaction_notes_async(self) -> str:
        """Get interaction notes asynchronously.
        
        Returns:
            String containing interaction notes
        """
        # For now, this is the same as the sync version since notes are stored locally
        # But in the future, this could be modified to handle async database operations
        return self.get_interaction_notes() 