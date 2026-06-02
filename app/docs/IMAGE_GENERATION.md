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
| Image pipeline | `app/image_pipeline/` | Reasoning/anime orchestration modules |

## Generated Files

Generated images, local model binaries, ComfyUI input/output files, and runtime storage outputs should stay out of Git. Seed registry data under `app/storage/character_db/` is treated as source data until explicitly reclassified.

## Local Adult Profiles

- `laptop_6gb` is SFW by default. Verified-adult requests require explicit
  per-request `content_mode=adult_only` and `adult_verified=true`.
- `pc_12gb` and `vps_96gb` are adult-default workers. Start them only with
  `ANIME_PIPELINE_ASSERT_VERIFIED_ADULT_WORKER=1`.
- Adult requests use local validation only. The local subject guard rejects
  prohibited or age-ambiguous contexts before generation and refinement.
- Adult benchmark fixtures and operator-authored instructions belong under
  `.local/benchmarks/adult_only/`; use
  `app/configs_vps/adult_fixture_pack.example.yaml` as the schema.
