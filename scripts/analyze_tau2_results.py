#!/usr/bin/env python3
"""
Analyze Tau2 benchmark results and extract task performance statistics.

This script processes Tau2 benchmark results JSON file to:
- Extract task IDs and their rewards across multiple trials
- Calculate average reward for each task
- Group tasks by reward level and display them sorted
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def analyze_tau2_results(json_file_path):
    """
    Analyze Tau2 benchmark results from a JSON file.

    Args:
        json_file_path: Path to the JSON results file
    """
    # Load the JSON file
    print(f"Loading results from: {json_file_path}")
    with open(json_file_path, 'r') as f:
        data = json.load(f)

    # Extract simulations
    simulations = data.get('simulations', [])
    print(f"Found {len(simulations)} simulations")

    # Group rewards by task_id
    task_rewards = defaultdict(list)

    for sim in simulations:
        task_id = sim.get('task_id')
        reward = sim.get('reward_info', {}).get('reward')

        if task_id is not None and reward is not None:
            task_rewards[task_id].append(reward)

    # Calculate average reward for each task
    task_avg_rewards = {}
    for task_id, rewards in task_rewards.items():
        avg_reward = sum(rewards) / len(rewards)
        task_avg_rewards[task_id] = avg_reward

    print(f"\nAnalyzed {len(task_avg_rewards)} unique tasks")

    # Group tasks by reward level
    reward_groups = defaultdict(list)
    for task_id, avg_reward in task_avg_rewards.items():
        reward_groups[avg_reward].append(task_id)

    # Sort task IDs within each reward group (numerically)
    for reward in reward_groups:
        # Convert to int for numeric sorting if possible, otherwise keep as string
        try:
            reward_groups[reward] = sorted(reward_groups[reward],
                                          key=lambda x: int(x))
        except ValueError:
            # If task_id is not numeric, sort as string
            reward_groups[reward] = sorted(reward_groups[reward])

    # Sort by reward level (low to high) and display
    print("\n" + "="*80)
    print("TASK PERFORMANCE SUMMARY (sorted by reward: low to high)")
    print("="*80)

    sorted_rewards = sorted(reward_groups.keys())

    for reward in sorted_rewards:
        task_ids = reward_groups[reward]
        count = len(task_ids)

        print(f"\nReward: {reward:.2f} ({count} tasks)")
        print(f"Task IDs: {', '.join(task_ids)}")

    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    total_tasks = len(task_avg_rewards)
    perfect_tasks = len([t for t, r in task_avg_rewards.items() if r == 1.0])
    failed_tasks = len([t for t, r in task_avg_rewards.items() if r == 0.0])
    partial_tasks = total_tasks - perfect_tasks - failed_tasks

    print(f"Total tasks: {total_tasks}")
    print(f"Perfect (reward = 1.0): {perfect_tasks} ({perfect_tasks/total_tasks*100:.1f}%)")
    print(f"Failed (reward = 0.0): {failed_tasks} ({failed_tasks/total_tasks*100:.1f}%)")
    print(f"Partial (0.0 < reward < 1.0): {partial_tasks} ({partial_tasks/total_tasks*100:.1f}%)")

    if task_avg_rewards:
        avg_overall = sum(task_avg_rewards.values()) / len(task_avg_rewards)
        print(f"\nOverall average reward: {avg_overall:.4f}")


def main():
    """Main function to parse arguments and run analysis."""
    parser = argparse.ArgumentParser(
        description='Analyze Tau2 benchmark results and extract task performance statistics.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Analyze a specific file
  %(prog)s results/tau2_retail_gpt5_trials4/20251120_212535_retail.json

  # Use default file location
  %(prog)s

  # Get help
  %(prog)s --help
        '''
    )

    parser.add_argument(
        'file',
        nargs='?',
        default='/media/zeyu/DA1474031473E145/camel/results/tau2_retail_gpt5_trials4/20251120_212535_retail.json',
        help='Path to the Tau2 benchmark results JSON file (default: %(default)s)'
    )

    args = parser.parse_args()

    # Check if file exists
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    if not file_path.is_file():
        print(f"Error: Not a file: {args.file}", file=sys.stderr)
        sys.exit(1)

    # Run analysis
    try:
        analyze_tau2_results(str(file_path))
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
