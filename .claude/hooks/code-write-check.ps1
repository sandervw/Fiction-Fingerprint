$raw = [Console]::In.ReadToEnd()
try {
    $payload = $raw | ConvertFrom-Json
} catch {
    exit 0
}

$path = $payload.tool_response.filePath
if (-not $path) { $path = $payload.tool_input.file_path }
if (-not $path) { exit 0 }
if ($path -notmatch '\.(py|sql|js|ts|css|tf|bicep|svelte|ya?ml|ipynb|toml)$') { exit 0 }

$reason = @'
**STOP.** In the code you just created/edited, did you add or see any comments greater than 12 words, or several lines of comments stacked?

**Cut them.** Every function, or code/block, should have no more than 1 comment, and that comment must be no more than 12 words long.
'@

@{ decision = 'block'; reason = $reason } | ConvertTo-Json -Compress
