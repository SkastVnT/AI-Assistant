# Image Generation

AI-Assistant supports hosted image providers and local image services.

## Hosted Providers

The chatbot image router can use providers such as fal.ai, Black Forest Labs, Replicate, OpenAI, StepFun, Together AI, and ComfyUI-backed local workflows depending on configured API keys and local availability.

Provider implementation files live in `services/chatbot/core/image_gen/providers/`.

## Local Services

| Component | Path | Notes |
|---|---|---|
| Stable Diffusion | `services/stable-diffusion/` | Local SD backend, default documented port `7861` |
| Edit Image / ComfyUI | `services/edit-image/` | ComfyUI-backed edit service, default documented port `8100` |
| Main ComfyUI tree | `ComfyUI/` | Local runtime; models and outputs are not tracked |
| Image pipeline | `image_pipeline/` | Reasoning/anime orchestration modules |

## Generated Files

Generated images, local model binaries, ComfyUI input/output files, and runtime storage outputs should stay out of Git. Seed registry data under `storage/character_db/` is treated as source data until explicitly reclassified.
