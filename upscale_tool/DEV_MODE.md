# 🔥 Development Mode - Hot Reload

## Quick Start

### Option 1: Batch File (Windows)
```bash
start_flask.bat
```

### Option 2: Command Line
```bash
python -m upscale_tool.dev_server
```

### Option 3: Regular Mode (No Hot Reload)
```bash
python -m upscale_tool.web_ui
```

## How It Works

1. **Start dev server**: `start_flask.bat` hoặc `python -m upscale_tool.dev_server`
2. **Edit files**: Sửa `web_ui.py` hoặc bất kỳ file `.py` nào
3. **Save**: Nhấn `Ctrl + S`
4. **Auto-reload**: Server tự động restart
5. **Refresh browser**: Nhấn `Ctrl + Shift + R` trên trình duyệt

## Features

✅ **Auto-reload on file save**
- Watchdog theo dõi thay đổi file
- Tự động restart server khi có thay đổi
- Debounce 2s để tránh restart liên tục

✅ **Hot Reload UI**
- Sửa CSS, layout, components
- Chỉ cần Ctrl+Shift+R để refresh UI
- Không cần restart thủ công

✅ **Development Friendly**
- Terminal hiển thị log rõ ràng
- Báo file nào thay đổi
- Dễ debug

## Example Workflow

```bash
# 1. Start dev server
start_flask.bat

# 2. Open http://127.0.0.1:7861

# 3. Edit web_ui.py
#    - Change CSS
#    - Update layout
#    - Add features

# 4. Save (Ctrl+S)
#    → Server auto-restarts

# 5. Browser: Ctrl+Shift+R
#    → See changes!
```

## Dependencies

- `watchdog>=2.0.0` - File watching
- `gradio>=3.0.0` - Web UI
- `flask>=2.0.0` - Optional (for future features)

## Production Mode

For production, use regular mode:
```bash
python -m upscale_tool.web_ui
```

No file watching overhead, better performance.
