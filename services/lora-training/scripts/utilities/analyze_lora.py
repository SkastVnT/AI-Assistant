"""
Analyze and inspect LoRA models
"""

import torch
from safetensors.torch import load_file
from pathlib import Path
from typing import Dict, List
import numpy as np


class LoRAAnalyzer:
    """Analyze LoRA models"""
    
    def __init__(self, lora_path: str):
        """
        Initialize analyzer
        
        Args:
            lora_path: Path to LoRA model
        """
        self.lora_path = lora_path
        self.state_dict = load_file(lora_path)
    
    def get_info(self) -> Dict:
        """Get basic LoRA information"""
        info = {
            'path': self.lora_path,
            'num_parameters': 0,
            'size_mb': Path(self.lora_path).stat().st_size / (1024 * 1024),
            'layers': [],
            'ranks': [],
            'modules': set()
        }
        
        # Analyze parameters
        for key, tensor in self.state_dict.items():
            info['num_parameters'] += tensor.numel()
            
            # Extract layer info
            if '.lora_A' in key or '.lora_B' in key:
                base_key = key.replace('.lora_A', '').replace('.lora_B', '')
                
                if base_key not in info['layers']:
                    info['layers'].append(base_key)
                
                # Extract module name
                module = base_key.split('.')[0] if '.' in base_key else base_key
                info['modules'].add(module)
                
                # Get rank
                if '.lora_A' in key:
                    rank = tensor.shape[0]
                    info['ranks'].append(rank)
        
        info['modules'] = sorted(list(info['modules']))
        info['avg_rank'] = np.mean(info['ranks']) if info['ranks'] else 0
        info['min_rank'] = min(info['ranks']) if info['ranks'] else 0
        info['max_rank'] = max(info['ranks']) if info['ranks'] else 0
        
        return info
    
    def print_summary(self):
        """Print LoRA summary"""
        info = self.get_info()
        
        print("="*80)
        print("LoRA Model Analysis")
        print("="*80)
        print(f"Path: {info['path']}")
        print(f"Size: {info['size_mb']:.2f} MB")
        print(f"Total Parameters: {info['num_parameters']:,}")
        print(f"\nRank Statistics:")
        print(f"  Average Rank: {info['avg_rank']:.1f}")
        print(f"  Min Rank: {info['min_rank']}")
        print(f"  Max Rank: {info['max_rank']}")
        print(f"\nNumber of Layers: {len(info['layers'])}")
        print(f"\nModules with LoRA:")
        for module in info['modules']:
            count = sum(1 for layer in info['layers'] if layer.startswith(module))
            print(f"  {module}: {count} layers")
        print("="*80)
    
    def print_detailed_layers(self):
        """Print detailed layer information"""
        print("\nDetailed Layer Information:")
        print("-"*80)
        
        layers_info = {}
        
        for key, tensor in self.state_dict.items():
            if '.lora_A' in key:
                base_key = key.replace('.lora_A', '')
                if base_key not in layers_info:
                    layers_info[base_key] = {}
                
                layers_info[base_key]['lora_A_shape'] = tuple(tensor.shape)
                layers_info[base_key]['rank'] = tensor.shape[0]
            
            elif '.lora_B' in key:
                base_key = key.replace('.lora_B', '')
                if base_key not in layers_info:
                    layers_info[base_key] = {}
                
                layers_info[base_key]['lora_B_shape'] = tuple(tensor.shape)
        
        for layer_name, layer_info in sorted(layers_info.items()):
            rank = layer_info.get('rank', 'N/A')
            lora_A = layer_info.get('lora_A_shape', 'N/A')
            lora_B = layer_info.get('lora_B_shape', 'N/A')
            
            print(f"{layer_name}")
            print(f"  Rank: {rank}")
            print(f"  LoRA A: {lora_A}")
            print(f"  LoRA B: {lora_B}")
            print()
    
    def analyze_weights_distribution(self):
        """Analyze weight distribution"""
        print("\nWeight Distribution Analysis:")
        print("-"*80)
        
        for key, tensor in self.state_dict.items():
            tensor_np = tensor.cpu().numpy()
            
            print(f"{key}")
            print(f"  Shape: {tensor.shape}")
            print(f"  Mean: {tensor_np.mean():.6f}")
            print(f"  Std: {tensor_np.std():.6f}")
            print(f"  Min: {tensor_np.min():.6f}")
            print(f"  Max: {tensor_np.max():.6f}")
            print(f"  Zeros: {(tensor_np == 0).sum()}/{tensor_np.size} ({(tensor_np == 0).sum()/tensor_np.size*100:.2f}%)")
            print()
    
    def compare_with(self, other_lora_path: str):
        """
        Compare with another LoRA
        
        Args:
            other_lora_path: Path to another LoRA model
        """
        other_state_dict = load_file(other_lora_path)
        
        print("\nComparison with another LoRA:")
        print("-"*80)
        print(f"LoRA 1: {self.lora_path}")
        print(f"LoRA 2: {other_lora_path}")
        print()
        
        # Compare keys
        keys1 = set(self.state_dict.keys())
        keys2 = set(other_state_dict.keys())
        
        common_keys = keys1 & keys2
        only_in_1 = keys1 - keys2
        only_in_2 = keys2 - keys1
        
        print(f"Common layers: {len(common_keys)}")
        print(f"Only in LoRA 1: {len(only_in_1)}")
        print(f"Only in LoRA 2: {len(only_in_2)}")
        
        if only_in_1:
            print(f"\nLayers only in LoRA 1:")
            for key in sorted(only_in_1):
                print(f"  {key}")
        
        if only_in_2:
            print(f"\nLayers only in LoRA 2:")
            for key in sorted(only_in_2):
                print(f"  {key}")
        
        # Compare common layers
        if common_keys:
            print(f"\nWeight differences for common layers:")
            for key in sorted(common_keys):
                t1 = self.state_dict[key].cpu().numpy()
                t2 = other_state_dict[key].cpu().numpy()
                
                diff = np.abs(t1 - t2).mean()
                print(f"  {key}: {diff:.6f}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze LoRA models")
    parser.add_argument("lora_path", type=str, help="Path to LoRA model")
    parser.add_argument("--detailed", action='store_true', help="Show detailed layer info")
    parser.add_argument("--weights", action='store_true', help="Analyze weight distribution")
    parser.add_argument("--compare", type=str, help="Compare with another LoRA")
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = LoRAAnalyzer(args.lora_path)
    
    # Print summary
    analyzer.print_summary()
    
    # Detailed info
    if args.detailed:
        analyzer.print_detailed_layers()
    
    # Weight distribution
    if args.weights:
        analyzer.analyze_weights_distribution()
    
    # Compare
    if args.compare:
        analyzer.compare_with(args.compare)


if __name__ == "__main__":
    main()
