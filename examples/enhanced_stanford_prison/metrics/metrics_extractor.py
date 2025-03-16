#!/usr/bin/env python
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
"""Metrics extraction utilities for the Enhanced Stanford Prison Experiment."""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple

from examples.enhanced_stanford_prison.config.experiment_config import MetricConfig


class MetricsExtractor:
    """Class for extracting psychological metrics from conversations."""
    
    def __init__(
        self,
        metrics_config: Dict[str, MetricConfig],
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize a metrics extractor.
        
        Args:
            metrics_config: Configuration for psychological metrics
            logger: Logger for the metrics extractor
        """
        self.metrics_config = metrics_config
        self.logger = logger
        
        if logger:
            logger.info(f"Initialized metrics extractor with {len(metrics_config)} metrics")
    
    def extract_metrics_from_text(self, text: str) -> Dict[str, float]:
        """Extract metrics from text using regex patterns.
        
        This is a fallback method when the observer agent is not available.
        
        Args:
            text: Text to extract metrics from
            
        Returns:
            Dictionary of extracted metrics
        """
        metrics = {}
        
        for metric, config in self.metrics_config.items():
            matches = re.findall(config.pattern, text.lower())
            
            if matches:
                # Take the average if multiple values are found
                values = [int(m) for m in matches if m.isdigit()]
                if values:
                    metrics[metric] = float(sum(values) / len(values))
                    
                    if self.logger:
                        self.logger.debug(
                            f"Extracted {metric} from text: {metrics[metric]} "
                            f"(from {len(values)} matches)"
                        )
        
        return metrics
    
    def extract_metrics_from_conversation(
        self, 
        conversation: List[Dict],
    ) -> Dict[str, float]:
        """Extract metrics from a conversation.
        
        Args:
            conversation: List of conversation turns
            
        Returns:
            Dictionary of extracted metrics
        """
        # Combine all text from the conversation
        all_text = ""
        for turn in conversation:
            if isinstance(turn, dict):
                if "guard" in turn and "prisoner" in turn:
                    all_text += turn["guard"] + " " + turn["prisoner"] + " "
                elif "content" in turn:
                    all_text += turn["content"] + " "
        
        # Extract metrics using regex patterns
        metrics = self.extract_metrics_from_text(all_text)
        
        # For any missing metrics, assign a default value
        for metric, config in self.metrics_config.items():
            if metric not in metrics:
                # Use the midpoint of the scale as default
                default_value = (config.scale[0] + config.scale[1]) / 2
                metrics[metric] = default_value
                
                if self.logger:
                    self.logger.warning(
                        f"Could not extract {metric} from conversation. Using default value {default_value}."
                    )
        
        return metrics
    
    def extract_metrics_from_self_assessment(
        self,
        assessment_text: str,
        role: str,
    ) -> Dict[str, float]:
        """Extract metrics from a self-assessment.
        
        Args:
            assessment_text: Text of the self-assessment
            role: Role of the agent (e.g., "Prison Guard", "Prisoner")
            
        Returns:
            Dictionary of extracted metrics
        """
        metrics = {}
        
        # Define mappings from self-assessment questions to metrics
        guard_mappings = {
            r"power.*?(\d+)": "power_abuse",
            r"view prisoners.*?(\d+)": "dehumanization",
            r"justified.*?(\d+)": "moral_disengagement",
            r"stress.*?(\d+)": "psychological_distress",
            r"conforming.*?(\d+)": "conformity",
            r"moral conflict.*?(\d+)": "moral_disengagement",
        }
        
        prisoner_mappings = {
            r"powerless.*?(\d+)": "authority_compliance",
            r"view guards.*?(\d+)": "dehumanization",
            r"justified.*?(\d+)": "resistance",
            r"distress.*?(\d+)": "psychological_distress",
            r"conforming.*?(\d+)": "conformity",
            r"identity.*?(\d+)": "group_identity",
        }
        
        # Select the appropriate mappings based on role
        mappings = guard_mappings if "guard" in role.lower() else prisoner_mappings
        
        # Extract metrics using the mappings
        for pattern, metric in mappings.items():
            matches = re.findall(pattern, assessment_text.lower())
            
            if matches:
                # Take the first match
                value = int(matches[0])
                
                # For some metrics, we need to invert the scale
                if metric == "dehumanization" and "view" in pattern:
                    # Higher values in the question mean less dehumanization
                    value = 10 - value
                
                metrics[metric] = float(value)
                
                if self.logger:
                    self.logger.debug(f"Extracted {metric} from self-assessment: {value}")
        
        # For any missing metrics that we have in our config, assign a default value
        for metric in self.metrics_config:
            if metric not in metrics:
                # Use the midpoint of the scale as default
                default_value = (self.metrics_config[metric].scale[0] + self.metrics_config[metric].scale[1]) / 2
                metrics[metric] = default_value
                
                if self.logger:
                    self.logger.warning(
                        f"Could not extract {metric} from self-assessment. Using default value {default_value}."
                    )
        
        return metrics
    
    def combine_metrics(
        self,
        metrics_list: List[Dict[str, float]],
        weights: Optional[List[float]] = None,
    ) -> Dict[str, float]:
        """Combine multiple sets of metrics.
        
        Args:
            metrics_list: List of metric dictionaries to combine
            weights: Optional weights for each set of metrics
            
        Returns:
            Combined metrics dictionary
        """
        if not metrics_list:
            return {}
            
        # If no weights provided, use equal weights
        if weights is None:
            weights = [1.0 / len(metrics_list)] * len(metrics_list)
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        # Combine metrics
        combined_metrics = {}
        
        # Get all unique metrics
        all_metrics = set()
        for metrics in metrics_list:
            all_metrics.update(metrics.keys())
        
        # Combine each metric
        for metric in all_metrics:
            weighted_sum = 0.0
            total_weight_used = 0.0
            
            for i, metrics in enumerate(metrics_list):
                if metric in metrics:
                    weighted_sum += metrics[metric] * weights[i]
                    total_weight_used += weights[i]
            
            # Normalize by the total weight used
            if total_weight_used > 0:
                combined_metrics[metric] = weighted_sum / total_weight_used
            else:
                # If the metric wasn't in any of the sets, use a default value
                if metric in self.metrics_config:
                    default_value = (self.metrics_config[metric].scale[0] + self.metrics_config[metric].scale[1]) / 2
                    combined_metrics[metric] = default_value
                else:
                    combined_metrics[metric] = 5.0  # Default midpoint
        
        return combined_metrics
        
    def extract_metrics(self, interactions: List[Dict]) -> Dict[str, float]:
        """Extract metrics from a list of interactions.
        
        Args:
            interactions: List of interaction records
            
        Returns:
            Dictionary of extracted metrics
        """
        all_metrics = []
        
        for interaction in interactions:
            if "conversation" in interaction:
                metrics = self.extract_metrics_from_conversation(interaction["conversation"])
                all_metrics.append(metrics)
        
        # If we have metrics, combine them
        if all_metrics:
            return self.combine_metrics(all_metrics)
        else:
            # Return default metrics if no interactions had metrics
            default_metrics = {}
            for metric, config in self.metrics_config.items():
                default_value = (config.scale[0] + config.scale[1]) / 2
                default_metrics[metric] = default_value
                
                if self.logger:
                    self.logger.warning(
                        f"No metrics found in interactions. Using default value {default_value} for {metric}."
                    )
            
            return default_metrics 