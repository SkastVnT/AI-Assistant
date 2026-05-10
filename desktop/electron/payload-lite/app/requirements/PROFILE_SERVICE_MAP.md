# Service to Environment Map

## Core profile (`venv-core`)
- hub-gateway
- chatbot
- speech2text
- text2sql
- document-intelligence
- mcp-server

Install source: [profile_core_services.txt](profile_core_services.txt)

## Image profile (`venv-image`)
- image-upscale
- lora-training

Install source: [profile_image_ai_services.txt](profile_image_ai_services.txt)

## Services with dedicated local venv
- stable-diffusion: uses `services/stable-diffusion/venv` via `webui.bat`
- edit-image: uses `services/edit-image/venv` via its own launcher/setup

## Parallel launchers
- Core stack: [scripts/start-core-services-parallel.bat](../scripts/start-core-services-parallel.bat)
- Image stack: [scripts/start-image-services-parallel.bat](../scripts/start-image-services-parallel.bat)
