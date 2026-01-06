"""
Phase 6 Gradio UI
=================

UI components for v0.4.0 features:
- PuLID tab
- EcomID tab
- Batch Processing tab
- GPU/Memory Management tab
"""

import logging
import gradio as gr
from typing import Optional, Tuple
from PIL import Image

logger = logging.getLogger(__name__)


# =============================================================================
# PuLID Tab
# =============================================================================

def create_pulid_tab():
    """Create PuLID identity preservation tab"""
    
    with gr.Tab("PuLID") as tab:
        gr.Markdown("""
        ## 🎭 PuLID - Identity Preservation
        
        Generate and edit images while preserving facial identity.
        Based on ByteDance's NeurIPS 2024 research.
        
        **Features:**
        - 🎯 High-fidelity identity preservation
        - ⚡ Lightning mode for fast generation
        - 🔄 Face swap capability
        """)
        
        with gr.Tabs():
            # Generate Tab
            with gr.Tab("Generate"):
                with gr.Row():
                    with gr.Column(scale=1):
                        pulid_face = gr.Image(
                            label="Reference Face",
                            type="pil",
                            height=256,
                        )
                        pulid_prompt = gr.Textbox(
                            label="Prompt",
                            placeholder="A portrait photo of a person...",
                            lines=3,
                        )
                        pulid_negative = gr.Textbox(
                            label="Negative Prompt",
                            value="blurry, low quality, distorted",
                            lines=2,
                        )
                        
                        with gr.Row():
                            pulid_id_strength = gr.Slider(
                                0.0, 1.0, 0.8,
                                label="ID Strength",
                                info="How much to preserve identity",
                            )
                            pulid_mode = gr.Dropdown(
                                ["standard", "lightning", "fidelity"],
                                value="standard",
                                label="Mode",
                            )
                        
                        with gr.Row():
                            pulid_steps = gr.Slider(
                                10, 50, 30,
                                step=1,
                                label="Steps",
                            )
                            pulid_cfg = gr.Slider(
                                1.0, 15.0, 7.5,
                                label="CFG Scale",
                            )
                        
                        pulid_seed = gr.Number(
                            value=-1,
                            label="Seed (-1 for random)",
                        )
                        
                        pulid_generate_btn = gr.Button(
                            "🎨 Generate",
                            variant="primary",
                        )
                    
                    with gr.Column(scale=1):
                        pulid_output = gr.Image(
                            label="Generated Image",
                            type="pil",
                            height=512,
                        )
                        pulid_info = gr.Markdown("")
            
            # Edit Tab
            with gr.Tab("Edit"):
                with gr.Row():
                    with gr.Column(scale=1):
                        pulid_edit_image = gr.Image(
                            label="Image to Edit",
                            type="pil",
                        )
                        pulid_edit_face = gr.Image(
                            label="Reference Face",
                            type="pil",
                            height=200,
                        )
                        pulid_edit_prompt = gr.Textbox(
                            label="Edit Prompt",
                            placeholder="Make them smile...",
                        )
                        
                        with gr.Row():
                            pulid_edit_id = gr.Slider(
                                0.0, 1.0, 0.8,
                                label="ID Strength",
                            )
                            pulid_edit_strength = gr.Slider(
                                0.0, 1.0, 0.5,
                                label="Edit Strength",
                            )
                        
                        pulid_edit_btn = gr.Button(
                            "✏️ Edit",
                            variant="primary",
                        )
                    
                    with gr.Column(scale=1):
                        pulid_edit_output = gr.Image(
                            label="Edited Image",
                            type="pil",
                        )
            
            # Face Swap Tab
            with gr.Tab("Face Swap"):
                with gr.Row():
                    with gr.Column(scale=1):
                        pulid_swap_source = gr.Image(
                            label="Source Image",
                            type="pil",
                        )
                        pulid_swap_face = gr.Image(
                            label="Target Face",
                            type="pil",
                            height=200,
                        )
                        
                        pulid_swap_strength = gr.Slider(
                            0.0, 1.0, 0.9,
                            label="Swap Strength",
                        )
                        pulid_preserve_expr = gr.Checkbox(
                            label="Preserve Expression",
                            value=True,
                        )
                        
                        pulid_swap_btn = gr.Button(
                            "🔄 Swap Face",
                            variant="primary",
                        )
                    
                    with gr.Column(scale=1):
                        pulid_swap_output = gr.Image(
                            label="Result",
                            type="pil",
                        )
    
    # Event handlers
    async def generate_pulid(
        face, prompt, negative, id_strength, mode, steps, cfg, seed
    ):
        try:
            from app.core.pulid import get_pulid_pipeline, PuLIDConfig, PuLIDMode
            
            if face is None:
                return None, "❌ Please upload a reference face"
            
            pipeline = get_pulid_pipeline()
            
            config = PuLIDConfig(
                id_strength=id_strength,
                num_inference_steps=int(steps),
                guidance_scale=cfg,
                mode=PuLIDMode[mode.upper()],
            )
            
            result = pipeline.generate(
                prompt=prompt,
                face_image=face,
                negative_prompt=negative,
                config=config,
                seed=int(seed) if seed >= 0 else None,
            )
            
            return result.image, f"✅ Generated in {result.generation_time:.1f}s | Seed: {result.seed}"
        except Exception as e:
            logger.error(f"PuLID generate error: {e}")
            return None, f"❌ Error: {str(e)}"
    
    async def edit_pulid(image, face, prompt, id_strength, edit_strength):
        try:
            from app.core.pulid import get_pulid_pipeline
            
            if image is None or face is None:
                return None
            
            pipeline = get_pulid_pipeline()
            result = pipeline.edit_with_id(
                image=image,
                face_reference=face,
                prompt=prompt,
                id_strength=id_strength,
                edit_strength=edit_strength,
            )
            
            return result.image
        except Exception as e:
            logger.error(f"PuLID edit error: {e}")
            return None
    
    async def swap_pulid(source, face, strength, preserve):
        try:
            from app.core.pulid import get_pulid_pipeline
            
            if source is None or face is None:
                return None
            
            pipeline = get_pulid_pipeline()
            result = pipeline.swap_face(
                source_image=source,
                target_face=face,
                swap_strength=strength,
                preserve_expression=preserve,
            )
            
            return result.image
        except Exception as e:
            logger.error(f"PuLID swap error: {e}")
            return None
    
    # Connect handlers
    pulid_generate_btn.click(
        fn=generate_pulid,
        inputs=[
            pulid_face, pulid_prompt, pulid_negative,
            pulid_id_strength, pulid_mode, pulid_steps, pulid_cfg, pulid_seed
        ],
        outputs=[pulid_output, pulid_info],
    )
    
    pulid_edit_btn.click(
        fn=edit_pulid,
        inputs=[
            pulid_edit_image, pulid_edit_face, pulid_edit_prompt,
            pulid_edit_id, pulid_edit_strength
        ],
        outputs=[pulid_edit_output],
    )
    
    pulid_swap_btn.click(
        fn=swap_pulid,
        inputs=[
            pulid_swap_source, pulid_swap_face,
            pulid_swap_strength, pulid_preserve_expr
        ],
        outputs=[pulid_swap_output],
    )
    
    return tab


# =============================================================================
# EcomID Tab
# =============================================================================

def create_ecomid_tab():
    """Create EcomID e-commerce identity tab"""
    
    with gr.Tab("EcomID") as tab:
        gr.Markdown("""
        ## 🛍️ EcomID - E-Commerce Identity
        
        Generate product/marketing images with consistent identity.
        Based on Alibaba's research.
        
        **Features:**
        - 📷 Multi-pose generation
        - 🛒 E-commerce optimized
        - 🎯 Keypoint-based control
        """)
        
        with gr.Tabs():
            # Standard Generate
            with gr.Tab("Generate"):
                with gr.Row():
                    with gr.Column(scale=1):
                        ecomid_face = gr.Image(
                            label="Reference Face",
                            type="pil",
                            height=256,
                        )
                        ecomid_prompt = gr.Textbox(
                            label="Prompt",
                            placeholder="Professional portrait for corporate website...",
                            lines=3,
                        )
                        ecomid_negative = gr.Textbox(
                            label="Negative Prompt",
                            value="ugly, distorted, low quality",
                            lines=2,
                        )
                        
                        with gr.Row():
                            ecomid_id_strength = gr.Slider(
                                0.0, 1.0, 0.8,
                                label="Identity Strength",
                            )
                            ecomid_pose_strength = gr.Slider(
                                0.0, 1.0, 0.5,
                                label="Pose Control",
                            )
                        
                        ecomid_mode = gr.Dropdown(
                            ["standard", "ecommerce", "portrait", "multi_pose"],
                            value="standard",
                            label="Mode",
                        )
                        
                        ecomid_generate_btn = gr.Button(
                            "🎨 Generate",
                            variant="primary",
                        )
                    
                    with gr.Column(scale=1):
                        ecomid_output = gr.Image(
                            label="Generated Image",
                            type="pil",
                        )
            
            # Multi-Pose
            with gr.Tab("Multi-Pose"):
                with gr.Row():
                    with gr.Column(scale=1):
                        ecomid_mp_face = gr.Image(
                            label="Reference Face",
                            type="pil",
                            height=256,
                        )
                        ecomid_mp_prompt = gr.Textbox(
                            label="Prompt",
                            placeholder="Professional headshot...",
                        )
                        ecomid_mp_poses = gr.CheckboxGroup(
                            ["front", "left", "right", "up", "down"],
                            value=["front", "left", "right"],
                            label="Pose Angles",
                        )
                        ecomid_mp_grid = gr.Checkbox(
                            label="Grid Layout",
                            value=True,
                        )
                        
                        ecomid_mp_btn = gr.Button(
                            "📷 Generate Multi-Pose",
                            variant="primary",
                        )
                    
                    with gr.Column(scale=1):
                        ecomid_mp_output = gr.Image(
                            label="Multi-Pose Result",
                            type="pil",
                        )
            
            # E-Commerce
            with gr.Tab("E-Commerce"):
                gr.Markdown("""
                ### 🛒 E-Commerce Mode
                
                Optimized for product photography and marketing materials.
                """)
                
                with gr.Row():
                    with gr.Column(scale=1):
                        ecomid_ec_face = gr.Image(
                            label="Model Face",
                            type="pil",
                        )
                        ecomid_ec_prompt = gr.Textbox(
                            label="Product Description",
                            placeholder="Model wearing blue dress, studio lighting...",
                            lines=3,
                        )
                        ecomid_ec_strength = gr.Slider(
                            0.0, 1.0, 0.8,
                            label="Identity Strength",
                        )
                        
                        ecomid_ec_btn = gr.Button(
                            "🛍️ Generate Product Image",
                            variant="primary",
                        )
                    
                    with gr.Column(scale=1):
                        ecomid_ec_output = gr.Image(
                            label="E-Commerce Result",
                            type="pil",
                        )
    
    # Event handlers
    async def generate_ecomid(face, prompt, negative, id_strength, pose_strength, mode):
        try:
            from app.core.ecomid import get_ecomid_pipeline, EcomIDConfig, EcomIDMode
            
            if face is None:
                return None
            
            pipeline = get_ecomid_pipeline()
            
            config = EcomIDConfig(
                identity_strength=id_strength,
                pose_strength=pose_strength,
                mode=EcomIDMode[mode.upper()],
            )
            
            result = pipeline.generate(
                prompt=prompt,
                face_image=face,
                negative_prompt=negative,
                config=config,
            )
            
            return result.image
        except Exception as e:
            logger.error(f"EcomID error: {e}")
            return None
    
    async def generate_multipose(face, prompt, poses, grid):
        try:
            from app.core.ecomid import get_ecomid_pipeline
            
            if face is None:
                return None
            
            pipeline = get_ecomid_pipeline()
            result = pipeline.generate_multi_pose(
                prompt=prompt,
                face_image=face,
                pose_angles=poses,
                grid_layout=grid,
            )
            
            return result.image
        except Exception as e:
            logger.error(f"EcomID multipose error: {e}")
            return None
    
    async def generate_ecommerce(face, prompt, strength):
        try:
            from app.core.ecomid import get_ecomid_pipeline, EcomIDConfig, EcomIDMode
            
            if face is None:
                return None
            
            pipeline = get_ecomid_pipeline()
            config = EcomIDConfig(
                identity_strength=strength,
                mode=EcomIDMode.ECOMMERCE,
            )
            
            result = pipeline.generate_ecommerce(
                prompt=prompt,
                face_image=face,
                config=config,
            )
            
            return result.image
        except Exception as e:
            logger.error(f"EcomID ecommerce error: {e}")
            return None
    
    # Connect handlers
    ecomid_generate_btn.click(
        fn=generate_ecomid,
        inputs=[
            ecomid_face, ecomid_prompt, ecomid_negative,
            ecomid_id_strength, ecomid_pose_strength, ecomid_mode
        ],
        outputs=[ecomid_output],
    )
    
    ecomid_mp_btn.click(
        fn=generate_multipose,
        inputs=[ecomid_mp_face, ecomid_mp_prompt, ecomid_mp_poses, ecomid_mp_grid],
        outputs=[ecomid_mp_output],
    )
    
    ecomid_ec_btn.click(
        fn=generate_ecommerce,
        inputs=[ecomid_ec_face, ecomid_ec_prompt, ecomid_ec_strength],
        outputs=[ecomid_ec_output],
    )
    
    return tab


# =============================================================================
# Batch Processing Tab
# =============================================================================

def create_batch_tab():
    """Create batch processing management tab"""
    
    with gr.Tab("Batch Processing") as tab:
        gr.Markdown("""
        ## 📦 Batch Processing
        
        Queue and manage multiple image processing jobs.
        
        **Features:**
        - 📋 Priority queue
        - 📊 Progress tracking
        - 🔄 Automatic retries
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                # Job submission
                gr.Markdown("### Submit New Job")
                
                batch_task_type = gr.Dropdown(
                    ["generate", "edit", "upscale", "face_swap"],
                    value="generate",
                    label="Task Type",
                )
                batch_params = gr.JSON(
                    label="Parameters",
                    value={"prompt": "A beautiful landscape", "steps": 30},
                )
                batch_priority = gr.Slider(
                    0, 10, 5,
                    step=1,
                    label="Priority (higher = more urgent)",
                )
                
                with gr.Row():
                    batch_submit_btn = gr.Button(
                        "📤 Submit Job",
                        variant="primary",
                    )
                    batch_submit_multi = gr.Button("📦 Submit Batch")
                
                batch_submit_result = gr.Textbox(
                    label="Submit Result",
                    interactive=False,
                )
            
            with gr.Column(scale=1):
                # Queue status
                gr.Markdown("### Queue Status")
                
                batch_refresh_btn = gr.Button("🔄 Refresh")
                
                batch_queue_stats = gr.JSON(
                    label="Queue Statistics",
                )
        
        gr.Markdown("---")
        
        with gr.Row():
            # Job management
            with gr.Column():
                gr.Markdown("### Job Management")
                
                batch_job_id = gr.Textbox(
                    label="Job ID",
                    placeholder="Enter job ID to check status...",
                )
                
                with gr.Row():
                    batch_check_btn = gr.Button("🔍 Check Status")
                    batch_cancel_btn = gr.Button("❌ Cancel Job", variant="stop")
                
                batch_job_status = gr.JSON(
                    label="Job Status",
                )
    
    # Event handlers
    async def submit_job(task_type, params, priority):
        try:
            from app.core.batch_processing import get_batch_processor
            
            processor = get_batch_processor()
            job_id = await processor.submit(
                task_type=task_type,
                params=params,
                priority=int(priority),
            )
            
            return f"✅ Job submitted: {job_id}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    async def get_queue_stats():
        try:
            from app.core.batch_processing import get_batch_processor
            
            processor = get_batch_processor()
            stats = await processor.get_queue_stats()
            return stats
        except Exception as e:
            return {"error": str(e)}
    
    async def check_job_status(job_id):
        try:
            from app.core.batch_processing import get_batch_processor
            
            if not job_id:
                return {"error": "Please enter a job ID"}
            
            processor = get_batch_processor()
            status = await processor.get_job_status(job_id)
            return status or {"error": "Job not found"}
        except Exception as e:
            return {"error": str(e)}
    
    async def cancel_job(job_id):
        try:
            from app.core.batch_processing import get_batch_processor
            
            if not job_id:
                return {"error": "Please enter a job ID"}
            
            processor = get_batch_processor()
            success = await processor.cancel_job(job_id)
            
            if success:
                return {"status": "cancelled", "job_id": job_id}
            return {"error": "Failed to cancel job"}
        except Exception as e:
            return {"error": str(e)}
    
    # Connect handlers
    batch_submit_btn.click(
        fn=submit_job,
        inputs=[batch_task_type, batch_params, batch_priority],
        outputs=[batch_submit_result],
    )
    
    batch_refresh_btn.click(
        fn=get_queue_stats,
        inputs=[],
        outputs=[batch_queue_stats],
    )
    
    batch_check_btn.click(
        fn=check_job_status,
        inputs=[batch_job_id],
        outputs=[batch_job_status],
    )
    
    batch_cancel_btn.click(
        fn=cancel_job,
        inputs=[batch_job_id],
        outputs=[batch_job_status],
    )
    
    return tab


# =============================================================================
# GPU/Memory Management Tab
# =============================================================================

def create_gpu_tab():
    """Create GPU and memory management tab"""
    
    with gr.Tab("GPU & Memory") as tab:
        gr.Markdown("""
        ## 🖥️ GPU & Memory Management
        
        Monitor and configure GPU resources and memory optimization.
        """)
        
        with gr.Row():
            # GPU Status
            with gr.Column():
                gr.Markdown("### 🎮 GPU Status")
                
                gpu_refresh_btn = gr.Button("🔄 Refresh GPU Status")
                gpu_status_display = gr.JSON(
                    label="GPU Information",
                )
                
                gr.Markdown("### GPU Configuration")
                
                gpu_strategy = gr.Dropdown(
                    ["round_robin", "least_loaded", "vram_based", "compute_based"],
                    value="least_loaded",
                    label="Load Balancing Strategy",
                )
                gpu_apply_btn = gr.Button("⚙️ Apply GPU Config")
                
                gpu_clear_btn = gr.Button("🧹 Clear GPU Cache", variant="secondary")
            
            # Memory Status
            with gr.Column():
                gr.Markdown("### 💾 Memory Status")
                
                mem_refresh_btn = gr.Button("🔄 Refresh Memory Status")
                mem_status_display = gr.JSON(
                    label="Memory Information",
                )
                
                gr.Markdown("### Memory Configuration")
                
                mem_strategy = gr.Dropdown(
                    ["none", "attention", "vae", "model_cpu", "sequential_cpu"],
                    value="attention",
                    label="Offload Strategy",
                )
                mem_target = gr.Slider(
                    2.0, 12.0, 6.0,
                    label="Target VRAM (GB)",
                )
                mem_xformers = gr.Checkbox(
                    label="Enable xformers",
                    value=True,
                )
                mem_quantization = gr.Dropdown(
                    ["none", "fp16", "bf16", "int8"],
                    value="fp16",
                    label="Quantization",
                )
                
                mem_apply_btn = gr.Button("⚙️ Apply Memory Config")
                mem_cleanup_btn = gr.Button("🧹 Cleanup Memory", variant="secondary")
        
        gr.Markdown("---")
        
        # Recommendations
        with gr.Row():
            gr.Markdown("### 💡 Recommendations")
        
        recommendations_display = gr.Markdown("")
    
    # Event handlers
    def get_gpu_status():
        try:
            from app.core.multi_gpu import get_gpu_manager
            
            manager = get_gpu_manager()
            return manager.get_gpu_report()
        except Exception as e:
            return {"error": str(e)}
    
    def get_memory_status():
        try:
            from app.core.model_offload import get_memory_optimizer
            
            optimizer = get_memory_optimizer()
            return optimizer.get_optimization_report()
        except Exception as e:
            return {"error": str(e)}
    
    def apply_gpu_config(strategy):
        try:
            from app.core.multi_gpu import get_gpu_manager, LoadBalanceStrategy
            
            manager = get_gpu_manager()
            manager.strategy = LoadBalanceStrategy(strategy)
            
            return {"status": "applied", "strategy": strategy}
        except Exception as e:
            return {"error": str(e)}
    
    def apply_memory_config(strategy, target, xformers, quant):
        try:
            from app.core.model_offload import (
                get_memory_optimizer,
                OffloadStrategy,
                QuantizationType,
            )
            
            optimizer = get_memory_optimizer()
            optimizer.config.strategy = OffloadStrategy(strategy)
            optimizer.config.target_vram_usage_gb = target
            optimizer.config.enable_xformers = xformers
            optimizer.config.quantization = QuantizationType(quant)
            
            return optimizer.get_optimization_report()
        except Exception as e:
            return {"error": str(e)}
    
    def clear_gpu_cache():
        try:
            import torch
            torch.cuda.empty_cache()
            return {"status": "GPU cache cleared"}
        except Exception as e:
            return {"error": str(e)}
    
    def cleanup_memory():
        try:
            from app.core.model_offload import get_memory_optimizer
            
            optimizer = get_memory_optimizer()
            optimizer.cleanup(aggressive=True)
            
            return optimizer.get_optimization_report()
        except Exception as e:
            return {"error": str(e)}
    
    def get_recommendations():
        try:
            from app.core.model_offload import get_memory_optimizer
            
            optimizer = get_memory_optimizer()
            report = optimizer.get_optimization_report()
            
            recs = report.get("recommendations", [])
            if recs:
                return "\n".join([f"• {r}" for r in recs])
            return "✅ System is optimally configured"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    # Connect handlers
    gpu_refresh_btn.click(
        fn=get_gpu_status,
        inputs=[],
        outputs=[gpu_status_display],
    )
    
    mem_refresh_btn.click(
        fn=get_memory_status,
        inputs=[],
        outputs=[mem_status_display],
    )
    
    gpu_apply_btn.click(
        fn=apply_gpu_config,
        inputs=[gpu_strategy],
        outputs=[gpu_status_display],
    )
    
    mem_apply_btn.click(
        fn=apply_memory_config,
        inputs=[mem_strategy, mem_target, mem_xformers, mem_quantization],
        outputs=[mem_status_display],
    )
    
    gpu_clear_btn.click(
        fn=clear_gpu_cache,
        inputs=[],
        outputs=[gpu_status_display],
    )
    
    mem_cleanup_btn.click(
        fn=cleanup_memory,
        inputs=[],
        outputs=[mem_status_display],
    )
    
    # Auto-refresh recommendations
    tab.select(
        fn=get_recommendations,
        inputs=[],
        outputs=[recommendations_display],
    )
    
    return tab


# =============================================================================
# Main Integration
# =============================================================================

def add_phase6_tabs(demo: gr.Blocks) -> gr.Blocks:
    """Add Phase 6 tabs to existing Gradio app"""
    
    with demo:
        create_pulid_tab()
        create_ecomid_tab()
        create_batch_tab()
        create_gpu_tab()
    
    return demo


def create_phase6_demo() -> gr.Blocks:
    """Create standalone Phase 6 demo"""
    
    with gr.Blocks(
        title="Edit Image v0.4.0 - Phase 6",
        theme=gr.themes.Soft(),
    ) as demo:
        gr.Markdown("""
        # 🎨 Edit Image Tool v0.4.0
        ## Phase 6 - Advanced Features
        
        **New in v0.4.0:**
        - 🎭 **PuLID** - Identity preservation (ByteDance NeurIPS 2024)
        - 🛍️ **EcomID** - E-commerce identity generation (Alibaba)
        - 📦 **Batch Processing** - Queue management for bulk operations
        - 🖥️ **Multi-GPU** - Load balancing across GPUs
        - 💾 **Memory Optimization** - Smart offloading strategies
        """)
        
        create_pulid_tab()
        create_ecomid_tab()
        create_batch_tab()
        create_gpu_tab()
    
    return demo


if __name__ == "__main__":
    demo = create_phase6_demo()
    demo.launch(server_name="0.0.0.0", server_port=7860)
