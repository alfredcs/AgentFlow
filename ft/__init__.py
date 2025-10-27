"""
GVPO Training Package for AgentFlow

This package provides a complete implementation of Group Variance Policy
Optimization (GVPO) for AgentFlow, replacing GRPO with a theoretically
superior algorithm.

Modules:
    gvpo_loss: Core GVPO loss computation and advantage estimation
    gvpo_trainer: GVPO trainer extending AgentFlowTrainer
    train_gvpo: Training entry point script

Key Classes:
    GVPOLoss: GVPO loss computation
    GVPOAgentFlowTrainer: GVPO trainer for AgentFlow

Key Functions:
    compute_gvpo_advantage: Compute GVPO advantages for verl integration
    create_gvpo_trainer: Factory function for GVPO trainer

Usage:
    from ft.gvpo_loss import GVPOLoss
    from ft.gvpo_trainer import GVPOAgentFlowTrainer

    # Initialize GVPO loss
    gvpo = GVPOLoss(beta=0.1)

    # Or use the trainer directly
    trainer = GVPOAgentFlowTrainer(config)
    trainer.fit()

Version: 1.0.0
"""

__version__ = '1.0.0'
__author__ = 'AgentFlow + GVPO Team'

# Import key components for easy access
from ft.gvpo_loss import (
    GVPOLoss,
    compute_gvpo_advantage,
)

try:
    from ft.gvpo_trainer import (
        GVPOAgentFlowTrainer,
        create_gvpo_trainer,
    )
except ImportError:
    # May fail if agentflow is not installed
    GVPOAgentFlowTrainer = None
    create_gvpo_trainer = None

__all__ = [
    'GVPOLoss',
    'compute_gvpo_advantage',
    'GVPOAgentFlowTrainer',
    'create_gvpo_trainer',
]
