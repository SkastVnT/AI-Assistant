"""
One-shot script: update all 16 all-characters LoRA entries in configs/lora_registry.yaml.
Adds civitai_version_id, civitai_filename, characters list, and fixes trigger_words/notes.
Run from repo root: python app/scripts/_update_all_chars_registry.py
"""
import os
import sys

try:
    from ruamel.yaml import YAML
    USE_RUAMEL = True
except ImportError:
    import yaml
    USE_RUAMEL = False

REGISTRY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "configs", "lora_registry.yaml"
)
REGISTRY_PATH = os.path.normpath(REGISTRY_PATH)

# ── All update payloads, indexed by registry entry name ─────────────────────
UPDATES = {
    "azur_lane_all_pony.safetensors": {
        "civitai_version_id": 554678,
        "civitai_filename": "azur_lane_all_v1.safetensors",
        "trigger_words": ["all in one"],
        "characters": [
            "bremerton", "formidable", "taihou", "sirius", "prinz_eugen",
            "belfast", "atago", "ayanami", "le_malin", "illustrious",
            "baltimore", "kashino", "dido", "cheshire", "shinano", "unicorn",
            "st_louis", "new_jersey", "laffey", "enterprise", "aegir", "zara",
            "implacable", "z23", "perseus", "takao", "akagi", "bismarck",
            "honolulu", "indomitable", "tashkent", "nagato", "kaga", "javelin",
            "musashi", "noshiro", "roon", "owari", "amagi", "unzen",
            "friedrich_der_grosse", "shimakaze", "yamashiro", "helena",
            "richelieu", "pola", "azuma", "essex", "shoukaku", "bismarck_zwei",
            "clemenceau", "yuudachi", "hammann", "sovetskaya_rossiya",
            "champagne", "marco_polo", "golden_hind", "ark_royal",
        ],
        "notes": "200+ chars. Use charactername_(azur_lane) format. Guide: civitai.com/articles/5480",
    },
    "all_chars_hsr_illustrious.safetensors": {
        "civitai_version_id": 1010462,
        "civitai_filename": "star_rail_all-000014.safetensors",
        "trigger_words": [
            "charactername_(honkai: star rail)",
            "herta_(unknowable_domain)",
            "fugue (honkai: star rail)",
            "rappa (honkai: star rail)",
            "march 7th (hunt) (honkai: star rail)",
        ],
        "characters": [
            "trailblazer", "kafka", "stelle", "sparkle", "march_7th", "acheron",
            "firefly", "silver_wolf", "dan_heng", "aventurine", "caelus",
            "black_swan", "blade", "jingliu", "dan_heng_imbibitor_lunae",
            "fu_xuan", "ruan_mei", "himeko", "topaz", "dr_ratio", "tingyun",
            "pom-pom", "robin", "seele", "herta", "huohuo", "jade", "rappa",
            "luocha", "qingque", "yunli", "lingsha", "jiaoqiu", "argenti",
            "asta", "numby", "sushang", "pela", "yanqing", "moze", "bailu",
            "fugue", "hanya", "sam", "gallagher", "misha", "xueyi", "yingxing",
            "yukong", "guinaifen", "constance", "danfeng", "luka", "hook",
            "natasha", "sunday", "boothill", "gepard", "serval", "welt",
        ],
        "notes": (
            "70+ chars (Illustrious-XL v2.0). Special triggers: herta_(unknowable_domain), "
            "fugue (honkai: star rail), rappa (honkai: star rail), "
            "march 7th (hunt) (honkai: star rail). "
            "Standard: charactername_(honkai: star rail)."
        ),
    },
    "all_chars_arknights_pony.safetensors": {
        "civitai_version_id": 637867,
        "civitai_filename": "arknights_all_v4_0711.safetensors",
        "trigger_words": ["arknights", "all in one"],
        "notes": "150-200 chars. Use charactername_(arknights) format. Guide: civitai.com/articles/5342",
    },
    "all_chars_lol_pony.safetensors": {
        "civitai_version_id": 470400,
        "civitai_filename": "league_of_legends_pony.safetensors",
        "trigger_words": ["all in one"],
        "characters": [
            "ahri", "jinx", "sona", "gwen", "lux", "caitlyn", "vi", "soraka",
            "lulu", "evelynn", "riven", "katarina", "miss_fortune", "kindred",
            "neeko", "poppy", "briar", "sett", "annie", "ashe", "nami",
            "morgana", "leona", "zoe", "janna", "seraphine", "fiora", "kayn",
            "leblanc", "diana", "kayle", "vayne", "zeri", "thresh", "karma",
            "yone", "yuumi", "senna", "cassiopeia", "orianna", "jayce",
            "rakan", "quinn", "braum", "hwei", "camille", "yasuo", "vex",
            "graves", "garen", "qiyana", "viego", "zed", "lillia", "talon",
            "xayah",
        ],
        "notes": "50+ chars. Use charactername_(league_of_legends) format.",
    },
    "all_chars_hi3_pony.safetensors": {
        "civitai_version_id": 561561,
        "civitai_filename": "honkai_impact_3rd_v1.safetensors",
        "trigger_words": ["all in one"],
        "characters": [
            "kiana_kaslana", "raiden_mei", "bronya_zaychik", "murata_himeko",
            "theresa_apocalypse", "fu_hua", "yae_sakura", "kallen_kaslana",
            "bianka_durandal_ataegina", "rita_rossweisse", "seele_vollerei",
            "rozaliya_olenyeva", "liliya_olenyeva", "elysia", "mobius", "raven",
            "carole_peppers", "pardofelis", "eden", "aponia", "griseo", "vill-v",
            "li_sushang", "senadina", "coralie", "helia", "thelema",
        ],
        "notes": (
            "30+ chars. Use danbooru tag format. "
            "Skin variants: kiana_kaslana_(white_comet), bianka_(haxxor_bunny), etc. "
            "Guide: civitai.com/articles/5619"
        ),
    },
    "all_chars_genshin_pony124.safetensors": {
        "civitai_version_id": 550532,
        "civitai_filename": "genshin_v4.safetensors",
        "trigger_words": [
            "hina_(genshin_impact)",
            "sethos_(genshin_impact)",
            "raiden_shogun_mitake",
        ],
        "notes": (
            "127 chars (v4.0). Special triggers for new chars: hina_(genshin_impact), "
            "sethos_(genshin_impact), raiden_shogun_mitake. "
            "Standard: charactername_(genshin_impact). Clorinde: use weight 0.6~0.8. "
            "Guide: civitai.com/articles/4584"
        ),
    },
    "all_chars_genshin_sd15.safetensors": {
        "civitai_version_id": 501862,
        "civitai_filename": "mki-genshin108-1.5-v3.safetensors",
        "trigger_words": [
            "aether (genshin impact)",
            "lumine (genshin impact)",
            "paimon (genshin impact)",
            "hu tao (genshin impact)",
            "keqing (genshin impact)",
            "ganyu (genshin impact)",
            "raiden shogun",
            "kamisato ayaka",
            "yae miko",
            "nahida (genshin impact)",
            "furina (genshin impact)",
            "arlecchino (genshin impact)",
        ],
        "notes": (
            "100 chars. SD1.5 (NovelAI1 base). "
            "IMPORTANT: use 'charactername (genshin impact)' format — spaces, no underscores. "
            "Costume suffix e.g. 'ganyu (twilight blossom) (genshin impact)'. "
            "CLIP SKIP 2."
        ),
    },
    "all_chars_wuthering_waves_pony.safetensors": {
        "civitai_version_id": 890954,
        "civitai_filename": "wuthering_waves_all.safetensors",
        "trigger_words": ["wuthering waves"],
        "characters": [
            "calcharo", "phrolova", "changli", "yinlin", "female_rover", "jinhsi",
            "zhezhi", "camellya", "yangyang", "danjin", "encore", "jiyan",
            "sanhua", "scar", "taoqi", "the_shorekeeper", "xiangli_yao",
            "baizhi", "male_rover", "zapstring", "chixia", "cloudy", "verina",
            "cosmos", "jianxin", "lingyang",
        ],
        "notes": "27 chars. Use charactername_(wuthering_waves) format, e.g. changli_(wuthering_waves).",
    },
    "all_chars_umamusume_pony.safetensors": {
        "civitai_version_id": 589974,
        "civitai_filename": "umamusume_all.safetensors",
        "trigger_words": ["all in one"],
        "notes": (
            "50~100 chars. Use character name directly — no 'character:' prefix needed. "
            "Guide: civitai.com/articles/5841"
        ),
    },
    "all_chars_idolmaster_cinderella_pony.safetensors": {
        "civitai_version_id": 899943,
        "civitai_filename": "idolmaster_cinderella_all.safetensors",
        "trigger_words": [":idolmaster_cinderella"],
        "notes": (
            "250+ chars (255 folders). "
            "Use danbooru tag names directly, e.g. shimamurauzuki, tachibanaarisu. "
            "Guide: civitai.com/articles/7719"
        ),
    },
    "all_chars_idolmaster_shinycolors_pony.safetensors": {
        "civitai_version_id": 559278,
        "civitai_filename": "idolmaster_shiny_colors.safetensors",
        "trigger_words": ["all in one"],
        "notes": "Guide: civitai.com/articles/5610. Note: suzuki_hana not covered.",
    },
    "all_chars_bocchi_the_rock_sdxl.safetensors": {
        "civitai_version_id": 450477,
        "civitai_filename": "bocchi_the_rock.safetensors",
        "trigger_words": [
            "gotoh_hitori",
            "ijichi_nijika",
            "yamada_ryo",
            "kita_ikuyo",
            "ijichi_seika",
            "pa-san",
        ],
        "notes": "SDXL base (Animagine XL 3.0), NOT Pony. Inference: Animagine XL 3.1. Weight 0.8~1.",
    },
    "all_chars_fate_stay_night_pony.safetensors": {
        "civitai_version_id": 556880,
        "civitai_filename": "stay_night_all.safetensors",
        "trigger_words": ["all in one"],
        "characters": [
            "artoria_pendragon_(fate)", "saber_(fate)", "cu_chulainn_(fate)",
            "archer_(fate)", "medusa_(fate)", "gilgamesh_(fate)", "mordred_(fate)",
            "jeanne_d'arc_alter_(fate)", "nero_claudius_(fate)", "medea_(fate)",
            "artoria_pendragon_(lancer)_(fate)", "enkidu_(fate)", "merlin_(fate)",
            "tamamo_(fate)", "mysterious_heroine_x_(fate)", "jeanne_d'arc_(fate)",
            "okita_souji_(fate)", "ozymandias_(fate)", "bedivere_(fate)",
            "euryale_(fate)", "florence_nightingale_(fate)", "altera_(fate)",
            "edmond_dantes_(fate)", "robin_hood_(fate)", "nursery_rhyme_(fate)",
            "kiyohime_(fate)", "oda_nobunaga_(fate)", "hassan_of_serenity_(fate)",
            "arjuna_(fate)", "tamamo_cat_(fate)", "minamoto_no_raikou_(fate)",
            "elizabeth_bathory_(fate)", "shuten_douji_(fate)",
            "jeanne_d'arc_(ruler)_(fate)", "bb_(fate)", "semiramis_(fate)",
            "ishtar_(fate)", "cu_chulainn_alter_(fate)", "amakusa_shirou_(fate)",
        ],
        "notes": (
            "200+ chars. Use charactername_(fate) format — NO 'character:' prefix. "
            "Guide: civitai.com/articles/5597"
        ),
    },
    "all_chars_amphoreus_hsr_illustrious.safetensors": {
        "civitai_version_id": 2250685,
        "civitai_filename": "All_inone_Amphoreus_V3.6.safetensors",
        "trigger_words": [
            "aglaea (honkai: star rail)",
            "anaxa (honkai: star rail)",
            "castorice (honkai: star rail)",
            "cyrene (honkai: star rail)",
            "cipher (honkai: star rail)",
            "cyrene (ripples of past reverie) (honkai: star rail)",
            "dan heng (permansor terrae) (honkai: star rail)",
            "evernight (honkai: star rail)",
            "little ica (honkai: star rail)",
            "mydei (honkai: star rail)",
            "phainon (honkai: star rail)",
            "tribbie (honkai: star rail)",
            "cerydra (honkai: star rail)",
            "hysilens (honkai: star rail)",
        ],
        "description": "All Characters Amphoreus HSR v3.6 (Illustrious, 14 chars). By Chenkin. 56MB.",
        "notes": "v3.6 — 14 chars. Use 'charactername (honkai: star rail)' as trigger. Guide: civitai.com/articles/19804",
    },
    "all_chars_hsr_2025_illustrious.safetensors": {
        "civitai_version_id": 2312748,
        "civitai_filename": "Star_Rail_251013.safetensors",
        "trigger_words": ["honkai: star rail"],
        "notes": "80+ chars (Illustrious). Recommend NoobAI-XL. Guide: civitai.com/articles/20764",
    },
    "lewd_elves_pony.safetensors": {
        "civitai_version_id": 1051022,
        "civitai_filename": "All_Characters_from_Youkoso_Sukebe_Elf_no_Mori_e_r1.safetensors",
        "notes": (
            "8 chars (Pony). Highly recommend 'uncensored' keyword. Also try 'pubic tattoo'. "
            "CLIP SKIP 1. Also has Illustrious XL version bundled on same page."
        ),
    },
}


def apply_updates_ruamel(registry_path: str) -> int:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 120
    yaml.best_sequence_indent = 4
    yaml.best_map_flow_style = False

    with open(registry_path, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    updated = 0
    for entry in data.get("character", []):
        name = entry.get("name", "")
        if name not in UPDATES:
            continue
        patch = UPDATES[name]
        for key, value in patch.items():
            entry[key] = value
        updated += 1

    with open(registry_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)

    return updated


def apply_updates_pyyaml(registry_path: str) -> int:
    import yaml

    class LiteralString(str):
        pass

    def literal_representer(dumper, data):
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    yaml.add_representer(LiteralString, literal_representer)
    yaml.add_representer(
        str,
        lambda dumper, data: dumper.represent_scalar(
            "tag:yaml.org,2002:str", data, style='"' if any(c in data for c in ':{}[]') else None
        ),
    )

    with open(registry_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    updated = 0
    for entry in data.get("character", []):
        name = entry.get("name", "")
        if name not in UPDATES:
            continue
        patch = UPDATES[name]
        for key, value in patch.items():
            entry[key] = value
        updated += 1

    with open(registry_path, "w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=120,
            indent=2,
        )

    return updated


if __name__ == "__main__":
    if not os.path.isfile(REGISTRY_PATH):
        print(f"ERROR: registry not found at {REGISTRY_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"Registry: {REGISTRY_PATH}")
    print(f"Loader:   {'ruamel.yaml' if USE_RUAMEL else 'PyYAML'}")

    if USE_RUAMEL:
        n = apply_updates_ruamel(REGISTRY_PATH)
    else:
        n = apply_updates_pyyaml(REGISTRY_PATH)

    print(f"Updated {n} / {len(UPDATES)} entries.")
    if n != len(UPDATES):
        print(f"WARNING: only {n} of {len(UPDATES)} names matched. Check entry names.")
