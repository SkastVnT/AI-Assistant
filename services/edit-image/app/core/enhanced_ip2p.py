"""
LLM-Enhanced InstructPix2Pix Pipeline.

This module enhances the InstructPix2Pix editing experience by:
1. Using LLM to parse natural language instructions into structured editing commands
2. Enriching prompts with web search for better context
3. Composing optimal prompts for the diffusion model

Based on research from private docs:
- LLM Parser: Natural instruction → structured editing tags
- Web Search Enrichment: Reference images and style descriptions
- Prompt Composer: Optimal prompt construction for IP2P

References:
- InstructPix2Pix: https://github.com/timothybrooks/instruct-pix2pix
- Research: private/Tổng Quan và Kế Hoạch Nâng Cấp Tính Năng Img2Img
"""

import logging
import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Union, List, Dict, Any, Tuple
from enum import Enum

import torch
from PIL import Image

logger = logging.getLogger(__name__)


# ==============================================================================
# Instruction Types & Parsing
# ==============================================================================

class EditAction(Enum):
    """Types of image editing actions."""
    STYLE_TRANSFER = "style_transfer"
    OBJECT_REPLACE = "object_replace"
    OBJECT_REMOVE = "object_remove"
    OBJECT_ADD = "object_add"
    BACKGROUND_CHANGE = "background_change"
    COLOR_CHANGE = "color_change"
    ATTRIBUTE_CHANGE = "attribute_change"
    EXPRESSION_CHANGE = "expression_change"
    POSE_CHANGE = "pose_change"
    LIGHTING_CHANGE = "lighting_change"
    WEATHER_CHANGE = "weather_change"
    TIME_OF_DAY = "time_of_day"
    SEASON_CHANGE = "season_change"
    ENHANCE = "enhance"
    ARTISTIC = "artistic"
    UNKNOWN = "unknown"


@dataclass
class ParsedInstruction:
    """Structured editing instruction from LLM parsing."""
    
    original_text: str
    action: EditAction
    subject: Optional[str] = None  # What to edit
    target: Optional[str] = None   # What to change to
    modifiers: List[str] = field(default_factory=list)
    style_tags: List[str] = field(default_factory=list)
    negative_tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    # Computed prompts
    positive_prompt: str = ""
    negative_prompt: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original_text,
            "action": self.action.value,
            "subject": self.subject,
            "target": self.target,
            "modifiers": self.modifiers,
            "style_tags": self.style_tags,
            "negative_tags": self.negative_tags,
            "confidence": self.confidence,
            "positive_prompt": self.positive_prompt,
            "negative_prompt": self.negative_prompt,
        }


# Instruction pattern matching
INSTRUCTION_PATTERNS = {
    EditAction.STYLE_TRANSFER: [
        r"(?:make|turn|convert|transform).*(?:into|to|like)\s+(\w+(?:\s+\w+)*)\s*(?:style|art|painting)?",
        r"(?:in the style of|styled as|as a)\s+(\w+(?:\s+\w+)*)",
        r"(?:anime|manga|cartoon|realistic|oil painting|watercolor|sketch)",
    ],
    EditAction.OBJECT_REPLACE: [
        r"(?:replace|change|swap)\s+(?:the\s+)?(\w+(?:\s+\w+)*)\s+(?:with|to|into)\s+(?:a\s+)?(\w+(?:\s+\w+)*)",
        r"(?:turn|make)\s+(?:the\s+)?(\w+)\s+(?:into|to)\s+(?:a\s+)?(\w+)",
    ],
    EditAction.OBJECT_REMOVE: [
        r"(?:remove|delete|erase|get rid of)\s+(?:the\s+)?(\w+(?:\s+\w+)*)",
        r"(?:without)\s+(?:the\s+)?(\w+)",
    ],
    EditAction.OBJECT_ADD: [
        r"(?:add|put|place|insert)\s+(?:a\s+)?(\w+(?:\s+\w+)*)",
        r"(?:with|including)\s+(?:a\s+)?(\w+)",
    ],
    EditAction.BACKGROUND_CHANGE: [
        r"(?:change|replace|make)\s+(?:the\s+)?background\s+(?:to|into)\s+(.+)",
        r"(?:in|at|on)\s+(?:a\s+)?(.+?)\s+background",
    ],
    EditAction.COLOR_CHANGE: [
        r"(?:change|make|turn)\s+(?:the\s+)?(\w+)\s+(?:to\s+)?(\w+)\s*(?:color)?",
        r"(\w+)\s+(?:colored?|hued?)",
    ],
    EditAction.EXPRESSION_CHANGE: [
        r"(?:make|change).*(?:expression|face|look)\s+(?:to\s+)?(\w+)",
        r"(?:smiling|crying|angry|sad|happy|surprised|neutral)",
    ],
    EditAction.LIGHTING_CHANGE: [
        r"(?:with|add|change to)\s+(\w+(?:\s+\w+)*)\s+lighting",
        r"(?:dramatic|soft|harsh|studio|natural|golden hour|neon)\s+light(?:ing)?",
    ],
    EditAction.WEATHER_CHANGE: [
        r"(?:in|with|during)\s+(?:the\s+)?(\w+)\s+(?:weather)?",
        r"(?:rainy|sunny|cloudy|snowy|foggy|stormy)",
    ],
    EditAction.ENHANCE: [
        r"(?:enhance|improve|upscale|sharpen|denoise)",
        r"(?:make|more)\s+(?:detailed|sharp|clear|hd|4k)",
    ],
}


# ==============================================================================
# LLM Instruction Parser
# ==============================================================================

class InstructionParser:
    """
    Parses natural language editing instructions into structured commands.
    
    Can use local patterns or LLM API for enhanced parsing.
    """
    
    def __init__(
        self,
        use_llm: bool = False,
        llm_endpoint: Optional[str] = None,
        llm_api_key: Optional[str] = None,
    ):
        self.use_llm = use_llm
        self.llm_endpoint = llm_endpoint
        self.llm_api_key = llm_api_key
        
        # Load Qwen or other local LLM if available
        self._llm = None
        
        logger.info(f"InstructionParser initialized (use_llm={use_llm})")
    
    def _parse_with_patterns(self, instruction: str) -> ParsedInstruction:
        """Parse instruction using regex patterns."""
        instruction_lower = instruction.lower().strip()
        
        best_match = None
        best_confidence = 0.0
        best_action = EditAction.UNKNOWN
        
        for action, patterns in INSTRUCTION_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, instruction_lower)
                if match:
                    confidence = len(match.group(0)) / len(instruction_lower)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = match
                        best_action = action
        
        # Extract subject and target from match
        subject = None
        target = None
        
        if best_match:
            groups = best_match.groups()
            if len(groups) >= 1:
                subject = groups[0]
            if len(groups) >= 2:
                target = groups[1]
        
        return ParsedInstruction(
            original_text=instruction,
            action=best_action,
            subject=subject,
            target=target,
            confidence=best_confidence,
        )
    
    def _parse_with_llm(self, instruction: str) -> ParsedInstruction:
        """Parse instruction using LLM."""
        if self._llm is None:
            try:
                self._load_llm()
            except Exception as e:
                logger.warning(f"LLM not available: {e}")
                return self._parse_with_patterns(instruction)
        
        prompt = f"""Analyze this image editing instruction and extract structured information.

Instruction: "{instruction}"

Return a JSON object with:
- action: One of [style_transfer, object_replace, object_remove, object_add, background_change, color_change, attribute_change, expression_change, pose_change, lighting_change, weather_change, time_of_day, season_change, enhance, artistic, unknown]
- subject: What is being edited (null if not specific)
- target: What it should become (null if not applicable)
- modifiers: List of modifying words (empty if none)
- style_tags: Suggested style tags for diffusion model
- negative_tags: Things to avoid

JSON only, no explanation:"""

        try:
            response = self._query_llm(prompt)
            data = json.loads(response)
            
            return ParsedInstruction(
                original_text=instruction,
                action=EditAction(data.get("action", "unknown")),
                subject=data.get("subject"),
                target=data.get("target"),
                modifiers=data.get("modifiers", []),
                style_tags=data.get("style_tags", []),
                negative_tags=data.get("negative_tags", []),
                confidence=0.9,  # LLM confidence
            )
        except Exception as e:
            logger.warning(f"LLM parsing failed: {e}")
            return self._parse_with_patterns(instruction)
    
    def _load_llm(self):
        """Load local LLM for parsing."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            # Try Qwen-2.5-0.5B-Instruct for lightweight parsing
            model_name = "Qwen/Qwen2.5-0.5B-Instruct"
            
            logger.info(f"Loading LLM: {model_name}")
            
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._llm = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                device_map="auto",
            )
            
            logger.info("LLM loaded successfully")
            
        except Exception as e:
            logger.warning(f"Could not load local LLM: {e}")
            raise
    
    def _query_llm(self, prompt: str) -> str:
        """Query the LLM."""
        if self._llm is None:
            raise RuntimeError("LLM not loaded")
        
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._llm.device)
        
        with torch.no_grad():
            outputs = self._llm.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.1,
                do_sample=False,
            )
        
        response = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
        # Extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            return json_match.group(0)
        return response
    
    def parse(self, instruction: str) -> ParsedInstruction:
        """
        Parse instruction into structured format.
        
        Args:
            instruction: Natural language editing instruction
            
        Returns:
            Parsed and structured instruction
        """
        if self.use_llm:
            return self._parse_with_llm(instruction)
        return self._parse_with_patterns(instruction)


# ==============================================================================
# Prompt Composer
# ==============================================================================

class PromptComposer:
    """
    Composes optimal prompts for InstructPix2Pix from parsed instructions.
    """
    
    # Style templates
    STYLE_TEMPLATES = {
        EditAction.STYLE_TRANSFER: "{target} style, {modifiers}, masterpiece, best quality",
        EditAction.OBJECT_REPLACE: "replace {subject} with {target}, seamless, realistic",
        EditAction.OBJECT_REMOVE: "remove {subject}, clean background, seamless",
        EditAction.OBJECT_ADD: "add {subject}, realistic integration, high quality",
        EditAction.BACKGROUND_CHANGE: "{target} background, consistent lighting, seamless blend",
        EditAction.COLOR_CHANGE: "change {subject} to {target} color, consistent",
        EditAction.EXPRESSION_CHANGE: "{target} expression, natural, realistic",
        EditAction.LIGHTING_CHANGE: "{target} lighting, atmospheric, professional",
        EditAction.ENHANCE: "enhanced, high resolution, sharp details, 4k",
        EditAction.ARTISTIC: "artistic, creative, unique style",
    }
    
    # Negative prompt templates
    NEGATIVE_TEMPLATES = {
        "default": "low quality, blurry, distorted, artifacts, watermark",
        "face": "deformed face, bad anatomy, extra limbs",
        "anime": "realistic, photo, 3d render",
        "realistic": "cartoon, anime, drawing",
    }
    
    def __init__(self):
        logger.info("PromptComposer initialized")
    
    def compose(
        self,
        parsed: ParsedInstruction,
        additional_tags: Optional[List[str]] = None,
        style_preset: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Compose positive and negative prompts.
        
        Args:
            parsed: Parsed instruction
            additional_tags: Extra tags to add
            style_preset: Style preset (anime, realistic, etc.)
            
        Returns:
            Tuple of (positive_prompt, negative_prompt)
        """
        # Get template
        template = self.STYLE_TEMPLATES.get(
            parsed.action,
            "{original}"
        )
        
        # Fill template
        positive = template.format(
            subject=parsed.subject or "subject",
            target=parsed.target or "target",
            modifiers=", ".join(parsed.modifiers) if parsed.modifiers else "detailed",
            original=parsed.original_text,
        )
        
        # Add style tags
        if parsed.style_tags:
            positive += ", " + ", ".join(parsed.style_tags)
        
        # Add additional tags
        if additional_tags:
            positive += ", " + ", ".join(additional_tags)
        
        # Compose negative prompt
        negative_parts = [self.NEGATIVE_TEMPLATES["default"]]
        
        if style_preset:
            if style_preset in self.NEGATIVE_TEMPLATES:
                negative_parts.append(self.NEGATIVE_TEMPLATES[style_preset])
        
        if parsed.negative_tags:
            negative_parts.extend(parsed.negative_tags)
        
        negative = ", ".join(negative_parts)
        
        # Update parsed instruction
        parsed.positive_prompt = positive
        parsed.negative_prompt = negative
        
        return positive, negative
    
    def enhance_prompt(
        self,
        prompt: str,
        quality_boost: bool = True,
        style: Optional[str] = None,
    ) -> str:
        """
        Enhance an existing prompt with quality boosters.
        
        Args:
            prompt: Original prompt
            quality_boost: Add quality tags
            style: Style to emphasize
            
        Returns:
            Enhanced prompt
        """
        parts = [prompt]
        
        if quality_boost:
            parts.extend([
                "masterpiece",
                "best quality",
                "highly detailed",
            ])
        
        if style == "anime":
            parts.extend(["anime style", "clean lines", "vibrant colors"])
        elif style == "realistic":
            parts.extend(["photorealistic", "professional photo", "8k"])
        elif style == "artistic":
            parts.extend(["artistic", "creative", "unique style"])
        
        return ", ".join(parts)


# ==============================================================================
# Web Search Enrichment
# ==============================================================================

class PromptEnricher:
    """
    Enriches prompts with web search results for better context.
    """
    
    def __init__(
        self,
        search_enabled: bool = True,
    ):
        self.search_enabled = search_enabled
        self._search_client = None
        
        logger.info("PromptEnricher initialized")
    
    def _get_search_client(self):
        """Get search client."""
        if self._search_client is None:
            try:
                from .search import AnimeSearchClient
                self._search_client = AnimeSearchClient()
            except ImportError:
                logger.warning("Search client not available")
        return self._search_client
    
    def enrich_with_character_tags(
        self,
        character_name: str,
        parsed: ParsedInstruction,
    ) -> ParsedInstruction:
        """
        Enrich parsed instruction with character-specific tags from Danbooru.
        
        Args:
            character_name: Character to search for
            parsed: Parsed instruction to enrich
            
        Returns:
            Enriched parsed instruction
        """
        if not self.search_enabled:
            return parsed
        
        client = self._get_search_client()
        if client is None:
            return parsed
        
        try:
            # Search for character on Danbooru
            results = client.search_danbooru(
                tags=[character_name],
                limit=10,
            )
            
            # Extract common tags
            tag_counts: Dict[str, int] = {}
            for result in results:
                for tag in result.get("tags", []):
                    if tag not in [character_name]:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            # Add most common tags
            top_tags = sorted(tag_counts.items(), key=lambda x: -x[1])[:5]
            for tag, count in top_tags:
                if tag not in parsed.style_tags:
                    parsed.style_tags.append(tag)
            
            logger.debug(f"Enriched with tags: {[t for t, _ in top_tags]}")
            
        except Exception as e:
            logger.warning(f"Failed to enrich from search: {e}")
        
        return parsed
    
    def enrich_with_style_reference(
        self,
        style_name: str,
        parsed: ParsedInstruction,
    ) -> ParsedInstruction:
        """
        Enrich with style reference tags.
        
        Args:
            style_name: Style to search for (e.g., "ghibli", "makoto shinkai")
            parsed: Parsed instruction
            
        Returns:
            Enriched instruction
        """
        # Common style mappings
        STYLE_MAPPINGS = {
            "ghibli": ["studio ghibli", "hayao miyazaki", "soft colors", "whimsical", "detailed background"],
            "makoto shinkai": ["makoto shinkai", "your name style", "vibrant sky", "photorealistic backgrounds", "lens flare"],
            "trigger": ["trigger style", "kill la kill", "dynamic poses", "sharp angles", "intense colors"],
            "kyoani": ["kyoto animation", "k-on style", "moe", "soft lighting", "slice of life"],
            "ufotable": ["ufotable", "demon slayer style", "dynamic action", "particle effects", "dramatic lighting"],
            "mappa": ["mappa style", "jujutsu kaisen", "dynamic animation", "dark themes"],
            "wit studio": ["wit studio", "attack on titan style", "epic scale", "detailed action"],
        }
        
        style_lower = style_name.lower()
        for key, tags in STYLE_MAPPINGS.items():
            if key in style_lower or style_lower in key:
                parsed.style_tags.extend(tags)
                break
        
        return parsed


# ==============================================================================
# Enhanced InstructPix2Pix Pipeline
# ==============================================================================

class EnhancedInstructPix2Pix:
    """
    Enhanced InstructPix2Pix with LLM parsing and prompt enrichment.
    
    Usage:
        pipeline = EnhancedInstructPix2Pix()
        
        result = pipeline.edit(
            image=image,
            instruction="make her hair blue and add cat ears",
        )
    """
    
    def __init__(
        self,
        device: str = "cuda",
        dtype: torch.dtype = torch.float16,
        use_llm: bool = False,
        enable_search: bool = True,
    ):
        self.device = device
        self.dtype = dtype
        
        self.parser = InstructionParser(use_llm=use_llm)
        self.composer = PromptComposer()
        self.enricher = PromptEnricher(search_enabled=enable_search)
        
        self._pipeline = None
        
        logger.info("EnhancedInstructPix2Pix initialized")
    
    def _load_pipeline(self):
        """Load InstructPix2Pix pipeline."""
        if self._pipeline is not None:
            return
        
        from diffusers import StableDiffusionInstructPix2PixPipeline
        
        logger.info("Loading InstructPix2Pix pipeline...")
        
        self._pipeline = StableDiffusionInstructPix2PixPipeline.from_pretrained(
            "timothybrooks/instruct-pix2pix",
            torch_dtype=self.dtype,
            safety_checker=None,
        ).to(self.device)
        
        # Enable optimizations
        if hasattr(self._pipeline, "enable_xformers_memory_efficient_attention"):
            try:
                self._pipeline.enable_xformers_memory_efficient_attention()
            except Exception:
                pass
        
        logger.info("InstructPix2Pix loaded")
    
    def parse_instruction(
        self,
        instruction: str,
        character_name: Optional[str] = None,
        style_reference: Optional[str] = None,
    ) -> ParsedInstruction:
        """
        Parse and enrich an editing instruction.
        
        Args:
            instruction: Natural language instruction
            character_name: Character to look up tags for
            style_reference: Style to look up
            
        Returns:
            Parsed and enriched instruction
        """
        # Parse
        parsed = self.parser.parse(instruction)
        
        # Enrich with character tags
        if character_name:
            parsed = self.enricher.enrich_with_character_tags(character_name, parsed)
        
        # Enrich with style
        if style_reference:
            parsed = self.enricher.enrich_with_style_reference(style_reference, parsed)
        
        # Compose final prompts
        self.composer.compose(parsed)
        
        return parsed
    
    def edit(
        self,
        image: Image.Image,
        instruction: str,
        character_name: Optional[str] = None,
        style_reference: Optional[str] = None,
        image_guidance_scale: float = 1.5,
        guidance_scale: float = 7.5,
        num_inference_steps: int = 30,
        seed: Optional[int] = None,
        **kwargs,
    ) -> Tuple[Image.Image, ParsedInstruction]:
        """
        Edit image with natural language instruction.
        
        Args:
            image: Input image
            instruction: Editing instruction
            character_name: Optional character for tag enrichment
            style_reference: Optional style reference
            image_guidance_scale: How much to follow original image
            guidance_scale: How much to follow instruction
            num_inference_steps: Denoising steps
            seed: Random seed
            
        Returns:
            Tuple of (edited image, parsed instruction details)
        """
        # Load pipeline if needed
        self._load_pipeline()
        
        # Parse and enrich instruction
        parsed = self.parse_instruction(
            instruction,
            character_name=character_name,
            style_reference=style_reference,
        )
        
        logger.info(f"Editing with action: {parsed.action.value}")
        logger.debug(f"Positive prompt: {parsed.positive_prompt}")
        logger.debug(f"Negative prompt: {parsed.negative_prompt}")
        
        # Prepare generator
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        
        # Edit
        result = self._pipeline(
            prompt=parsed.positive_prompt,
            negative_prompt=parsed.negative_prompt,
            image=image,
            image_guidance_scale=image_guidance_scale,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
            generator=generator,
            **kwargs,
        )
        
        return result.images[0], parsed
    
    def batch_edit(
        self,
        image: Image.Image,
        instructions: List[str],
        **kwargs,
    ) -> List[Tuple[Image.Image, ParsedInstruction]]:
        """
        Apply multiple editing instructions to an image.
        
        Args:
            image: Input image
            instructions: List of editing instructions
            
        Returns:
            List of (edited image, parsed instruction) tuples
        """
        results = []
        current_image = image
        
        for instruction in instructions:
            edited, parsed = self.edit(current_image, instruction, **kwargs)
            results.append((edited, parsed))
            current_image = edited  # Chain edits
        
        return results
    
    def suggest_edits(
        self,
        image: Image.Image,
        context: Optional[str] = None,
    ) -> List[str]:
        """
        Suggest possible edits for an image.
        
        Args:
            image: Input image
            context: Optional context about the image
            
        Returns:
            List of suggested edit instructions
        """
        suggestions = [
            "Make it more vibrant",
            "Add dramatic lighting",
            "Convert to anime style",
            "Make it look like a painting",
            "Add golden hour lighting",
            "Make the colors more saturated",
            "Add a sunset background",
            "Make it look more professional",
        ]
        
        # Could use image captioning to generate context-aware suggestions
        return suggestions
    
    def unload(self):
        """Unload pipeline."""
        self._pipeline = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# ==============================================================================
# Convenience Functions
# ==============================================================================

_enhanced_ip2p: Optional[EnhancedInstructPix2Pix] = None

def get_enhanced_ip2p() -> EnhancedInstructPix2Pix:
    """Get singleton enhanced InstructPix2Pix instance."""
    global _enhanced_ip2p
    if _enhanced_ip2p is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _enhanced_ip2p = EnhancedInstructPix2Pix(device=device)
    return _enhanced_ip2p


def smart_edit(
    image: Image.Image,
    instruction: str,
    **kwargs,
) -> Image.Image:
    """
    Smart image editing with LLM-enhanced understanding.
    
    Args:
        image: Input image
        instruction: Natural language instruction
        
    Returns:
        Edited image
    """
    pipeline = get_enhanced_ip2p()
    result, _ = pipeline.edit(image, instruction, **kwargs)
    return result


def parse_instruction(instruction: str) -> Dict[str, Any]:
    """
    Parse editing instruction into structured format.
    
    Args:
        instruction: Natural language instruction
        
    Returns:
        Dictionary with parsed instruction details
    """
    pipeline = get_enhanced_ip2p()
    parsed = pipeline.parse_instruction(instruction)
    return parsed.to_dict()
