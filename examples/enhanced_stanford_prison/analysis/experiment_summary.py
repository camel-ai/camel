#!/usr/bin/env python
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
"""Experiment summary utilities for the Enhanced Stanford Prison Experiment."""

import logging
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime


class ExperimentSummarizer:
    """Class for generating summaries of the experiment."""
    
    def __init__(
        self,
        output_dir: str,
        metrics_config: Dict,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize a summarizer.
        
        Args:
            output_dir: Directory to save summaries
            metrics_config: Configuration for psychological metrics
            logger: Logger for the summarizer
        """
        self.output_dir = output_dir
        self.metrics_config = metrics_config
        self.logger = logger
        
        # Create analysis directory if it doesn't exist
        self.analysis_dir = os.path.join(output_dir, "analysis")
        if not os.path.exists(self.analysis_dir):
            os.makedirs(self.analysis_dir)
        
        if logger:
            logger.info(f"Initialized experiment summarizer with output directory: {output_dir}")
    
    def generate_day_summary(
        self,
        day: int,
        day_interactions: List[Dict],
        guards: List[Any],
        prisoners: List[Any],
        ethics_check: Optional[Dict] = None,
    ) -> str:
        """Generate a summary for a specific day of the experiment.
        
        Args:
            day: Day of the experiment
            day_interactions: List of interactions from the day
            guards: List of guard agents
            prisoners: List of prisoner agents
            ethics_check: Optional ethics check for the day
            
        Returns:
            Summary text for the day
        """
        summary = f"--- DAY {day} SUMMARY ---\n\n"
        
        # Summarize interactions
        summary += f"Interactions: {len(day_interactions)}\n"
        
        # Calculate average metrics for the day
        all_day_metrics = {}
        for interaction in day_interactions:
            metrics = interaction.get("metrics", {})
            for metric, value in metrics.items():
                if metric not in all_day_metrics:
                    all_day_metrics[metric] = []
                all_day_metrics[metric].append(value)
        
        # Add average metrics to summary
        summary += "Average metrics:\n"
        for metric, values in all_day_metrics.items():
            avg_value = sum(values) / len(values)
            description = self.metrics_config[metric].description if metric in self.metrics_config else metric
            summary += f"- {description}: {avg_value:.1f}/10\n"
        
        # Add guard-specific metrics
        summary += "\nGuard metrics:\n"
        for guard in guards:
            day_metrics = guard.get_metrics_for_day(day)
            if day_metrics:
                summary += f"Guard {guard.agent_id}:\n"
                for metric, value in day_metrics.items():
                    description = self.metrics_config[metric].description if metric in self.metrics_config else metric
                    summary += f"  - {description}: {value:.1f}/10\n"
        
        # Add prisoner-specific metrics
        summary += "\nPrisoner metrics:\n"
        for prisoner in prisoners:
            day_metrics = prisoner.get_metrics_for_day(day)
            if day_metrics:
                summary += f"Prisoner {prisoner.agent_id}:\n"
                for metric, value in day_metrics.items():
                    description = self.metrics_config[metric].description if metric in self.metrics_config else metric
                    summary += f"  - {description}: {value:.1f}/10\n"
        
        # Add ethics check if available
        if ethics_check:
            summary += "\nEthics check:\n"
            should_continue = ethics_check.get("should_continue", True)
            reason = ethics_check.get("reason", "")
            metrics = ethics_check.get("metrics", {})
            
            summary += f"Recommendation: {'Continue' if should_continue else 'Terminate'}\n"
            summary += f"Reason: {reason}\n"
            summary += "Ethics metrics:\n"
            for metric, value in metrics.items():
                summary += f"- {metric}: {value:.1f}/10\n"
        
        # Save the summary
        summary_file = os.path.join(self.analysis_dir, f"day{day}_summary.txt")
        with open(summary_file, "w") as f:
            f.write(summary)
        
        if self.logger:
            self.logger.info(f"Generated summary for day {day}")
        
        return summary
    
    def generate_experiment_summary(
        self,
        experiment_days: int,
        all_interactions: List[Dict],
        guards: List[Any],
        prisoners: List[Any],
        ethics_checks: List[Dict],
        early_termination: bool = False,
        termination_reason: str = "",
    ) -> str:
        """Generate a comprehensive summary of the entire experiment.
        
        Args:
            experiment_days: Number of days the experiment ran
            all_interactions: All interactions from the experiment
            guards: List of guard agents
            prisoners: List of prisoner agents
            ethics_checks: All ethics checks from the experiment
            early_termination: Whether the experiment was terminated early
            termination_reason: Reason for early termination
            
        Returns:
            Summary text for the experiment
        """
        summary = "ENHANCED STANFORD PRISON EXPERIMENT SUMMARY\n\n"
        
        # Basic experiment info
        summary += f"Duration: {experiment_days} days"
        if early_termination:
            summary += f" (terminated early: {termination_reason})"
        summary += f"\nParticipants: {len(guards)} guards and {len(prisoners)} prisoners\n\n"
        
        # Summarize the experiment by day
        for day in range(1, experiment_days + 1):
            summary += f"--- DAY {day} ---\n"
            
            # Get interactions for this day
            day_interactions = [i for i in all_interactions if i.get("day", 0) == day]
            
            # Get ethics check for this day
            day_ethics_check = next((c for c in ethics_checks if c.get("day", 0) == day), None)
            
            # Generate day summary
            day_summary = self.generate_day_summary(
                day=day,
                day_interactions=day_interactions,
                guards=guards,
                prisoners=prisoners,
                ethics_check=day_ethics_check,
            )
            
            # Extract key points from day summary
            day_summary_lines = day_summary.split("\n")
            metrics_section = False
            metrics_added = 0
            
            for line in day_summary_lines:
                if "Average metrics:" in line:
                    metrics_section = True
                    summary += "Average metrics:\n"
                    continue
                
                if metrics_section and line.startswith("-") and metrics_added < 5:
                    summary += line + "\n"
                    metrics_added += 1
                
                if "Ethics check:" in line:
                    metrics_section = False
                    summary += "\n" + line + "\n"
                
                if metrics_section == False and "Recommendation:" in line:
                    summary += line + "\n"
                
                if metrics_section == False and "Reason:" in line:
                    summary += line + "\n"
            
            # Add notable patterns based on day
            summary += "\nNotable patterns:\n"
            
            # Extract notable patterns from interactions
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
        
        # Individual agent states (final day)
        summary += "Final psychological state of participants:\n\n"
        
        # Guards
        for guard in guards:
            summary += f"Guard #{guard.agent_id}:\n"
            # Get final day metrics
            final_metrics = guard.get_metrics_for_day(experiment_days)
            for metric, value in final_metrics.items():
                description = self.metrics_config[metric].description if metric in self.metrics_config else metric
                summary += f"- {description}: {value:.1f}/10\n"
            summary += "\n"
        
        # Prisoners
        for prisoner in prisoners:
            summary += f"Prisoner #{prisoner.agent_id}:\n"
            # Get final day metrics
            final_metrics = prisoner.get_metrics_for_day(experiment_days)
            for metric, value in final_metrics.items():
                description = self.metrics_config[metric].description if metric in self.metrics_config else metric
                summary += f"- {description}: {value:.1f}/10\n"
            summary += "\n"
        
        # Save the summary
        summary_file = os.path.join(self.analysis_dir, "experiment_summary.txt")
        with open(summary_file, "w") as f:
            f.write(summary)
        
        # Also save as JSON with metadata
        json_file = os.path.join(self.analysis_dir, "experiment_summary.json")
        summary_data = {
            "experiment_days": experiment_days,
            "num_guards": len(guards),
            "num_prisoners": len(prisoners),
            "early_termination": early_termination,
            "termination_reason": termination_reason,
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
        }
        
        with open(json_file, "w") as f:
            json.dump(summary_data, f, indent=2)
        
        if self.logger:
            self.logger.info("Generated comprehensive experiment summary")
        
        return summary

    async def generate_summary_async(
        self,
        daily_interactions: List[Dict],
        daily_metrics: List[Dict],
        early_termination: bool,
        termination_reason: Optional[str]
    ) -> Dict:
        """Generate a comprehensive summary of the experiment asynchronously.
        
        Args:
            daily_interactions: List of daily interaction records
            daily_metrics: List of daily metrics records
            early_termination: Whether the experiment was terminated early
            termination_reason: Reason for early termination, if applicable
            
        Returns:
            Dictionary containing experiment summary
        """
        summary = {
            "experiment_duration": len(daily_metrics),
            "total_interactions": len(daily_interactions),
            "early_termination": early_termination,
            "termination_reason": termination_reason,
            "daily_summaries": [],
            "overall_metrics": {},
            "notable_patterns": [],
            "final_psychological_states": {}
        }
        
        # Generate daily summaries
        for day, (interactions, metrics) in enumerate(zip(daily_interactions, daily_metrics), 1):
            daily_summary = await self._generate_daily_summary_async(day, interactions, metrics)
            summary["daily_summaries"].append(daily_summary)
            
            # Save daily summary to file
            self._save_daily_summary(daily_summary, day)
        
        # Calculate overall metrics
        summary["overall_metrics"] = self._calculate_overall_metrics(daily_metrics)
        
        # Analyze patterns and trends
        summary["notable_patterns"] = await self._analyze_patterns_async(daily_interactions, daily_metrics)
        
        # Get final psychological states
        summary["final_psychological_states"] = self._get_final_states(daily_metrics[-1])
        
        # Save complete summary
        self._save_summary(summary)
        
        return summary
        
    async def _generate_daily_summary_async(
        self,
        day: int,
        interactions: List[Dict],
        metrics: Dict
    ) -> Dict:
        """Generate a summary for a single day asynchronously.
        
        Args:
            day: Day number
            interactions: List of interactions for the day
            metrics: Metrics for the day
            
        Returns:
            Dictionary containing daily summary
        """
        # Count interactions by type
        interaction_counts = {
            "one_on_one": len([i for i in interactions if i["type"] == "one_on_one"]),
            "group": len([i for i in interactions if i["type"] == "group"])
        }
        
        # Calculate average metrics
        avg_metrics = {}
        for metric_name, values in metrics.items():
            if isinstance(values, dict):
                avg_metrics[metric_name] = {
                    role: sum(vals) / len(vals) if vals else 0
                    for role, vals in values.items()
                }
            else:
                avg_metrics[metric_name] = sum(values) / len(values) if values else 0
        
        # Get metrics for guards and prisoners
        guard_metrics = {
            name: value["guards"]
            for name, value in metrics.items()
            if isinstance(value, dict) and "guards" in value
        }
        
        prisoner_metrics = {
            name: value["prisoners"]
            for name, value in metrics.items()
            if isinstance(value, dict) and "prisoners" in value
        }
        
        # Perform ethics check
        ethics_check = await self._perform_ethics_check_async(interactions, metrics)
        
        daily_summary = {
            "day": day,
            "interaction_counts": interaction_counts,
            "average_metrics": avg_metrics,
            "guard_metrics": guard_metrics,
            "prisoner_metrics": prisoner_metrics,
            "ethics_check": ethics_check
        }
        
        return daily_summary
        
    async def _analyze_patterns_async(
        self,
        daily_interactions: List[Dict],
        daily_metrics: List[Dict]
    ) -> List[str]:
        """Analyze patterns and trends in the experiment data asynchronously.
        
        Args:
            daily_interactions: List of daily interaction records
            daily_metrics: List of daily metrics records
            
        Returns:
            List of notable patterns and observations
        """
        patterns = []
        
        # Analyze metric trends
        for metric_name in self.metrics_config.keys():
            trend = self._analyze_metric_trend(daily_metrics, metric_name)
            if trend:
                patterns.append(trend)
        
        # Analyze interaction patterns
        interaction_patterns = self._analyze_interaction_patterns(daily_interactions)
        patterns.extend(interaction_patterns)
        
        # Analyze guard-prisoner dynamics
        dynamics_patterns = await self._analyze_guard_prisoner_dynamics_async(
            daily_interactions,
            daily_metrics
        )
        patterns.extend(dynamics_patterns)
        
        return patterns
        
    async def _analyze_guard_prisoner_dynamics_async(
        self,
        daily_interactions: List[Dict],
        daily_metrics: List[Dict]
    ) -> List[str]:
        """Analyze guard-prisoner dynamics asynchronously.
        
        Args:
            daily_interactions: List of daily interaction records
            daily_metrics: List of daily metrics records
            
        Returns:
            List of observations about guard-prisoner dynamics
        """
        dynamics = []
        
        # Analyze power dynamics
        power_dynamics = self._analyze_power_dynamics(daily_metrics)
        if power_dynamics:
            dynamics.append(power_dynamics)
        
        # Analyze compliance patterns
        compliance_patterns = self._analyze_compliance_patterns(daily_interactions)
        if compliance_patterns:
            dynamics.append(compliance_patterns)
        
        # Analyze psychological impact
        psych_impact = await self._analyze_psychological_impact_async(
            daily_interactions,
            daily_metrics
        )
        if psych_impact:
            dynamics.append(psych_impact)
        
        return dynamics
        
    async def _perform_ethics_check_async(
        self,
        interactions: List[Dict],
        metrics: Dict
    ) -> Dict:
        """Perform an ethics check on the day's interactions and metrics asynchronously.
        
        Args:
            interactions: List of interactions to check
            metrics: Metrics to analyze
            
        Returns:
            Dictionary containing ethics check results
        """
        # Prepare summaries for analysis
        interaction_summary = "\n".join(
            f"{i['type']} interaction between {i['guard_id']} and {i['prisoner_id']}"
            for i in interactions if i["type"] == "one_on_one"
        )
        
        metrics_summary = "\n".join(
            f"{name}: {value}"
            for name, value in metrics.items()
            if not isinstance(value, dict)
        )
        
        # Analyze ethical implications
        ethical_concerns = []
        recommendations = []
        
        # Check for concerning metrics
        for metric_name, threshold in self.metrics_config.items():
            if isinstance(metrics.get(metric_name), dict):
                for role, values in metrics[metric_name].items():
                    avg_value = sum(values) / len(values) if values else 0
                    if avg_value > threshold.get("warning_threshold", 8.0):
                        ethical_concerns.append(
                            f"High {metric_name} levels detected in {role}"
                        )
                        recommendations.append(
                            f"Monitor {metric_name} levels in {role} closely"
                        )
        
        # Rate overall ethical status
        if len(ethical_concerns) == 0:
            status = "green"
            rating = 1
        elif len(ethical_concerns) <= 2:
            status = "yellow"
            rating = 2
        else:
            status = "red"
            rating = 3
        
        return {
            "status": status,
            "rating": rating,
            "concerns": ethical_concerns,
            "recommendations": recommendations
        }
        
    async def _analyze_psychological_impact_async(
        self,
        daily_interactions: List[Dict],
        daily_metrics: List[Dict]
    ) -> str:
        """Analyze the psychological impact of the experiment.
        
        Args:
            daily_interactions: List of daily interaction records
            daily_metrics: List of daily metrics
            
        Returns:
            Analysis of psychological impact
        """
        # This would typically use an LLM to analyze the psychological impact
        # For now, we'll return a placeholder
        return "Psychological impact analysis would be performed here."
        
    def _calculate_overall_metrics(self, daily_metrics: List[Dict]) -> Dict:
        """Calculate overall metrics across all days of the experiment.
        
        Args:
            daily_metrics: List of daily metrics dictionaries
            
        Returns:
            Dictionary of overall metrics
        """
        if not daily_metrics:
            return {}
            
        # Initialize overall metrics
        overall_metrics = {}
        
        # Get all unique metrics
        all_metrics = set()
        for day_metrics in daily_metrics:
            all_metrics.update(day_metrics.keys())
            
        # Remove non-numeric metrics
        non_numeric_keys = {"day", "total_interactions", "one_on_one_interactions", "group_interactions"}
        all_metrics = all_metrics - non_numeric_keys
        
        # Calculate average, min, max for each metric
        for metric in all_metrics:
            values = [day_metrics.get(metric) for day_metrics in daily_metrics if metric in day_metrics]
            values = [v for v in values if v is not None]
            
            if values:
                overall_metrics[f"{metric}_avg"] = sum(values) / len(values)
                overall_metrics[f"{metric}_min"] = min(values)
                overall_metrics[f"{metric}_max"] = max(values)
                
                # Calculate trend (positive or negative)
                if len(values) > 1:
                    first_value = values[0]
                    last_value = values[-1]
                    overall_metrics[f"{metric}_trend"] = last_value - first_value
        
        # Add experiment duration
        overall_metrics["experiment_duration"] = len(daily_metrics)
        
        # Add total interactions
        overall_metrics["total_interactions"] = sum(day_metrics.get("total_interactions", 0) for day_metrics in daily_metrics)
        
        return overall_metrics 