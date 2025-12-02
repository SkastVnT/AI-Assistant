#!/usr/bin/env python3
"""
Benchmark and compare different LoRA training configurations
"""

import os
import time
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime
import torch


class TrainingBenchmark:
    """Benchmark LoRA training with different configurations"""
    
    def __init__(self, base_config_path: str, output_dir: str = "benchmarks"):
        """
        Initialize benchmark
        
        Args:
            base_config_path: Path to base configuration
            output_dir: Directory to save benchmark results
        """
        self.base_config = self.load_config(base_config_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.results = []
    
    def load_config(self, config_path: str) -> dict:
        """Load YAML configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def save_config(self, config: dict, config_path: str):
        """Save YAML configuration"""
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
    
    def create_config_variant(
        self,
        variant_name: str,
        modifications: dict
    ) -> str:
        """
        Create a configuration variant
        
        Args:
            variant_name: Name for this variant
            modifications: Dictionary of config modifications
        
        Returns:
            Path to created config file
        """
        config = self.base_config.copy()
        
        # Apply modifications
        for key_path, value in modifications.items():
            keys = key_path.split('.')
            target = config
            
            for key in keys[:-1]:
                if key not in target:
                    target[key] = {}
                target = target[key]
            
            target[keys[-1]] = value
        
        # Save variant config
        config_path = self.output_dir / f"config_{variant_name}.yaml"
        self.save_config(config, str(config_path))
        
        return str(config_path)
    
    def run_training_variant(
        self,
        variant_name: str,
        config_path: str,
        num_epochs: int = 2
    ) -> dict:
        """
        Run training with a configuration variant
        
        Args:
            variant_name: Name of variant
            config_path: Path to config
            num_epochs: Number of epochs to train
        
        Returns:
            Dictionary with benchmark results
        """
        print(f"\n{'='*80}")
        print(f"Running variant: {variant_name}")
        print(f"{'='*80}\n")
        
        start_time = time.time()
        
        # Import training module
        from train_lora import LoRATrainer
        
        try:
            # Create trainer
            trainer = LoRATrainer(config_path=config_path)
            
            # Override epochs for benchmark
            trainer.config['training']['num_train_epochs'] = num_epochs
            
            # Run training
            trainer.train()
            
            elapsed_time = time.time() - start_time
            
            result = {
                'variant_name': variant_name,
                'config_path': config_path,
                'success': True,
                'elapsed_time': elapsed_time,
                'epochs': num_epochs,
                'final_loss': trainer.best_loss if hasattr(trainer, 'best_loss') else None,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            
            result = {
                'variant_name': variant_name,
                'config_path': config_path,
                'success': False,
                'error': str(e),
                'elapsed_time': elapsed_time,
                'timestamp': datetime.now().isoformat()
            }
        
        self.results.append(result)
        return result
    
    def benchmark_learning_rates(
        self,
        learning_rates: list = [1e-5, 5e-5, 1e-4, 2e-4]
    ):
        """Benchmark different learning rates"""
        print("\nBenchmarking Learning Rates...")
        
        for lr in learning_rates:
            variant_name = f"lr_{lr:.0e}"
            config_path = self.create_config_variant(
                variant_name,
                {'training.learning_rate': float(lr)}
            )
            self.run_training_variant(variant_name, config_path)
    
    def benchmark_ranks(
        self,
        ranks: list = [8, 16, 32, 64]
    ):
        """Benchmark different LoRA ranks"""
        print("\nBenchmarking LoRA Ranks...")
        
        for rank in ranks:
            variant_name = f"rank_{rank}"
            config_path = self.create_config_variant(
                variant_name,
                {
                    'lora.rank': rank,
                    'lora.alpha': rank * 2  # Keep alpha = 2*rank
                }
            )
            self.run_training_variant(variant_name, config_path)
    
    def benchmark_batch_sizes(
        self,
        configs: list = [
            {'batch': 1, 'accum': 4},
            {'batch': 1, 'accum': 8},
            {'batch': 2, 'accum': 4},
        ]
    ):
        """Benchmark different batch size configurations"""
        print("\nBenchmarking Batch Sizes...")
        
        for config in configs:
            batch = config['batch']
            accum = config['accum']
            variant_name = f"batch{batch}_accum{accum}"
            
            config_path = self.create_config_variant(
                variant_name,
                {
                    'training.train_batch_size': batch,
                    'training.gradient_accumulation_steps': accum
                }
            )
            self.run_training_variant(variant_name, config_path)
    
    def save_results(self):
        """Save benchmark results"""
        results_path = self.output_dir / "benchmark_results.json"
        
        with open(results_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nResults saved to: {results_path}")
        
        # Print summary
        print("\n" + "="*80)
        print("Benchmark Summary")
        print("="*80)
        
        for result in self.results:
            status = "✓" if result['success'] else "✗"
            elapsed = result['elapsed_time']
            
            print(f"{status} {result['variant_name']}: {elapsed:.1f}s")
            
            if result['success'] and result.get('final_loss'):
                print(f"   Final loss: {result['final_loss']:.4f}")
            elif not result['success']:
                print(f"   Error: {result.get('error', 'Unknown')}")
        
        print("="*80)


def main():
    parser = argparse.ArgumentParser(description="Benchmark LoRA training configurations")
    parser.add_argument(
        "--base_config",
        type=str,
        default="configs/default_config.yaml",
        help="Base configuration file"
    )
    parser.add_argument(
        "--benchmark",
        type=str,
        choices=['lr', 'rank', 'batch', 'all'],
        default='all',
        help="Which parameter to benchmark"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="benchmarks",
        help="Output directory for results"
    )
    
    args = parser.parse_args()
    
    # Create benchmark
    benchmark = TrainingBenchmark(args.base_config, args.output_dir)
    
    # Run benchmarks
    if args.benchmark == 'lr' or args.benchmark == 'all':
        benchmark.benchmark_learning_rates()
    
    if args.benchmark == 'rank' or args.benchmark == 'all':
        benchmark.benchmark_ranks()
    
    if args.benchmark == 'batch' or args.benchmark == 'all':
        benchmark.benchmark_batch_sizes()
    
    # Save results
    benchmark.save_results()


if __name__ == "__main__":
    main()
