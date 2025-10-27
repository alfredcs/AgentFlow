#!/usr/bin/env python3
"""
GVPO Unit Tests

Comprehensive test suite for GVPO implementation, covering:
- Loss computation
- Weight calculation
- Advantage estimation
- Integration with AgentFlow
- Configuration validation
"""

import sys
import os
from pathlib import Path
import unittest
import warnings

# Add parent directory to path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import torch
import numpy as np
from typing import Dict

# Import GVPO modules
from ft.gvpo_loss import GVPOLoss, compute_gvpo_advantage


class TestGVPOLoss(unittest.TestCase):
    """Test GVPO loss computation."""

    def setUp(self):
        """Set up test fixtures."""
        self.gvpo = GVPOLoss(beta=0.1)
        self.batch_size = 16
        self.num_samples = 4
        self.seq_len = 50

        # Create test data
        torch.manual_seed(42)
        self.rewards = torch.randn(self.batch_size)
        self.log_probs = torch.randn(self.batch_size)
        self.ref_log_probs = torch.randn(self.batch_size)

        # Create UIDs (4 prompts, 4 samples each)
        self.uid = torch.repeat_interleave(
            torch.arange(self.batch_size // self.num_samples),
            self.num_samples
        )

    def test_weight_computation(self):
        """Test GVPO weight computation."""
        weights, metrics = self.gvpo.compute_gvpo_weights(
            self.rewards,
            self.log_probs,
            self.ref_log_probs,
            self.uid,
            self.num_samples,
        )

        # Check shapes
        self.assertEqual(weights.shape, self.rewards.shape)

        # Check zero-sum property (per group)
        for uid_val in torch.unique(self.uid):
            group_mask = (self.uid == uid_val)
            group_weights = weights[group_mask]
            # Weights should sum to ~0 (within numerical precision)
            self.assertAlmostEqual(
                group_weights.sum().item(), 0.0, places=5,
                msg=f"Weights not zero-sum for group {uid_val}"
            )

        # Check metrics
        self.assertIn('gvpo/mean_reward', metrics)
        self.assertIn('gvpo/mean_weight', metrics)
        self.assertIn('gvpo/std_weight', metrics)

    def test_loss_computation(self):
        """Test GVPO loss computation."""
        weights = torch.randn(self.batch_size)
        log_probs = torch.randn(self.batch_size)

        loss, metrics = self.gvpo.compute_gvpo_loss(
            weights, log_probs, self.num_samples
        )

        # Check loss is a scalar
        self.assertEqual(loss.shape, torch.Size([]))

        # Check loss is finite
        self.assertTrue(torch.isfinite(loss))

        # Check metrics
        self.assertIn('gvpo/loss', metrics)
        self.assertIn('gvpo/weighted_log_prob', metrics)

    def test_advantage_computation(self):
        """Test GVPO advantage computation."""
        advantages, metrics = self.gvpo.compute_advantages(
            self.rewards,
            self.log_probs,
            self.ref_log_probs,
            self.uid,
            self.num_samples,
        )

        # Check shapes
        self.assertEqual(advantages.shape, self.rewards.shape)

        # Check advantages are finite
        self.assertTrue(torch.all(torch.isfinite(advantages)))

        # Check metrics
        self.assertIn('gvpo/advantage_mean', metrics)
        self.assertIn('gvpo/advantage_std', metrics)

    def test_bessel_correction(self):
        """Test Bessel correction in loss computation."""
        gvpo_bessel = GVPOLoss(beta=0.1, use_bessel_correction=True)
        gvpo_no_bessel = GVPOLoss(beta=0.1, use_bessel_correction=False)

        weights = torch.randn(self.batch_size)
        log_probs = torch.randn(self.batch_size)

        loss_bessel, _ = gvpo_bessel.compute_gvpo_loss(
            weights, log_probs, self.num_samples
        )
        loss_no_bessel, _ = gvpo_no_bessel.compute_gvpo_loss(
            weights, log_probs, self.num_samples
        )

        # Losses should be different
        self.assertNotAlmostEqual(
            loss_bessel.item(), loss_no_bessel.item(),
            msg="Bessel correction should affect loss"
        )

    def test_weight_clipping(self):
        """Test weight clipping."""
        clip_value = 2.0
        gvpo_clip = GVPOLoss(beta=0.1, clip_weight=clip_value)

        # Create extreme rewards to trigger clipping
        extreme_rewards = torch.tensor([10.0, -10.0, 5.0, -5.0] * 4)
        log_probs = torch.randn(self.batch_size)
        ref_log_probs = torch.randn(self.batch_size)

        weights, _ = gvpo_clip.compute_gvpo_weights(
            extreme_rewards, log_probs, ref_log_probs,
            self.uid, self.num_samples
        )

        # Check weights are clipped
        self.assertTrue(torch.all(weights <= clip_value))
        self.assertTrue(torch.all(weights >= -clip_value))

    def test_beta_parameter(self):
        """Test that beta affects weight computation."""
        gvpo_low = GVPOLoss(beta=0.01)
        gvpo_high = GVPOLoss(beta=1.0)

        weights_low, _ = gvpo_low.compute_gvpo_weights(
            self.rewards, self.log_probs, self.ref_log_probs,
            self.uid, self.num_samples
        )

        weights_high, _ = gvpo_high.compute_gvpo_weights(
            self.rewards, self.log_probs, self.ref_log_probs,
            self.uid, self.num_samples
        )

        # Different beta should give different weights
        self.assertFalse(
            torch.allclose(weights_low, weights_high),
            msg="Different beta should produce different weights"
        )


class TestLogProbComputation(unittest.TestCase):
    """Test log probability computation."""

    def setUp(self):
        """Set up test fixtures."""
        self.gvpo = GVPOLoss(beta=0.1)
        self.batch_size = 4
        self.seq_len = 10
        self.vocab_size = 100

    def test_compute_log_probs(self):
        """Test log probability computation."""
        # Create dummy data
        logits = torch.randn(self.batch_size, self.seq_len, self.vocab_size)
        input_ids = torch.randint(0, self.vocab_size, (self.batch_size, self.seq_len))
        attention_mask = torch.ones(self.batch_size, self.seq_len)

        log_probs = self.gvpo.compute_log_probs(
            logits, input_ids, attention_mask
        )

        # Check shape (shifted by 1 for autoregressive)
        expected_shape = (self.batch_size, self.seq_len - 1)
        self.assertEqual(log_probs.shape, expected_shape)

        # Check log probs are negative (probabilities <= 1)
        self.assertTrue(torch.all(log_probs <= 0))

    def test_sequence_log_prob(self):
        """Test sequence-level log probability."""
        token_log_probs = torch.randn(self.batch_size, self.seq_len - 1)
        mask = torch.ones(self.batch_size, self.seq_len - 1)

        seq_log_prob = self.gvpo.compute_sequence_log_prob(
            token_log_probs, mask
        )

        # Check shape
        self.assertEqual(seq_log_prob.shape, (self.batch_size,))

        # Check it's a sum
        expected = token_log_probs.sum(dim=-1)
        self.assertTrue(torch.allclose(seq_log_prob, expected))


class TestGVPOIntegration(unittest.TestCase):
    """Test GVPO integration with AgentFlow."""

    def setUp(self):
        """Set up test fixtures."""
        warnings.filterwarnings('ignore', category=DeprecationWarning)

    def test_config_validation(self):
        """Test configuration parameter validation."""
        # Test valid beta
        gvpo = GVPOLoss(beta=0.1)
        self.assertEqual(gvpo.beta, 0.1)

        # Test edge cases
        gvpo_low = GVPOLoss(beta=0.001)
        self.assertEqual(gvpo_low.beta, 0.001)

        gvpo_high = GVPOLoss(beta=0.999)
        self.assertEqual(gvpo_high.beta, 0.999)

    def test_numerical_stability(self):
        """Test numerical stability with extreme values."""
        gvpo = GVPOLoss(beta=0.1)

        # Test with extreme rewards
        extreme_rewards = torch.tensor([1e6, -1e6, 1e5, -1e5])
        log_probs = torch.tensor([0.0, -1.0, -2.0, -3.0])
        ref_log_probs = torch.tensor([-0.5, -1.5, -2.5, -3.5])
        uid = torch.tensor([0, 0, 1, 1])

        # Should not produce NaN or Inf
        weights, _ = gvpo.compute_gvpo_weights(
            extreme_rewards, log_probs, ref_log_probs, uid, 2
        )

        self.assertTrue(torch.all(torch.isfinite(weights)))

    def test_batch_processing(self):
        """Test batch processing with different group sizes."""
        gvpo = GVPOLoss(beta=0.1)

        # Uneven groups
        rewards = torch.randn(10)
        log_probs = torch.randn(10)
        ref_log_probs = torch.randn(10)
        # 3 groups: sizes 4, 3, 3
        uid = torch.tensor([0, 0, 0, 0, 1, 1, 1, 2, 2, 2])

        weights, metrics = gvpo.compute_gvpo_weights(
            rewards, log_probs, ref_log_probs, uid, 4
        )

        # Should handle uneven groups
        self.assertEqual(weights.shape, (10,))
        self.assertTrue(torch.all(torch.isfinite(weights)))


class TestEndToEnd(unittest.TestCase):
    """End-to-end integration tests."""

    def test_full_pipeline(self):
        """Test full GVPO pipeline."""
        # Create realistic test data
        batch_size = 32
        num_samples = 8
        seq_len = 100

        rewards = torch.randn(batch_size) + 1.0  # Mean reward = 1.0
        log_probs = -torch.rand(batch_size) * 5  # Negative log probs
        ref_log_probs = -torch.rand(batch_size) * 5

        uid = torch.repeat_interleave(
            torch.arange(batch_size // num_samples),
            num_samples
        )

        # Initialize GVPO
        gvpo = GVPOLoss(beta=0.1)

        # Compute weights
        weights, weight_metrics = gvpo.compute_gvpo_weights(
            rewards, log_probs, ref_log_probs, uid, num_samples
        )

        # Compute loss
        loss, loss_metrics = gvpo.compute_gvpo_loss(
            weights, log_probs, num_samples
        )

        # Verify results
        self.assertTrue(torch.isfinite(loss))
        self.assertGreater(len(weight_metrics), 0)
        self.assertGreater(len(loss_metrics), 0)

        # Print summary
        print("\n" + "="*60)
        print("End-to-End Test Summary")
        print("="*60)
        print(f"Batch size: {batch_size}")
        print(f"Num samples: {num_samples}")
        print(f"Loss: {loss.item():.4f}")
        print(f"Mean reward: {weight_metrics['gvpo/mean_reward']:.4f}")
        print(f"Mean weight: {weight_metrics['gvpo/mean_weight']:.4f}")
        print(f"Std weight: {weight_metrics['gvpo/std_weight']:.4f}")
        print("="*60)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestGVPOLoss))
    suite.addTests(loader.loadTestsFromTestCase(TestLogProbComputation))
    suite.addTests(loader.loadTestsFromTestCase(TestGVPOIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEnd))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    print("\n" + "#"*60)
    print("# GVPO Unit Tests")
    print("#"*60 + "\n")

    success = run_tests()

    print("\n" + "="*60)
    if success:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print("="*60 + "\n")

    sys.exit(0 if success else 1)
