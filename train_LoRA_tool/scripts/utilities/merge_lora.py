"""
Merge multiple LoRA models or merge LoRA into base model
"""

import torch
import argparse
from pathlib import Path
from safetensors.torch import load_file, save_file
from typing import Dict, List, Tuple


class LoRAMerger:
    """Merge LoRA models"""
    
    @staticmethod
    def merge_loras(
        lora_paths: List[str],
        weights: List[float],
        output_path: str
    ):
        """
        Merge multiple LoRA models with weighted average
        
        Args:
            lora_paths: List of paths to LoRA models
            weights: List of weights for each LoRA (should sum to 1.0)
            output_path: Output path for merged LoRA
        """
        if len(lora_paths) != len(weights):
            raise ValueError("Number of LoRAs must match number of weights")
        
        # Normalize weights
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        print(f"Merging {len(lora_paths)} LoRA models...")
        
        # Load first LoRA as base
        merged_state_dict = load_file(lora_paths[0])
        
        # Scale by first weight
        for key in merged_state_dict:
            merged_state_dict[key] = merged_state_dict[key] * weights[0]
        
        # Add remaining LoRAs
        for lora_path, weight in zip(lora_paths[1:], weights[1:]):
            print(f"Adding {lora_path} with weight {weight:.3f}")
            
            state_dict = load_file(lora_path)
            
            for key in state_dict:
                if key in merged_state_dict:
                    merged_state_dict[key] += state_dict[key] * weight
                else:
                    merged_state_dict[key] = state_dict[key] * weight
        
        # Save merged LoRA
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        save_file(merged_state_dict, output_path)
        
        print(f"\nMerged LoRA saved to: {output_path}")
    
    @staticmethod
    def extract_lora_diff(
        base_model_path: str,
        finetuned_model_path: str,
        output_path: str,
        rank: int = 16
    ):
        """
        Extract LoRA from difference between base and finetuned model
        
        Args:
            base_model_path: Path to base model
            finetuned_model_path: Path to finetuned model
            output_path: Output path for extracted LoRA
            rank: LoRA rank
        """
        print("Extracting LoRA from model difference...")
        print("This is an experimental feature and may not work for all models.")
        
        # Load models
        base_state_dict = load_file(base_model_path)
        finetuned_state_dict = load_file(finetuned_model_path)
        
        lora_state_dict = {}
        
        # Compute difference
        for key in base_state_dict:
            if key in finetuned_state_dict:
                diff = finetuned_state_dict[key] - base_state_dict[key]
                
                # Perform SVD to get low-rank approximation
                if len(diff.shape) == 2:  # Linear layer
                    U, S, V = torch.svd(diff)
                    
                    # Keep top-k singular values
                    U_k = U[:, :rank]
                    S_k = torch.diag(S[:rank])
                    V_k = V[:, :rank].T
                    
                    # Store as LoRA matrices
                    lora_state_dict[f"{key}.lora_A"] = V_k
                    lora_state_dict[f"{key}.lora_B"] = U_k @ S_k
        
        # Save LoRA
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        save_file(lora_state_dict, output_path)
        
        print(f"LoRA extracted and saved to: {output_path}")
    
    @staticmethod
    def merge_lora_to_base(
        base_model_path: str,
        lora_path: str,
        output_path: str,
        alpha: float = 1.0
    ):
        """
        Merge LoRA weights into base model
        
        Args:
            base_model_path: Path to base model
            lora_path: Path to LoRA model
            output_path: Output path for merged model
            alpha: LoRA strength/alpha
        """
        print(f"Merging LoRA into base model...")
        print(f"LoRA strength: {alpha}")
        
        # Load base model and LoRA
        base_state_dict = load_file(base_model_path)
        lora_state_dict = load_file(lora_path)
        
        merged_state_dict = base_state_dict.copy()
        
        # Merge LoRA weights
        lora_keys = set()
        for key in lora_state_dict:
            # Extract base key (remove .lora_A or .lora_B)
            if '.lora_A' in key:
                base_key = key.replace('.lora_A', '')
                lora_keys.add(base_key)
            elif '.lora_B' in key:
                base_key = key.replace('.lora_B', '')
                lora_keys.add(base_key)
        
        # Apply LoRA
        for base_key in lora_keys:
            lora_A_key = f"{base_key}.lora_A"
            lora_B_key = f"{base_key}.lora_B"
            
            if lora_A_key in lora_state_dict and lora_B_key in lora_state_dict:
                lora_A = lora_state_dict[lora_A_key]
                lora_B = lora_state_dict[lora_B_key]
                
                # Compute LoRA update: alpha * B @ A
                lora_update = alpha * (lora_B @ lora_A)
                
                if base_key in merged_state_dict:
                    merged_state_dict[base_key] += lora_update
        
        # Save merged model
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        save_file(merged_state_dict, output_path)
        
        print(f"Merged model saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="LoRA merging utilities")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Merge LoRAs command
    merge_parser = subparsers.add_parser('merge_loras', help='Merge multiple LoRAs')
    merge_parser.add_argument('--loras', nargs='+', required=True, help='Paths to LoRA models')
    merge_parser.add_argument('--weights', nargs='+', type=float, required=True, help='Weights for each LoRA')
    merge_parser.add_argument('--output', type=str, required=True, help='Output path')
    
    # Merge to base command
    base_parser = subparsers.add_parser('merge_to_base', help='Merge LoRA into base model')
    base_parser.add_argument('--base_model', type=str, required=True, help='Base model path')
    base_parser.add_argument('--lora', type=str, required=True, help='LoRA model path')
    base_parser.add_argument('--output', type=str, required=True, help='Output path')
    base_parser.add_argument('--alpha', type=float, default=1.0, help='LoRA strength')
    
    # Extract LoRA command
    extract_parser = subparsers.add_parser('extract_lora', help='Extract LoRA from model difference')
    extract_parser.add_argument('--base_model', type=str, required=True, help='Base model path')
    extract_parser.add_argument('--finetuned_model', type=str, required=True, help='Finetuned model path')
    extract_parser.add_argument('--output', type=str, required=True, help='Output path')
    extract_parser.add_argument('--rank', type=int, default=16, help='LoRA rank')
    
    args = parser.parse_args()
    
    merger = LoRAMerger()
    
    if args.command == 'merge_loras':
        merger.merge_loras(args.loras, args.weights, args.output)
    
    elif args.command == 'merge_to_base':
        merger.merge_lora_to_base(args.base_model, args.lora, args.output, args.alpha)
    
    elif args.command == 'extract_lora':
        merger.extract_lora_diff(args.base_model, args.finetuned_model, args.output, args.rank)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
