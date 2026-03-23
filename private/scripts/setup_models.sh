#!/bin/bash
# =============================================================================
# Copy Models from Downloads to AI-Assistant/ComfyUI
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# =============================================================================
# DIRECTORIES
# =============================================================================

# Source directories (from your Downloads/Compressed folder)
DOWNLOADS_BASE="${HOME}/Downloads/Compressed/AI-Assistant/services/stable-diffusion/models"

# Target directories
COMFYUI_MODELS="/workspace/AI-Assistant/ComfyUI/models"
SD_WEBUI_MODELS="/workspace/AI-Assistant/services/stable-diffusion/models"

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}           Stable Diffusion Models Setup Script${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# =============================================================================
# CHECK SOURCE DIRECTORY
# =============================================================================

if [ -d "$DOWNLOADS_BASE" ]; then
    log_info "Found models in: $DOWNLOADS_BASE"
    SOURCE_DIR="$DOWNLOADS_BASE"
else
    echo ""
    log_warn "Default source directory not found."
    echo ""
    echo "Please enter the full path to your models folder:"
    echo "(e.g., /home/user/Downloads/AI-models/)"
    echo ""
    read -p "Path: " SOURCE_DIR
    
    if [ ! -d "$SOURCE_DIR" ]; then
        log_error "Directory not found: $SOURCE_DIR"
        exit 1
    fi
fi

echo ""
log_info "Source: $SOURCE_DIR"
log_info "Target: $COMFYUI_MODELS"
echo ""

# =============================================================================
# CREATE TARGET DIRECTORIES
# =============================================================================

mkdir -p "$COMFYUI_MODELS/checkpoints"
mkdir -p "$COMFYUI_MODELS/loras"
mkdir -p "$COMFYUI_MODELS/vae"
mkdir -p "$COMFYUI_MODELS/upscale_models"
mkdir -p "$COMFYUI_MODELS/controlnet"
mkdir -p "$COMFYUI_MODELS/embeddings"
mkdir -p "$COMFYUI_MODELS/clip"
mkdir -p "$COMFYUI_MODELS/clip_vision"
mkdir -p "$COMFYUI_MODELS/facerestore_models"
mkdir -p "$COMFYUI_MODELS/insightface"

log_success "Target directories created"

# =============================================================================
# COPY FUNCTIONS
# =============================================================================

copy_with_link() {
    local src="$1"
    local dest="$2"
    local name=$(basename "$src")
    
    if [ -f "$dest/$name" ] || [ -L "$dest/$name" ]; then
        log_warn "Exists: $name (skipping)"
        return 0
    fi
    
    # Use symlink if on same filesystem, copy otherwise
    if ln "$src" "$dest/$name" 2>/dev/null; then
        log_success "Linked: $name"
    elif ln -s "$src" "$dest/$name" 2>/dev/null; then
        log_success "Symlinked: $name"
    else
        log_info "Copying: $name..."
        cp "$src" "$dest/"
        log_success "Copied: $name"
    fi
}

copy_directory() {
    local src_dir="$1"
    local dest_dir="$2"
    local label="$3"
    
    if [ ! -d "$src_dir" ]; then
        log_warn "Source not found: $src_dir"
        return 0
    fi
    
    echo ""
    log_info "Processing $label..."
    
    local count=0
    for file in "$src_dir"/*.{safetensors,ckpt,pt,pth,bin}; do
        [ -f "$file" ] || continue
        copy_with_link "$file" "$dest_dir"
        ((count++))
    done
    
    if [ $count -eq 0 ]; then
        log_warn "No models found in $src_dir"
    else
        log_success "Processed $count $label files"
    fi
}

# =============================================================================
# COPY MODELS
# =============================================================================

# Checkpoints (main models)
copy_directory "$SOURCE_DIR/Stable-diffusion" "$COMFYUI_MODELS/checkpoints" "Checkpoints"

# LoRA
copy_directory "$SOURCE_DIR/Lora" "$COMFYUI_MODELS/loras" "LoRA"

# VAE
copy_directory "$SOURCE_DIR/VAE" "$COMFYUI_MODELS/vae" "VAE"

# Upscalers (ESRGAN)
copy_directory "$SOURCE_DIR/ESRGAN" "$COMFYUI_MODELS/upscale_models" "ESRGAN Upscalers"
copy_directory "$SOURCE_DIR/SwinIR" "$COMFYUI_MODELS/upscale_models" "SwinIR Upscalers"

# Face Restoration
if [ -d "$SOURCE_DIR/GFPGAN" ]; then
    echo ""
    log_info "Processing Face Restoration models..."
    for file in "$SOURCE_DIR/GFPGAN"/*.pth; do
        [ -f "$file" ] || continue
        copy_with_link "$file" "$COMFYUI_MODELS/facerestore_models"
    done
fi

if [ -d "$SOURCE_DIR/Codeformer" ]; then
    for file in "$SOURCE_DIR/Codeformer"/*.pth "$SOURCE_DIR/Codeformer"/*.PTH; do
        [ -f "$file" ] || continue
        copy_with_link "$file" "$COMFYUI_MODELS/facerestore_models"
    done
fi

# LDSR (Large Scale Diffusion Super Resolution)
if [ -d "$SOURCE_DIR/LDSR" ]; then
    echo ""
    log_info "Processing LDSR..."
    mkdir -p "$COMFYUI_MODELS/ldsr"
    for file in "$SOURCE_DIR/LDSR"/*; do
        [ -f "$file" ] || continue
        copy_with_link "$file" "$COMFYUI_MODELS/ldsr"
    done
fi

# BLIP (for captioning)
if [ -d "$SOURCE_DIR/BLIP" ]; then
    echo ""
    log_info "Processing BLIP..."
    mkdir -p "$COMFYUI_MODELS/blip"
    for file in "$SOURCE_DIR/BLIP"/*.pth; do
        [ -f "$file" ] || continue
        copy_with_link "$file" "$COMFYUI_MODELS/blip"
    done
fi

# DeepDanbooru (for tagging)
if [ -d "$SOURCE_DIR/torch_deepdanbooru" ]; then
    echo ""
    log_info "Processing DeepDanbooru..."
    mkdir -p "$COMFYUI_MODELS/deepdanbooru"
    for file in "$SOURCE_DIR/torch_deepdanbooru"/*.pt; do
        [ -f "$file" ] || continue
        copy_with_link "$file" "$COMFYUI_MODELS/deepdanbooru"
    done
fi

# Karlo (for CLIP stats)
if [ -d "$SOURCE_DIR/karlo" ]; then
    echo ""
    log_info "Processing Karlo..."
    mkdir -p "$COMFYUI_MODELS/karlo"
    for file in "$SOURCE_DIR/karlo"/*; do
        [ -f "$file" ] || continue
        copy_with_link "$file" "$COMFYUI_MODELS/karlo"
    done
fi

# =============================================================================
# SHOW SUMMARY
# =============================================================================

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                     MODELS SUMMARY${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

count_files() {
    local dir="$1"
    local name="$2"
    local count=$(find "$dir" -type f \( -name "*.safetensors" -o -name "*.ckpt" -o -name "*.pt" -o -name "*.pth" \) 2>/dev/null | wc -l)
    printf "  %-20s : %d files\n" "$name" "$count"
}

count_files "$COMFYUI_MODELS/checkpoints" "Checkpoints"
count_files "$COMFYUI_MODELS/loras" "LoRA"
count_files "$COMFYUI_MODELS/vae" "VAE"
count_files "$COMFYUI_MODELS/upscale_models" "Upscalers"
count_files "$COMFYUI_MODELS/facerestore_models" "Face Restore"
count_files "$COMFYUI_MODELS/controlnet" "ControlNet"

echo ""
log_success "Models setup complete!"
echo ""
echo "Next steps:"
echo "  1. Start ComfyUI: ./deploy.sh local"
echo "  2. Open: http://localhost:8189"
echo "  3. Your models will appear in the model dropdown menus"
echo ""
