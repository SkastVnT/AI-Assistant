"""
bulk_model_downloader.py — Download LoRAs, ADetailer models, VAEs from CivitAI.

Usage:
    python app/scripts/bulk_model_downloader.py [--dry-run] [--category CATEGORY]

Categories: all, lora_character, lora_effect, adetailer, vae, checkpoint, pose
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

# ── Paths ────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = ROOT / "app"
COMFYUI = ROOT / "ComfyUI" / "models"

DIRS = {
    "lora_character": COMFYUI / "loras" / "characters",
    "lora_effect": COMFYUI / "loras" / "effects",
    "lora_pose": COMFYUI / "loras" / "poses",
    "lora_quality": COMFYUI / "loras" / "anime-quality",
    "lora_style": COMFYUI / "loras" / "styles",
    "embedding": COMFYUI / "embeddings",
    "adetailer_bbox": COMFYUI / "ultralytics" / "bbox",
    "adetailer_segm": COMFYUI / "ultralytics" / "segm",
    "vae": COMFYUI / "vae",
    "checkpoint": COMFYUI / "checkpoints",
    "controlnet": COMFYUI / "controlnet",
}

CIVITAI_API = "https://civitai.com/api/v1"

# Optional: set CIVITAI_API_KEY env var for higher rate limits
API_KEY = os.environ.get("CIVITAI_API_KEY", "")

# ── Model registry ──────────────────────────────────────────────────
# Format: (url_or_model_id, category, subfolder_or_None, friendly_name)

MODELS: list[dict] = [
    # ═══════════════ CHARACTER LoRAs ═══════════════
    {
        "url": "https://civitai.com/models/163219",
        "cat": "lora_character",
        "sub": "hu_tao",
        "name": "GenshinXL Hu Tao",
    },
    {
        "url": "https://civitai.com/models/97336",
        "cat": "lora_character",
        "sub": "hu_tao",
        "name": "Hu Tao Genshin Impact",
    },
    {
        "url": "https://civitai.com/models/434763",
        "cat": "lora_character",
        "sub": "honkai_star_rail",
        "name": "All Characters Honkai Star Rail",
    },
    {
        "url": "https://civitai.com/models/462775",
        "cat": "lora_character",
        "sub": "arknights",
        "name": "All Characters Arknights",
        "version_id": 637867,
    },
    {
        "url": "https://civitai.com/models/422180",
        "cat": "lora_character",
        "sub": "league_of_legends",
        "name": "All Characters League of Legends",
    },
    {
        "url": "https://civitai.com/models/423315",
        "cat": "lora_character",
        "sub": "honkai_impact_3rd",
        "name": "All Characters Honkai Impact 3rd",
    },
    {
        "url": "https://civitai.com/models/482588",
        "cat": "lora_character",
        "sub": "azur_lane",
        "name": "All Characters Azur Lane",
    },
    {
        "url": "https://civitai.com/models/804903",
        "cat": "lora_character",
        "sub": "idolmaster_cinderella",
        "name": "All Characters Idolmaster Cinderella",
    },
    {
        "url": "https://civitai.com/models/115839",
        "cat": "lora_character",
        "sub": "tokisaki_kurumi",
        "name": "Tokisaki Kurumi Date A Live",
    },
    # civitai.red URLs (mirror) — extract model ID, try civitai.com API
    {
        "url": "https://civitai.com/models/938888",
        "cat": "lora_character",
        "sub": "sukebe_elf",
        "name": "All Characters Sukebe Elf no Mori",
    },
    {
        "url": "https://civitai.com/models/796742",
        "cat": "lora_character",
        "sub": "wuthering_waves",
        "name": "All Characters Wuthering Waves",
    },
    {
        "url": "https://civitai.com/models/503179",
        "cat": "lora_character",
        "sub": "idolmaster_shiny_colors",
        "name": "All Characters Idolmaster Shiny Colors",
    },
    {
        "url": "https://civitai.com/models/404014",
        "cat": "lora_character",
        "sub": "bocchi_the_rock",
        "name": "All Characters Bocchi the Rock",
    },
    {
        "url": "https://civitai.com/models/1866697",
        "cat": "lora_character",
        "sub": "honkai_star_rail_amphoreus",
        "name": "All Characters HSR Amphoreus v36",
    },
    {
        "url": "https://civitai.com/models/357976",
        "cat": "lora_character",
        "sub": "genshin_impact_pony",
        "name": "Pony All Characters Genshin 124",
    },
    {
        "url": "https://civitai.com/models/500998",
        "cat": "lora_character",
        "sub": "fate_stay_night",
        "name": "All Characters Fate/Stay Night",
    },
    {
        "url": "https://civitai.com/models/530902",
        "cat": "lora_character",
        "sub": "umamusume",
        "name": "All Characters Umamusume",
    },
    {
        "url": "https://civitai.com/models/450738",
        "cat": "lora_character",
        "sub": "genshin_impact_100",
        "name": "All Characters Genshin Impact 100",
    },
    {
        "url": "https://civitai.com/models/2043415",
        "cat": "lora_character",
        "sub": "honkai_star_rail_2025",
        "name": "2025 All Characters HSR",
    },
    # ═══════════════ EYE LoRAs ═══════════════
    {
        "url": "https://civitai.com/models/1826240",
        "cat": "lora_quality",
        "sub": None,
        "name": "Eyes for Illustrious Perfect Anime Eyes",
    },
    {
        "url": "https://civitai.com/models/91611",
        "cat": "lora_effect",
        "sub": "eyes",
        "name": "Empty Eyes Highlighting",
    },
    {
        "url": "https://civitai.com/models/8275",
        "cat": "lora_effect",
        "sub": "eyes",
        "name": "Empty Eyes Utsurome Hypnotic",
    },
    {
        "url": "https://civitai.com/models/472484",
        "cat": "lora_effect",
        "sub": "eyes",
        "name": "Empty Eyes Pony",
    },
    {
        "url": "https://civitai.com/models/1839798",
        "cat": "lora_effect",
        "sub": "eyes",
        "name": "Bloodshot Eyes",
    },
    {
        "url": "https://civitai.com/models/1970882",
        "cat": "lora_effect",
        "sub": "eyes",
        "name": "Bloodshot Eyes V2",
    },
    {
        "url": "https://civitai.com/models/140423",
        "cat": "lora_effect",
        "sub": "eyes",
        "name": "Sleepy Eyes",
    },
    {
        "url": "https://civitai.com/models/158012",
        "cat": "lora_effect",
        "sub": "eyes",
        "name": "Rolling Eyes",
    },
    {
        "url": "https://civitai.com/models/215444",
        "cat": "lora_effect",
        "sub": "eyes",
        "name": "Uneven Ahegao One Eye Half Closed",
    },
    # ═══════════════ MOUTH / EXPRESSION LoRAs ═══════════════
    {
        "url": "https://civitai.com/models/154510",
        "cat": "lora_effect",
        "sub": "mouth",
        "name": "Mouthpull",
    },
    {
        "url": "https://civitai.com/models/1143396",
        "cat": "lora_effect",
        "sub": "mouth",
        "name": "Mouth Wider Anime Illustrious/Pony",
    },
    {
        "url": "https://civitai.com/models/954895",
        "cat": "lora_effect",
        "sub": "mouth",
        "name": "Pulling Anothers Mouth Open Pony",
    },
    {
        "url": "https://civitai.com/models/174836",
        "cat": "lora_effect",
        "sub": "expression",
        "name": "A Better Crying",
    },
    {
        "url": "https://civitai.com/models/322121",
        "cat": "lora_effect",
        "sub": "expression",
        "name": "Ohogao SDXL Illustrious Pony",
    },
    {
        "url": "https://civitai.com/models/2405459",
        "cat": "lora_effect",
        "sub": "mouth",
        "name": "Pearly Mouthpull",
    },
    {
        "url": "https://civitai.com/models/486043",
        "cat": "lora_effect",
        "sub": "expression",
        "name": "Akanbe Eyelid Pull Tongue Out",
    },
    {
        "url": "https://civitai.com/models/1388307",
        "cat": "lora_effect",
        "sub": "expression",
        "name": "Double Cheek Pull",
    },
    # ═══════════════ DRUNK / SLEEP LoRAs ═══════════════
    {
        "url": "https://civitai.com/models/1323366",
        "cat": "lora_effect",
        "sub": "drunk",
        "name": "Drunk Pony",
    },
    {
        "url": "https://civitai.com/models/1887900",
        "cat": "lora_effect",
        "sub": "drunk",
        "name": "Drunk Pouting Concept",
    },
    {
        "url": "https://civitai.com/models/549243",
        "cat": "lora_effect",
        "sub": "drunk",
        "name": "Drunk Illustrious",
    },
    {
        "url": "https://civitai.com/models/1461180",
        "cat": "lora_effect",
        "sub": "drunk",
        "name": "Drunk on Bar Stool",
    },
    {
        "url": "https://civitai.com/models/1927838",
        "cat": "lora_effect",
        "sub": "drunk",
        "name": "Drunk and Sleep",
    },
    {
        "url": "https://civitai.com/models/64238",
        "cat": "lora_effect",
        "sub": "sleep",
        "name": "Angel Sleep Concept",
    },
    {
        "url": "https://civitai.com/models/1297732",
        "cat": "lora_effect",
        "sub": "sleep",
        "name": "Sleeping with Eyes Open Unconscious",
    },
    {
        "url": "https://civitai.com/models/14228",
        "cat": "lora_effect",
        "sub": "sleep",
        "name": "Drooling on Sleep",
    },
    {
        "url": "https://civitai.com/models/1920246",
        "cat": "lora_effect",
        "sub": "sleep",
        "name": "Sleep Peek Concept",
    },
    # ═══════════════ DROOL / SALIVA LoRAs ═══════════════
    {
        "url": "https://civitai.com/models/2123267",
        "cat": "lora_effect",
        "sub": "drool",
        "name": "Drooling Saliva Spit Collection",
    },
    {
        "url": "https://civitai.com/models/1895630",
        "cat": "lora_effect",
        "sub": "drool",
        "name": "Ballgag Drooling",
    },
    {
        "url": "https://civitai.com/models/1190775",
        "cat": "lora_effect",
        "sub": "drool",
        "name": "Drool Illustrious",
    },
    # ═══════════════ BODY / POSE LoRAs ═══════════════
    {
        "url": "https://civitai.com/models/14247",
        "cat": "lora_effect",
        "sub": "legs",
        "name": "Murkys Legs Up",
    },
    {
        "url": "https://civitai.com/models/17657",
        "cat": "lora_effect",
        "sub": "legs",
        "name": "Legs Together Up Pose",
    },
    {
        "url": "https://civitai.com/models/12945",
        "cat": "lora_effect",
        "sub": "legs",
        "name": "Better Legwears",
    },
    {
        "url": "https://civitai.com/models/10353",
        "cat": "lora_effect",
        "sub": "pose",
        "name": "Jack O Challenge Pose",
    },
    {
        "url": "https://civitai.com/models/438059",
        "cat": "lora_effect",
        "sub": "pose",
        "name": "Dynamic Poses Slider PonyXL",
    },
    {
        "url": "https://civitai.com/models/18738",
        "cat": "lora_effect",
        "sub": "pose",
        "name": "Feet Pose Anime",
    },
    # ═══════════════ STYLE / QUALITY LoRAs ═══════════════
    {
        "url": "https://civitai.com/models/1377820",
        "cat": "lora_quality",
        "sub": None,
        "name": "Add Micro Details Concept",
    },
    {
        "url": "https://civitai.com/models/585589",
        "cat": "lora_effect",
        "sub": "style",
        "name": "Hentai Comic Random Generator Full Color",
    },
    {
        "url": "https://civitai.com/models/588622",
        "cat": "lora_effect",
        "sub": "style",
        "name": "Hentai Comic Random Generator Hard Core",
    },
    # ═══════════════ CLOTHING / OUTFIT LoRAs ═══════════════
    {
        "url": "https://civitai.com/models/10185",
        "cat": "lora_effect",
        "sub": "outfit",
        "name": "Virgin Killer Sweater",
    },
    {
        "url": "https://civitai.com/models/18933",
        "cat": "lora_effect",
        "sub": "outfit",
        "name": "Virgin Destroyer Sweater",
    },
    {
        "url": "https://civitai.com/models/7957",
        "cat": "lora_effect",
        "sub": "outfit",
        "name": "Slingshot Swimsuit",
    },
    {
        "url": "https://civitai.com/models/8762",
        "cat": "lora_effect",
        "sub": "outfit",
        "name": "Bondage Suspension",
    },
    {
        "url": "https://civitai.com/models/9652",
        "cat": "lora_effect",
        "sub": "outfit",
        "name": "Lactation",
    },
    {
        "url": "https://civitai.com/models/17379",
        "cat": "lora_effect",
        "sub": "outfit",
        "name": "Female Masturbation Boob Fondling",
    },
    {
        "url": "https://civitai.com/models/8500",
        "cat": "lora_effect",
        "sub": "outfit",
        "name": "Milking Machine",
    },
    # ═══════════════ ADETAILER / DETECTION MODELS ═══════════════
    {
        "url": "https://civitai.com/models/150925",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Eyes Detection ADetailer",
    },
    {
        "url": "https://civitai.com/models/330727",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Full Eyes Detection ADetailer",
    },
    {
        "url": "https://civitai.com/models/1076050",
        "cat": "adetailer_segm",
        "sub": None,
        "name": "Anime Girl Face Segmentation",
    },
    {
        "url": "https://civitai.com/models/1306938",
        "cat": "adetailer_segm",
        "sub": None,
        "name": "2D Mouth Detection YOLO Segm",
    },
    {
        "url": "https://civitai.com/models/157210",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Animal Ear Detection ADetailer",
    },
    {
        "url": "https://civitai.com/models/1816953",
        "cat": "adetailer_segm",
        "sub": None,
        "name": "Female Body Detection",
    },
    {
        "url": "https://civitai.com/models/2201851",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Person Female Detection",
    },
    {
        "url": "https://civitai.com/models/158108",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Booba Detection ADetailer",
    },
    {
        "url": "https://civitai.com/models/1438127",
        "cat": "adetailer_segm",
        "sub": None,
        "name": "Clothes Detection",
    },
    {
        "url": "https://civitai.com/models/988420",
        "cat": "adetailer_segm",
        "sub": None,
        "name": "Womens Underwear Detection",
    },
    {
        "url": "https://civitai.com/models/1394424",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Thighhigh Detection ADetailer",
    },
    {
        "url": "https://civitai.com/models/329458",
        "cat": "adetailer_segm",
        "sub": None,
        "name": "Hand Detailer Segmentation",
    },
    {
        "url": "https://civitai.com/models/753616",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Text Speech Bubbles Watermarks",
    },
    {
        "url": "https://civitai.com/models/957701",
        "cat": "adetailer_segm",
        "sub": None,
        "name": "2D Belly Torso Stomach YOLO Segm",
    },
    {
        "url": "https://civitai.com/models/1218452",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "2D Female Pubic Hair Detector",
    },
    {
        "url": "https://civitai.com/models/948634",
        "cat": "adetailer_segm",
        "sub": None,
        "name": "2D Armpit YOLO Segmentation",
    },
    {
        "url": "https://civitai.com/models/989087",
        "cat": "adetailer_segm",
        "sub": None,
        "name": "2D One-Piece Swimsuit Detection",
    },
    {
        "url": "https://civitai.com/models/537506",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "ADetailers Collection",
    },
    {
        "url": "https://civitai.com/models/1959394",
        "cat": "adetailer_segm",
        "sub": None,
        "name": "Anime Girl Hair Detect",
    },
    {
        "url": "https://civitai.com/models/1087472",
        "cat": "adetailer_segm",
        "sub": None,
        "name": "2D Strapless Leotard Segm",
    },
    {
        "url": "https://civitai.com/models/2201118",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Soles Detector ADetailer",
    },
    {
        "url": "https://civitai.com/models/150234",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Pussy ADetailer",
    },
    {
        "url": "https://civitai.com/models/490259",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Nipples Model ADetailer",
    },
    {
        "url": "https://civitai.com/models/1313556",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Anime NSFW Detection All-in-One",
    },
    # ═══════════════ VAE ═══════════════
    {
        "url": "https://civitai.com/models/110630",
        "cat": "vae",
        "sub": None,
        "name": "Anything Model VAE v4.0",
    },
    {
        "url": "https://civitai.com/models/217931",
        "cat": "vae",
        "sub": None,
        "name": "SD VAE for Anime",
    },
    {
        "url": "https://civitai.com/models/115979",
        "cat": "vae",
        "sub": None,
        "name": "CleanVAE",
    },
    {
        "url": "https://civitai.com/models/22354",
        "cat": "vae",
        "sub": None,
        "name": "ClearVAE SD15",
    },
    # ═══════════════ CHECKPOINT ═══════════════
    {
        "url": "https://civitai.com/models/827184",
        "cat": "checkpoint",
        "sub": None,
        "name": "WAI Illustrious SDXL",
    },
    # ═══════════════ OPENPOSE LoRAs ═══════════════
    {
        "url": "https://civitai.com/models/129435",
        "cat": "lora_pose",
        "sub": "from_above",
        "name": "OpenPose From Above",
    },
    {
        "url": "https://civitai.com/models/128029",
        "cat": "lora_pose",
        "sub": "standing",
        "name": "OpenPose Standing",
    },
    {
        "url": "https://civitai.com/models/137086",
        "cat": "lora_pose",
        "sub": "squatting",
        "name": "OpenPose Squatting",
    },
    {
        "url": "https://civitai.com/models/130644",
        "cat": "lora_pose",
        "sub": "from_below",
        "name": "OpenPose From Below",
    },
    {
        "url": "https://civitai.com/models/135053",
        "cat": "lora_pose",
        "sub": "leaning_forward",
        "name": "OpenPose Leaning Forward",
    },
    {
        "url": "https://civitai.com/models/139618",
        "cat": "lora_pose",
        "sub": "crossed_legs",
        "name": "OpenPose Crossed Legs",
    },
    {
        "url": "https://civitai.com/models/136185",
        "cat": "lora_pose",
        "sub": "contrapposto",
        "name": "OpenPose Contrapposto",
    },
    {
        "url": "https://civitai.com/models/122442",
        "cat": "lora_pose",
        "sub": "pantyshot",
        "name": "OpenPose Pantyshot Leaning",
    },
    {
        "url": "https://civitai.com/models/138079",
        "cat": "lora_pose",
        "sub": "wariza",
        "name": "OpenPose Wariza",
    },
    {
        "url": "https://civitai.com/models/199989",
        "cat": "lora_pose",
        "sub": "incoming_hug",
        "name": "OpenPose Incoming Hug",
    },
    {
        "url": "https://civitai.com/models/139761",
        "cat": "lora_pose",
        "sub": "hugging_own_legs",
        "name": "OpenPose Hugging Own Legs",
    },
    {
        "url": "https://civitai.com/models/132324",
        "cat": "lora_pose",
        "sub": "from_side",
        "name": "OpenPose From Side",
    },
    {
        "url": "https://civitai.com/models/139509",
        "cat": "lora_pose",
        "sub": "crossed_arms",
        "name": "OpenPose Crossed Arms",
    },
    {
        "url": "https://civitai.com/models/137709",
        "cat": "lora_pose",
        "sub": "seiza",
        "name": "OpenPose Seiza",
    },
    {
        "url": "https://civitai.com/models/143831",
        "cat": "lora_pose",
        "sub": "yandere_trance",
        "name": "OpenPose Yandere Trance",
    },
    {
        "url": "https://civitai.com/models/132242",
        "cat": "lora_pose",
        "sub": "jumping",
        "name": "OpenPose Jumping",
    },
    {
        "url": "https://civitai.com/models/133809",
        "cat": "lora_pose",
        "sub": "paw_poses",
        "name": "OpenPose Paw Poses",
    },
    {
        "url": "https://civitai.com/models/136853",
        "cat": "lora_pose",
        "sub": "hug",
        "name": "OpenPose Hug",
    },
    {
        "url": "https://civitai.com/models/134075",
        "cat": "lora_pose",
        "sub": "reaching_viewer",
        "name": "OpenPose Reaching Towards Viewer",
    },
    {
        "url": "https://civitai.com/models/203686",
        "cat": "lora_pose",
        "sub": "hand_in_hair",
        "name": "OpenPose Hand in Hair",
    },
    {
        "url": "https://civitai.com/models/191514",
        "cat": "lora_pose",
        "sub": "knees_together",
        "name": "OpenPose Knees Together Feet Apart",
    },
    {
        "url": "https://civitai.com/models/141049",
        "cat": "lora_pose",
        "sub": "head_rest",
        "name": "OpenPose Head Rest",
    },
    {
        "url": "https://civitai.com/models/138955",
        "cat": "lora_pose",
        "sub": "running",
        "name": "OpenPose Running",
    },
    {
        "url": "https://civitai.com/models/152396",
        "cat": "lora_pose",
        "sub": "fetal_position",
        "name": "OpenPose Fetal Position",
    },
    {
        "url": "https://civitai.com/models/149843",
        "cat": "lora_pose",
        "sub": "3girls_from_below",
        "name": "OpenPose 3Girls From Below",
    },
    {
        "url": "https://civitai.com/models/14488",
        "cat": "lora_pose",
        "sub": "300_poses",
        "name": "Over 300 Poses SFW",
    },
    {
        "url": "https://civitai.com/models/140628",
        "cat": "lora_pose",
        "sub": "carrying_person",
        "name": "OpenPose Carrying Person",
    },
    {
        "url": "https://civitai.com/models/141814",
        "cat": "lora_pose",
        "sub": "pointing",
        "name": "OpenPose Pointing",
    },
    {
        "url": "https://civitai.com/models/142326",
        "cat": "lora_pose",
        "sub": "holding_hands",
        "name": "OpenPose Holding Hands",
    },
    {
        "url": "https://civitai.com/models/138964",
        "cat": "lora_pose",
        "sub": "strangling_pov",
        "name": "OpenPose Strangling POV",
    },
    {
        "url": "https://civitai.com/models/145473",
        "cat": "lora_pose",
        "sub": "middle_finger",
        "name": "OpenPose Middle Finger",
    },
    {
        "url": "https://civitai.com/models/120904",
        "cat": "lora_pose",
        "sub": "arm_behind_head",
        "name": "OpenPose Arm Behind Head",
    },
    {
        "url": "https://civitai.com/models/142711",
        "cat": "lora_pose",
        "sub": "pov_holding_hands",
        "name": "OpenPose POV Holding Hands",
    },
    {
        "url": "https://civitai.com/models/144931",
        "cat": "lora_pose",
        "sub": "holding_food",
        "name": "OpenPose Holding Food",
    },
    {
        "url": "https://civitai.com/models/167868",
        "cat": "lora_pose",
        "sub": "cover_solo_duo",
        "name": "OpenPose Cover Solo Duo",
    },
    {
        "url": "https://civitai.com/models/192941",
        "cat": "lora_pose",
        "sub": "playing_guitar",
        "name": "OpenPose Playing Guitar",
    },
    {
        "url": "https://civitai.com/models/213828",
        "cat": "lora_pose",
        "sub": "sitting_leaning_back",
        "name": "OpenPose Sitting Leaning Back",
    },
    {
        "url": "https://civitai.com/models/211714",
        "cat": "lora_pose",
        "sub": "crossed_arms_v2",
        "name": "OpenPose Crossed Arms v2",
    },
    # ═══════════════ NEW: from private/new_download.txt ═══════════════
    # Eye-detection (eyeful)
    {
        "url": "https://civitai.com/models/178518",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Eyeful Robust Eye Detection ADetailer",
    },
    # Eye-quality LoRAs
    {
        "url": "https://civitai.com/models/596221",
        "cat": "lora_effect",
        "sub": "eyes",
        "name": "Eyes for Pony Lora Perfect Anime Eyes",
    },
    {
        "url": "https://civitai.com/models/1690241",
        "cat": "lora_effect",
        "sub": "eyes",
        "name": "SDXL White Eyelashes Helper",
    },
    {
        "url": "https://civitai.com/models/1719571",
        "cat": "lora_effect",
        "sub": "eyes",
        "name": "Lora Illustrious XL Eye Focus",
    },
    # Style / screencap
    {
        "url": "https://civitai.com/models/345962",
        "cat": "lora_style",
        "sub": None,
        "name": "Fine Anime Screencap XL",
    },
    {
        "url": "https://civitai.com/models/269772",
        "cat": "lora_style",
        "sub": None,
        "name": "MemaXL Flat Anime Style",
    },
    {
        "url": "https://civitai.com/models/1059388",
        "cat": "lora_style",
        "sub": None,
        "name": "Flux Illustrious Anime Style",
    },
    {
        "url": "https://civitai.com/models/1261082",
        "cat": "lora_style",
        "sub": None,
        "name": "Text Expressive Language Loving It",
    },
    {
        "url": "https://civitai.com/models/1623264",
        "cat": "lora_style",
        "sub": None,
        "name": "Textolyte Style Illustrious",
    },
    # Detail boosters
    {
        "url": "https://civitai.com/models/1145743",
        "cat": "lora_quality",
        "sub": None,
        "name": "Smooth Detailer Booster NoobAI/Illustrious/Pony",
    },
    # NSFW improvement LoRAs (new IDs)
    {
        "url": "https://civitai.com/models/1430080",
        "cat": "lora_effect",
        "sub": "nsfw",
        "name": "Better Ahegao Lora Illustrious",
    },
    {
        "url": "https://civitai.com/models/1466471",
        "cat": "lora_effect",
        "sub": "nsfw",
        "name": "Better Anal Fingering Illustrious",
    },
    {
        "url": "https://civitai.com/models/17122",
        "cat": "lora_effect",
        "sub": "nsfw",
        "name": "Better Pink Pussy",
    },
    {
        "url": "https://civitai.com/models/2183555",
        "cat": "lora_effect",
        "sub": "nsfw",
        "name": "Better Nipples and Pussy",
    },
    {
        "url": "https://civitai.com/models/459445",
        "cat": "lora_effect",
        "sub": "nsfw",
        "name": "Better Panties",
    },
    {
        "url": "https://civitai.com/models/72811",
        "cat": "lora_effect",
        "sub": "nsfw",
        "name": "Better Nipples Maybe",
    },
    {
        "url": "https://civitai.com/models/728342",
        "cat": "lora_effect",
        "sub": "nsfw",
        "name": "Better Cum on Tongue",
    },
    # Character packs (new)
    {
        "url": "https://civitai.com/models/413006",
        "cat": "lora_character",
        "sub": "touhou_pony",
        "name": "Pony Touhou Characters 145",
    },
    {
        "url": "https://civitai.com/models/422352",
        "cat": "lora_character",
        "sub": "oshi_no_ko",
        "name": "All Characters Oshi no Ko",
    },
    {
        "url": "https://civitai.com/models/471854",
        "cat": "lora_character",
        "sub": "zenless_zone_zero",
        "name": "All Characters Zenless Zone Zero",
    },
    {
        "url": "https://civitai.com/models/539130",
        "cat": "lora_character",
        "sub": "fire_emblem",
        "name": "All Characters Fire Emblem",
    },
    {
        "url": "https://civitai.com/models/558527",
        "cat": "lora_character",
        "sub": "frieren",
        "name": "All Characters Frieren",
    },
    {
        "url": "https://civitai.com/models/677863",
        "cat": "lora_character",
        "sub": "nikke",
        "name": "All Characters Nikke",
    },
    # Textual-inversion embeddings
    {
        "url": "https://civitai.com/models/7808",
        "cat": "embedding",
        "sub": None,
        "name": "EasyNegative",
    },
    {
        "url": "https://civitai.com/models/64870",
        "cat": "embedding",
        "sub": None,
        "name": "Better Hands Embedding",
    },
    # ═══════════════ HuggingFace YOLO detectors ═══════════════
    # Format differs: hf_repo + hf_file route through download_hf_yolo()
    {
        "hf_repo": "deepghs/anime_head_detection",
        "hf_file": "head_detect_v1.6_n.onnx",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "DeepGHS Anime Head Detection",
    },
    {
        "hf_repo": "Fuyucchi/yolov8_animeface",
        "hf_file": "yolov8_animeface.pt",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Fuyucchi YOLOv8 Animeface",
    },
    {
        "hf_repo": "deepghs/anime_hand_detection",
        "hf_file": "hand_detect_v1.0_n.onnx",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "DeepGHS Anime Hand Detection",
    },
    {
        "hf_repo": "deepghs/AnimeText_yolo",
        "hf_file": "yolov8s_text_seg.pt",
        "cat": "adetailer_segm",
        "sub": None,
        "name": "DeepGHS AnimeText YOLO Segm",
    },
    {
        "hf_repo": "karma1jp/yolo26n-anime-segmentation",
        "hf_file": "yolo26n-anime-seg.pt",
        "cat": "adetailer_segm",
        "sub": None,
        "name": "Karma1JP YOLOv26n Anime Segmentation",
    },
    {
        "hf_repo": "sophic00/animehead",
        "hf_file": "animehead.pt",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Sophic00 Anime Head",
    },
    {
        "hf_repo": "iitolstykh/YOLO-Face-Person-Detector",
        "hf_file": "yolov8n-face-person.pt",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Itolstykh YOLO Face Person Detector",
    },
    {
        "hf_repo": "Kiuyha/Manga-Bubble-YOLO",
        "hf_file": "manga_bubble_yolo.pt",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Kiuyha Manga Bubble YOLO",
    },
    {
        "hf_repo": "poptoz/yolo26-hand-pose-face-detection",
        "hf_file": "yolo26-hand-pose-face.pt",
        "cat": "adetailer_bbox",
        "sub": None,
        "name": "Poptoz YOLO26 Hand Pose Face Detection",
    },
]


def _extract_model_id(url: str) -> int | None:
    """Extract CivitAI model ID from URL."""
    m = re.search(r"/models/(\d+)", url)
    return int(m.group(1)) if m else None


def _get_model_info(model_id: int) -> dict | None:
    """Fetch model info from CivitAI API."""
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    try:
        resp = requests.get(
            f"{CIVITAI_API}/models/{model_id}", headers=headers, timeout=30
        )
        if resp.status_code == 200:
            return resp.json()
        print(f"  ⚠ API returned {resp.status_code} for model {model_id}")
        return None
    except Exception as e:
        print(f"  ⚠ API error for model {model_id}: {e}")
        return None


def _pick_best_version(info: dict, version_id: int | None = None) -> dict | None:
    """Pick the best version from model info."""
    versions = info.get("modelVersions", [])
    if not versions:
        return None

    # If specific version requested
    if version_id:
        for v in versions:
            if v.get("id") == version_id:
                return v

    # Prefer SDXL/Illustrious/NoobAI/Pony compatible
    sdxl_keywords = {"SDXL", "Illustrious", "NoobAI", "Pony", "XL"}
    for v in versions:
        base = v.get("baseModel", "")
        if any(kw.lower() in base.lower() for kw in sdxl_keywords):
            return v

    # Fallback: latest version
    return versions[0]


def _pick_best_file(version: dict) -> dict | None:
    """Pick the best file from a version (prefer safetensors, then .pt)."""
    files = version.get("files", [])
    if not files:
        return None

    # Prefer safetensors
    for f in files:
        if f.get("name", "").endswith(".safetensors"):
            return f

    # Then .pt
    for f in files:
        if f.get("name", "").endswith(".pt"):
            return f

    # Fallback: first file
    return files[0]


def _resolve_dest_dir(entry: dict) -> Path:
    """Resolve destination directory for a model."""
    cat = entry["cat"]
    base = DIRS.get(cat)
    if not base:
        base = COMFYUI / "loras"
    sub = entry.get("sub")
    if sub:
        return base / sub
    return base


def _download_file(url: str, dest_path: Path, size_hint: int = 0) -> bool:
    """Download a file with progress indication."""
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    try:
        resp = requests.get(
            url, headers=headers, stream=True, timeout=120, allow_redirects=True
        )
        if resp.status_code != 200:
            print(f"  ✗ Download failed: HTTP {resp.status_code}")
            return False

        total = int(resp.headers.get("content-length", size_hint or 0))
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        downloaded = 0
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = (downloaded / total) * 100
                    mb = downloaded / (1024 * 1024)
                    total_mb = total / (1024 * 1024)
                    print(
                        f"\r  ⏬ {mb:.1f}/{total_mb:.1f} MB ({pct:.0f}%)",
                        end="",
                        flush=True,
                    )

        print()
        return True

    except Exception as e:
        print(f"  ✗ Download error: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False


def _download_hf_yolo(entry: dict, dry_run: bool = False) -> dict:
    """Download a YOLO weight file from a HuggingFace repo.

    Strategy: probe HF resolve URL for the listed candidate filename. If 404,
    fall back to scanning the repo's `tree/main` listing via the HF API and
    pick the first .pt/.onnx/.pth file. Result mirrors process_model().
    """
    name = entry["name"]
    repo = entry["hf_repo"]
    candidate = entry.get("hf_file") or ""
    result = {
        "name": name,
        "url": f"hf://{repo}",
        "status": "unknown",
        "file": None,
        "error": None,
    }

    dest_dir = _resolve_dest_dir(entry)
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f"📦 {name}  (HuggingFace: {repo})")

    candidates: list[str] = []
    if candidate:
        candidates.append(candidate)

    # Probe repo file tree via HF API to discover real filenames
    try:
        api_resp = requests.get(
            f"https://huggingface.co/api/models/{repo}",
            timeout=30,
        )
        if api_resp.status_code == 200:
            siblings = api_resp.json().get("siblings", []) or []
            for sib in siblings:
                fname = sib.get("rfilename") or ""
                if fname.lower().endswith((".pt", ".onnx", ".pth", ".safetensors")):
                    if fname not in candidates:
                        candidates.append(fname)
    except Exception as e:
        print(f"  ⚠ HF API probe failed: {e}")

    if not candidates:
        result["status"] = "no_file"
        result["error"] = "No weight files discovered in HF repo"
        return result

    # Try each candidate filename until one downloads
    for fname in candidates:
        url = f"https://huggingface.co/{repo}/resolve/main/{fname}"
        # Use a safe-prefixed local name so multiple repos don't collide
        local_name = f"{repo.replace('/', '_')}__{Path(fname).name}"
        dest_path = dest_dir / local_name
        result["file"] = str(dest_path)

        if dest_path.exists():
            print(f"   ✅ Already exists: {local_name}")
            result["status"] = "exists"
            return result

        if dry_run:
            print(f"   🔍 DRY RUN — would fetch {fname} → {dest_path}")
            result["status"] = "dry_run"
            return result

        # HEAD probe to avoid wasting bandwidth on a 404
        try:
            head = requests.head(url, allow_redirects=True, timeout=20)
            if head.status_code != 200:
                continue
        except Exception:
            continue

        print(f"   ⬇  Fetching {fname}")
        if _download_file(url, dest_path):
            actual_size = dest_path.stat().st_size
            print(f"   ✅ Downloaded: {actual_size / (1024 * 1024):.1f} MB")
            result["status"] = "downloaded"

            meta_path = dest_path.with_suffix(dest_path.suffix + ".json")
            meta_path.write_text(
                json.dumps(
                    {
                        "hf_repo": repo,
                        "hf_file": fname,
                        "name": name,
                        "category": entry["cat"],
                        "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return result

    result["status"] = "download_fail"
    result["error"] = f"None of the candidates downloaded: {candidates[:3]}"
    return result


def process_model(entry: dict, dry_run: bool = False) -> dict:
    """Process a single model entry. Returns result dict."""
    # HuggingFace entries take a different code path
    if entry.get("hf_repo"):
        return _download_hf_yolo(entry, dry_run=dry_run)

    name = entry["name"]
    url = entry["url"]
    model_id = _extract_model_id(url)
    version_id = entry.get("version_id")

    result = {
        "name": name,
        "url": url,
        "status": "unknown",
        "file": None,
        "error": None,
    }

    if not model_id:
        result["status"] = "skip"
        result["error"] = "Cannot extract model ID from URL"
        return result

    print(f"\n{'=' * 60}")
    print(f"📦 {name}")
    print(f"   URL: {url} (ID: {model_id})")

    # Check API
    info = _get_model_info(model_id)
    if not info:
        result["status"] = "api_fail"
        result["error"] = f"Cannot fetch model info for ID {model_id}"
        return result

    version = _pick_best_version(info, version_id)
    if not version:
        result["status"] = "no_version"
        result["error"] = "No compatible version found"
        return result

    file_info = _pick_best_file(version)
    if not file_info:
        result["status"] = "no_file"
        result["error"] = "No downloadable file found"
        return result

    filename = file_info["name"]
    download_url = file_info.get("downloadUrl", "")
    size_bytes = file_info.get("sizeKB", 0) * 1024
    trigger_words = version.get("trainedWords", [])
    base_model = version.get("baseModel", "unknown")

    dest_dir = _resolve_dest_dir(entry)
    dest_path = dest_dir / filename

    print(f"   File: {filename}")
    print(f"   Base: {base_model}")
    print(f"   Size: {size_bytes / (1024 * 1024):.1f} MB")
    if trigger_words:
        print(f"   Triggers: {', '.join(trigger_words[:5])}")
    print(f"   Dest: {dest_path}")

    result["file"] = str(dest_path)

    # Check if already exists
    if dest_path.exists():
        print("   ✅ Already exists — skipping")
        result["status"] = "exists"
        return result

    if dry_run:
        print("   🔍 DRY RUN — would download")
        result["status"] = "dry_run"
        return result

    # Download
    if not download_url:
        download_url = f"https://civitai.com/api/download/models/{version['id']}"

    print("   Downloading...")
    success = _download_file(download_url, dest_path, int(size_bytes))

    if success and dest_path.exists():
        actual_size = dest_path.stat().st_size
        print(f"   ✅ Downloaded: {actual_size / (1024 * 1024):.1f} MB")
        result["status"] = "downloaded"

        # Save metadata alongside
        meta_path = dest_path.with_suffix(".json")
        meta = {
            "model_id": model_id,
            "version_id": version["id"],
            "name": name,
            "filename": filename,
            "base_model": base_model,
            "trigger_words": trigger_words,
            "category": entry["cat"],
            "download_url": download_url,
            "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    else:
        result["status"] = "download_fail"
        result["error"] = "Download failed or file empty"

    return result


def main():
    parser = argparse.ArgumentParser(description="Bulk model downloader for ComfyUI")
    parser.add_argument(
        "--dry-run", action="store_true", help="Only show what would be downloaded"
    )
    parser.add_argument(
        "--category",
        default="all",
        help="Filter by category: all, lora_character, lora_effect, lora_pose, "
        "lora_quality, adetailer_bbox, adetailer_segm, vae, checkpoint",
    )
    args = parser.parse_args()

    # Ensure directories exist
    for d in DIRS.values():
        d.mkdir(parents=True, exist_ok=True)

    # Filter models
    models = MODELS
    if args.category != "all":
        models = [
            m
            for m in models
            if m["cat"] == args.category or m["cat"].startswith(args.category)
        ]

    print("🚀 Bulk Model Downloader")
    print(f"   Models to process: {len(models)}")
    print(f"   Category filter: {args.category}")
    print(f"   Dry run: {args.dry_run}")
    if API_KEY:
        print("   API key: configured")
    else:
        print("   API key: not set (set CIVITAI_API_KEY for higher rate limits)")

    results = []
    for entry in models:
        result = process_model(entry, dry_run=args.dry_run)
        results.append(result)
        # Rate limit: don't hammer CivitAI
        time.sleep(1.0)

    # Summary
    print(f"\n{'=' * 60}")
    print("📊 SUMMARY")
    print(f"{'=' * 60}")

    by_status = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r)

    for status, items in sorted(by_status.items()):
        icon = {
            "downloaded": "✅",
            "exists": "📦",
            "dry_run": "🔍",
            "api_fail": "❌",
            "download_fail": "❌",
            "no_version": "⚠️",
            "no_file": "⚠️",
            "skip": "⏭️",
        }.get(status, "❓")
        print(f"\n{icon} {status.upper()} ({len(items)}):")
        for item in items:
            line = f"   - {item['name']}"
            if item.get("error"):
                line += f" — {item['error']}"
            if item.get("file"):
                line += f" → {Path(item['file']).name}"
            print(line)

    # Save full report
    report_path = APP_ROOT / "storage" / "download_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n📄 Full report saved: {report_path}")

    failed = [
        r
        for r in results
        if r["status"] in ("api_fail", "download_fail", "no_version", "no_file", "skip")
    ]
    if failed:
        print(f"\n⚠️  {len(failed)} models need manual download — see report above")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
