#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interactions module for the Enhanced Stanford Prison Experiment.
Handles both one-on-one and group interactions between guards and prisoners.
"""

import random
from typing import Dict, List, Tuple
import logging
from datetime import datetime

from camel.messages import BaseMessage

from .agents.agent_with_memory import AgentWithMemory
from .agents.observer_agent import ObserverAgent

class InteractionManager:
    """Manages interactions between guards and prisoners."""
    
    def __init__(
        self,
        interaction_config: Dict,
        observer: ObserverAgent,
        logger: logging.Logger
    ):
        """Initialize the interaction manager.
        
        Args:
            interaction_config: Full experiment configuration
            observer: Observer agent for monitoring interactions
            logger: Logger instance
        """
        self.config = interaction_config
        self.interactions_config = interaction_config.get("interactions", {})
        
        # Process metrics configuration
        from .config.experiment_config import create_metrics_config
        self.metrics_config = create_metrics_config(interaction_config.get("metrics", {}))
        
        self.observer = observer
        self.logger = logger
        self.max_turns = self.interactions_config.get("max_turns", 15)
        self.min_turns = self.interactions_config.get("min_turns", 5)

    def run_one_on_one_interaction(
        self,
        guard: AgentWithMemory,
        prisoner: AgentWithMemory
    ) -> Dict:
        """Run a one-on-one interaction between a guard and prisoner.
        
        Args:
            guard: Guard agent
            prisoner: Prisoner agent
            
        Returns:
            Dictionary containing interaction details and messages
        """
        messages: List[BaseMessage] = []
        start_time = datetime.now()
        
        # Initial message from guard
        guard_msg = guard.generate_initial_message(prisoner.agent_id)
        messages.append(guard_msg)
        
        # Conversation loop
        for turn in range(self.max_turns):
            # Prisoner response
            prisoner_msg = prisoner.process_message(guard_msg)
            messages.append(prisoner_msg)
            
            # Observer analysis after prisoner's message
            self.observer.analyze_message(prisoner_msg, context={
                "turn": turn,
                "speaker_role": "prisoner",
                "speaker_name": prisoner.agent_id
            })
            
            # Check if conversation should end
            if self._should_end_conversation(messages):
                break
                
            # Guard response
            guard_msg = guard.process_message(prisoner_msg)
            messages.append(guard_msg)
            
            # Observer analysis after guard's message
            self.observer.analyze_message(guard_msg, context={
                "turn": turn,
                "speaker_role": "guard",
                "speaker_name": guard.agent_id
            })
            
            # Check if conversation should end
            if self._should_end_conversation(messages):
                break
        
        # Create interaction record
        interaction_record = {
            "type": "one_on_one",
            "guard": guard.agent_id,
            "prisoner": prisoner.agent_id,
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "num_turns": len(messages),
            "messages": [msg.to_dict() for msg in messages],
            "observer_notes": self.observer.get_interaction_notes()
        }
        
        return interaction_record

    def run_group_interaction(
        self,
        num_guards: int,
        num_prisoners: int
    ) -> Dict:
        """Run a group interaction between multiple guards and prisoners.
        
        Args:
            num_guards: Number of guards to include
            num_prisoners: Number of prisoners to include
            
        Returns:
            Dictionary containing group interaction details
        """
        # Select random participants
        participating_guards = random.sample(list(self.guards.values()), num_guards)
        participating_prisoners = random.sample(list(self.prisoners.values()), num_prisoners)
        
        messages: List[BaseMessage] = []
        start_time = datetime.now()
        
        # Initial group context
        group_context = {
            "interaction_type": "group",
            "participants": {
                "guards": [g.agent_id for g in participating_guards],
                "prisoners": [p.agent_id for p in participating_prisoners]
            }
        }
        
        # Initial message from a random guard
        current_guard = random.choice(participating_guards)
        guard_msg = current_guard.generate_initial_message(
            f"Group of prisoners: {', '.join(p.agent_id for p in participating_prisoners)}"
        )
        messages.append(guard_msg)
        
        # Group conversation loop
        for turn in range(self.max_turns):
            # Random prisoner response
            current_prisoner = random.choice(participating_prisoners)
            prisoner_msg = current_prisoner.process_message(
                guard_msg,
                context=group_context
            )
            messages.append(prisoner_msg)
            
            # Observer analysis
            self.observer.analyze_message(prisoner_msg, context={
                "turn": turn,
                "speaker_role": "prisoner",
                "speaker_name": current_prisoner.agent_id,
                "group_context": group_context
            })
            
            if self._should_end_conversation(messages):
                break
                
            # Random guard response
            current_guard = random.choice(participating_guards)
            guard_msg = current_guard.process_message(
                prisoner_msg,
                context=group_context
            )
            messages.append(guard_msg)
            
            # Observer analysis
            self.observer.analyze_message(guard_msg, context={
                "turn": turn,
                "speaker_role": "guard",
                "speaker_name": current_guard.agent_id,
                "group_context": group_context
            })
            
            if self._should_end_conversation(messages):
                break
        
        # Create group interaction record
        interaction_record = {
            "type": "group",
            "guards": [g.agent_id for g in participating_guards],
            "prisoners": [p.agent_id for p in participating_prisoners],
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "num_turns": len(messages),
            "messages": [msg.to_dict() for msg in messages],
            "observer_notes": self.observer.get_interaction_notes()
        }
        
        return interaction_record

    def _should_end_conversation(self, messages: List[BaseMessage]) -> bool:
        """Determine if a conversation should end based on message content.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Boolean indicating if conversation should end
        """
        if not messages:
            return False
            
        last_message = messages[-1]
        
        # Check for conversation ending indicators
        end_indicators = [
            "goodbye", "end", "stop", "finished",
            "that's all", "we're done", "dismissed"
        ]
        
        return any(indicator in last_message.content.lower() 
                  for indicator in end_indicators)

    async def run_one_on_one_interaction_async(
        self,
        guard: AgentWithMemory,
        prisoner: AgentWithMemory
    ) -> Dict:
        """Run a one-on-one interaction between a guard and prisoner asynchronously.
        
        Args:
            guard: Guard agent
            prisoner: Prisoner agent
            
        Returns:
            Dictionary containing interaction details and messages
        """
        messages: List[BaseMessage] = []
        start_time = datetime.now()
        
        # Initial message from guard
        guard_msg = await guard.generate_initial_message_async(prisoner.agent_id)
        messages.append(guard_msg)
        
        # Conversation loop
        for turn in range(self.max_turns):
            # Prisoner response
            prisoner_msg = await prisoner.process_message_async(guard_msg)
            messages.append(prisoner_msg)
            
            # Observer analysis after prisoner's message
            await self.observer.analyze_message_async(prisoner_msg, context={
                "turn": turn,
                "speaker_role": "prisoner",
                "speaker_name": prisoner.agent_id,
                "metrics_config": self.metrics_config,
                "day": self.config.get("current_day", 0),
                "guard_id": guard.agent_id,
                "prisoner_id": prisoner.agent_id
            })
            
            # Check if conversation should end
            if self._should_end_conversation(messages):
                break
                
            # Guard response
            guard_msg = await guard.process_message_async(prisoner_msg)
            messages.append(guard_msg)
            
            # Observer analysis after guard's message
            await self.observer.analyze_message_async(guard_msg, context={
                "turn": turn,
                "speaker_role": "guard",
                "speaker_name": guard.agent_id,
                "metrics_config": self.metrics_config,
                "day": self.config.get("current_day", 0),
                "guard_id": guard.agent_id,
                "prisoner_id": prisoner.agent_id
            })
            
            # Check if conversation should end
            if self._should_end_conversation(messages):
                break
        
        # Create interaction record
        interaction_record = {
            "type": "one_on_one",
            "guard": guard.agent_id,
            "prisoner": prisoner.agent_id,
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "num_turns": len(messages),
            "messages": [msg.to_dict() for msg in messages],
            "observer_notes": await self.observer.get_interaction_notes_async()
        }
        
        return interaction_record

    async def run_group_interaction_async(
        self,
        guards: Dict[str, AgentWithMemory],
        prisoners: Dict[str, AgentWithMemory]
    ) -> Dict:
        """Run a group interaction between multiple guards and prisoners asynchronously.
        
        Args:
            guards: Dictionary of guard agents
            prisoners: Dictionary of prisoner agents
            
        Returns:
            Dictionary containing group interaction details
        """
        num_guards = self.interactions_config.get("group_interaction_guards", 2)
        num_prisoners = self.interactions_config.get("group_interaction_prisoners", 3)
        
        # Ensure we have enough participants
        num_guards = min(num_guards, len(guards))
        num_prisoners = min(num_prisoners, len(prisoners))
        
        if num_guards == 0 or num_prisoners == 0:
            if self.logger:
                self.logger.error(f"Cannot run group interaction with {num_guards} guards and {num_prisoners} prisoners")
            raise ValueError("Not enough participants for group interaction")
        
        # Select random participants
        participating_guards = random.sample(list(guards.values()), num_guards)
        participating_prisoners = random.sample(list(prisoners.values()), num_prisoners)
        
        messages: List[BaseMessage] = []
        start_time = datetime.now()
        
        # Initial group context
        group_context = {
            "interaction_type": "group",
            "participants": {
                "guards": [g.agent_id for g in participating_guards],
                "prisoners": [p.agent_id for p in participating_prisoners]
            }
        }
        
        try:
            # Initial message from a random guard
            current_guard = random.choice(participating_guards)
            guard_msg = await current_guard.generate_initial_message_async(
                f"Group of prisoners: {', '.join(p.agent_id for p in participating_prisoners)}"
            )
            messages.append(guard_msg)
            
            # Group conversation loop
            for turn in range(self.max_turns):
                try:
                    # Random prisoner response
                    current_prisoner = random.choice(participating_prisoners)
                    prisoner_msg = await current_prisoner.process_message_async(
                        guard_msg,
                        context=group_context
                    )
                    messages.append(prisoner_msg)
                    
                    # Observer analysis
                    await self.observer.analyze_message_async(prisoner_msg, context={
                        "turn": turn,
                        "speaker_role": "prisoner",
                        "speaker_name": current_prisoner.agent_id,
                        "metrics_config": self.metrics_config,
                        "day": self.config.get("current_day", 0),
                        "guard_id": current_guard.agent_id,
                        "prisoner_id": current_prisoner.agent_id,
                        "group_context": group_context
                    })
                    
                    if self._should_end_conversation(messages):
                        break
                        
                    # Random guard response
                    current_guard = random.choice(participating_guards)
                    guard_msg = await current_guard.process_message_async(
                        prisoner_msg,
                        context=group_context
                    )
                    messages.append(guard_msg)
                    
                    # Observer analysis
                    await self.observer.analyze_message_async(guard_msg, context={
                        "turn": turn,
                        "speaker_role": "guard",
                        "speaker_name": current_guard.agent_id,
                        "metrics_config": self.metrics_config,
                        "day": self.config.get("current_day", 0),
                        "guard_id": current_guard.agent_id,
                        "prisoner_id": current_prisoner.agent_id,
                        "group_context": group_context
                    })
                    
                    if self._should_end_conversation(messages):
                        break
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Error in group interaction turn {turn}: {str(e)}")
                    # Continue with the next turn if there's an error
                    continue
            
            # Create group interaction record
            interaction_record = {
                "type": "group",
                "guards": [g.agent_id for g in participating_guards],
                "prisoners": [p.agent_id for p in participating_prisoners],
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "num_turns": len(messages),
                "messages": [msg.to_dict() for msg in messages],
                "observer_notes": await self.observer.get_interaction_notes_async()
            }
            
            return interaction_record
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in group interaction: {str(e)}")
            # Return a minimal record in case of error
            return {
                "type": "group",
                "guards": [g.agent_id for g in participating_guards],
                "prisoners": [p.agent_id for p in participating_prisoners],
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "num_turns": len(messages),
                "messages": [msg.to_dict() for msg in messages if hasattr(msg, 'to_dict')],
                "error": str(e)
            } 