"""
GVPO (Group Variance Policy Optimization) Algorithm Implementation

This module implements the core GVPO algorithm as described in the paper:
"Group Variance Policy Optimization for Stable Reinforcement Learning"

Key Features:
- Zero-sum weight constraint eliminates intractable partition function
- Unbiased advantage estimation with Bessel correction
- No importance sampling or clipping needed
- Analytical KL integration for better stability

Mathematical Foundation:
    w_i = (R(x,y_i) - R̄) - β(log(π_θ/π_θ') - log(π_θ/π_θ')̄)
    Loss = -β * Σ w_i * log π_θ(y_i|x) / (k-1)

where:
    - R(x,y_i): reward for response y_i to prompt x
    - R̄: mean reward across k responses
    - β: temperature parameter (KL coefficient)
    - π_θ: current policy
    - π_θ': reference policy
    - k: number of responses per prompt
"""

import torch
import torch.nn.functional as F
from typing import Dict, Optional, Tuple
import numpy as np


class GVPOAlgorithm:
    """
    Core GVPO algorithm implementation.

    This class provides the mathematical foundation for GVPO training,
    including advantage computation and loss calculation.
    """

    def __init__(
        self,
        beta: float = 0.1,
        num_samples_per_prompt: int = 8,
        use_bessel_correction: bool = True,
        eps: float = 1e-8
    ):
        """
        Initialize GVPO algorithm.

        Args:
            beta: Temperature parameter for KL regularization (default: 0.1)
                 Higher values = stronger KL penalty
            num_samples_per_prompt: Number of responses (k) per prompt (default: 8)
            use_bessel_correction: Apply k-1 normalization for unbiased estimation (default: True)
            eps: Small constant for numerical stability (default: 1e-8)
        """
        self.beta = beta
        self.k = num_samples_per_prompt
        self.use_bessel_correction = use_bessel_correction
        self.eps = eps

    def compute_gvpo_advantages(
        self,
        rewards: torch.Tensor,
        log_probs_current: torch.Tensor,
        log_probs_ref: torch.Tensor,
        group_sizes: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Compute GVPO advantages (weights) for policy optimization.

        This is the core difference between GVPO and GRPO:
        - GRPO: standardizes rewards by dividing by std
        - GVPO: centers rewards and subtracts policy KL term

        Args:
            rewards: Tensor of shape (batch_size,) containing rewards
            log_probs_current: Log probabilities under current policy, shape (batch_size,)
            log_probs_ref: Log probabilities under reference policy, shape (batch_size,)
            group_sizes: Optional tensor indicating group sizes for variable-k batches
                        If None, assumes all groups have size self.k

        Returns:
            advantages: Tensor of shape (batch_size,) containing GVPO weights
            metrics: Dictionary containing diagnostic metrics
        """
        batch_size = rewards.shape[0]

        # Determine grouping
        if group_sizes is None:
            # Fixed group size: assume batch_size is divisible by k
            assert batch_size % self.k == 0, f"Batch size {batch_size} must be divisible by k={self.k}"
            num_groups = batch_size // self.k
            group_sizes = torch.full((num_groups,), self.k, device=rewards.device)
        else:
            num_groups = len(group_sizes)
            assert batch_size == group_sizes.sum(), "group_sizes must sum to batch_size"

        # Compute log ratio (policy divergence term)
        log_ratio = log_probs_current - log_probs_ref  # shape: (batch_size,)

        # Process each group independently
        advantages = torch.zeros_like(rewards)
        group_metrics = []

        start_idx = 0
        for group_idx in range(num_groups):
            k_group = group_sizes[group_idx].item()
            end_idx = start_idx + k_group

            # Extract group data
            group_rewards = rewards[start_idx:end_idx]
            group_log_ratio = log_ratio[start_idx:end_idx]

            # Step 1: Center rewards (subtract mean)
            reward_mean = group_rewards.mean()
            reward_centered = group_rewards - reward_mean

            # Step 2: Center log ratios (subtract mean)
            log_ratio_mean = group_log_ratio.mean()
            log_ratio_centered = group_log_ratio - log_ratio_mean

            # Step 3: Compute GVPO advantages
            # w_i = (R_i - R̄) - β(s_i - s̄)
            group_advantages = reward_centered - self.beta * log_ratio_centered

            # Verify zero-sum constraint
            advantage_sum = group_advantages.sum()
            assert torch.abs(advantage_sum) < self.eps * k_group, \
                f"Zero-sum constraint violated: sum={advantage_sum.item()}"

            advantages[start_idx:end_idx] = group_advantages

            # Collect metrics for this group
            group_metrics.append({
                'reward_mean': reward_mean.item(),
                'reward_std': group_rewards.std().item(),
                'log_ratio_mean': log_ratio_mean.item(),
                'log_ratio_std': group_log_ratio.std().item(),
                'advantage_std': group_advantages.std().item(),
                'kl_approx': log_ratio_mean.item()  # First-order KL approximation
            })

            start_idx = end_idx

        # Aggregate metrics across all groups
        metrics = {
            'reward_mean': np.mean([m['reward_mean'] for m in group_metrics]),
            'reward_std': np.mean([m['reward_std'] for m in group_metrics]),
            'kl_div': np.mean([m['kl_approx'] for m in group_metrics]),
            'log_ratio_std': np.mean([m['log_ratio_std'] for m in group_metrics]),
            'advantage_std': np.mean([m['advantage_std'] for m in group_metrics]),
        }

        return advantages, metrics

    def compute_gvpo_loss(
        self,
        advantages: torch.Tensor,
        log_probs_current: torch.Tensor,
        group_sizes: Optional[torch.Tensor] = None,
        reduction: str = 'mean'
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Compute GVPO loss function.

        Loss formula:
            L = -β * Σ w_i * log π_θ(y_i|x) / (k-1)

        The (k-1) denominator is Bessel's correction for unbiased variance estimation.

        Args:
            advantages: GVPO advantages from compute_gvpo_advantages
            log_probs_current: Log probabilities under current policy
            group_sizes: Optional group sizes for variable-k batches
            reduction: 'mean' or 'sum' (default: 'mean')

        Returns:
            loss: Scalar loss value
            metrics: Dictionary containing loss components
        """
        batch_size = advantages.shape[0]

        # Determine grouping
        if group_sizes is None:
            num_groups = batch_size // self.k
            group_sizes = torch.full((num_groups,), self.k, device=advantages.device)
        else:
            num_groups = len(group_sizes)

        # Compute per-group loss
        total_loss = 0.0
        start_idx = 0

        for group_idx in range(num_groups):
            k_group = group_sizes[group_idx].item()
            end_idx = start_idx + k_group

            # Extract group data
            group_advantages = advantages[start_idx:end_idx]
            group_log_probs = log_probs_current[start_idx:end_idx]

            # Compute loss for this group
            # L = -β * Σ w_i * log π_θ(y_i|x) / (k-1)
            normalization = (k_group - 1) if self.use_bessel_correction else k_group
            group_loss = -self.beta * (group_advantages * group_log_probs).sum() / normalization

            total_loss += group_loss
            start_idx = end_idx

        # Apply reduction
        if reduction == 'mean':
            loss = total_loss / num_groups
        elif reduction == 'sum':
            loss = total_loss
        else:
            raise ValueError(f"Unknown reduction: {reduction}")

        metrics = {
            'gvpo_loss': loss.item(),
            'num_groups': num_groups,
            'bessel_correction': self.use_bessel_correction
        }

        return loss, metrics

    def compute_advantages_and_loss(
        self,
        rewards: torch.Tensor,
        log_probs_current: torch.Tensor,
        log_probs_ref: torch.Tensor,
        group_sizes: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, float]]:
        """
        Convenience method to compute both advantages and loss in one call.

        Args:
            rewards: Tensor of rewards
            log_probs_current: Log probabilities under current policy
            log_probs_ref: Log probabilities under reference policy
            group_sizes: Optional group sizes

        Returns:
            advantages: GVPO advantages
            loss: GVPO loss
            metrics: Combined metrics from both computations
        """
        advantages, adv_metrics = self.compute_gvpo_advantages(
            rewards, log_probs_current, log_probs_ref, group_sizes
        )

        loss, loss_metrics = self.compute_gvpo_loss(
            advantages, log_probs_current, group_sizes
        )

        # Combine metrics
        metrics = {**adv_metrics, **loss_metrics}

        return advantages, loss, metrics


def compare_grpo_vs_gvpo(
    rewards: torch.Tensor,
    log_probs_current: torch.Tensor,
    log_probs_ref: torch.Tensor,
    k: int = 8,
    beta: float = 0.1
) -> Dict[str, torch.Tensor]:
    """
    Utility function to compare GRPO and GVPO advantage computation.

    This demonstrates the key algorithmic difference between the two methods.

    Args:
        rewards: Tensor of rewards
        log_probs_current: Log probabilities under current policy
        log_probs_ref: Log probabilities under reference policy
        k: Number of samples per group
        beta: Temperature parameter

    Returns:
        Dictionary with GRPO and GVPO advantages and comparison metrics
    """
    batch_size = rewards.shape[0]
    num_groups = batch_size // k

    grpo_advantages = torch.zeros_like(rewards)
    gvpo_advantages = torch.zeros_like(rewards)

    for i in range(num_groups):
        start_idx = i * k
        end_idx = start_idx + k

        group_rewards = rewards[start_idx:end_idx]
        group_log_probs_current = log_probs_current[start_idx:end_idx]
        group_log_probs_ref = log_probs_ref[start_idx:end_idx]

        # GRPO: Standardize rewards (center and divide by std)
        reward_mean = group_rewards.mean()
        reward_std = group_rewards.std() + 1e-8
        grpo_adv = (group_rewards - reward_mean) / reward_std
        grpo_advantages[start_idx:end_idx] = grpo_adv

        # GVPO: Center rewards and subtract KL term (no std division)
        log_ratio = group_log_probs_current - group_log_probs_ref
        log_ratio_mean = log_ratio.mean()
        gvpo_adv = (group_rewards - reward_mean) - beta * (log_ratio - log_ratio_mean)
        gvpo_advantages[start_idx:end_idx] = gvpo_adv

    return {
        'grpo_advantages': grpo_advantages,
        'gvpo_advantages': gvpo_advantages,
        'difference': torch.abs(grpo_advantages - gvpo_advantages).mean(),
        'grpo_std': grpo_advantages.std(),
        'gvpo_std': gvpo_advantages.std()
    }
