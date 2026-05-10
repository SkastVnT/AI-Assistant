#!/usr/bin/env python3
"""
Toggle chatbot feature flags interactively or via CLI.

Usage:
    python scripts/toggle_features.py               # interactive menu
    python scripts/toggle_features.py --list        # show current state
    python scripts/toggle_features.py quota off     # disable quota
    python scripts/toggle_features.py video on      # enable video (no payment lock)
    python scripts/toggle_features.py registration off
    python scripts/toggle_features.py payment off
    python scripts/toggle_features.py all off       # disable ALL restrictions
    python scripts/toggle_features.py all on        # enable ALL restrictions
"""
import sys
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "features.json"


def load():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved → {CONFIG_PATH}")


def show(data):
    print("\n┌─────────────────────────────────────────────────┐")
    print("│          Chatbot Feature Flags                  │")
    print("├─────────────────────────────────────────────────┤")
    flags = {
        "require_login":       data.get("auth", {}).get("require_login", True),
        "allow_registration":  data.get("auth", {}).get("allow_registration", True),
        "quota (image limit)": data.get("quota", {}).get("enabled", True),
        "  image limit":       data.get("quota", {}).get("image_gen_limit", 5),
        "video unlock":        data.get("video", {}).get("enabled", True),
        "  require_payment":   data.get("video", {}).get("require_payment_unlock", True),
        "payment / QR":        data.get("payment", {}).get("enabled", True),
    }
    for k, v in flags.items():
        if isinstance(v, bool):
            state = "\033[92m ON \033[0m" if v else "\033[91m OFF\033[0m"
            print(f"│  {k:<30} [{state}] │")
        else:
            print(f"│  {k:<30}  {str(v):<6} │")
    print("└─────────────────────────────────────────────────┘\n")


def set_feature(data, feature, state: bool):
    feature = feature.lower().strip()
    changed = []
    if feature in ("quota", "image", "image_quota"):
        data.setdefault("quota", {})["enabled"] = state
        changed.append(f"quota.enabled = {state}")
    elif feature in ("video",):
        data.setdefault("video", {})["enabled"] = state
        data.setdefault("video", {})["require_payment_unlock"] = state
        changed.append(f"video = {state}")
    elif feature in ("payment", "qr"):
        data.setdefault("payment", {})["enabled"] = state
        data.setdefault("payment", {})["qr_generation"] = state
        changed.append(f"payment = {state}")
    elif feature in ("login", "require_login"):
        data.setdefault("auth", {})["require_login"] = state
        changed.append(f"auth.require_login = {state}")
    elif feature in ("registration", "register"):
        data.setdefault("auth", {})["allow_registration"] = state
        changed.append(f"auth.allow_registration = {state}")
    elif feature == "all":
        data.setdefault("quota", {})["enabled"] = state
        data.setdefault("video", {})["require_payment_unlock"] = state
        data.setdefault("payment", {})["enabled"] = state
        data.setdefault("auth", {})["require_login"] = state
        changed.append(f"ALL restrictions = {state}")
    else:
        print(f"  Unknown feature: {feature}")
        print("  Valid: quota | video | payment | login | registration | all")
        return

    for c in changed:
        print(f"  ✓ {c}")


def interactive(data):
    print("\nChatbot Feature Toggle")
    print("=" * 40)
    show(data)
    print("Chọn tính năng:")
    menu = [
        ("1", "quota",        "Image generation limit (5 ảnh/user)"),
        ("2", "video",        "Video generation + payment lock"),
        ("3", "payment",      "Payment / QR generation"),
        ("4", "login",        "Require login"),
        ("5", "registration", "Allow registration"),
        ("6", "all",          "ALL restrictions"),
    ]
    for num, _, desc in menu:
        print(f"  [{num}] {desc}")
    print("  [7] Xem trạng thái")
    print("  [0] Thoát")

    choice = input("\n> ").strip()
    if choice == "0":
        return
    if choice == "7":
        show(data)
        return

    mapping = {m[0]: m[1] for m in menu}
    if choice not in mapping:
        print("  Lựa chọn không hợp lệ")
        return

    feature = mapping[choice]
    val = input(f"  Bật/Tắt {feature}? [on/off]: ").strip().lower()
    if val not in ("on", "off", "1", "0", "true", "false"):
        print("  Nhập on hoặc off")
        return

    state = val in ("on", "1", "true")
    set_feature(data, feature, state)
    save(data)
    show(data)
    print("  Restart chatbot service để áp dụng.\n")


def main():
    if not CONFIG_PATH.exists():
        print(f"ERROR: Not found: {CONFIG_PATH}")
        sys.exit(1)

    data = load()

    args = sys.argv[1:]

    if not args or args == ["--interactive"]:
        interactive(data)
        return

    if args[0] == "--list":
        show(data)
        return

    if len(args) >= 2:
        feature = args[0]
        val = args[1].lower()
        state = val in ("on", "1", "true", "enable", "enabled")
        set_feature(data, feature, state)
        save(data)
        show(data)
        return

    print(__doc__)


if __name__ == "__main__":
    main()
