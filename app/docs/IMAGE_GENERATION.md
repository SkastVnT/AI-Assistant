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

## Public SFW Parity Benchmarks

The official LOCAL anime benchmark entry point is:

```bash
python app/scripts/run_anime_benchmark.py --profile pc_12gb --suite sfw --parity --run-id sfw-parity-001 --artifact-root .local/benchmarks/sfw
```

- `pc_12gb` is the default local quality benchmark profile.
- `--suite auto` resolves to SFW; `adult_only` must be selected explicitly.
- SFW benchmark runs force `ANIME_PIPELINE_ADULT_CONTENT_POLICY=sfw_only` inside the benchmark process so quality profiles can be tested without adult-worker assertion.
- Comparator captures are imported with `app/scripts/anime_benchmark_evidence.py`, then sanitized reports are published to `app/docs/benchmark-reports/<run_id>/`.
- `local_quality_gate_passed` is not a parity claim. ChatGPT/Gemini parity requires local run artifacts plus comparator blind-review evidence.

## Local Adult Profiles

- `laptop_6gb` is SFW by default. Verified-adult requests require explicit
  per-request `content_mode=adult_only` and `adult_verified=true`.
- For normal service runs, `pc_12gb`, `rtx5070`, and `vps_96gb` are adult-default
  workers unless overridden by config/env. Start adult-default workers only with
  `ANIME_PIPELINE_ASSERT_VERIFIED_ADULT_WORKER=1`.
- Adult requests use local validation only. The local subject guard rejects
  prohibited or age-ambiguous contexts before generation and refinement.
- Adult benchmark fixtures and operator-authored instructions belong under
  `.local/benchmarks/adult_only/`; use
  `app/configs_vps/adult_fixture_pack.example.yaml` as the schema.
