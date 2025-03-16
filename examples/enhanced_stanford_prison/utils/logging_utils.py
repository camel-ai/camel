#!/usr/bin/env python
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
"""Logging utilities for the Enhanced Stanford Prison Experiment."""

import logging
import os
import sys
from datetime import datetime
from typing import Optional

from colorama import Fore, Style


class ColoredFormatter(logging.Formatter):
    """Custom formatter for colored console output."""
    
    COLORS = {
        'DEBUG': Fore.BLUE,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }
    
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
            record.msg = f"{self.COLORS[levelname]}{record.msg}{Style.RESET_ALL}"
        return super().format(record)


def setup_logger(
    name: str,
    log_dir: str,
    level: str = "INFO",
    console_output: bool = True,
    file_output: bool = True,
) -> logging.Logger:
    """Set up a logger with console and file handlers.
    
    Args:
        name: Name of the logger
        log_dir: Directory to store log files
        level: Logging level
        console_output: Whether to output logs to console
        file_output: Whether to output logs to file
        
    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.propagate = False
    
    # Clear existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatters
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if file_output:
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"{name}_{timestamp}.log")
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_experiment_logger(
    output_dir: str,
    level: str = "INFO",
    component: Optional[str] = None,
) -> logging.Logger:
    """Get a logger for the experiment.
    
    Args:
        output_dir: Output directory for the experiment
        level: Logging level
        component: Optional component name to append to logger name
        
    Returns:
        Configured logger
    """
    log_dir = os.path.join(output_dir, "logs")
    logger_name = "stanford_prison"
    
    if component:
        logger_name = f"{logger_name}.{component}"
    
    return setup_logger(
        name=logger_name,
        log_dir=log_dir,
        level=level,
        console_output=True,
        file_output=True,
    ) 