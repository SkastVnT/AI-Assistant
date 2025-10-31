# Session Manager Quick Guide

## 🎯 Quick Access

```bash
# Run the manager
session_manager.bat
```

## 📋 Features

### 1. List All Sessions
Shows all transcription sessions with file counts.

### 2. Show Latest Session
Displays detailed info about the most recent session:
- Session timestamp
- Creation time
- List of files with sizes

### 3. Read Latest Transcript
Prints the latest final transcript to console.

### 4. Clean Old Sessions
Keeps only the 10 most recent sessions, deletes older ones.

### 5. Archive Sessions
Archives sessions older than N days to a ZIP file.
- Default: 7 days
- Optionally delete after archiving

## 💡 Usage Examples

### Find Latest Transcript Manually
```powershell
$latest = Get-ChildItem app\data\results\sessions\ | Sort-Object Name -Descending | Select-Object -First 1
Get-Content "$($latest.FullName)\final_transcript_*.txt"
```

### Compare Two Sessions
```powershell
$sessions = Get-ChildItem app\data\results\sessions\ | Sort-Object Name -Descending | Select-Object -First 2
Get-Content "$($sessions[0].FullName)\final_transcript_*.txt"  # Latest
Get-Content "$($sessions[1].FullName)\final_transcript_*.txt"  # Previous
```

### Export Latest to Desktop
```powershell
$latest = Get-ChildItem app\data\results\sessions\ | Sort-Object Name -Descending | Select-Object -First 1
$transcript = Get-ChildItem "$($latest.FullName)\final_transcript_*.txt"
Copy-Item $transcript.FullName "$env:USERPROFILE\Desktop\transcript_$(Get-Date -Format 'yyyyMMdd').txt"
```

## 🗂️ Session Naming

Format: `session_YYYYMMDD_HHMMSS`

Example: `session_20251023_174157`
- Date: 2025-10-23
- Time: 17:41:57

## 📄 Files in Each Session

| Filename Pattern | Description |
|------------------|-------------|
| `whisper_*.txt` | Raw Whisper large-v3 transcript |
| `phowhisper_*.txt` | Raw PhoWhisper-large transcript |
| `final_transcript_*.txt` | ⭐ **Main output** - Qwen-fused with 3-role separation |
| `processing_log_*.txt` | Processing statistics and timings |

## 🧹 Maintenance

### Weekly Cleanup
```powershell
# Keep last 20 sessions
Get-ChildItem app\data\results\sessions\ | Sort-Object Name -Descending | Select-Object -Skip 20 | Remove-Item -Recurse -Force
```

### Monthly Archive
```powershell
# Archive sessions older than 30 days
$threshold = (Get-Date).AddDays(-30)
Get-ChildItem app\data\results\sessions\ | Where-Object { $_.CreationTime -lt $threshold } | 
    Compress-Archive -DestinationPath "archive_$(Get-Date -Format 'yyyyMM').zip"
```

## 🔍 Search Sessions

### Find Session by Date
```powershell
Get-ChildItem app\data\results\sessions\ | Where-Object { $_.Name -like "*20251023*" }
```

### Find Sessions with Errors
```powershell
Get-ChildItem app\data\results\sessions\ -Recurse -Filter "processing_log_*.txt" | 
    ForEach-Object { 
        if ((Get-Content $_.FullName) -match "ERROR") { 
            Write-Host $_.Directory.Name -ForegroundColor Red 
        } 
    }
```

### Get Total Storage Used
```powershell
$size = (Get-ChildItem app\data\results\sessions\ -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "$([math]::Round($size, 2)) MB total"
```

## ⚠️ Important Notes

1. **Don't manually rename sessions** - breaks chronological sorting
2. **Archive before deleting** - you can't undo deletion
3. **Final transcript is the main output** - other files are for debugging
4. **Sessions are gitignored** - safe to accumulate locally

## 🆘 Troubleshooting

### Session not showing in manager?
Check folder naming: must be `session_YYYYMMDD_HHMMSS` format.

### Can't find transcript?
Look for `final_transcript_*.txt` or `dual_fused_*.txt` in session folder.

### Too many sessions slowing down?
Run cleanup (option 4) or archive old ones (option 5).
