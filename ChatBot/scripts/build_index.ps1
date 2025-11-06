# PowerShell script to build integrated index.html without inline scripts
$content = Get-Content "templates/index.html" -Encoding UTF8 -Raw

# Use regex to extract only the HTML structure and modals, removing all <script> blocks
# Pattern: Keep everything from start to first <script>, then skip all scripts, keep modals, skip final scripts

# Step 1: Extract HTML header (lines 1-156)
$lines = Get-Content "templates/index.html" -Encoding UTF8
$header = $lines[0..155]

# Step 2: Extract modal HTML only (between </script> tags, excluding script content)
# Find the modal section that doesn't have inline scripts
$modalsStart = 1788 - 1  # Convert to 0-indexed
$modalsEnd = 3458 - 1    # Just before the second script block

# Extract and filter modals - skip lines with <script> tags
$modals = @()
$inScript = $false
for ($i = $modalsStart; $i -le $modalsEnd; $i++) {
    $line = $lines[$i]
    
    # Check if entering script block
    if ($line -match '^\s*<script') {
        $inScript = $true
        continue
    }
    
    # Check if exiting script block
    if ($line -match '^\s*</script>') {
        $inScript = $false
        continue
    }
    
    # Only add lines that are not in script blocks
    if (-not $inScript) {
        $modals += $line
    }
}

# Step 3: Extract remaining modals after line 3458 (Image Preview + History modals)
$remainingModalsStart = 3459  # 0-indexed: 3458
$remainingModalsEnd = 3490    # 0-indexed: 3489

$remainingModals = @()
$inScript = $false
for ($i = $remainingModalsStart; $i -le $remainingModalsEnd; $i++) {
    $line = $lines[$i]
    
    if ($line -match '^\s*<script') {
        $inScript = $true
        continue
    }
    
    if ($line -match '^\s*</script>') {
        $inScript = $false
        continue
    }
    
    if (-not $inScript) {
        $remainingModals += $line
    }
}

# Step 4: Create footer with module import
$footer = @(
    '',
    '    <!-- Load JavaScript modules -->',
    '    <script type="module" src="{{ url_for(''static'', filename=''js/main.js'') }}"></script>',
    '</body>',
    '</html>'
)

# Combine all parts
$newContent = $header + $modals + $remainingModals + $footer

# Save
$newContent | Set-Content "templates/index_modular.html" -Encoding UTF8

Write-Host "Created templates/index_modular.html with $($newContent.Count) lines"
Write-Host "Header: $($header.Count) lines"
Write-Host "Modals: $($modals.Count) lines"
Write-Host "Remaining Modals: $($remainingModals.Count) lines"
Write-Host "Footer: $($footer.Count) lines"
