# Setup Scripts

Windows batch files for easy setup and launching of the LoRA Training Tool.

## Available Scripts

### `setup.bat`
**Purpose:** Initial environment setup

**What it does:**
- Creates Python virtual environment (`lora/`)
- Installs all required dependencies
- Validates Python installation
- Sets up directory structure

**When to use:** Run once before first use, or after moving the tool to a new location

**Usage:**
```bash
setup.bat
```

---

### `train.bat`
**Purpose:** Interactive training launcher

**What it does:**
- Activates virtual environment
- Displays available configurations
- Lets you select a config file
- Launches training with selected config

**When to use:** Every time you want to start training

**Usage:**
```bash
train.bat
```

---

### `quickstart.bat`
**Purpose:** Complete step-by-step wizard

**What it does:**
1. Checks environment setup
2. Validates dataset
3. Helps choose configuration
4. Launches training

**When to use:** First-time users or when you want guided setup

**Usage:**
```bash
quickstart.bat
```

---

### `preprocess.bat`
**Purpose:** Dataset preprocessing menu

**What it does:**
- **Validate:** Check images for corruption/invalid formats
- **Caption:** Auto-generate captions using BLIP
- **Split:** Divide dataset into train/validation sets

**When to use:** Before training, to prepare your dataset

**Usage:**
```bash
preprocess.bat
```

---

### `utilities.bat`
**Purpose:** All-in-one utilities menu

**What it does:**
- Access resume training
- Generate samples
- Analyze LoRAs
- Merge models
- Convert formats
- Run benchmarks

**When to use:** After training, for model management

**Usage:**
```bash
utilities.bat
```

---

### `batch_generate.bat`
**Purpose:** Batch sample generation

**What it does:**
- Detects trained models
- Generates samples from multiple prompts
- Creates comparison grids
- Batch processes multiple models

**When to use:** Testing multiple models or prompts

**Usage:**
```bash
batch_generate.bat
```

## Typical Workflow

```
1. setup.bat          → One-time setup
2. preprocess.bat     → Prepare dataset
3. train.bat          → Train model
   or quickstart.bat  → Guided training
4. utilities.bat      → Manage models
5. batch_generate.bat → Test results
```

## Troubleshooting

**Q: "Python not found" error**
- Install Python 3.8+ from python.org
- Add Python to PATH during installation
- Restart command prompt

**Q: "venv creation failed"**
- Check write permissions
- Ensure enough disk space (20GB+)
- Run as administrator if needed

**Q: Batch file closes immediately**
- Right-click → "Edit" to see error messages
- Or run from command prompt to see output

**Q: Dependencies installation fails**
- Check internet connection
- Try: `pip install --upgrade pip`
- Manually install: `pip install -r requirements.txt`

## Tips

- **Always run from project root** (`train_LoRA_tool/`)
- **Don't move .bat files** - they assume specific directory structure
- **Check logs** if training fails: `outputs/logs/`
- **Use quickstart.bat** for first-time setup
