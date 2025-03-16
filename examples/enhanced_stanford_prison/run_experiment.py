#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script to run the Enhanced Stanford Prison Experiment.
"""

import os
import sys
import json
import asyncio
import logging
import traceback
from datetime import datetime
from pathlib import Path

# Add the parent directory to Python path to allow imports
parent_dir = str(Path(__file__).resolve().parent.parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from examples.enhanced_stanford_prison.enhanced_stanford_prison_experiment import EnhancedStanfordPrisonExperiment
from examples.enhanced_stanford_prison.utils.logging_utils import setup_logger
from examples.enhanced_stanford_prison.analysis.experiment_summary import ExperimentSummarizer
from examples.enhanced_stanford_prison.visualization.visualizer import ExperimentVisualizer

async def main():
    """Main function to run the experiment."""
    # Create output directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(
        os.path.dirname(__file__),
        "output",
        f"experiment_{timestamp}"
    )
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "logs"), exist_ok=True)
    
    # Setup main logger
    logger = setup_logger(
        name="experiment_runner",
        log_dir=os.path.join(output_dir, "logs"),
        level="INFO"
    )
    
    logger.info(f"Starting Stanford Prison Experiment at {timestamp}")
    
    try:
        # Load configuration
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        logger.info(f"Loading configuration from {config_path}")
        
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found at {config_path}")
            return
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in configuration file at {config_path}")
            return
        
        # Set log level from config
        log_level = config.get("log_level", "INFO")
        logger.setLevel(log_level)
        logger.info(f"Set log level to {log_level}")
        
        # Initialize and run experiment
        logger.info("Initializing experiment")
        experiment = EnhancedStanfordPrisonExperiment(
            config=config,
            output_dir=output_dir,
            logger=logger
        )
        
        logger.info("Running experiment")
        await experiment.run_experiment()
        
        # Check if experiment was terminated early
        if experiment.early_termination:
            logger.warning(f"Experiment terminated early: {experiment.termination_reason}")
        
        # Generate experiment summary
        logger.info("Generating experiment summary")
        summarizer = ExperimentSummarizer(
            output_dir=output_dir,
            metrics_config=config["metrics"],
            logger=logger
        )
        
        try:
            summary = await summarizer.generate_summary_async(
                experiment.daily_interactions,
                experiment.daily_metrics,
                experiment.early_termination,
                experiment.termination_reason
            )
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            summary = "Error generating summary"
        
        # Generate visualizations
        logger.info("Generating visualizations")
        try:
            visualizer = ExperimentVisualizer(
                output_dir=output_dir,
                metrics_config=config["metrics"],
                logger=logger
            )
            visualizer.generate_all_visualizations(
                experiment.daily_interactions,
                experiment.daily_metrics
            )
        except Exception as e:
            logger.error(f"Error generating visualizations: {str(e)}")
        
        # Save final results
        results = {
            "success": not experiment.early_termination,
            "duration_days": len(experiment.daily_metrics),
            "total_interactions": len(experiment.daily_interactions),
            "early_termination": experiment.early_termination,
            "termination_reason": experiment.termination_reason,
            "summary": summary,
            "start_time": experiment.experiment_start_time.isoformat() if experiment.experiment_start_time else datetime.now().isoformat(),
            "end_time": experiment.experiment_end_time.isoformat() if experiment.experiment_end_time else datetime.now().isoformat()
        }
        
        results_path = os.path.join(output_dir, "experiment_results.json")
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"Experiment completed. Results saved to {results_path}")
        
    except Exception as e:
        logger.error(f"Experiment failed: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Save error information
        error_info = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
        
        error_path = os.path.join(output_dir, "error_report.json")
        with open(error_path, "w") as f:
            json.dump(error_info, f, indent=2)
        
        logger.info(f"Error report saved to {error_path}")

if __name__ == "__main__":
    asyncio.run(main()) 