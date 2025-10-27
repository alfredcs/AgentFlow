#!/usr/bin/env python3
"""
GRPO vs GVPO Comparison Script

This script demonstrates the key differences between GRPO and GVPO
by computing advantages using both methods on the same data.

Usage:
    python ft/compare_grpo_gvpo.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import torch
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from typing import Tuple

# GVPO implementation
from ft.gvpo_loss import GVPOLoss


def compute_grpo_advantages(
    rewards: torch.Tensor,
    uid: torch.Tensor,
) -> torch.Tensor:
    """
    Compute GRPO advantages.

    GRPO formula: adv_i = (R_i - R̄) / σ_R

    Args:
        rewards: Reward values
        uid: Group identifiers

    Returns:
        GRPO advantages
    """
    advantages = torch.zeros_like(rewards)

    for uid_val in torch.unique(uid):
        group_mask = (uid == uid_val)
        group_indices = group_mask.nonzero(as_tuple=True)[0]

        group_rewards = rewards[group_indices]
        mean_reward = group_rewards.mean()
        std_reward = group_rewards.std()

        if std_reward > 1e-8:
            group_advantages = (group_rewards - mean_reward) / std_reward
        else:
            group_advantages = torch.zeros_like(group_rewards)

        advantages[group_indices] = group_advantages

    return advantages


def compare_methods(
    rewards: torch.Tensor,
    log_probs: torch.Tensor,
    ref_log_probs: torch.Tensor,
    uid: torch.Tensor,
    num_samples: int,
    beta: float = 0.1,
) -> Tuple[torch.Tensor, torch.Tensor, dict]:
    """
    Compare GRPO and GVPO on the same data.

    Args:
        rewards: Reward values
        log_probs: Current policy log probs
        ref_log_probs: Reference policy log probs
        uid: Group identifiers
        num_samples: Number of samples per group
        beta: KL penalty coefficient for GVPO

    Returns:
        Tuple of (grpo_advantages, gvpo_advantages, metrics)
    """
    # Compute GRPO advantages
    grpo_advantages = compute_grpo_advantages(rewards, uid)

    # Compute GVPO advantages
    gvpo = GVPOLoss(beta=beta)
    gvpo_advantages, gvpo_metrics = gvpo.compute_advantages(
        rewards, log_probs, ref_log_probs, uid, num_samples
    )

    # Compute comparison metrics
    metrics = {
        'grpo_mean': grpo_advantages.mean().item(),
        'grpo_std': grpo_advantages.std().item(),
        'grpo_max': grpo_advantages.max().item(),
        'grpo_min': grpo_advantages.min().item(),
        'gvpo_mean': gvpo_advantages.mean().item(),
        'gvpo_std': gvpo_advantages.std().item(),
        'gvpo_max': gvpo_advantages.max().item(),
        'gvpo_min': gvpo_advantages.min().item(),
        'correlation': torch.corrcoef(
            torch.stack([grpo_advantages, gvpo_advantages])
        )[0, 1].item(),
    }

    return grpo_advantages, gvpo_advantages, metrics


def visualize_comparison(
    rewards: torch.Tensor,
    grpo_advantages: torch.Tensor,
    gvpo_advantages: torch.Tensor,
    uid: torch.Tensor,
    save_path: str = 'ft/grpo_vs_gvpo_comparison.png',
):
    """
    Create visualization comparing GRPO and GVPO.

    Args:
        rewards: Reward values
        grpo_advantages: GRPO advantages
        gvpo_advantages: GVPO advantages
        uid: Group identifiers
        save_path: Path to save the plot
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Advantages vs Rewards
    ax = axes[0, 0]
    ax.scatter(rewards.numpy(), grpo_advantages.numpy(),
              alpha=0.6, label='GRPO', s=50)
    ax.scatter(rewards.numpy(), gvpo_advantages.numpy(),
              alpha=0.6, label='GVPO', s=50)
    ax.set_xlabel('Reward', fontsize=12)
    ax.set_ylabel('Advantage', fontsize=12)
    ax.set_title('Advantages vs Rewards', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 2: Advantage Distribution
    ax = axes[0, 1]
    ax.hist(grpo_advantages.numpy(), bins=30, alpha=0.6, label='GRPO',
           density=True)
    ax.hist(gvpo_advantages.numpy(), bins=30, alpha=0.6, label='GVPO',
           density=True)
    ax.set_xlabel('Advantage Value', fontsize=12)
    ax.set_ylabel('Density', fontsize=12)
    ax.set_title('Advantage Distribution', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 3: GRPO vs GVPO Scatter
    ax = axes[1, 0]
    ax.scatter(grpo_advantages.numpy(), gvpo_advantages.numpy(),
              alpha=0.6, s=50)
    ax.plot([grpo_advantages.min(), grpo_advantages.max()],
           [grpo_advantages.min(), grpo_advantages.max()],
           'r--', label='y=x', linewidth=2)
    ax.set_xlabel('GRPO Advantage', fontsize=12)
    ax.set_ylabel('GVPO Advantage', fontsize=12)
    ax.set_title('GRPO vs GVPO Correlation', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 4: Per-group comparison
    ax = axes[1, 1]
    unique_uids = torch.unique(uid)
    grpo_group_means = []
    gvpo_group_means = []

    for uid_val in unique_uids:
        group_mask = (uid == uid_val)
        grpo_group_means.append(grpo_advantages[group_mask].mean().item())
        gvpo_group_means.append(gvpo_advantages[group_mask].mean().item())

    x = np.arange(len(unique_uids))
    width = 0.35

    ax.bar(x - width/2, grpo_group_means, width, label='GRPO', alpha=0.8)
    ax.bar(x + width/2, gvpo_group_means, width, label='GVPO', alpha=0.8)
    ax.set_xlabel('Group ID', fontsize=12)
    ax.set_ylabel('Mean Advantage', fontsize=12)
    ax.set_title('Per-Group Mean Advantages', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{i}' for i in range(len(unique_uids))])
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Visualization saved to: {save_path}")


def print_comparison_table(metrics: dict):
    """Print comparison metrics in a formatted table."""
    print("\n" + "="*70)
    print(" "*20 + "GRPO vs GVPO Comparison")
    print("="*70)
    print(f"{'Metric':<25} {'GRPO':>15} {'GVPO':>15} {'Difference':>15}")
    print("-"*70)

    print(f"{'Mean Advantage':<25} {metrics['grpo_mean']:>15.4f} "
          f"{metrics['gvpo_mean']:>15.4f} "
          f"{metrics['gvpo_mean'] - metrics['grpo_mean']:>15.4f}")

    print(f"{'Std Advantage':<25} {metrics['grpo_std']:>15.4f} "
          f"{metrics['gvpo_std']:>15.4f} "
          f"{metrics['gvpo_std'] - metrics['grpo_std']:>15.4f}")

    print(f"{'Max Advantage':<25} {metrics['grpo_max']:>15.4f} "
          f"{metrics['gvpo_max']:>15.4f} "
          f"{metrics['gvpo_max'] - metrics['grpo_max']:>15.4f}")

    print(f"{'Min Advantage':<25} {metrics['grpo_min']:>15.4f} "
          f"{metrics['gvpo_min']:>15.4f} "
          f"{metrics['gvpo_min'] - metrics['grpo_min']:>15.4f}")

    print("-"*70)
    print(f"{'Correlation':<25} {metrics['correlation']:>46.4f}")
    print("="*70)


def print_explanation():
    """Print explanation of key differences."""
    print("\n" + "="*70)
    print(" "*25 + "Key Differences")
    print("="*70)

    print("\n1. ADVANTAGE COMPUTATION")
    print("   GRPO: adv = (R - R̄) / σ_R")
    print("   GVPO: adv = (R - R̄) - β(log_ratio - log_ratio_̄)")
    print("   ")
    print("   → GRPO normalizes by standard deviation")
    print("   → GVPO incorporates KL divergence analytically")

    print("\n2. NORMALIZATION")
    print("   GRPO: Divides by reward std → unit variance advantages")
    print("   GVPO: Centers only → preserves relative magnitudes")

    print("\n3. KL DIVERGENCE")
    print("   GRPO: Applied as external penalty")
    print("   GVPO: Built into gradient weights")

    print("\n4. THEORETICAL GUARANTEES")
    print("   GRPO: No convergence proof")
    print("   GVPO: Provably converges to KL-constrained optimal policy")

    print("\n5. STABILITY")
    print("   GRPO: Can suffer from importance sampling ratio explosion")
    print("   GVPO: More stable, no importance sampling in gradients")

    print("\n6. EMPIRICAL PERFORMANCE")
    print("   GRPO: Baseline")
    print("   GVPO: +40% on AIME 2024 (14.79 → 20.72)")

    print("="*70)


def main():
    """Main comparison function."""
    print("\n" + "#"*70)
    print("#" + " "*20 + "GRPO vs GVPO Comparison" + " "*20 + "#")
    print("#"*70)

    # Set random seed for reproducibility
    torch.manual_seed(42)

    # Generate synthetic data
    batch_size = 32
    num_samples = 8

    print("\nGenerating synthetic data...")
    print(f"  Batch size: {batch_size}")
    print(f"  Samples per group: {num_samples}")
    print(f"  Total groups: {batch_size // num_samples}")

    # Create diverse reward distribution
    rewards = torch.randn(batch_size) * 2 + 1.0

    # Log probs with some variation
    log_probs = -torch.rand(batch_size) * 3 - 1.0
    ref_log_probs = log_probs + torch.randn(batch_size) * 0.5

    # Group IDs
    uid = torch.repeat_interleave(
        torch.arange(batch_size // num_samples),
        num_samples
    )

    # Compare methods
    print("\nComputing advantages with both methods...")
    beta = 0.1
    grpo_adv, gvpo_adv, metrics = compare_methods(
        rewards, log_probs, ref_log_probs, uid, num_samples, beta=beta
    )

    # Print comparison
    print_comparison_table(metrics)

    # Print explanation
    print_explanation()

    # Create visualization
    print("\nCreating visualization...")
    try:
        visualize_comparison(rewards, grpo_adv, gvpo_adv, uid)
    except Exception as e:
        print(f"⚠ Could not create visualization: {e}")

    print("\n" + "="*70)
    print("✓ Comparison complete!")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
