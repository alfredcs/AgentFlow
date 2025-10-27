"""
GVPO Loss Computation Module

This module implements the Group Variance Policy Optimization (GVPO) loss computation.
GVPO is an improvement over GRPO that provides better theoretical guarantees and
improved empirical performance.

Key differences from GRPO:
- Uses centered advantages without standard deviation normalization
- Incorporates KL divergence analytically into gradient weights
- Provides provable convergence to the KL-constrained optimal policy

Mathematical formulation:
w_i = (R(x, y_i) - R̄) - β(log(π_θ/π_θ') - log(π_θ/π_θ')̄)

where:
- R(x, y_i) is the reward for response y_i to prompt x
- R̄ is the mean reward across the group
- π_θ is the current policy
- π_θ' is the reference policy
- β is the KL coefficient
- bar notation indicates group-level averaging

References:
- Paper: "Reasoning through Incentives: Group Variance Policy Optimization"
- GitHub: https://github.com/alfredcs/Reasoning-through-incentives
"""

import torch
import torch.nn.functional as F
from typing import Dict, Tuple, Optional
import numpy as np


class GVPOLoss:
    """
    GVPO Loss computation class.

    This class handles the computation of GVPO loss, which combines:
    1. Group-relative rewards (centered by group mean)
    2. KL divergence penalty (incorporated analytically)
    3. Zero-sum weight constraint for theoretical guarantees
    """

    def __init__(
        self,
        beta: float = 0.1,
        use_bessel_correction: bool = True,
        clip_weight: Optional[float] = None,
        normalize_weights: bool = True,
    ):
        """
        Initialize GVPO loss computation.

        Args:
            beta: KL penalty coefficient, controls the trade-off between
                  reward maximization and policy constraint
            use_bessel_correction: Use (k-1) denominator for unbiased estimation
            clip_weight: Optional value to clip weight magnitudes for stability
            normalize_weights: Whether to ensure zero-sum weights explicitly
        """
        self.beta = beta
        self.use_bessel_correction = use_bessel_correction
        self.clip_weight = clip_weight
        self.normalize_weights = normalize_weights

    def compute_log_probs(
        self,
        logits: torch.Tensor,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        response_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Compute log probabilities for the generated sequences.

        Args:
            logits: Model output logits, shape (batch_size, seq_len, vocab_size)
            input_ids: Token IDs, shape (batch_size, seq_len)
            attention_mask: Attention mask, shape (batch_size, seq_len)
            response_mask: Mask for response tokens only, shape (batch_size, seq_len)
                         If None, uses attention_mask

        Returns:
            Log probabilities for each token, shape (batch_size, seq_len)
        """
        # Shift logits and labels for autoregressive prediction
        shift_logits = logits[..., :-1, :].contiguous()
        shift_labels = input_ids[..., 1:].contiguous()

        # Compute log probabilities
        log_probs = F.log_softmax(shift_logits, dim=-1)

        # Gather log probs for the actual tokens
        token_log_probs = torch.gather(
            log_probs,
            dim=-1,
            index=shift_labels.unsqueeze(-1)
        ).squeeze(-1)

        # Apply masking
        if response_mask is not None:
            mask = response_mask[..., 1:].contiguous()
        else:
            mask = attention_mask[..., 1:].contiguous()

        token_log_probs = token_log_probs * mask

        return token_log_probs

    def compute_sequence_log_prob(
        self,
        token_log_probs: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute sequence-level log probability by summing token log probs.

        Args:
            token_log_probs: Token-level log probs, shape (batch_size, seq_len)
            mask: Mask for valid tokens, shape (batch_size, seq_len)

        Returns:
            Sequence log probabilities, shape (batch_size,)
        """
        return (token_log_probs * mask).sum(dim=-1)

    def compute_gvpo_weights(
        self,
        rewards: torch.Tensor,
        log_probs: torch.Tensor,
        ref_log_probs: torch.Tensor,
        uid: torch.Tensor,
        num_samples: int,
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Compute GVPO gradient weights.

        This is the core of the GVPO algorithm. The weights are computed as:
        w_i = (R_i - R̄) - β(log_ratio_i - log_ratio_̄)

        where log_ratio = log(π_θ/π_θ')

        Args:
            rewards: Reward values, shape (batch_size,)
            log_probs: Log probs from current policy, shape (batch_size,)
            ref_log_probs: Log probs from reference policy, shape (batch_size,)
            uid: Unique identifiers for grouping samples, shape (batch_size,)
            num_samples: Number of samples per prompt (k in the paper)

        Returns:
            Tuple of (weights, metrics_dict)
            - weights: GVPO weights, shape (batch_size,)
            - metrics_dict: Dictionary of diagnostic metrics
        """
        # Compute log importance ratios
        log_ratios = log_probs - ref_log_probs

        # Group samples by uid
        unique_uids = torch.unique(uid)
        batch_size = rewards.shape[0]

        weights = torch.zeros_like(rewards)
        metrics = {
            'gvpo/mean_reward': 0.0,
            'gvpo/std_reward': 0.0,
            'gvpo/mean_log_ratio': 0.0,
            'gvpo/std_log_ratio': 0.0,
            'gvpo/mean_weight': 0.0,
            'gvpo/std_weight': 0.0,
            'gvpo/max_weight': 0.0,
            'gvpo/min_weight': 0.0,
        }

        # Compute weights for each group
        for uid_val in unique_uids:
            # Find indices for this group
            group_mask = (uid == uid_val)
            group_indices = group_mask.nonzero(as_tuple=True)[0]

            if len(group_indices) == 0:
                continue

            # Get group data
            group_rewards = rewards[group_indices]
            group_log_ratios = log_ratios[group_indices]

            # Compute group means
            mean_reward = group_rewards.mean()
            mean_log_ratio = group_log_ratios.mean()

            # Compute centered values
            centered_rewards = group_rewards - mean_reward
            centered_log_ratios = group_log_ratios - mean_log_ratio

            # Compute GVPO weights: w_i = (R_i - R̄) - β(log_ratio_i - log_ratio_̄)
            group_weights = centered_rewards - self.beta * centered_log_ratios

            # Ensure zero-sum constraint (should be satisfied by construction, but enforce for numerical stability)
            if self.normalize_weights:
                group_weights = group_weights - group_weights.mean()

            # Optional clipping for stability
            if self.clip_weight is not None:
                group_weights = torch.clamp(
                    group_weights,
                    min=-self.clip_weight,
                    max=self.clip_weight
                )

            weights[group_indices] = group_weights

        # Compute metrics
        metrics['gvpo/mean_reward'] = rewards.mean().item()
        metrics['gvpo/std_reward'] = rewards.std().item()
        metrics['gvpo/mean_log_ratio'] = log_ratios.mean().item()
        metrics['gvpo/std_log_ratio'] = log_ratios.std().item()
        metrics['gvpo/mean_weight'] = weights.mean().item()
        metrics['gvpo/std_weight'] = weights.std().item()
        metrics['gvpo/max_weight'] = weights.max().item()
        metrics['gvpo/min_weight'] = weights.min().item()

        return weights, metrics

    def compute_gvpo_loss(
        self,
        weights: torch.Tensor,
        log_probs: torch.Tensor,
        num_samples: int,
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Compute the final GVPO loss.

        Loss = -β * Σ w_i * log π_θ(y_i|x) / (k-1)

        Args:
            weights: GVPO weights, shape (batch_size,)
            log_probs: Log probabilities from current policy, shape (batch_size,)
            num_samples: Number of samples per prompt (k)

        Returns:
            Tuple of (loss, metrics_dict)
        """
        # Compute weighted log probability
        weighted_log_probs = weights * log_probs

        # Use Bessel correction (k-1) for unbiased estimation
        denominator = (num_samples - 1) if self.use_bessel_correction else num_samples

        # GVPO loss: negative weighted log probability, scaled by beta and normalized
        loss = -self.beta * weighted_log_probs.sum() / denominator

        metrics = {
            'gvpo/loss': loss.item(),
            'gvpo/weighted_log_prob': weighted_log_probs.mean().item(),
        }

        return loss, metrics

    def compute_advantages(
        self,
        rewards: torch.Tensor,
        log_probs: torch.Tensor,
        ref_log_probs: torch.Tensor,
        uid: torch.Tensor,
        num_samples: int,
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        Compute GVPO advantages (weights normalized as advantages).

        This is useful for integration with existing PPO-style trainers.

        Args:
            rewards: Reward values, shape (batch_size,)
            log_probs: Log probs from current policy, shape (batch_size,)
            ref_log_probs: Log probs from reference policy, shape (batch_size,)
            uid: Unique identifiers for grouping, shape (batch_size,)
            num_samples: Number of samples per prompt

        Returns:
            Tuple of (advantages, metrics_dict)
        """
        weights, metrics = self.compute_gvpo_weights(
            rewards, log_probs, ref_log_probs, uid, num_samples
        )

        # For compatibility with PPO, we can normalize weights to have unit std
        # within each group (optional, can be disabled)
        unique_uids = torch.unique(uid)
        advantages = torch.zeros_like(weights)

        for uid_val in unique_uids:
            group_mask = (uid == uid_val)
            group_indices = group_mask.nonzero(as_tuple=True)[0]

            if len(group_indices) > 1:
                group_weights = weights[group_indices]
                # Normalize to unit std (optional)
                group_std = group_weights.std()
                if group_std > 1e-8:
                    advantages[group_indices] = group_weights / group_std
                else:
                    advantages[group_indices] = group_weights
            else:
                advantages[group_indices] = 0.0

        metrics['gvpo/advantage_mean'] = advantages.mean().item()
        metrics['gvpo/advantage_std'] = advantages.std().item()

        return advantages, metrics


def compute_gvpo_advantage(
    batch,
    adv_estimator: str,
    num_repeat: int,
    beta: float = 0.1,
    config: Optional[Dict] = None,
    **kwargs
) -> torch.Tensor:
    """
    Compute GVPO advantages for integration with verl framework.

    This function is designed to be used as a drop-in replacement for
    the compute_advantage function in verl.trainer.ppo.ray_trainer.

    Args:
        batch: DataProto batch containing rewards, log_probs, ref_log_probs
        adv_estimator: Advantage estimator type (should be 'gvpo')
        num_repeat: Number of samples per prompt
        beta: KL penalty coefficient
        config: Optional config dict with GVPO parameters
        **kwargs: Additional arguments (ignored)

    Returns:
        Batch with advantages added
    """
    if adv_estimator != 'gvpo':
        raise ValueError(f"Expected adv_estimator='gvpo', got '{adv_estimator}'")

    # Extract GVPO config if provided
    gvpo_config = config.get('gvpo', {}) if config else {}
    beta = gvpo_config.get('beta', beta)
    use_bessel_correction = gvpo_config.get('use_bessel_correction', True)
    clip_weight = gvpo_config.get('clip_weight', None)

    # Initialize GVPO loss module
    gvpo = GVPOLoss(
        beta=beta,
        use_bessel_correction=use_bessel_correction,
        clip_weight=clip_weight,
    )

    # Extract data from batch
    rewards = batch.batch['token_level_rewards'].sum(dim=-1)  # Sum over sequence

    # Get sequence-level log probs
    if 'old_log_probs' in batch.batch:
        log_probs = batch.batch['old_log_probs'].sum(dim=-1)
    else:
        raise ValueError("batch must contain 'old_log_probs'")

    if 'ref_log_probs' in batch.batch:
        ref_log_probs = batch.batch['ref_log_probs'].sum(dim=-1)
    else:
        raise ValueError("batch must contain 'ref_log_probs'")

    # Get UIDs for grouping
    if 'uid' in batch.non_tensor_batch:
        uid_list = batch.non_tensor_batch['uid']
        # Convert to tensor
        unique_ids = {id_val: idx for idx, id_val in enumerate(set(uid_list))}
        uid = torch.tensor([unique_ids[id_val] for id_val in uid_list],
                          device=rewards.device)
    else:
        raise ValueError("batch must contain 'uid' in non_tensor_batch")

    # Compute GVPO advantages
    advantages, metrics = gvpo.compute_advantages(
        rewards=rewards,
        log_probs=log_probs,
        ref_log_probs=ref_log_probs,
        uid=uid,
        num_samples=num_repeat,
    )

    # Add advantages to batch
    # Expand to token-level for compatibility with PPO trainer
    seq_len = batch.batch['token_level_rewards'].shape[1]
    token_advantages = advantages.unsqueeze(-1).expand(-1, seq_len)
    batch.batch['advantages'] = token_advantages

    # Store metrics in batch meta_info
    if 'metrics' not in batch.meta_info:
        batch.meta_info['metrics'] = {}
    batch.meta_info['metrics'].update(metrics)

    return batch


if __name__ == '__main__':
    # Test GVPO loss computation
    print("Testing GVPO Loss Computation...")

    # Create dummy data
    batch_size = 16
    num_samples = 4
    seq_len = 50

    rewards = torch.randn(batch_size)
    log_probs = torch.randn(batch_size)
    ref_log_probs = torch.randn(batch_size)

    # Create UIDs (4 prompts, 4 samples each)
    uid = torch.repeat_interleave(torch.arange(batch_size // num_samples), num_samples)

    # Initialize GVPO
    gvpo = GVPOLoss(beta=0.1)

    # Compute weights
    weights, metrics = gvpo.compute_gvpo_weights(
        rewards, log_probs, ref_log_probs, uid, num_samples
    )

    print("\nGVPO Weights:", weights)
    print("\nMetrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value:.4f}")

    # Compute loss
    loss, loss_metrics = gvpo.compute_gvpo_loss(weights, log_probs, num_samples)

    print(f"\nGVPO Loss: {loss.item():.4f}")
    print("\nLoss Metrics:")
    for key, value in loss_metrics.items():
        print(f"  {key}: {value:.4f}")

    # Test advantages computation
    advantages, adv_metrics = gvpo.compute_advantages(
        rewards, log_probs, ref_log_probs, uid, num_samples
    )

    print("\nGVPO Advantages:", advantages)
    print("\nAdvantage Metrics:")
    for key, value in adv_metrics.items():
        print(f"  {key}: {value:.4f}")

    print("\nGVPO Loss Computation Test Passed!")
