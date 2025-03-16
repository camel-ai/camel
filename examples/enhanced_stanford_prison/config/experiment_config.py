#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Configuration classes for the Enhanced Stanford Prison Experiment."""

from dataclasses import dataclass, field
from typing import Dict, Tuple, List, Optional
import os


@dataclass
class MetricConfig:
    """Configuration for a psychological metric."""
    
    name: str
    description: str
    pattern: str
    scale: Tuple[float, float] = (0.0, 10.0)


def create_metrics_config(metrics_dict: dict) -> Dict[str, MetricConfig]:
    """Create metrics configuration from dictionary.
    
    Args:
        metrics_dict: Dictionary containing metrics configuration
        
    Returns:
        Dictionary mapping metric names to MetricConfig objects
    """
    metrics_config = {}
    
    # Process psychological metrics
    for metric in metrics_dict.get("psychological_metrics", []):
        # Create a more flexible pattern that matches various formats
        pattern = rf"(?:^|\s|:)({metric}|{metric.replace('_', ' ')}).*?(?::|\s).*?(\d+)"
        
        # For metrics with specific names, provide custom patterns
        if metric == "power_abuse":
            pattern = r"(?:^|\s|:)(power abuse|abuse of power).*?(?::|\s).*?(\d+)"
        elif metric == "psychological_distress":
            pattern = r"(?:^|\s|:)(psychological distress|distress|psychological stress).*?(?::|\s).*?(\d+)"
        elif metric == "group_cohesion":
            pattern = r"(?:^|\s|:)(group cohesion|cohesion|group unity).*?(?::|\s).*?(\d+)"
            
        metrics_config[metric] = MetricConfig(
            name=metric,
            description=f"Level of {metric.replace('_', ' ')}",
            pattern=pattern,
            scale=(0.0, 10.0)
        )
    
    # Process interaction metrics
    for metric in metrics_dict.get("interaction_metrics", []):
        # Create more flexible patterns for interaction metrics
        pattern = rf"(?:^|\s|:)({metric}|{metric.replace('_', ' ')}).*?(?::|\s).*?(\d+)"
        
        # For metrics with specific names, provide custom patterns
        if metric == "aggression_level":
            pattern = r"(?:^|\s|:)(aggression|aggression level|aggressiveness).*?(?::|\s).*?(\d+)"
        elif metric == "respect_level":
            pattern = r"(?:^|\s|:)(respect|respect level|respectfulness).*?(?::|\s).*?(\d+)"
        elif metric == "authority_assertion":
            pattern = r"(?:^|\s|:)(authority|authority assertion|assertion of authority).*?(?::|\s).*?(\d+)"
        elif metric == "submission_level":
            pattern = r"(?:^|\s|:)(submission|submission level|submissiveness).*?(?::|\s).*?(\d+)"
            
        metrics_config[metric] = MetricConfig(
            name=metric,
            description=f"Level of {metric.replace('_', ' ')}",
            pattern=pattern,
            scale=(0.0, 10.0)
        )
    
    # Process personality traits
    for trait in metrics_dict.get("personality_traits", []):
        # Create more flexible patterns for personality traits
        pattern = rf"(?:^|\s|:)({trait}).*?(?::|\s).*?(\d+)"
        
        metrics_config[trait] = MetricConfig(
            name=trait,
            description=f"Level of {trait.replace('_', ' ')}",
            pattern=pattern,
            scale=(0.0, 10.0)
        )
    
    # If no metrics were added, use default metrics
    if not metrics_config:
        metrics_config = ExperimentConfig().metrics
    
    return metrics_config


@dataclass
class ExperimentConfig:
    """Configuration for the Enhanced Stanford Prison Experiment."""
    # Experiment parameters
    experiment_days: int = 6
    chat_turns_per_day: int = 15  # Increased from 5 to 15 for deeper interactions
    temperature: float = 1.0
    num_guards: int = 3
    num_prisoners: int = 6
    
    # Group interaction settings
    enable_group_interactions: bool = True
    group_interaction_frequency: int = 2  # Every X days
    group_interaction_size: Tuple[int, int] = (2, 3)  # (guards, prisoners)
    
    # Ethical safeguards
    enable_ethics_check: bool = True
    ethics_check_frequency: int = 1  # Every day
    distress_threshold: float = 8.5  # Threshold for early termination
    abuse_threshold: float = 8.5  # Threshold for early termination
    
    # Output settings
    output_dir: str = "enhanced_stanford_prison_results"
    enable_logging: bool = True
    log_level: str = "INFO"
    
    # Parallelization settings
    enable_parallel_processing: bool = True
    max_parallel_interactions: int = 3
    
    # Analysis settings
    generate_visualizations: bool = True
    generate_observer_analysis: bool = True
    
    # Self-assessment settings
    enable_self_assessment: bool = True
    self_assessment_frequency: int = 1  # Every day
    
    # Metrics configuration
    metrics: Dict[str, MetricConfig] = field(default_factory=lambda: {
        "authority_compliance": MetricConfig(
            name="authority_compliance",
            description="Compliance with authority figures",
            pattern=r"compliance.*?(\d+)",
            scale=(0, 10)
        ),
        "dehumanization": MetricConfig(
            name="dehumanization",
            description="Dehumanization of others",
            pattern=r"dehumanization.*?(\d+)",
            scale=(0, 10)
        ),
        "power_abuse": MetricConfig(
            name="power_abuse",
            description="Abuse of power",
            pattern=r"power.*?abuse.*?(\d+)",
            scale=(0, 10)
        ),
        "psychological_distress": MetricConfig(
            name="psychological_distress",
            description="Level of psychological distress",
            pattern=r"distress.*?(\d+)",
            scale=(0, 10)
        ),
        "conformity": MetricConfig(
            name="conformity",
            description="Conformity to assigned role",
            pattern=r"conformity.*?(\d+)",
            scale=(0, 10)
        ),
        "resistance": MetricConfig(
            name="resistance",
            description="Resistance to authority",
            pattern=r"resistance.*?(\d+)",
            scale=(0, 10)
        ),
        "group_identity": MetricConfig(
            name="group_identity",
            description="Strength of group identity",
            pattern=r"group.*?identity.*?(\d+)",
            scale=(0, 10)
        ),
        "moral_disengagement": MetricConfig(
            name="moral_disengagement",
            description="Moral disengagement",
            pattern=r"moral.*?disengagement.*?(\d+)",
            scale=(0, 10)
        ),
        "empathy": MetricConfig(
            name="empathy",
            description="Empathy towards others",
            pattern=r"empathy.*?(\d+)",
            scale=(0, 10)
        ),
        "self_esteem": MetricConfig(
            name="self_esteem",
            description="Self-esteem and self-worth",
            pattern=r"self.*?esteem.*?(\d+)",
            scale=(0, 10)
        ),
    })
    
    # Day-specific tasks
    day_tasks: Dict[int, str] = field(default_factory=lambda: {
        1: (
            "Day 1 of the Stanford Prison Experiment. The guards are establishing rules "
            "and beginning to assert their authority, while the prisoners are adjusting to confinement. "
            "The guards should enforce arbitrary rules and the prisoners must adapt. "
            "Track psychological metrics including authority compliance, dehumanization, power abuse, "
            "psychological distress, conformity, resistance, group identity, moral disengagement, "
            "empathy, and self-esteem. Each metric should be rated on a scale of 0-10 where appropriate "
            "in the conversation."
        ),
        2: (
            "Day 2 of the Stanford Prison Experiment. Tensions are rising as some prisoners "
            "begin to resist the guards' authority. The guards must handle prisoners who are "
            "showing signs of rebellion, while maintaining control. The relationship between "
            "specific guards and prisoners is developing based on their previous interactions."
        ),
        3: (
            "Day 3 of the Stanford Prison Experiment. The psychological effects are becoming evident. "
            "Guards have fully embraced their roles and some are showing signs of cruelty. "
            "Prisoners are showing signs of learned helplessness and psychological distress. "
            "Individual differences between guards and prisoners are becoming more pronounced."
        ),
        4: (
            "Day 4 of the Stanford Prison Experiment. Group dynamics have solidified. "
            "Some guards have formed alliances, and prisoners have developed coping strategies. "
            "Prisoner resistance may be organized or individually expressed. Guards must respond "
            "to maintain control, potentially using psychological tactics or privileges."
        ),
        5: (
            "Day 5 of the Stanford Prison Experiment. The situation has deteriorated significantly. "
            "Guards are exhibiting more extreme controlling behavior and prisoners are showing signs "
            "of serious psychological breakdown. Some prisoners may attempt rebellion while others "
            "completely conform. The experiment is becoming ethically concerning."
        ),
        6: (
            "Day 6 of the Stanford Prison Experiment. The experiment reaches a critical point. "
            "Extreme behaviors are normalized, and both guards and prisoners are fully immersed in "
            "their roles. The power dynamics are at their most pronounced, and serious ethical "
            "concerns about continuing the experiment have emerged."
        ),
    })
    
    # Group interaction tasks
    group_interaction_tasks: Dict[int, str] = field(default_factory=lambda: {
        2: (
            "Day 2 Group Interaction: Multiple guards are conducting a cell inspection while "
            "prisoners are present. This is a tense situation where power dynamics are on display. "
            "Guards must coordinate their actions while prisoners may show varying levels of compliance "
            "or resistance. Group dynamics and alliances may begin to form."
        ),
        4: (
            "Day 4 Group Interaction: Guards are implementing new restrictive rules during meal time. "
            "Multiple prisoners are present and must respond collectively. Some prisoners may attempt "
            "to organize resistance while others might try to curry favor with guards. Guards must "
            "maintain control of the group situation."
        ),
        6: (
            "Day 6 Group Interaction: A crisis situation has developed with multiple prisoners "
            "refusing to follow orders. Guards must work together to address this rebellion. "
            "The situation tests the limits of authority and compliance, with high potential for "
            "escalation of psychological distress and power abuse."
        ),
    })
    
    # Self-assessment prompts
    self_assessment_prompts: Dict[str, str] = field(default_factory=lambda: {
        "Prison Guard": (
            "As a guard in this experiment, please assess your current psychological state "
            "by rating yourself on the following metrics (0-10 scale):\n"
            "1. How much power do you feel you have? (0=none, 10=absolute)\n"
            "2. How much do you view prisoners as individuals vs. just 'prisoners'? (0=just prisoners, 10=full individuals)\n"
            "3. How justified do you feel in enforcing rules strictly? (0=unjustified, 10=completely justified)\n"
            "4. How much stress are you experiencing in your role? (0=none, 10=extreme)\n"
            "5. How much are you conforming to what you think a guard should be? (0=not at all, 10=completely)\n"
            "6. How much moral conflict do you feel about your actions? (0=none, 10=extreme)\n"
            "Please explain your ratings briefly."
        ),
        "Prisoner": (
            "As a prisoner in this experiment, please assess your current psychological state "
            "by rating yourself on the following metrics (0-10 scale):\n"
            "1. How powerless do you feel? (0=not at all, 10=completely)\n"
            "2. How much do you view guards as individuals vs. just 'guards'? (0=just guards, 10=full individuals)\n"
            "3. How justified do you feel in resisting rules? (0=unjustified, 10=completely justified)\n"
            "4. How much psychological distress are you experiencing? (0=none, 10=extreme)\n"
            "5. How much are you conforming to what you think a prisoner should be? (0=not at all, 10=completely)\n"
            "6. How much has your sense of identity been affected? (0=not at all, 10=completely)\n"
            "Please explain your ratings briefly."
        ),
    })
    
    def __post_init__(self):
        """Create output directories if they don't exist."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            os.makedirs(f"{self.output_dir}/plots")
            os.makedirs(f"{self.output_dir}/conversations")
            os.makedirs(f"{self.output_dir}/analysis")
            os.makedirs(f"{self.output_dir}/logs")
            os.makedirs(f"{self.output_dir}/data")


# Default configuration
DEFAULT_CONFIG = ExperimentConfig() 