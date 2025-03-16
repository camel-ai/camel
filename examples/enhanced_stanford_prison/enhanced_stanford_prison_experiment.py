#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enhanced Stanford Prison Experiment main module.
This module contains the core experiment class that orchestrates the entire simulation.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import random

from camel.agents import ChatAgent
from camel.messages import BaseMessage

from .config.experiment_config import ExperimentConfig, create_metrics_config
from .agents.agent_with_memory import AgentWithMemory
from .agents.observer_agent import ObserverAgent
from .metrics.metrics_extractor import MetricsExtractor
from .analysis.experiment_summary import ExperimentSummarizer
from .visualization.visualizer import ExperimentVisualizer
from .utils.logging_utils import setup_logger
from .interactions import InteractionManager

class EnhancedStanfordPrisonExperiment:
    """Main class for running the Enhanced Stanford Prison Experiment simulation."""
    
    def __init__(
        self,
        config: Dict,
        output_dir: str,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize the experiment with configuration and setup necessary components.
        
        Args:
            config: Configuration dictionary containing experiment parameters
            output_dir: Directory to store experiment outputs
            logger: Optional logger instance
        """
        self.config = config
        self.output_dir = output_dir
        self.logger = logger or setup_logger(
            name="experiment",
            log_dir=os.path.join(output_dir, "logs"),
            level="INFO"
        )
        
        # Create necessary directories
        os.makedirs(os.path.join(output_dir, "logs"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "data"), exist_ok=True)
        
        # Create metrics configuration
        metrics_config = create_metrics_config(config["metrics"])
        self.metrics_config = metrics_config
        
        # Initialize components
        self.metrics_extractor = MetricsExtractor(
            metrics_config=metrics_config,
            logger=self.logger
        )
        
        # Initialize observer agent
        self.observer = ObserverAgent(
            model=None,  # We'll set this later
            role="Psychologist Observer",
            logger=self.logger,
            output_dir=output_dir
        )
        self.observer.initialize_chat_agent(config["agent_messages"]["observer_system_message"])
        
        # Initialize containers for agents and data
        self.guards: Dict[str, AgentWithMemory] = {}
        self.prisoners: Dict[str, AgentWithMemory] = {}
        self.daily_interactions: List[Dict] = []
        self.daily_metrics: List[Dict] = []
        
        self.experiment_start_time = None
        self.experiment_end_time = None
        self.early_termination = False
        self.termination_reason = None
        
        # Initialize interaction manager
        self.interaction_manager = InteractionManager(
            interaction_config=config,  # Pass the full config
            observer=self.observer,
            logger=self.logger
        )
        
        # Initialize agents
        self.initialize_agents()

    def initialize_agents(self):
        """Initialize guard and prisoner agents with their respective configurations."""
        # Create metrics configuration
        metrics_config = create_metrics_config(self.config["metrics"])
        
        # Initialize guards
        for i in range(self.config["num_guards"]):
            guard_id = f"guard_{i+1}"
            guard = AgentWithMemory(
                role_name="Prison Guard",
                agent_id=guard_id,
                model=None,  # We'll set this during chat agent initialization
                personality_traits=self.config.get("guard_traits", {}),
                logger=self.logger,
                metrics_config=metrics_config
            )
            guard.initialize_chat_agent(self.config["agent_messages"]["guard_system_message"])
            self.guards[guard_id] = guard
            
        # Initialize prisoners
        for i in range(self.config["num_prisoners"]):
            prisoner_id = f"prisoner_{i+1}"
            prisoner = AgentWithMemory(
                role_name="Prisoner",
                agent_id=prisoner_id,
                model=None,  # We'll set this during chat agent initialization
                personality_traits=self.config.get("prisoner_traits", {}),
                logger=self.logger,
                metrics_config=metrics_config
            )
            prisoner.initialize_chat_agent(self.config["agent_messages"]["prisoner_system_message"])
            self.prisoners[prisoner_id] = prisoner
            
        self.logger.info(f"Initialized {len(self.guards)} guards and {len(self.prisoners)} prisoners")

    def check_ethical_boundaries(self, day: int) -> Tuple[bool, Optional[str]]:
        """Check if any ethical boundaries have been crossed.
        
        Args:
            day: Current day of the experiment
        
        Returns:
            Tuple of (should_terminate, reason)
        """
        daily_metrics = self.daily_metrics[day - 1]
        
        # Check abuse of power threshold
        if daily_metrics.get("avg_abuse_of_power", 0) > self.config["ethical_bounds"]["max_abuse_threshold"]:
            return True, "Excessive abuse of power detected"
            
        # Check psychological distress threshold
        if daily_metrics.get("avg_psychological_distress", 0) > self.config["ethical_bounds"]["max_distress_threshold"]:
            return True, "Critical psychological distress levels detected"
            
        return False, None

    def save_experiment_state(self):
        """Save the current state of the experiment to disk."""
        experiment_data = {
            "config": self.config,
            "daily_interactions": self.daily_interactions,
            "daily_metrics": self.daily_metrics,
            "start_time": self.experiment_start_time.isoformat(),
            "end_time": self.experiment_end_time.isoformat() if self.experiment_end_time else None,
            "early_termination": self.early_termination,
            "termination_reason": self.termination_reason
        }
        
        output_path = os.path.join(self.output_dir, "data", "experiment_state.json")
        with open(output_path, "w") as f:
            json.dump(experiment_data, f, indent=2)
        
        self.logger.info(f"Saved experiment state to {output_path}")

    async def run_daily_interactions(self, day: int) -> List[Dict]:
        """Run a day's worth of interactions between guards and prisoners.
        
        Args:
            day: Current day number
            
        Returns:
            List of interaction records
        """
        interactions = []
        
        # Get interaction counts from config
        daily_one_on_one = self.config["interactions"].get("daily_one_on_one", 3)
        daily_group = self.config["interactions"].get("daily_group", 1)
        
        # Run one-on-one interactions
        for _ in range(daily_one_on_one):
            # Randomly select guard and prisoner
            guard = random.choice(list(self.guards.values()))
            prisoner = random.choice(list(self.prisoners.values()))
            
            try:
                # Update the day in the interaction manager's config
                self.interaction_manager.config["current_day"] = day
                
                interaction = await self.interaction_manager.run_one_on_one_interaction_async(
                    guard=guard,
                    prisoner=prisoner
                )
                interactions.append(interaction)
                
                # Update agent memories
                await guard.update_memory_async(interaction)
                await prisoner.update_memory_async(interaction)
                
                # Perform self-assessments
                await guard.perform_self_assessment_async()
                await prisoner.perform_self_assessment_async()
                
            except Exception as e:
                self.logger.error(f"Error in one-on-one interaction: {str(e)}", exc_info=True)
                continue
        
        # Run group interactions
        for _ in range(daily_group):
            try:
                # Update the day in the interaction manager's config
                self.interaction_manager.config["current_day"] = day
                
                # Ensure there are enough guards and prisoners for the group interaction
                min_guards = self.config["interactions"].get("group_interaction_guards", 2)
                min_prisoners = self.config["interactions"].get("group_interaction_prisoners", 3)
                
                if len(self.guards) < min_guards or len(self.prisoners) < min_prisoners:
                    self.logger.warning(
                        f"Not enough agents for group interaction. Need at least {min_guards} guards "
                        f"and {min_prisoners} prisoners. Have {len(self.guards)} guards and "
                        f"{len(self.prisoners)} prisoners."
                    )
                    continue
                
                interaction = await self.interaction_manager.run_group_interaction_async(
                    guards=self.guards,
                    prisoners=self.prisoners
                )
                interactions.append(interaction)
                
                # Update memories for all participants
                for guard_id in interaction["guards"]:
                    if guard_id in self.guards:
                        await self.guards[guard_id].update_memory_async(interaction)
                for prisoner_id in interaction["prisoners"]:
                    if prisoner_id in self.prisoners:
                        await self.prisoners[prisoner_id].update_memory_async(interaction)
                    
                # Perform self-assessments for all participants
                for guard_id in interaction["guards"]:
                    if guard_id in self.guards:
                        await self.guards[guard_id].perform_self_assessment_async()
                for prisoner_id in interaction["prisoners"]:
                    if prisoner_id in self.prisoners:
                        await self.prisoners[prisoner_id].perform_self_assessment_async()
                    
            except Exception as e:
                self.logger.error(f"Error in group interaction: {str(e)}", exc_info=True)
                continue
        
        # Save interactions to file
        self._save_interactions(interactions, day)
        
        return interactions
        
    def _save_interactions(self, interactions: List[Dict], day: int) -> None:
        """Save interactions to a JSON file.
        
        Args:
            interactions: List of interaction records
            day: Current day number
        """
        import json
        import os
        
        # Create data directory if it doesn't exist
        data_dir = os.path.join(self.output_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        # Save interactions to file
        output_file = os.path.join(data_dir, f"day_{day}_interactions.json")
        with open(output_file, "w") as f:
            json.dump(interactions, f, indent=2)

    def calculate_daily_metrics(self, day: int, interactions: List[Dict]) -> Dict:
        """Calculate metrics for a single day based on interactions.
        
        Args:
            day: Current day number
            interactions: List of interaction records
            
        Returns:
            Dictionary of calculated metrics
        """
        metrics = self.metrics_extractor.extract_metrics(interactions)
        
        # Add day-specific information
        metrics["day"] = day
        metrics["total_interactions"] = len(interactions)
        metrics["one_on_one_interactions"] = sum(1 for i in interactions if i["type"] == "one_on_one")
        metrics["group_interactions"] = sum(1 for i in interactions if i["type"] == "group")
        
        # Calculate per-role averages
        guard_metrics = {}
        prisoner_metrics = {}
        
        for metric_name, value in metrics.items():
            if isinstance(value, dict):
                if "guards" in value:
                    guard_metrics[metric_name] = value["guards"]
                if "prisoners" in value:
                    prisoner_metrics[metric_name] = value["prisoners"]
        
        metrics["guard_averages"] = {
            name: sum(values.values()) / len(values) 
            for name, values in guard_metrics.items()
        }
        
        metrics["prisoner_averages"] = {
            name: sum(values.values()) / len(values) 
            for name, values in prisoner_metrics.items()
        }
        
        return metrics

    def check_experiment_health(self) -> bool:
        """Perform a health check on the experiment setup.
        
        This checks that all components are properly initialized and that the
        configuration is valid.
        
        Returns:
            Boolean indicating if the experiment is healthy
        """
        try:
            # Check that required config elements are present
            required_config = [
                "duration_days", "num_guards", "num_prisoners", 
                "interactions", "metrics", "agent_messages"
            ]
            
            missing_config = [key for key in required_config if key not in self.config]
            if missing_config:
                self.logger.error(f"Missing required config keys: {', '.join(missing_config)}")
                return False
            
            # Check that guards and prisoners are initialized
            if not self.guards:
                self.logger.error("No guards initialized")
                return False
                
            if not self.prisoners:
                self.logger.error("No prisoners initialized")
                return False
            
            # Check that the observer is initialized
            if not self.observer:
                self.logger.error("Observer not initialized")
                return False
                
            if not self.observer.chat_agent:
                self.logger.error("Observer chat agent not initialized")
                return False
            
            # Check that the interaction manager is initialized
            if not self.interaction_manager:
                self.logger.error("Interaction manager not initialized")
                return False
            
            # Check that metrics configuration is valid
            if "metrics" not in self.config:
                self.logger.error("No metrics configuration found")
                return False
                
            # Check all agents have chat agents initialized
            for guard_id, guard in self.guards.items():
                if not guard.chat_agent:
                    self.logger.error(f"Guard {guard_id} chat agent not initialized")
                    return False
                    
            for prisoner_id, prisoner in self.prisoners.items():
                if not prisoner.chat_agent:
                    self.logger.error(f"Prisoner {prisoner_id} chat agent not initialized")
                    return False
            
            # All checks passed
            self.logger.info("Experiment health check passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Error in experiment health check: {str(e)}")
            return False

    async def run_experiment(self) -> None:
        """Run the Enhanced Stanford Prison Experiment."""
        self.experiment_start_time = datetime.now()
        self.logger.info("Starting Enhanced Stanford Prison Experiment")
        
        try:
            # Initialize agents and verify experiment health
            self.initialize_agents()
            
            if not self.check_experiment_health():
                self.logger.error("Experiment health check failed. Aborting experiment.")
                self.early_termination = True
                self.termination_reason = "Failed health check"
                self.experiment_end_time = datetime.now()
                return
            
            # Run experiment for specified number of days
            for day in range(1, self.config["duration_days"] + 1):
                self.logger.info(f"Starting day {day}")
                
                # Run interactions and collect metrics
                daily_interactions = await self.run_daily_interactions(day)
                self.daily_interactions.extend(daily_interactions)
                
                # Calculate and store daily metrics
                daily_metrics = self.calculate_daily_metrics(day, daily_interactions)
                self.daily_metrics.append(daily_metrics)
                
                # Check for early termination
                if self._should_terminate_early(daily_metrics):
                    self.early_termination = True
                    self.termination_reason = "Ethical boundaries exceeded"
                    break
                
                # Save experiment state
                self.save_experiment_state()
                
            self.experiment_end_time = datetime.now()
                
        except Exception as e:
            self.logger.error(f"Error running experiment: {str(e)}", exc_info=True)
            self.early_termination = True
            self.termination_reason = f"Error: {str(e)}"
            self.experiment_end_time = datetime.now()

    async def run_daily_interactions_async(self) -> List[Dict]:
        """Run all interactions for a single day asynchronously.
        
        Returns:
            List of interaction records
        """
        daily_interactions = []
        
        # Run one-on-one interactions
        one_on_one_tasks = []
        for guard in self.guards.values():
            for prisoner in self.prisoners.values():
                task = asyncio.create_task(
                    self.interaction_manager.run_one_on_one_interaction_async(
                        guard, prisoner
                    )
                )
                one_on_one_tasks.append(task)
        
        one_on_one_results = await asyncio.gather(*one_on_one_tasks)
        daily_interactions.extend(one_on_one_results)
        
        # Run group interactions
        group_tasks = []
        for _ in range(self.config["interactions"]["daily_group_interactions"]):
            task = asyncio.create_task(
                self.interaction_manager.run_group_interaction_async(
                    self.config["interactions"]["guards_per_group"],
                    self.config["interactions"]["prisoners_per_group"]
                )
            )
            group_tasks.append(task)
        
        group_results = await asyncio.gather(*group_tasks)
        daily_interactions.extend(group_results)
        
        return daily_interactions
    
    async def calculate_daily_metrics_async(
        self,
        interactions: List[Dict]
    ) -> Dict:
        """Calculate metrics for a single day asynchronously.
        
        Args:
            interactions: List of interaction records
            
        Returns:
            Dictionary containing daily metrics
        """
        # Extract metrics from interactions
        interaction_metrics_tasks = []
        for interaction in interactions:
            task = asyncio.create_task(
                self.metrics_extractor.extract_metrics_from_conversation_async(
                    interaction["messages"]
                )
            )
            interaction_metrics_tasks.append(task)
        
        interaction_metrics = await asyncio.gather(*interaction_metrics_tasks)
        
        # Get self-assessments from all agents
        assessment_tasks = []
        for agent in list(self.guards.values()) + list(self.prisoners.values()):
            task = asyncio.create_task(agent.perform_self_assessment_async())
            assessment_tasks.append(task)
        
        assessments = await asyncio.gather(*assessment_tasks)
        
        # Combine metrics
        daily_metrics = {
            "day": self.current_day,
            "timestamp": datetime.now().isoformat(),
            "interaction_metrics": interaction_metrics,
            "self_assessments": {
                assessment["agent"]: assessment["metrics"]
                for assessment in assessments
            }
        }
        
        return daily_metrics
    
    async def run_experiment_async(self):
        """Run the entire experiment asynchronously."""
        self.experiment_start_time = datetime.now()
        self.logger.info("Starting Enhanced Stanford Prison Experiment")
        
        # Save initial configuration
        with open(os.path.join(self.output_dir, "config.json"), "w") as f:
            json.dump(self.config, f, indent=2)
        
        try:
            # Run experiment for specified number of days
            for day in range(self.config["experiment_duration"]):
                self.current_day = day + 1
                self.logger.info(f"Starting Day {self.current_day}")
                
                # Run daily interactions
                interactions = await self.run_daily_interactions_async()
                self.daily_interactions.append(interactions)
                
                # Calculate daily metrics
                metrics = await self.calculate_daily_metrics_async(interactions)
                self.daily_metrics.append(metrics)
                
                # Check ethical boundaries
                should_terminate, reason = self.check_ethical_boundaries(self.current_day)
                if should_terminate:
                    self.early_termination = True
                    self.termination_reason = reason
                    self.logger.warning(f"Experiment terminated early: {reason}")
                    break
                
                # Save daily data
                self._save_daily_data(interactions, metrics)
                
                self.logger.info(f"Completed Day {self.current_day}")
        
        except Exception as e:
            self.logger.error(f"Error during experiment: {str(e)}")
            raise
        
        finally:
            self.experiment_end_time = datetime.now()
            self._finalize_experiment()
    
    def _save_daily_data(self, interactions: List[Dict], metrics: Dict):
        """Save daily interaction and metrics data."""
        day_dir = os.path.join(self.output_dir, "daily_data", f"day_{self.current_day}")
        os.makedirs(day_dir, exist_ok=True)
        
        # Save interactions
        with open(os.path.join(day_dir, "interactions.json"), "w") as f:
            json.dump(interactions, f, indent=2)
        
        # Save metrics
        with open(os.path.join(day_dir, "metrics.json"), "w") as f:
            json.dump(metrics, f, indent=2)
    
    def _finalize_experiment(self):
        """Finalize the experiment by generating summaries and visualizations."""
        # Generate final summary
        self.summarizer = ExperimentSummarizer(
            output_dir=self.output_dir,
            metrics_config=self.metrics_config,
            logger=self.logger
        )
        
        self.summarizer.generate_experiment_summary(
            experiment_days=len(self.daily_metrics),
            all_interactions=self.daily_interactions,
            guards=list(self.guards.values()),
            prisoners=list(self.prisoners.values()),
            ethics_checks=[],  # Add ethics checks if available
            early_termination=self.early_termination,
            termination_reason=self.termination_reason or ""
        )
        
        # Generate visualizations
        self.visualizer = ExperimentVisualizer(
            output_dir=self.output_dir,
            metrics_config=self.metrics_config,
            logger=self.logger
        )
        
        # Create dataframe from interactions and agents
        df = self.visualizer.create_dataframe_from_interactions(self.daily_interactions)
        
        # Generate visualizations
        self.visualizer.plot_metrics_over_time(df)
        self.visualizer.plot_guards_vs_prisoners(df)
        self.visualizer.plot_individual_trends(df)
        self.visualizer.plot_correlation_heatmap(df)
        
        # Generate radar charts for the last day
        if self.daily_metrics:
            last_day = max(m.get("day", 1) for m in self.daily_metrics)
            self.visualizer.plot_radar_charts(df, last_day)
        
        self.logger.info("Experiment completed successfully")

    def _should_terminate_early(self, metrics: Dict) -> bool:
        """Check if the experiment should be terminated early based on metrics.
        
        Args:
            metrics: Dictionary containing daily metrics
            
        Returns:
            Boolean indicating if experiment should be terminated
        """
        # Check abuse of power threshold
        if metrics.get("guard_averages", {}).get("power_abuse", 0) > self.config["ethical_bounds"]["max_abuse_threshold"]:
            self.logger.warning("Terminating experiment due to excessive abuse of power")
            return True
            
        # Check psychological distress threshold
        if metrics.get("prisoner_averages", {}).get("psychological_distress", 0) > self.config["ethical_bounds"]["max_distress_threshold"]:
            self.logger.warning("Terminating experiment due to critical psychological distress levels")
            return True
            
        return False 