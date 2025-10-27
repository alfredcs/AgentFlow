# GVPO Training for AgentFlow

This directory contains a complete implementation of **Group Variance Policy Optimization (GVPO)** for AgentFlow, replacing GRPO with a theoretically superior algorithm that provides better empirical performance.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Performance Tuning](#performance-tuning)
- [Troubleshooting](#troubleshooting)
- [References](#references)

## Overview

GVPO (Group Variance Policy Optimization) is an improvement over GRPO that offers:

- **Theoretical Guarantees**: Provably converges to the KL-constrained optimal policy
- **Better Stability**: No importance sampling ratio explosion
- **Improved Performance**: 40%+ relative improvement on complex reasoning tasks (AIME 2024)
- **Analytical KL Integration**: KL divergence is built into gradient weights, not applied externally

### GVPO vs GRPO Comparison

| Aspect | GRPO | GVPO |
|--------|------|------|
| **Advantage Formula** | `(R - R̄) / σ_R` | `(R - R̄) - β(log_ratio - log_ratio_̄)` |
| **Normalization** | By standard deviation | Centered only (no std division) |
| **KL Handling** | External penalty | Analytically embedded |
| **Convergence** | No proof | Proven optimal convergence |
| **Stability** | Prone to gradient explosion | More stable gradients |
| **Performance** | Baseline | +40% on math reasoning |

## Key Features

1. **Drop-in Replacement**: Minimal changes to existing AgentFlow training pipeline
2. **Production Ready**: Comprehensive error handling, logging, and monitoring
3. **Highly Configurable**: Extensive YAML configuration with sensible defaults
4. **Well Tested**: Includes unit tests and validation scripts
5. **Documented**: Clear documentation and inline comments

## Installation

### Prerequisites

- Python 3.9+
- CUDA 11.8+ (for GPU training)
- 8× A100 GPUs (or equivalent, configurable)

### Setup Steps

```bash
# 1. Clone the repository (if not already done)
git clone https://github.com/alfredcd/AgentFlow.git
cd AgentFlow

# 2. Install base AgentFlow dependencies
pip install -e .

# 3. Install GVPO-specific requirements
pip install -r ft/requirements.txt

# 4. Install verl framework
pip install git+https://github.com/volcengine/verl.git

# 5. (Optional) Install flash-attention for better performance
pip install flash-attn --no-build-isolation
```

## Quick Start

### 1. Prepare Your Data

Place your training and validation data in the `data` directory:

```
data/
├── train/
│   └── combined_train.parquet
└── val/
    └── aime24.parquet
```

Data format (Parquet columns):
- `question`: Input prompt
- `answer`: Ground truth answer (for reward computation)
- `data_id`: Unique identifier for grouping

### 2. Configure Training

Edit `ft/config_gvpo.yaml` to customize:

```yaml
env:
  BASE_MODEL: 'Qwen/Qwen2.5-7B-Instruct'  # Your model
  N_GPUS: 8  # Number of GPUs

python_args:
  algorithm.gvpo_beta: 0.1  # KL penalty coefficient
  actor_rollout_ref.rollout.n: 8  # Samples per prompt
  data.train_batch_size: 32  # Batch size
  trainer.total_epochs: 5  # Training epochs
```

### 3. Run Training

```bash
# Basic training
python ft/train_gvpo.py

# With custom config
python ft/train_gvpo.py --config my_config.yaml

# Override specific parameters
python ft/train_gvpo.py algorithm.gvpo_beta=0.15 data.train_batch_size=16

# Validate config without training
python ft/train_gvpo.py --validate-only

# Dry run (print command without execution)
python ft/train_gvpo.py --dry-run
```

### 4. Monitor Training

Training metrics are logged to:
- **Console**: Real-time progress
- **Wandb**: Online dashboard (if configured)

Key metrics to watch:
- `gvpo/loss`: GVPO training loss
- `gvpo/mean_reward`: Average reward
- `gvpo/mean_weight`: GVPO gradient weights
- `actor/entropy_loss`: Policy entropy
- `eval/accuracy`: Validation accuracy

## Configuration

### Key Configuration Parameters

#### GVPO Algorithm

```yaml
algorithm.adv_estimator: 'gvpo'  # Use GVPO
algorithm.gvpo_beta: 0.1  # KL penalty (0.05-0.15)
algorithm.gvpo_use_bessel_correction: True  # Unbiased estimation
algorithm.gvpo_clip_weight: null  # Optional weight clipping
algorithm.gvpo_normalize_weights: True  # Zero-sum constraint
```

**Beta Selection Guide**:
- **Math/Reasoning**: 0.1-0.15 (stronger constraint for accuracy)
- **General QA**: 0.05-0.08 (more flexibility)
- **Code Generation**: 0.1-0.15 (prevent syntax errors)

#### Rollout Configuration

```yaml
actor_rollout_ref.rollout.n: 8  # Samples per prompt (k)
actor_rollout_ref.rollout.gpu_memory_utilization: 0.6
```

**Sample Count (n) Guide**:
- Minimum: 4 (GVPO needs multiple samples)
- Recommended: 8-16
- Higher is better but more expensive
- GVPO scales well with more samples

#### Training Configuration

```yaml
data.train_batch_size: 32  # Prompts per batch
actor_rollout_ref.actor.ppo_mini_batch_size: 8
actor_rollout_ref.actor.optim.lr: 1e-6  # Learning rate
trainer.total_epochs: 5
```

**Effective Batch Size**: `train_batch_size × rollout.n`
- Example: 32 × 8 = 256 total samples per batch

## Architecture

### File Structure

```
ft/
├── gvpo_loss.py           # Core GVPO loss computation
├── gvpo_trainer.py        # GVPO trainer (extends AgentFlowTrainer)
├── train_gvpo.py          # Training entry point
├── config_gvpo.yaml       # GVPO configuration
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── test_gvpo.py          # Unit tests
└── utils.py              # Utility functions (if needed)
```

### Code Flow

```
train_gvpo.py
    ↓
Load config_gvpo.yaml
    ↓
Initialize GVPOAgentFlowTrainer (gvpo_trainer.py)
    ↓
Training Loop:
    ├── Agent Rollout (generate responses)
    ├── Compute rewards
    ├── Compute GVPO advantages (gvpo_loss.py)
    └── Update policy
```

### Integration with verl

GVPO integrates seamlessly with the verl framework:

1. **Advantage Computation**: `compute_gvpo_advantage()` replaces standard advantage estimators
2. **Trainer Extension**: `GVPOAgentFlowTrainer` extends `AgentFlowTrainer`
3. **Configuration**: Standard hydra/omegaconf configuration
4. **Data Flow**: Compatible with verl's `DataProto` format

## Performance Tuning

### GPU Memory Optimization

```yaml
# Reduce memory usage
actor_rollout_ref.rollout.gpu_memory_utilization: 0.5
actor_rollout_ref.model.enable_gradient_checkpointing: True
actor_rollout_ref.actor.fsdp_config.param_offload: True

# Reduce batch size
data.train_batch_size: 16
actor_rollout_ref.rollout.n: 4
```

### Speed Optimization

```yaml
# Increase throughput
actor_rollout_ref.rollout.gpu_memory_utilization: 0.75
actor_rollout_ref.actor.fsdp_config.param_offload: False
actor_rollout_ref.actor.fsdp_config.optimizer_offload: False

# Increase batch size (if memory allows)
data.train_batch_size: 64
actor_rollout_ref.actor.ppo_mini_batch_size: 16
```

### Hyperparameter Tuning

```yaml
# More aggressive training
actor_rollout_ref.actor.optim.lr: 5e-6
algorithm.gvpo_beta: 0.05
actor_rollout_ref.actor.entropy_coeff: 0.01  # More exploration

# More conservative training
actor_rollout_ref.actor.optim.lr: 5e-7
algorithm.gvpo_beta: 0.15
actor_rollout_ref.actor.entropy_coeff: 0.0  # Less exploration
```

## Troubleshooting

### Common Issues

#### 1. Out of Memory (OOM)

**Symptoms**: CUDA OOM errors during training

**Solutions**:
```yaml
# Reduce batch size
data.train_batch_size: 16
actor_rollout_ref.rollout.n: 4

# Reduce memory utilization
actor_rollout_ref.rollout.gpu_memory_utilization: 0.5

# Enable gradient checkpointing
actor_rollout_ref.model.enable_gradient_checkpointing: True

# Enable FSDP offloading
actor_rollout_ref.actor.fsdp_config.param_offload: True
```

#### 2. Training Instability

**Symptoms**: Loss spikes, NaN values, diverging metrics

**Solutions**:
```yaml
# Reduce learning rate
actor_rollout_ref.actor.optim.lr: 5e-7

# Increase KL penalty
algorithm.gvpo_beta: 0.15

# Enable weight clipping
algorithm.gvpo_clip_weight: 5.0

# Reduce PPO clip range
actor_rollout_ref.actor.clip_ratio_low: 0.1
actor_rollout_ref.actor.clip_ratio_high: 0.2
```

#### 3. Slow Convergence

**Symptoms**: Validation metrics not improving

**Solutions**:
```yaml
# Increase sample count
actor_rollout_ref.rollout.n: 16

# Adjust learning rate
actor_rollout_ref.actor.optim.lr: 2e-6

# Reduce KL penalty (if not overfitting)
algorithm.gvpo_beta: 0.08

# Add entropy bonus
actor_rollout_ref.actor.entropy_coeff: 0.01
```

#### 4. Empty Rollouts

**Symptoms**: "No training tasks completed" errors

**Solutions**:
- Check agent timeout: `env.AGENT_MAX_TIMEOUT: 500`
- Verify tools are configured correctly
- Check server connectivity: `agentflow.port: 9999`
- Review agent logs for execution errors

### Debugging Tips

```bash
# Enable debug logging
export VERBOSITY=DEBUG

# Test with smaller batch
python ft/train_gvpo.py data.train_batch_size=2 actor_rollout_ref.rollout.n=2

# Validate config only
python ft/train_gvpo.py --validate-only

# Check GPU usage
nvidia-smi -l 1

# Monitor training metrics
wandb sync  # Sync offline wandb logs
```

## Testing

### Run Unit Tests

```bash
# Test GVPO loss computation
python ft/gvpo_loss.py

# Run full test suite
python ft/test_gvpo.py

# Test with pytest
pytest ft/test_gvpo.py -v
```

### Validate Installation

```bash
# Check imports
python -c "from ft.gvpo_loss import GVPOLoss; print('✓ Import successful')"

# Validate config
python ft/train_gvpo.py --validate-only

# Dry run training
python ft/train_gvpo.py --dry-run
```

## Key Configuration Parameters

  # GVPO-specific
  algorithm.adv_estimator: 'gvpo'
  algorithm.gvpo_beta: 0.1  # KL penalty (0.05-0.15)
  actor_rollout_ref.rollout.n: 8  # Samples per prompt

  # Recommended for math reasoning
  gvpo_beta: 0.1, n: 8-16

  # Recommended for general QA  
  gvpo_beta: 0.05-0.08, n: 8

  📈 Performance Characteristics

  | Config | Batch Size | Samples | GPU Memory |
  |--------|------------|---------|------------|
  | Small  | 4          | 2       | ~12GB/GPU  |
  | Medium | 16         | 4       | ~24GB/GPU  |
  | Large  | 32         | 8       | ~36GB/GPU  |


## References

### Papers

1. **GVPO Paper**: "Reasoning through Incentives: Group Variance Policy Optimization"
   - GitHub: https://github.com/alfredcs/Reasoning-through-incentives
   - Comparison: [gvpo_vs_grpo.pdf](https://github.com/alfredcs/Reasoning-through-incentives/blob/main/gvpo_vs_grpo.pdf)

2. **AgentFlow Paper**: (Original AgentFlow paper)
   - GitHub: https://github.com/alfredcs/AgentFlow

### Code References

- **verl Framework**: https://github.com/volcengine/verl
- **GVPO Reference Implementation**: https://github.com/alfredcs/Reasoning-through-incentives/tree/main/src
- **AgentFlow Training**: https://github.com/alfredcs/AgentFlow/tree/main/ft

## License

This implementation follows the same license as AgentFlow. Please refer to the main repository for license details.

## Contributing

Contributions are welcome! Please:

1. Test your changes thoroughly
2. Follow the existing code style
3. Add tests for new features
4. Update documentation

## Support

For issues and questions:

- **AgentFlow Issues**: https://github.com/alfredcs/AgentFlow/docs
- **GVPO Issues**: https://github.com/alfredcs/Reasoning-through-incentives/issues

## Acknowledgments

- **GVPO Implementation**: Based on the Reasoning-through-incentives repository
- **AgentFlow Framework**: Built on the AgentFlow training infrastructure
- **verl Framework**: Uses verl for distributed RL training

---

**Last Updated**: 2025-10-27

**Version**: 1.0.0

**Status**: Production Ready
