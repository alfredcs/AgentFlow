"""
GVPO Trainer for AgentFlow

This module extends the AgentFlowTrainer to use GVPO instead of GRPO
for advantage computation. It provides a drop-in replacement that requires
minimal changes to the existing training pipeline.

Key Features:
- Seamless integration with existing AgentFlow infrastructure
- Uses GVPO for advantage computation instead of GRPO
- Maintains compatibility with verl framework
- Supports all AgentFlow features (agent mode, async rollout, etc.)

Usage:
    Replace 'algorithm.adv_estimator: grpo' with 'algorithm.adv_estimator: gvpo'
    in your config file and use this trainer instead of AgentFlowTrainer.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import torch
from typing import Dict, Optional
from copy import deepcopy

from verl import DataProto
from verl.trainer.ppo.ray_trainer import (
    AdvantageEstimator,
    apply_kl_penalty,
    compute_response_mask,
)
from verl.trainer.ppo.core_algos import agg_loss
from verl.trainer.ppo.metric_utils import (
    compute_data_metrics,
    compute_throughout_metrics,
    compute_timing_metrics,
)
from verl.protocol import pad_dataproto_to_divisor, unpad_dataproto
from verl.utils.metric import reduce_metrics

# Import AgentFlowTrainer from the existing codebase
from agentflow.verl.trainer import AgentFlowTrainer

# Import GVPO loss computation
from ft.gvpo_loss import compute_gvpo_advantage, GVPOLoss


class GVPOAgentFlowTrainer(AgentFlowTrainer):
    """
    GVPO-enhanced AgentFlow Trainer.

    This trainer extends AgentFlowTrainer to use GVPO (Group Variance Policy
    Optimization) instead of GRPO for advantage computation. GVPO provides:

    1. Better theoretical guarantees (provable convergence to optimal policy)
    2. More stable training (no importance sampling ratio explosion)
    3. Improved empirical performance (especially on complex reasoning tasks)

    The trainer is designed to be a drop-in replacement - just change the
    adv_estimator in config from 'grpo' to 'gvpo' and use this trainer class.
    """

    def __init__(self, *args, **kwargs):
        """Initialize GVPO trainer with same arguments as AgentFlowTrainer."""
        super().__init__(*args, **kwargs)

        # Extract GVPO-specific configuration
        self.gvpo_beta = self.config.algorithm.get('gvpo_beta', 0.1)
        self.gvpo_use_bessel_correction = self.config.algorithm.get(
            'gvpo_use_bessel_correction', True
        )
        self.gvpo_clip_weight = self.config.algorithm.get('gvpo_clip_weight', None)
        self.gvpo_normalize_weights = self.config.algorithm.get(
            'gvpo_normalize_weights', True
        )

        # Initialize GVPO loss module
        self.gvpo_loss = GVPOLoss(
            beta=self.gvpo_beta,
            use_bessel_correction=self.gvpo_use_bessel_correction,
            clip_weight=self.gvpo_clip_weight,
            normalize_weights=self.gvpo_normalize_weights,
        )

        print(f"\n{'='*80}")
        print(f"GVPO Trainer Initialized")
        print(f"{'='*80}")
        print(f"GVPO Beta (KL coefficient): {self.gvpo_beta}")
        print(f"Use Bessel Correction: {self.gvpo_use_bessel_correction}")
        print(f"Clip Weight: {self.gvpo_clip_weight}")
        print(f"Normalize Weights: {self.gvpo_normalize_weights}")
        print(f"{'='*80}\n")

    def _compute_gvpo_advantages(self, batch: DataProto) -> DataProto:
        """
        Compute GVPO advantages for the batch.

        This replaces the standard advantage computation with GVPO-specific logic.

        Args:
            batch: DataProto containing rewards, log_probs, ref_log_probs, and uid

        Returns:
            DataProto with advantages added
        """
        # Extract sequence-level values
        # token_level_rewards should be summed to get total reward
        if 'token_level_rewards' in batch.batch:
            rewards = batch.batch['token_level_rewards'].sum(dim=-1)
        else:
            raise ValueError("Batch must contain 'token_level_rewards'")

        # Get log probabilities (summed over sequence)
        if 'old_log_probs' in batch.batch:
            # old_log_probs is token-level, sum to get sequence-level
            response_mask = batch.batch.get('response_mask',
                                           batch.batch.get('attention_mask'))
            log_probs = (batch.batch['old_log_probs'] * response_mask).sum(dim=-1)
        else:
            raise ValueError("Batch must contain 'old_log_probs'")

        if 'ref_log_probs' in batch.batch:
            # ref_log_probs is token-level, sum to get sequence-level
            ref_log_probs = (batch.batch['ref_log_probs'] * response_mask).sum(dim=-1)
        else:
            raise ValueError("Batch must contain 'ref_log_probs'")

        # Get UIDs for grouping
        if 'uid' in batch.non_tensor_batch:
            uid_list = batch.non_tensor_batch['uid']
            # Convert to tensor with proper device
            unique_ids = {id_val: idx for idx, id_val in enumerate(set(uid_list))}
            uid = torch.tensor(
                [unique_ids[id_val] for id_val in uid_list],
                device=rewards.device
            )
        else:
            raise ValueError("Batch must contain 'uid' in non_tensor_batch for GVPO")

        # Compute GVPO weights
        weights, gvpo_metrics = self.gvpo_loss.compute_gvpo_weights(
            rewards=rewards,
            log_probs=log_probs,
            ref_log_probs=ref_log_probs,
            uid=uid,
            num_samples=self.config.actor_rollout_ref.rollout.n,
        )

        # Convert weights to advantages (expand to token-level)
        seq_len = batch.batch['token_level_rewards'].shape[1]
        token_advantages = weights.unsqueeze(-1).expand(-1, seq_len)

        # Add advantages to batch
        batch.batch['advantages'] = token_advantages

        # Store metrics
        if 'metrics' not in batch.meta_info:
            batch.meta_info['metrics'] = {}
        batch.meta_info['metrics'].update(gvpo_metrics)

        return batch

    def _train_step(self, batch_dict: dict) -> dict:
        """
        Override train step to use GVPO advantage computation.

        This method is nearly identical to the parent class, with the key difference
        being the use of GVPO for advantage computation instead of GRPO.
        """
        batch: DataProto = DataProto.from_single_dict(batch_dict)
        metrics = {}
        timing_raw = {}

        # Data validation
        print(f"Training data keys: {batch_dict.keys()}")
        for key, value in batch_dict.items():
            if isinstance(value, list):
                print(f"Training data {key} length: {len(value)}")
                if len(value) == 0:
                    print(f"Warning: Empty data in {key}")
            elif isinstance(value, torch.Tensor):
                print(f"Training data {key} shape: {value.shape}")
                if value.numel() == 0:
                    print(f"Warning: Empty tensor in {key}")

        if not batch_dict or all(
            (isinstance(v, list) and len(v) == 0) or
            (isinstance(v, torch.Tensor) and v.numel() == 0)
            for v in batch_dict.values()
        ):
            raise ValueError("Training data is empty. Check your training dataset.")

        # Import timer context manager
        from agentflow.verl.trainer import _timer

        with _timer("step", timing_raw):
            gen_batch = batch

            # Generate rollouts
            with _timer("gen", timing_raw):
                self.async_rollout_manager.wake_up()
                self.agent_mode_daemon.set_up_data_and_server(
                    gen_batch.non_tensor_batch,
                    self.async_rollout_manager.server_addresses
                )

                if self.agent_mode_daemon._total_tasks_queued == 0:
                    raise ValueError("No training tasks were queued.")

                self.agent_mode_daemon.run_until_all_finished()

                if len(self.agent_mode_daemon._completed_rollouts) == 0:
                    raise ValueError("No training tasks completed.")

                batch, agent_metrics = self.agent_mode_daemon.get_train_data_batch(
                    max_prompt_length=self.config.data.max_prompt_length,
                    max_response_length=self.config.data.max_response_length,
                    device=gen_batch.batch["fake_ids"].device,
                )
                metrics.update(agent_metrics)
                self.agent_mode_daemon.clear_data_and_server()
                self.async_rollout_manager.sleep()

            # Handle REMAX baseline if needed
            if self.config.algorithm.adv_estimator == AdvantageEstimator.REMAX:
                with _timer("gen_max", timing_raw):
                    gen_baseline_batch = deepcopy(gen_batch)
                    gen_baseline_batch.meta_info["do_sample"] = False
                    gen_baseline_output = self.actor_rollout_wg.generate_sequences(
                        gen_baseline_batch
                    )

                    batch = batch.union(gen_baseline_output)
                    reward_baseline_tensor = self.reward_fn(batch)
                    reward_baseline_tensor = reward_baseline_tensor.sum(dim=-1)

                    batch.pop(batch_keys=list(gen_baseline_output.batch.keys()))
                    batch.batch["reward_baselines"] = reward_baseline_tensor

                    del gen_baseline_batch, gen_baseline_output

            # Set UID for grouping
            batch.non_tensor_batch["uid"] = batch.non_tensor_batch["data_id_list"]

            # Compute response mask
            batch.batch["response_mask"] = compute_response_mask(batch)

            # Compute global valid tokens
            batch.meta_info["global_token_num"] = torch.sum(
                batch.batch["attention_mask"], dim=-1
            ).tolist()

            # Compute rewards
            with _timer("reward", timing_raw):
                if self.use_rm:
                    reward_tensor = self.rm_wg.compute_rm_score(batch)
                    batch = batch.union(reward_tensor)

            # Pad for parallel computation
            batch, pad_size = pad_dataproto_to_divisor(
                batch, self.actor_rollout_wg.world_size
            )

            # Recompute old_log_probs
            with _timer("old_log_prob", timing_raw):
                old_log_prob = self.actor_rollout_wg.compute_log_prob(batch)
                entropys = old_log_prob.batch["entropys"]
                response_masks = batch.batch["response_mask"]
                loss_agg_mode = self.config.actor_rollout_ref.actor.loss_agg_mode
                entropy_loss = agg_loss(
                    loss_mat=entropys,
                    loss_mask=response_masks,
                    loss_agg_mode=loss_agg_mode
                )
                old_log_prob_metrics = {"actor/entropy_loss": entropy_loss.detach().item()}
                metrics.update(old_log_prob_metrics)
                old_log_prob.batch.pop("entropys")
                batch = batch.union(old_log_prob)

            # Compute reference log_prob
            if self.use_reference_policy:
                with _timer("ref", timing_raw):
                    ref_log_prob = self.ref_policy_wg.compute_ref_log_prob(batch)
                    batch = batch.union(ref_log_prob)

            # Compute values (if using critic)
            if self.use_critic:
                with _timer("values", timing_raw):
                    values = self.critic_wg.compute_values(batch)
                    batch = batch.union(values)

            # Unpad for advantage computation
            batch = unpad_dataproto(batch, pad_size=pad_size)

            # ============================================================
            # GVPO-specific advantage computation
            # ============================================================
            with _timer("adv", timing_raw):
                # Apply KL penalty to rewards if configured
                if self.config.algorithm.use_kl_in_reward:
                    batch, kl_metrics = apply_kl_penalty(
                        batch,
                        kl_ctrl=self.kl_ctrl_in_reward,
                        kl_penalty=self.config.algorithm.kl_penalty
                    )
                    metrics.update(kl_metrics)
                else:
                    batch.batch["token_level_rewards"] = batch.batch["token_level_scores"]

                # Use GVPO for advantage computation
                if self.config.algorithm.adv_estimator == 'gvpo':
                    batch = self._compute_gvpo_advantages(batch)
                    # Add GVPO metrics
                    if 'metrics' in batch.meta_info:
                        metrics.update(batch.meta_info['metrics'])
                else:
                    # Fall back to parent class implementation
                    from verl.trainer.ppo.ray_trainer import compute_advantage
                    batch = compute_advantage(
                        batch,
                        adv_estimator=self.config.algorithm.adv_estimator,
                        gamma=self.config.algorithm.gamma,
                        lam=self.config.algorithm.lam,
                        num_repeat=self.config.actor_rollout_ref.rollout.n,
                        norm_adv_by_std_in_grpo=self.config.algorithm.get(
                            "norm_adv_by_std_in_grpo", True
                        ),
                        config=self.config.algorithm,
                    )

            # Drop samples and balance batch
            keep_indices = (~batch.batch["is_drop_mask"]).nonzero(as_tuple=True)[0]
            metrics["agent_mode/n_dropped_sample_because_of_prompt"] = (
                batch.batch["is_drop_mask"].shape[0] - keep_indices.shape[0]
            )
            batch = batch[keep_indices]

            # Round to mini-batch size
            import random
            mini_batch_size = self.config.actor_rollout_ref.actor.ppo_mini_batch_size
            n_transition = len(batch)

            random_indices = list(range(n_transition))
            random.shuffle(random_indices)
            batch.reorder(torch.tensor(random_indices).type(torch.int32))
            n_remained_transition = n_transition // mini_batch_size * mini_batch_size
            batch = batch[list(range(n_remained_transition))]
            metrics["agent_mode/n_dropped_sample_because_of_mini_batch"] = (
                n_transition - n_remained_transition
            )

            n_transition = len(batch)
            # Make divisible by k_partitions
            k_partitions = self.config.trainer.n_gpus_per_node
            n_remained_transition = n_transition // k_partitions * k_partitions
            if n_remained_transition != n_transition:
                batch = batch[list(range(n_remained_transition))]
            metrics["agent_mode/n_dropped_sample_because_of_gpu_partitions"] = (
                n_transition - n_remained_transition
            )

            # Balance batch
            if self.config.trainer.balance_batch:
                self._balance_batch(batch, metrics=metrics)

            # Update critic
            if self.use_critic:
                with _timer("update_critic", timing_raw):
                    critic_output = self.critic_wg.update_critic(batch)
                critic_output_metrics = reduce_metrics(critic_output.meta_info["metrics"])
                metrics.update(critic_output_metrics)

            # Update actor (after critic warmup)
            if self.config.trainer.critic_warmup <= self.global_steps:
                with _timer("update_actor", timing_raw):
                    batch.meta_info["multi_turn"] = (
                        self.config.actor_rollout_ref.rollout.multi_turn.enable
                    )
                    actor_output = self.actor_rollout_wg.update_actor(batch)
                actor_output_metrics = reduce_metrics(actor_output.meta_info["metrics"])
                metrics.update(actor_output_metrics)

        # Compute training metrics
        metrics.update(compute_data_metrics(batch=batch, use_critic=self.use_critic))
        metrics.update(compute_timing_metrics(batch=batch, timing_raw=timing_raw))

        n_gpus = self.resource_pool_manager.get_n_gpus()
        metrics.update(
            compute_throughout_metrics(batch=batch, timing_raw=timing_raw, n_gpus=n_gpus)
        )

        return metrics


def create_gvpo_trainer(*args, **kwargs):
    """
    Factory function to create GVPO trainer.

    This is useful for maintaining compatibility with existing training scripts.
    """
    return GVPOAgentFlowTrainer(*args, **kwargs)


if __name__ == '__main__':
    print("GVPO Trainer Module")
    print("=" * 80)
    print("This module provides GVPOAgentFlowTrainer, a drop-in replacement")
    print("for AgentFlowTrainer that uses GVPO instead of GRPO.")
    print("\nKey features:")
    print("  - Seamless integration with AgentFlow infrastructure")
    print("  - GVPO advantage computation with theoretical guarantees")
    print("  - Improved stability and performance")
    print("\nUsage:")
    print("  1. Set algorithm.adv_estimator: 'gvpo' in config")
    print("  2. Use GVPOAgentFlowTrainer instead of AgentFlowTrainer")
    print("=" * 80)
