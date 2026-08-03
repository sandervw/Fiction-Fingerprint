$raw = [Console]::In.ReadToEnd()
try {
    $payload = $raw | ConvertFrom-Json
} catch {
    exit 0
}

$path = $payload.tool_response.filePath
if (-not $path) { $path = $payload.tool_input.file_path }
if (-not $path) { exit 0 }
if ($path -notmatch '\.md$') { exit 0 }

$reason = @'
**STOP.** In the documentation you just created/edited, did you see or write any instances of the following?
- 'X, not Y'
- Justification
- Exhaustive examples or metaphors
- Other consideration
- Bonus effects
- Tradeoffs/alternatives
- 'Did X because Y'
- Stating the way a thing worked in the past
- 'Key findings'
- Edit date logging

**Cut them.** Cut whole clauses and entire sections. Cut both your own and pre-existing examples. Documentation should record exactly the way a project runs/should-run, and nothing else.
'@

@{ decision = 'block'; reason = $reason } | ConvertTo-Json -Compress
