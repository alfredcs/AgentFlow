# GVPO Installation and Setup Guide

This guide provides step-by-step instructions for installing and setting up GVPO training for AgentFlow.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Verification](#verification)
5. [First Training Run](#first-training-run)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### Hardware Requirements

- **Minimum**: 4× NVIDIA GPUs with 24GB VRAM each (e.g., RTX 3090, A5000)
- **Recommended**: 8× NVIDIA A100 GPUs (40GB or 80GB)
- **CPU**: 32+ cores recommended for data processing
- **RAM**: 128GB+ recommended
- **Storage**: 500GB+ free space for models and data

### Software Requirements

- **OS**: Linux (Ubuntu 20.04+ recommended) or macOS
- **Python**: 3.9, 3.10, or 3.11
- **CUDA**: 11.8 or 12.1+ (for GPU training)
- **Git**: For repository cloning

## Installation

### Step 1: Clone Repository

```bash
# Clone AgentFlow repository
git clone https://github.com/lupantech/AgentFlow.git
cd AgentFlow

# Verify ft directory exists
ls -la ft/
```

### Step 2: Create Python Environment

```bash
# Using conda (recommended)
conda create -n gvpo python=3.10
conda activate gvpo

# Or using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Base Dependencies

```bash
# Install AgentFlow
pip install -e .

# Install PyTorch (adjust for your CUDA version)
# For CUDA 11.8:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Step 4: Install GVPO Requirements

```bash
# Install GVPO-specific dependencies
pip install -r ft/requirements.txt

# Install verl framework
pip install git+https://github.com/volcengine/verl.git
```

### Step 5: Install Optional Performance Packages

```bash
# Flash Attention (highly recommended for performance)
pip install flash-attn --no-build-isolation

# xformers (optional, for additional optimizations)
pip install xformers

# vLLM (for fast inference)
pip install vllm
```

## Configuration

### Step 1: Prepare Data

Create data directories and add your training/validation data:

```bash
mkdir -p data/train data/val

# Copy your data files
# Data should be in Parquet format with columns:
# - question: input prompt
# - answer: ground truth (for reward computation)
# - data_id: unique identifier
```

### Step 2: Configure Environment

Edit `ft/config_gvpo.yaml`:

```yaml
env:
  BASE_MODEL: 'Qwen/Qwen2.5-7B-Instruct'  # Your model path
  N_GPUS: 8  # Number of GPUs
  CUDA_VISIBLE_DEVICES: '0,1,2,3,4,5,6,7'  # GPU IDs

python_args:
  data.train_files: 'data/train/combined_train.parquet'
  data.val_files: 'data/val/aime24.parquet'
```

### Step 3: Set API Keys (if needed)

```bash
# For OpenAI API (optional, for reward computation)
export OPENAI_API_KEY='your-api-key-here'

# Or add to config_gvpo.yaml
```

## Verification

### Step 1: Run Tests

```bash
# Test GVPO loss module
python ft/gvpo_loss.py

# Run full test suite
python ft/test_gvpo.py

# Or use quick start script
./ft/quick_start.sh test
```

Expected output:
```
✓ All tests passed!
Ran 12 tests in 0.040s
OK
```

### Step 2: Validate Configuration

```bash
# Validate config without training
python ft/train_gvpo.py --validate-only

# Or use quick start script
./ft/quick_start.sh validate
```

Expected output:
```
✓ Configuration validation passed
```

### Step 3: Check GPU Setup

```bash
# Check CUDA availability
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPU count: {torch.cuda.device_count()}')"

# Monitor GPU usage
watch -n 1 nvidia-smi
```

### Step 4: Run Comparison Demo

```bash
# Compare GRPO vs GVPO
python ft/compare_grpo_gvpo.py
```

This generates a visualization showing the differences between GRPO and GVPO.

## First Training Run

### Quick Test Run

Start with a small-scale test to verify everything works:

```bash
# Test with reduced batch size and 1 epoch
python ft/train_gvpo.py \
    data.train_batch_size=4 \
    actor_rollout_ref.rollout.n=2 \
    trainer.total_epochs=1

# Or use quick start script
./ft/quick_start.sh train-small
```

### Full Training Run

Once verification is complete, start full training:

```bash
# Basic training with default config
python ft/train_gvpo.py

# With custom parameters
python ft/train_gvpo.py \
    algorithm.gvpo_beta=0.15 \
    data.train_batch_size=32 \
    trainer.total_epochs=5

# Or use quick start script
./ft/quick_start.sh train
```

### Monitor Training

Training metrics are logged to:

1. **Console**: Real-time progress with tqdm
2. **Wandb**: Online dashboard (if configured)
3. **Local logs**: Checkpoints and metrics

```bash
# Watch training progress
tail -f logs/training.log

# Monitor GPU usage
watch -n 1 nvidia-smi

# View wandb dashboard
wandb sync  # if offline
```

## Troubleshooting

### Issue: Import Errors

**Error**: `ModuleNotFoundError: No module named 'ft'`

**Solution**:
```bash
# Ensure you're in the AgentFlow root directory
cd /path/to/AgentFlow

# Add to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Or install in development mode
pip install -e .
```

### Issue: CUDA Out of Memory

**Error**: `CUDA out of memory`

**Solution**:
```yaml
# Reduce batch size in config_gvpo.yaml
data.train_batch_size: 16  # or 8
actor_rollout_ref.rollout.n: 4  # or 2

# Reduce GPU memory utilization
actor_rollout_ref.rollout.gpu_memory_utilization: 0.5

# Enable gradient checkpointing
actor_rollout_ref.model.enable_gradient_checkpointing: True
```

### Issue: verl Installation Fails

**Error**: Problems installing verl

**Solution**:
```bash
# Try installing from source
git clone https://github.com/volcengine/verl.git
cd verl
pip install -e .

# Or use specific commit
pip install git+https://github.com/volcengine/verl.git@main
```

### Issue: Training Hangs

**Symptoms**: Training starts but makes no progress

**Solution**:
```bash
# Check if processes are running
ps aux | grep python

# Check GPU usage
nvidia-smi

# Enable debug logging
export VERBOSITY=DEBUG
python ft/train_gvpo.py

# Check agent server
curl http://localhost:9999/health
```

### Issue: Empty Rollouts

**Error**: "No training tasks completed"

**Solution**:
```yaml
# Increase timeout in config_gvpo.yaml
env:
  AGENT_MAX_TIMEOUT: 1000  # Increase from 500

# Check tool configuration
env:
  ENABLE_TOOLS: ["Base_Generator_Tool"]  # Start with minimal tools
```

### Issue: Validation Fails

**Error**: "Insufficient validation completion"

**Solution**:
```yaml
# Reduce validation strictness
agentflow.enable_rollout_validation: False

# Or provide more validation data
data.val_files: 'data/val/larger_val_set.parquet'
```

## Next Steps

After successful installation and first training run:

1. **Read the README**: `ft/README.md` for detailed usage
2. **Tune Hyperparameters**: Adjust `config_gvpo.yaml` for your task
3. **Monitor Metrics**: Use wandb or tensorboard for tracking
4. **Scale Up**: Increase batch size and samples as you stabilize
5. **Experiment**: Try different beta values and rollout samples

## Getting Help

- **Issues**: https://github.com/lupantech/AgentFlow/issues
- **Documentation**: See `ft/README.md`
- **Comparison**: Run `python ft/compare_grpo_gvpo.py`

## Quick Reference

```bash
# Common commands
./ft/quick_start.sh check      # Check prerequisites
./ft/quick_start.sh test       # Run tests
./ft/quick_start.sh validate   # Validate config
./ft/quick_start.sh train      # Start training
./ft/quick_start.sh train-small # Test training

# Direct Python commands
python ft/test_gvpo.py                    # Run tests
python ft/train_gvpo.py --validate-only   # Validate
python ft/train_gvpo.py                   # Train
python ft/compare_grpo_gvpo.py            # Compare methods
```

---

**Last Updated**: 2025-10-27

**Version**: 1.0.0
