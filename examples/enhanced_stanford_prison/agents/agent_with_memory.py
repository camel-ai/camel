#!/usr/bin/env python
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
"""Agent with memory for the Enhanced Stanford Prison Experiment."""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.types import RoleType

from examples.enhanced_stanford_prison.config.experiment_config import MetricConfig


class AgentWithMemory:
    """Class that maintains memory and context for an agent in the experiment.
    
    This enhanced agent maintains a history of conversations, psychological metrics,
    and can provide context for new interactions based on past experiences.
    """
    
    def __init__(
        self, 
        role_name: str, 
        agent_id: str, 
        model: Any, 
        personality_traits: Optional[Dict[str, float]] = None,
        logger: Optional[logging.Logger] = None,
        metrics_config: Optional[Dict[str, MetricConfig]] = None,
    ):
        """Initialize an agent with memory.
        
        Args:
            role_name: Name of the agent's role (e.g., "Prison Guard", "Prisoner")
            agent_id: Unique identifier for the agent
            model: Language model to use for the agent
            personality_traits: Dictionary of personality traits and their values
            logger: Logger for the agent
            metrics_config: Configuration for psychological metrics
        """
        self.role_name = role_name
        self.agent_id = agent_id
        self.model = model
        self.conversation_history = []
        self.personality_traits = personality_traits or {}
        self.self_assessments = []
        self.logger = logger
        self.metrics_config = metrics_config or {}
        
        # Initialize metrics tracking
        self.psychological_metrics = {}
        if metrics_config:
            self.psychological_metrics = {metric: [] for metric in metrics_config}
        
        self.day_metrics = {}
        self.chat_agent = None
        
        if logger:
            logger.info(f"Initialized {role_name} agent with ID {agent_id}")
            if personality_traits:
                traits_str = ", ".join([f"{k}: {v:.1f}" for k, v in personality_traits.items()])
                logger.info(f"Agent {agent_id} personality traits: {traits_str}")
    
    def initialize_chat_agent(self, system_message: str) -> ChatAgent:
        """Initialize a chat agent for this agent.
        
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
    
    def get_context_for_day(
        self, 
        day: int, 
        max_history_items: int = 5,
        include_self_assessments: bool = True,
    ) -> str:
        """Get relevant context from previous conversations.
        
        Args:
            day: Current day of the experiment
            max_history_items: Maximum number of previous conversations to include
            include_self_assessments: Whether to include self-assessments in the context
            
        Returns:
            Context string for the agent
        """
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
                if isinstance(turn, dict):
                    # Handle group interactions
                    if "group_interaction" in turn and turn["group_interaction"]:
                        if "content" in turn:
                            if self.role_name == "Prison Guard":
                                if "guard_id" in turn and turn["guard_id"] == self.agent_id:
                                    context += f"You said: {turn['content']}\n"
                                else:
                                    context += f"Guard #{turn['guard_id']} said: {turn['content']}\n"
                            else:  # Prisoner
                                if "prisoner_id" in turn and turn["prisoner_id"] == self.agent_id:
                                    context += f"You said: {turn['content']}\n"
                                else:
                                    context += f"Prisoner #{turn['prisoner_id']} said: {turn['content']}\n"
                    # Handle one-on-one interactions
                    elif "guard" in turn and "prisoner" in turn:
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
                    if self.metrics_config and metric in self.metrics_config:
                        context += f"- {self.metrics_config[metric].description}: {value}/10\n"
                    else:
                        context += f"- {metric}: {value}/10\n"
                context += "\n"
        
        # Add self-assessments if available
        if include_self_assessments and self.self_assessments:
            context += "Your self-assessments:\n"
            # Get self-assessments from previous days
            previous_assessments = [a for a in self.self_assessments if a["day"] < day]
            # Sort by recency - most recent first
            previous_assessments.sort(key=lambda x: x["day"], reverse=True)
            # Take the most recent assessments
            recent_assessments = previous_assessments[:3]
            
            for assessment in reversed(recent_assessments):
                context += f"Day {assessment['day']} self-assessment:\n{assessment['content']}\n\n"
        
        return context
    
    def add_conversation(
        self, 
        day: int, 
        conversation: List[Dict], 
        metrics: Dict[str, float],
        is_group_interaction: bool = False,
    ):
        """Add a conversation to the agent's memory.
        
        Args:
            day: Day of the experiment
            conversation: List of conversation turns
            metrics: Dictionary of psychological metrics
            is_group_interaction: Whether this was a group interaction
        """
        self.conversation_history.append({
            "day": day,
            "conversation": conversation,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
            "is_group_interaction": is_group_interaction,
        })
        
        # Update the day metrics
        if day not in self.day_metrics:
            self.day_metrics[day] = {}
            
        for metric, value in metrics.items():
            self.day_metrics[day][metric] = value
            if metric in self.psychological_metrics:
                self.psychological_metrics[metric].append((day, value))
        
        if self.logger:
            metrics_str = ", ".join([f"{k}: {v:.1f}" for k, v in metrics.items()])
            self.logger.info(
                f"Added conversation for {self.role_name} {self.agent_id} on day {day}. "
                f"Metrics: {metrics_str}"
            )
    
    def add_self_assessment(self, day: int, assessment_content: str, metrics: Dict[str, float]):
        """Add a self-assessment to the agent's memory.
        
        Args:
            day: Day of the experiment
            assessment_content: Content of the self-assessment
            metrics: Dictionary of psychological metrics from the self-assessment
        """
        self.self_assessments.append({
            "day": day,
            "content": assessment_content,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Update metrics with self-assessment data
        if day not in self.day_metrics:
            self.day_metrics[day] = {}
            
        for metric, value in metrics.items():
            # Average with existing metrics if available
            if metric in self.day_metrics[day]:
                self.day_metrics[day][metric] = (self.day_metrics[day][metric] + value) / 2
            else:
                self.day_metrics[day][metric] = value
            
            if metric in self.psychological_metrics:
                self.psychological_metrics[metric].append((day, value))
        
        if self.logger:
            self.logger.info(
                f"Added self-assessment for {self.role_name} {self.agent_id} on day {day}"
            )
    
    def get_personality_description(self) -> str:
        """Get a description of the agent's personality.
        
        Returns:
            String description of personality traits
        """
        if not self.personality_traits:
            return ""
            
        return " ".join([f"{trait}: {value:.1f}/10" for trait, value in self.personality_traits.items()])
    
    def get_metrics_for_day(self, day: int) -> Dict[str, float]:
        """Get psychological metrics for a specific day.
        
        Args:
            day: Day of the experiment
            
        Returns:
            Dictionary of metrics for the day
        """
        return self.day_metrics.get(day, {})
    
    def get_metric_history(self, metric: str) -> List[Tuple[int, float]]:
        """Get the history of a specific metric.
        
        Args:
            metric: Name of the metric
            
        Returns:
            List of (day, value) tuples for the metric
        """
        return self.psychological_metrics.get(metric, [])

    async def process_message_async(self, message: BaseMessage, context: Optional[Dict] = None) -> BaseMessage:
        """Process a message asynchronously and generate a response.
        
        Args:
            message: Message to process
            context: Additional context for processing the message
            
        Returns:
            Response message
        """
        if not self.chat_agent:
            raise ValueError(f"Chat agent not initialized for {self.role_name} {self.agent_id}")
        
        try:
            # Log incoming message
            if self.logger:
                self.logger.debug(
                    f"{self.role_name} {self.agent_id} received message: {message.content[:100]}..."
                )
            
            # Add context from memory if available
            if context and "day" in context:
                memory_context = self.get_context_for_day(context["day"])
                if memory_context:
                    context["memory"] = memory_context
                    if self.logger:
                        self.logger.debug(f"Added memory context for {self.role_name} {self.agent_id}")
            
            # Get response from chat agent
            response = await self.chat_agent.astep(message)
            
            # Log response
            if self.logger:
                self.logger.debug(
                    f"{self.role_name} {self.agent_id} responded: {response.msg.content[:100]}..."
                )
            
            return response.msg
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error processing message for {self.role_name} {self.agent_id}: {str(e)}")
            
            # Create a fallback response if there's an error
            from camel.messages import BaseMessage
            fallback_content = (
                f"I apologize, but I'm experiencing some confusion as {self.role_name} {self.agent_id}. "
                f"Could you please clarify or repeat what you just said?"
            )
            return BaseMessage(
                role_name=self.role_name,
                role_type=RoleType.ASSISTANT,
                meta_dict=None,
                content=fallback_content
            )

    async def generate_initial_message_async(self, recipient: str) -> BaseMessage:
        """Generate an initial message asynchronously.
        
        Args:
            recipient: The recipient of the message.
            
        Returns:
            The initial message.
        """
        try:
            if not self.chat_agent:
                raise ValueError(f"Chat agent not initialized for {self.role_name} {self.agent_id}")
            
            # Generate a prompt based on the role
            if "guard" in self.role_name.lower():
                prompt = (
                    f"You are a guard in the Stanford Prison Experiment. "
                    f"Generate an initial message to prisoner {recipient}. "
                    f"This should reflect your role as an authority figure. "
                    f"Keep it under 100 words."
                )
            else:
                prompt = (
                    f"You are a prisoner in the Stanford Prison Experiment. "
                    f"Generate an initial message to guard {recipient}. "
                    f"This should reflect your position as a prisoner. "
                    f"Keep it under 100 words."
                )
            
            # Get response from the chat agent
            from camel.messages import BaseMessage
            from camel.types import RoleType
            response = await self.chat_agent.astep(BaseMessage(
                role_name="user",
                role_type=RoleType.USER,
                meta_dict=None,
                content=prompt
            ))
            
            return response.msg
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error generating initial message for {self.role_name} {self.agent_id}: {str(e)}")
            
            # Create a fallback response if there's an error
            from camel.messages import BaseMessage
            from camel.types import RoleType
            fallback_content = (
                f"Hello, this is {self.role_name} {self.agent_id}. "
                f"I'm here to communicate with you."
            )
            return BaseMessage(
                role_name=self.role_name,
                role_type=RoleType.ASSISTANT,
                meta_dict=None,
                content=fallback_content
            )

    async def update_memory_async(self, interaction: Dict) -> None:
        """Update memory with an interaction asynchronously.
        
        Args:
            interaction: Interaction to add to memory
        """
        try:
            if "day" not in interaction:
                # Default to day 1 if not specified
                day = 1
                if self.logger:
                    self.logger.warning(f"No day specified for interaction. Defaulting to day {day}.")
            else:
                day = interaction.get("day", 1)
            
            # Extract metrics from the interaction if available
            if "metrics" in interaction:
                metrics = interaction["metrics"]
            else:
                # Use empty metrics if not available
                metrics = {}
                if self.logger:
                    self.logger.warning(f"No metrics found in interaction for {self.role_name} {self.agent_id}.")
            
            # Extract conversation from the interaction
            if "conversation" in interaction:
                conversation = interaction["conversation"]
            elif "messages" in interaction:
                conversation = interaction["messages"]
            else:
                # Use empty conversation if not available
                conversation = []
                if self.logger:
                    self.logger.warning(f"No conversation found in interaction for {self.role_name} {self.agent_id}.")
            
            # Determine if it's a group interaction
            is_group = interaction.get("type", "") == "group"
            
            # Add the conversation to memory
            self.add_conversation(
                day=day,
                conversation=conversation,
                metrics=metrics,
                is_group_interaction=is_group
            )
            
            if self.logger:
                self.logger.info(
                    f"Updated memory for {self.role_name} {self.agent_id} with interaction from day {day}"
                )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error updating memory for {self.role_name} {self.agent_id}: {str(e)}")

    async def perform_self_assessment_async(self, day: int = None) -> Dict[str, float]:
        """Perform a self-assessment asynchronously.
        
        Args:
            day: The day for which to perform the self-assessment.
            
        Returns:
            A dictionary of metrics.
        """
        if day is None:
            if not self.conversation_history:
                day = 1
            else:
                # Find the maximum day in conversation_history
                day = max([conv.get("day", 1) for conv in self.conversation_history])
            
        try:
            prompt = self._generate_self_assessment_prompt(day)
            
            # Use BaseMessage instead of HumanMessage
            from camel.messages import BaseMessage
            from camel.types import RoleType
            response = await self.chat_agent.astep(BaseMessage(
                role_name="user",
                role_type=RoleType.USER,
                meta_dict=None,
                content=prompt
            ))
            
            # Extract metrics from the self-assessment
            # This would typically be done by a metrics extractor
            # For now, we'll just return a placeholder
            metrics = {"self_assessment_completed": 1.0}
            
            # Add the self-assessment to memory
            self.add_self_assessment(day, response.msg.content, metrics)
            
            return metrics
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error performing self-assessment for {self.role_name} {self.agent_id}: {str(e)}")
            return {"error": 1.0}

    async def add_self_assessment_async(
        self, 
        day: int, 
        assessment_content: str, 
        metrics: Dict[str, float]
    ) -> None:
        """Add a self-assessment asynchronously.
        
        Args:
            day: Day of the experiment
            assessment_content: Content of the self-assessment
            metrics: Dictionary of psychological metrics
        """
        # For now, this is the same as the sync version since memory updates are local
        # But in the future, this could be modified to handle async database operations
        self.add_self_assessment(day, assessment_content, metrics)

    def _generate_self_assessment_prompt(self, day: int) -> str:
        """Generate a prompt for self-assessment.
        
        Args:
            day: The day for which to generate the self-assessment prompt.
            
        Returns:
            The self-assessment prompt.
        """
        # Get the self-assessment prompt based on role
        if "guard" in self.role_name.lower():
            prompt = (
                "As a guard in the Stanford Prison Experiment, please assess your current psychological state. "
                "Rate yourself on these aspects (0-10 scale):\n"
                "1. Authority (How much authority do you feel you have?)\n"
                "2. Power (How powerful do you feel?)\n"
                "3. Empathy (How much empathy do you feel for prisoners?)\n"
                "4. Stress (How stressed are you?)\n"
                "5. Moral conflict (Do you feel any moral conflict about your actions?)\n"
                "For each rating, briefly explain your reasoning."
            )
        else:
            prompt = (
                "As a prisoner in the Stanford Prison Experiment, please assess your current psychological state. "
                "Rate yourself on these aspects (0-10 scale):\n"
                "1. Compliance (How compliant are you with guard demands?)\n"
                "2. Resistance (How much do you resist guard authority?)\n"
                "3. Anxiety (How anxious do you feel?)\n"
                "4. Identity (How much do you still feel like your true self?)\n"
                "5. Solidarity (How connected do you feel to other prisoners?)\n"
                "For each rating, briefly explain your reasoning."
            )
        
        # Get the context for the self-assessment
        context = self.get_context_for_day(day)
        if context:
            prompt += f"\n\nBelow is context from your previous interactions to help with your assessment:\n{context}"
        
        return prompt 