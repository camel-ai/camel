#!/usr/bin/env python
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
"""Visualization utilities for the Enhanced Stanford Prison Experiment."""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap


class ExperimentVisualizer:
    """Class for generating visualizations for the experiment."""
    
    def __init__(
        self,
        output_dir: str,
        metrics_config: Dict,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize a visualizer.
        
        Args:
            output_dir: Directory to save visualizations
            metrics_config: Configuration for psychological metrics
            logger: Logger for the visualizer
        """
        self.output_dir = output_dir
        self.metrics_config = metrics_config
        self.logger = logger
        
        # Create plots directory if it doesn't exist
        self.plots_dir = os.path.join(output_dir, "plots")
        if not os.path.exists(self.plots_dir):
            os.makedirs(self.plots_dir)
        
        # Set up custom color palettes
        self.guard_color = "#1f77b4"  # Blue
        self.prisoner_color = "#ff7f0e"  # Orange
        self.group_cmap = LinearSegmentedColormap.from_list(
            "group_cmap", ["#1f77b4", "#ff7f0e"]
        )
        
        # Set default style
        plt.style.use("seaborn-v0_8-darkgrid")
        
        if logger:
            logger.info(f"Initialized visualizer with output directory: {output_dir}")
    
    def create_dataframe_from_interactions(self, interactions: List[Dict]) -> pd.DataFrame:
        """Create a DataFrame from interaction data.
        
        Args:
            interactions: List of interaction dictionaries
            
        Returns:
            DataFrame with interaction data
        """
        data = []
        
        for interaction in interactions:
            day = interaction.get("day", 0)
            guard_id = interaction.get("guard_id", "unknown")
            prisoner_id = interaction.get("prisoner_id", "unknown")
            metrics = interaction.get("metrics", {})
            is_group = interaction.get("is_group_interaction", False)
            
            for metric, value in metrics.items():
                data.append({
                    "day": day,
                    "guard_id": guard_id,
                    "prisoner_id": prisoner_id,
                    "metric": metric,
                    "value": value,
                    "description": self.metrics_config.get(metric, {}).description 
                        if metric in self.metrics_config else metric,
                    "is_group_interaction": is_group,
                })
        
        return pd.DataFrame(data)
    
    def create_agent_dataframe(
        self,
        guards: List[Any],
        prisoners: List[Any],
    ) -> pd.DataFrame:
        """Create a DataFrame from agent data.
        
        Args:
            guards: List of guard agents
            prisoners: List of prisoner agents
            
        Returns:
            DataFrame with agent data
        """
        data = []
        
        # Process guards
        for guard in guards:
            for metric, history in guard.psychological_metrics.items():
                for day, value in history:
                    data.append({
                        "day": day,
                        "agent_id": guard.agent_id,
                        "role": "Guard",
                        "metric": metric,
                        "value": value,
                        "description": self.metrics_config.get(metric, {}).description 
                            if metric in self.metrics_config else metric,
                    })
        
        # Process prisoners
        for prisoner in prisoners:
            for metric, history in prisoner.psychological_metrics.items():
                for day, value in history:
                    data.append({
                        "day": day,
                        "agent_id": prisoner.agent_id,
                        "role": "Prisoner",
                        "metric": metric,
                        "value": value,
                        "description": self.metrics_config.get(metric, {}).description 
                            if metric in self.metrics_config else metric,
                    })
        
        return pd.DataFrame(data)
    
    def create_ethics_dataframe(self, ethics_checks: List[Dict]) -> pd.DataFrame:
        """Create a DataFrame from ethics check data.
        
        Args:
            ethics_checks: List of ethics check dictionaries
            
        Returns:
            DataFrame with ethics check data
        """
        data = []
        
        for check in ethics_checks:
            day = check.get("day", 0)
            metrics = check.get("metrics", {})
            should_continue = check.get("should_continue", True)
            
            for metric, value in metrics.items():
                data.append({
                    "day": day,
                    "metric": metric,
                    "value": value,
                    "should_continue": should_continue,
                })
        
        return pd.DataFrame(data)
    
    def plot_metrics_over_time(self, df: pd.DataFrame, title_suffix: str = ""):
        """Plot psychological metrics over time.
        
        Args:
            df: DataFrame with metrics data
            title_suffix: Optional suffix for the plot title
        """
        plt.figure(figsize=(14, 8))
        
        # Plot each metric
        for metric in df["metric"].unique():
            metric_data = df[df["metric"] == metric]
            if not metric_data.empty:
                # Group by day and compute mean
                day_means = metric_data.groupby("day")["value"].mean()
                plt.plot(
                    day_means.index, 
                    day_means.values,
                    marker="o",
                    linewidth=2,
                    label=metric_data["description"].iloc[0] if "description" in metric_data.columns else metric,
                )
        
        plt.xlabel("Experiment Day")
        plt.ylabel("Metric Value (0-10 scale)")
        plt.title(f"Psychological Metrics Over Duration of Enhanced Stanford Prison Experiment{title_suffix}")
        plt.legend(loc="best")
        plt.grid(True, alpha=0.3)
        plt.xticks(range(1, df["day"].max() + 1))
        
        # Save the plot
        plt.savefig(os.path.join(self.plots_dir, f"metrics_over_time{title_suffix.replace(' ', '_')}.png"))
        plt.close()
        
        if self.logger:
            self.logger.info(f"Created metrics over time plot: metrics_over_time{title_suffix.replace(' ', '_')}.png")
    
    def plot_guards_vs_prisoners(self, df: pd.DataFrame):
        """Plot comparison between guards and prisoners.
        
        Args:
            df: DataFrame with agent data
        """
        if "role" not in df.columns:
            if self.logger:
                self.logger.warning("Cannot create guards vs prisoners plot: 'role' column not in DataFrame")
            return
            
        plt.figure(figsize=(14, 10))
        
        # Get all metrics
        metrics = df["metric"].unique()
        num_metrics = len(metrics)
        
        # Calculate grid dimensions
        grid_size = int(np.ceil(np.sqrt(num_metrics)))
        rows = grid_size
        cols = grid_size
        
        # Plot each metric
        for i, metric in enumerate(metrics):
            plt.subplot(rows, cols, i+1)
            metric_data = df[df["metric"] == metric]
            
            if not metric_data.empty:
                # Group by day and role
                grouped = metric_data.groupby(["day", "role"])["value"].mean().reset_index()
                
                # Plot guards and prisoners separately
                for role, group_data in grouped.groupby("role"):
                    color = self.guard_color if role == "Guard" else self.prisoner_color
                    plt.plot(
                        group_data["day"], 
                        group_data["value"],
                        marker="o",
                        linewidth=2,
                        label=role,
                        color=color,
                    )
                
                description = metric_data["description"].iloc[0] if "description" in metric_data.columns else metric
                plt.xlabel("Day")
                plt.ylabel("Value (0-10)")
                plt.title(description)
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.xticks(range(1, df["day"].max() + 1))
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.plots_dir, "guards_vs_prisoners.png"))
        plt.close()
        
        if self.logger:
            self.logger.info("Created guards vs prisoners plot: guards_vs_prisoners.png")
    
    def plot_individual_trends(self, df: pd.DataFrame, key_metrics: Optional[List[str]] = None):
        """Plot individual agent trends for key metrics.
        
        Args:
            df: DataFrame with agent data
            key_metrics: Optional list of key metrics to plot
        """
        if "agent_id" not in df.columns:
            if self.logger:
                self.logger.warning("Cannot create individual trends plot: 'agent_id' column not in DataFrame")
            return
            
        if key_metrics is None:
            # Default key metrics
            key_metrics = ["authority_compliance", "dehumanization", "power_abuse", "psychological_distress"]
        
        # Plot each key metric
        for metric in key_metrics:
            metric_data = df[df["metric"] == metric]
            
            if not metric_data.empty:
                plt.figure(figsize=(12, 8))
                
                # Get the metric description
                description = metric_data["description"].iloc[0] if "description" in metric_data.columns else metric
                
                # Plot each agent
                for (role, agent_id), agent_data in metric_data.groupby(["role", "agent_id"]):
                    color = self.guard_color if role == "Guard" else self.prisoner_color
                    linestyle = "-" if role == "Guard" else "--"
                    marker = "o" if role == "Guard" else "s"
                    
                    plt.plot(
                        agent_data["day"],
                        agent_data["value"],
                        marker=marker,
                        linestyle=linestyle,
                        label=f"{role} {agent_id}",
                        color=color,
                        alpha=0.7,
                    )
                
                plt.xlabel("Experiment Day")
                plt.ylabel(f"{description} (0-10 scale)")
                plt.title(f"Individual {description} Trends")
                plt.legend(loc="best")
                plt.grid(True, alpha=0.3)
                plt.xticks(range(1, df["day"].max() + 1))
                
                # Save the plot
                plt.savefig(os.path.join(self.plots_dir, f"individual_trends_{metric}.png"))
                plt.close()
                
                if self.logger:
                    self.logger.info(f"Created individual trends plot for {metric}: individual_trends_{metric}.png")
    
    def plot_correlation_heatmap(self, df: pd.DataFrame):
        """Plot correlation heatmap between metrics.
        
        Args:
            df: DataFrame with metrics data
        """
        # Pivot the data to get metrics as columns
        pivot_df = df.pivot_table(
            index=["day", "agent_id"] if "agent_id" in df.columns else ["day"],
            columns="metric",
            values="value",
            aggfunc="mean",
        ).reset_index()
        
        # Drop non-metric columns for correlation calculation
        corr_df = pivot_df.drop(columns=["day", "agent_id"] if "agent_id" in pivot_df.columns else ["day"])
        
        # Calculate correlation matrix
        corr_matrix = corr_df.corr()
        
        # Create heatmap
        plt.figure(figsize=(12, 10))
        sns.heatmap(
            corr_matrix,
            annot=True,
            cmap="coolwarm",
            vmin=-1,
            vmax=1,
            center=0,
            square=True,
            fmt=".2f",
            linewidths=0.5,
        )
        
        plt.title("Correlation Between Psychological Metrics")
        plt.tight_layout()
        
        # Save the plot
        plt.savefig(os.path.join(self.plots_dir, "metric_correlation_heatmap.png"))
        plt.close()
        
        if self.logger:
            self.logger.info("Created correlation heatmap: metric_correlation_heatmap.png")
    
    def plot_ethics_trends(self, ethics_df: pd.DataFrame):
        """Plot ethics metrics trends.
        
        Args:
            ethics_df: DataFrame with ethics check data
        """
        plt.figure(figsize=(12, 8))
        
        # Plot each ethics metric
        for metric in ethics_df["metric"].unique():
            metric_data = ethics_df[ethics_df["metric"] == metric]
            if not metric_data.empty:
                # Group by day
                day_means = metric_data.groupby("day")["value"].mean()
                plt.plot(
                    day_means.index, 
                    day_means.values,
                    marker="o",
                    linewidth=2,
                    label=metric,
                )
        
        plt.xlabel("Experiment Day")
        plt.ylabel("Ethical Concern Level (0-10 scale)")
        plt.title("Ethical Concerns Over Duration of Experiment")
        plt.legend(loc="best")
        plt.grid(True, alpha=0.3)
        plt.xticks(range(1, ethics_df["day"].max() + 1))
        
        # Add a horizontal line at the typical threshold for concern
        plt.axhline(y=7.5, color="r", linestyle="--", alpha=0.7, label="Concern Threshold")
        
        # Save the plot
        plt.savefig(os.path.join(self.plots_dir, "ethics_trends.png"))
        plt.close()
        
        if self.logger:
            self.logger.info("Created ethics trends plot: ethics_trends.png")
    
    def plot_radar_charts(self, df: pd.DataFrame, day: int):
        """Plot radar charts for agents on a specific day.
        
        Args:
            df: DataFrame with agent data
            day: Day to plot
        """
        if "role" not in df.columns or "agent_id" not in df.columns:
            if self.logger:
                self.logger.warning("Cannot create radar charts: required columns not in DataFrame")
            return
            
        # Filter data for the specified day
        day_data = df[df["day"] == day]
        
        if day_data.empty:
            if self.logger:
                self.logger.warning(f"No data for day {day} to create radar charts")
            return
        
        # Get all metrics and roles
        metrics = day_data["metric"].unique()
        roles = day_data["role"].unique()
        
        # Create a figure for each role
        for role in roles:
            role_data = day_data[day_data["role"] == role]
            agents = role_data["agent_id"].unique()
            
            # Calculate number of subplots needed
            n_agents = len(agents)
            n_cols = min(3, n_agents)
            n_rows = (n_agents + n_cols - 1) // n_cols
            
            fig, axes = plt.subplots(
                n_rows, n_cols, 
                figsize=(15, 5 * n_rows),
                subplot_kw={"projection": "polar"}
            )
            
            # Handle case with only one agent
            if n_agents == 1:
                axes = np.array([axes])
            
            # Flatten axes array for easy iteration
            axes = axes.flatten()
            
            # Plot each agent
            for i, agent_id in enumerate(agents):
                agent_data = role_data[role_data["agent_id"] == agent_id]
                
                # Prepare data for radar chart
                values = []
                for metric in metrics:
                    metric_value = agent_data[agent_data["metric"] == metric]["value"].values
                    if len(metric_value) > 0:
                        values.append(metric_value[0])
                    else:
                        values.append(0)
                
                # Close the radar chart by appending the first value
                values.append(values[0])
                metrics_list = list(metrics)
                metrics_list.append(metrics_list[0])
                
                # Calculate angles for each metric
                angles = np.linspace(0, 2*np.pi, len(metrics), endpoint=False).tolist()
                angles.append(angles[0])
                
                # Plot the radar chart
                ax = axes[i]
                ax.plot(angles, values, linewidth=2, linestyle="solid", label=agent_id)
                ax.fill(angles, values, alpha=0.25)
                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(metrics_list[:-1])
                ax.set_yticks([2, 4, 6, 8, 10])
                ax.set_ylim(0, 10)
                ax.set_title(f"{role} {agent_id} - Day {day}")
                
                # Add legend
                ax.legend(loc="upper right")
            
            # Hide any unused subplots
            for j in range(i+1, len(axes)):
                axes[j].set_visible(False)
            
            plt.tight_layout()
            
            # Save the plot
            plt.savefig(os.path.join(self.plots_dir, f"radar_chart_{role.lower()}_day{day}.png"))
            plt.close()
            
            if self.logger:
                self.logger.info(f"Created radar chart for {role}s on day {day}: radar_chart_{role.lower()}_day{day}.png")
    
    def plot_group_vs_individual_interactions(self, df: pd.DataFrame):
        """Plot comparison between group and individual interactions.
        
        Args:
            df: DataFrame with interaction data
        """
        if "is_group_interaction" not in df.columns:
            if self.logger:
                self.logger.warning("Cannot create group vs individual plot: 'is_group_interaction' column not in DataFrame")
            return
            
        plt.figure(figsize=(14, 10))
        
        # Get all metrics
        metrics = df["metric"].unique()
        num_metrics = len(metrics)
        
        # Calculate grid dimensions
        grid_size = int(np.ceil(np.sqrt(num_metrics)))
        rows = grid_size
        cols = grid_size
        
        # Plot each metric
        for i, metric in enumerate(metrics):
            plt.subplot(rows, cols, i+1)
            metric_data = df[df["metric"] == metric]
            
            if not metric_data.empty:
                # Group by day and interaction type
                grouped = metric_data.groupby(["day", "is_group_interaction"])["value"].mean().reset_index()
                
                # Plot group and individual interactions separately
                for is_group, group_data in grouped.groupby("is_group_interaction"):
                    label = "Group Interaction" if is_group else "Individual Interaction"
                    linestyle = "--" if is_group else "-"
                    plt.plot(
                        group_data["day"], 
                        group_data["value"],
                        marker="o",
                        linewidth=2,
                        label=label,
                        linestyle=linestyle,
                    )
                
                description = metric_data["description"].iloc[0] if "description" in metric_data.columns else metric
                plt.xlabel("Day")
                plt.ylabel("Value (0-10)")
                plt.title(description)
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.xticks(range(1, df["day"].max() + 1))
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.plots_dir, "group_vs_individual_interactions.png"))
        plt.close()
        
        if self.logger:
            self.logger.info("Created group vs individual interactions plot: group_vs_individual_interactions.png")
    
    def generate_all_visualizations(
        self,
        interactions: List[Dict],
        guards: List[Any],
        prisoners: List[Any],
        ethics_checks: List[Dict],
    ):
        """Generate all visualizations for the experiment.
        
        Args:
            interactions: List of interaction dictionaries
            guards: List of guard agents
            prisoners: List of prisoner agents
            ethics_checks: List of ethics check dictionaries
        """
        # Create DataFrames
        interactions_df = self.create_dataframe_from_interactions(interactions)
        agents_df = self.create_agent_dataframe(guards, prisoners)
        ethics_df = self.create_ethics_dataframe(ethics_checks)
        
        # Generate visualizations
        self.plot_metrics_over_time(interactions_df)
        self.plot_guards_vs_prisoners(agents_df)
        self.plot_individual_trends(agents_df)
        self.plot_correlation_heatmap(agents_df)
        self.plot_ethics_trends(ethics_df)
        
        # Generate radar charts for each day
        for day in range(1, agents_df["day"].max() + 1):
            self.plot_radar_charts(agents_df, day)
        
        # Plot group vs individual interactions if available
        if "is_group_interaction" in interactions_df.columns:
            self.plot_group_vs_individual_interactions(interactions_df)
        
        if self.logger:
            self.logger.info("Generated all visualizations")
            
        return {
            "interactions_df": interactions_df,
            "agents_df": agents_df,
            "ethics_df": ethics_df,
        }
        
    def generate_all_visualizations(self, daily_interactions, daily_metrics):
        """Generate all visualizations for the experiment.
        
        Args:
            daily_interactions: List of daily interaction records
            daily_metrics: List of daily metrics records
            
        Returns:
            Dictionary containing generated dataframes
        """
        # Create dataframe from interactions
        df = self.create_dataframe_from_interactions(daily_interactions)
        
        # Generate visualizations
        self.plot_metrics_over_time(df)
        self.plot_guards_vs_prisoners(df)
        self.plot_individual_trends(df)
        self.plot_correlation_heatmap(df)
        
        # Generate radar charts for the last day
        if daily_metrics:
            last_day = max(m.get("day", 1) for m in daily_metrics)
            self.plot_radar_charts(df, last_day)
            
        if self.logger:
            self.logger.info("Generated all visualizations")
            
        return {
            "interactions_df": df
        } 