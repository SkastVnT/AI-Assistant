"""
Convert LoRA between different formats (safetensors, pytorch, diffusers)
"""

import torch
from pathlib import Path
from safetensors.torch import load_file, save_file
import argparse


class LoRAConverter:
    """Convert LoRA between different formats"""
    
    @staticmethod
    def safetensors_to_pytorch(input_path: str, output_path: str):
        """
        Convert safetensors to pytorch .pt/.pth format
        
        Args:
            input_path: Input .safetensors file
            output_path: Output .pt or .pth file
        """
        print(f"Converting {input_path} to PyTorch format...")
        
        # Load safetensors
        state_dict = load_file(input_path)
        
        # Save as pytorch
        torch.save(state_dict, output_path)
        
        print(f"Saved to: {output_path}")
    
    @staticmethod
    def pytorch_to_safetensors(input_path: str, output_path: str):
        """
        Convert pytorch .pt/.pth to safetensors format
        
        Args:
            input_path: Input .pt or .pth file
            output_path: Output .safetensors file
        """
        print(f"Converting {input_path} to safetensors format...")
        
        # Load pytorch
        state_dict = torch.load(input_path, map_location='cpu')
        
        # Handle different pytorch formats
        if isinstance(state_dict, dict) and 'state_dict' in state_dict:
            state_dict = state_dict['state_dict']
        
        # Convert to CPU and float32
        state_dict = {k: v.cpu().float() for k, v in state_dict.items()}
        
        # Save as safetensors
        save_file(state_dict, output_path)
        
        print(f"Saved to: {output_path}")
    
    @staticmethod
    def resize_lora_rank(
        input_path: str,
        output_path: str,
        new_rank: int,
        method: str = "truncate"
    ):
        """
        Resize LoRA rank (experimental)
        
        Args:
            input_path: Input LoRA file
            output_path: Output LoRA file
            new_rank: New rank
            method: Resize method ('truncate' or 'pad')
        """
        print(f"Resizing LoRA rank to {new_rank}...")
        print(f"Method: {method}")
        
        # Load LoRA
        state_dict = load_file(input_path)
        new_state_dict = {}
        
        for key, tensor in state_dict.items():
            if '.lora_A' in key or '.lora_B' in key:
                current_rank = tensor.shape[0] if '.lora_A' in key else tensor.shape[1]
                
                if current_rank == new_rank:
                    new_state_dict[key] = tensor
                
                elif current_rank > new_rank:
                    # Truncate
                    if '.lora_A' in key:
                        new_state_dict[key] = tensor[:new_rank, :]
                    else:  # lora_B
                        new_state_dict[key] = tensor[:, :new_rank]
                
                else:  # current_rank < new_rank
                    # Pad
                    if method == "pad":
                        if '.lora_A' in key:
                            pad_size = (new_rank - current_rank, 0)
                            new_state_dict[key] = torch.nn.functional.pad(
                                tensor, (0, 0, 0, pad_size[0])
                            )
                        else:  # lora_B
                            pad_size = (0, new_rank - current_rank)
                            new_state_dict[key] = torch.nn.functional.pad(
                                tensor, (0, pad_size[1], 0, 0)
                            )
                    else:
                        print(f"Warning: Cannot increase rank with truncate method")
                        new_state_dict[key] = tensor
            else:
                new_state_dict[key] = tensor
        
        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        save_file(new_state_dict, output_path)
        
        print(f"Resized LoRA saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert LoRA formats")
    subparsers = parser.add_subparsers(dest='command', help='Conversion command')
    
    # Safetensors to PyTorch
    st_to_pt = subparsers.add_parser('st2pt', help='Convert safetensors to pytorch')
    st_to_pt.add_argument('--input', required=True, help='Input .safetensors file')
    st_to_pt.add_argument('--output', required=True, help='Output .pt file')
    
    # PyTorch to Safetensors
    pt_to_st = subparsers.add_parser('pt2st', help='Convert pytorch to safetensors')
    pt_to_st.add_argument('--input', required=True, help='Input .pt file')
    pt_to_st.add_argument('--output', required=True, help='Output .safetensors file')
    
    # Resize rank
    resize = subparsers.add_parser('resize', help='Resize LoRA rank')
    resize.add_argument('--input', required=True, help='Input LoRA file')
    resize.add_argument('--output', required=True, help='Output LoRA file')
    resize.add_argument('--rank', type=int, required=True, help='New rank')
    resize.add_argument('--method', choices=['truncate', 'pad'], default='truncate')
    
    args = parser.parse_args()
    
    converter = LoRAConverter()
    
    if args.command == 'st2pt':
        converter.safetensors_to_pytorch(args.input, args.output)
    
    elif args.command == 'pt2st':
        converter.pytorch_to_safetensors(args.input, args.output)
    
    elif args.command == 'resize':
        converter.resize_lora_rank(args.input, args.output, args.rank, args.method)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
