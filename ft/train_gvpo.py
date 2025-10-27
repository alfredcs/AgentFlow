#!/usr/bin/env python3
"""
GVPO Training Entry Point for AgentFlow

This script launches GVPO training with AgentFlow infrastructure.
It handles configuration loading, environment setup, and trainer initialization.

Usage:
    python ft/train_gvpo.py
    python ft/train_gvpo.py --config ft/config_gvpo.yaml
    python ft/train_gvpo.py data.train_batch_size=16 algorithm.gvpo_beta=0.15

Features:
    - Loads GVPO configuration from YAML
    - Sets up environment variables
    - Initializes GVPO trainer
    - Supports command-line overrides
    - Production-ready error handling and logging
"""

import sys
import os
from pathlib import Path
import yaml
import argparse
from typing import Dict, Any
import subprocess

# Add parent directory to Python path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file has invalid YAML
    """
    print(f"\n{'='*80}")
    print(f"Loading Configuration")
    print(f"{'='*80}")
    print(f"Config file: {config_path}")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print(f"✓ Configuration loaded successfully")
        return config
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML file: {e}")


def setup_environment(env_config: Dict[str, Any]) -> None:
    """
    Set up environment variables from configuration.

    Args:
        env_config: Dictionary of environment variables
    """
    print(f"\n{'='*80}")
    print(f"Setting Up Environment")
    print(f"{'='*80}")

    for key, value in env_config.items():
        # Convert non-string values to strings
        str_value = str(value)
        os.environ[key] = str_value

        # Mask sensitive keys
        if 'KEY' in key or 'TOKEN' in key or 'PASSWORD' in key:
            display_value = '***' + str_value[-4:] if len(str_value) > 4 else '***'
        else:
            display_value = str_value

        print(f"  {key} = {display_value}")

    print(f"✓ Environment variables set")


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate configuration for GVPO training.

    Args:
        config: Configuration dictionary

    Raises:
        ValueError: If configuration is invalid
    """
    print(f"\n{'='*80}")
    print(f"Validating Configuration")
    print(f"{'='*80}")

    required_sections = ['env', 'python_args']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")

    # Check for GVPO-specific parameters
    python_args = config['python_args']

    if 'algorithm.adv_estimator' not in python_args:
        raise ValueError("Missing algorithm.adv_estimator in config")

    adv_estimator = python_args['algorithm.adv_estimator']
    if adv_estimator != 'gvpo':
        print(f"⚠ Warning: adv_estimator is '{adv_estimator}', expected 'gvpo'")

    # Validate GVPO beta
    if 'algorithm.gvpo_beta' in python_args:
        beta = python_args['algorithm.gvpo_beta']
        if not (0.0 < beta < 1.0):
            print(f"⚠ Warning: gvpo_beta={beta} is outside typical range (0.05-0.15)")

    # Validate rollout samples
    if 'actor_rollout_ref.rollout.n' in python_args:
        n_samples = python_args['actor_rollout_ref.rollout.n']
        if n_samples < 4:
            print(f"⚠ Warning: rollout.n={n_samples} is low. GVPO works best with n>=8")

    print(f"✓ Configuration validated")


def build_command(config: Dict[str, Any], overrides: list) -> list:
    """
    Build training command with arguments.

    Args:
        config: Configuration dictionary
        overrides: List of command-line override arguments

    Returns:
        Command list for subprocess
    """
    print(f"\n{'='*80}")
    print(f"Building Training Command")
    print(f"{'='*80}")

    # Base command - use agentflow.verl with GVPO trainer
    command = ["python", "-m", "agentflow.verl"]

    # Add arguments from config
    python_args = config.get('python_args', {})
    for key, value in python_args.items():
        # Expand environment variables in values
        if isinstance(value, str):
            expanded_value = os.path.expandvars(value)
            command.append(f"{key}={expanded_value}")
        else:
            command.append(f"{key}={value}")

    # Add user overrides
    command.extend(overrides)

    print("Command:")
    print("  " + " \\\n    ".join([str(item) for item in command]))
    print(f"✓ Command built")

    return command


def run_training(command: list) -> int:
    """
    Run training command.

    Args:
        command: Training command list

    Returns:
        Exit code from training process
    """
    print(f"\n{'='*80}")
    print(f"Starting GVPO Training")
    print(f"{'='*80}\n")

    try:
        # Run training with environment variables
        result = subprocess.run(
            command,
            check=False,  # Don't raise exception on non-zero exit
            env=os.environ,
        )
        return result.returncode
    except KeyboardInterrupt:
        print("\n\n⚠ Training interrupted by user")
        return 130  # Standard exit code for Ctrl+C
    except Exception as e:
        print(f"\n\n✗ Error during training: {e}")
        return 1


def main():
    """Main entry point for GVPO training."""
    parser = argparse.ArgumentParser(
        description="Train AgentFlow with GVPO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train with default config
  python ft/train_gvpo.py

  # Train with custom config
  python ft/train_gvpo.py --config my_config.yaml

  # Override specific parameters
  python ft/train_gvpo.py algorithm.gvpo_beta=0.15 data.train_batch_size=16

  # Combine config and overrides
  python ft/train_gvpo.py --config ft/config_gvpo.yaml trainer.total_epochs=10
        """
    )

    parser.add_argument(
        '--config',
        type=str,
        default='ft/config_gvpo.yaml',
        help='Path to YAML configuration file (default: ft/config_gvpo.yaml)'
    )

    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate configuration without training'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print command without executing'
    )

    parser.add_argument(
        'overrides',
        nargs='*',
        help='Config overrides in key=value format'
    )

    args = parser.parse_args()

    print(f"\n{'#'*80}")
    print(f"# GVPO Training for AgentFlow")
    print(f"{'#'*80}\n")

    try:
        # Load configuration
        config = load_config(args.config)

        # Set up environment
        if 'env' in config:
            setup_environment(config['env'])

        # Validate configuration
        validate_config(config)

        if args.validate_only:
            print(f"\n{'='*80}")
            print(f"✓ Configuration validation passed")
            print(f"{'='*80}\n")
            return 0

        # Build command
        command = build_command(config, args.overrides)

        if args.dry_run:
            print(f"\n{'='*80}")
            print(f"✓ Dry run complete (command not executed)")
            print(f"{'='*80}\n")
            return 0

        # Run training
        exit_code = run_training(command)

        # Print final status
        print(f"\n{'='*80}")
        if exit_code == 0:
            print(f"✓ Training completed successfully")
        else:
            print(f"✗ Training failed with exit code {exit_code}")
        print(f"{'='*80}\n")

        return exit_code

    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        return 1
    except ValueError as e:
        print(f"\n✗ Configuration Error: {e}")
        return 1
    except yaml.YAMLError as e:
        print(f"\n✗ YAML Error: {e}")
        return 1
    except KeyboardInterrupt:
        print(f"\n\n⚠ Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
