"""
LoRA layer implementation
"""

import torch
import torch.nn as nn
from typing import List, Optional


class LoRALayer(nn.Module):
    """
    LoRA (Low-Rank Adaptation) layer
    Implements: W' = W + (alpha/r) * B * A
    where A is (r x in_features), B is (out_features x r)
    """
    
    def __init__(
        self,
        in_features: int,
        out_features: int,
        rank: int = 4,
        alpha: float = 1.0,
        dropout: float = 0.0
    ):
        """
        Initialize LoRA layer
        
        Args:
            in_features: Input dimension
            out_features: Output dimension
            rank: LoRA rank
            alpha: LoRA alpha (scaling factor)
            dropout: Dropout rate
        """
        super().__init__()
        
        self.rank = rank
        self.alpha = alpha
        self.scaling = alpha / rank
        
        # LoRA matrices
        self.lora_A = nn.Parameter(torch.zeros(rank, in_features))
        self.lora_B = nn.Parameter(torch.zeros(out_features, rank))
        
        # Dropout
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()
        
        # Initialize weights
        nn.init.kaiming_uniform_(self.lora_A, a=5**0.5)
        nn.init.zeros_(self.lora_B)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: Input tensor
        
        Returns:
            Output tensor
        """
        # Apply LoRA: x @ A^T @ B^T * scaling
        result = self.dropout(x)
        result = result @ self.lora_A.T
        result = result @ self.lora_B.T
        result = result * self.scaling
        
        return result


class LoRALinear(nn.Module):
    """Linear layer with LoRA adaptation"""
    
    def __init__(
        self,
        linear: nn.Linear,
        rank: int = 4,
        alpha: float = 1.0,
        dropout: float = 0.0
    ):
        """
        Wrap a linear layer with LoRA
        
        Args:
            linear: Original linear layer
            rank: LoRA rank
            alpha: LoRA alpha
            dropout: LoRA dropout
        """
        super().__init__()
        
        self.linear = linear
        self.lora = LoRALayer(
            in_features=linear.in_features,
            out_features=linear.out_features,
            rank=rank,
            alpha=alpha,
            dropout=dropout
        )
        
        # Freeze original weights
        for param in self.linear.parameters():
            param.requires_grad = False
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass"""
        # Original linear + LoRA adaptation
        return self.linear(x) + self.lora(x)


def apply_lora_to_model(
    model: nn.Module,
    rank: int = 4,
    alpha: float = 1.0,
    dropout: float = 0.0,
    target_modules: Optional[List[str]] = None
) -> nn.Module:
    """
    Apply LoRA to specific modules in a model
    
    Args:
        model: Model to apply LoRA to
        rank: LoRA rank
        alpha: LoRA alpha
        dropout: LoRA dropout
        target_modules: List of module name patterns to apply LoRA to
    
    Returns:
        Module containing all LoRA layers
    """
    if target_modules is None:
        target_modules = ["to_q", "to_k", "to_v", "to_out.0"]
    
    lora_layers = nn.ModuleDict()
    
    # Recursively find and replace target modules
    for name, module in model.named_modules():
        # Check if this module matches any target pattern
        should_apply = any(target in name for target in target_modules)
        
        if should_apply and isinstance(module, nn.Linear):
            # Create LoRA layer
            lora_linear = LoRALinear(
                linear=module,
                rank=rank,
                alpha=alpha,
                dropout=dropout
            )
            
            # Store LoRA layer
            lora_layers[name.replace('.', '_')] = lora_linear
            
            # Replace module in model
            parent_name = '.'.join(name.split('.')[:-1])
            child_name = name.split('.')[-1]
            
            if parent_name:
                parent = model.get_submodule(parent_name)
            else:
                parent = model
            
            setattr(parent, child_name, lora_linear)
    
    print(f"Applied LoRA to {len(lora_layers)} modules")
    
    return lora_layers
