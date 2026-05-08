# Cursor sessionStart hook: inject changelog digest once per day.
# Disable by creating an empty file: .cursor/disable-cursor-digest

try {
    $ErrorActionPreference = "Stop"

    $workspaceRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    $cursorDir = Join-Path $workspaceRoot ".cursor"
    $cacheDir = Join-Path $cursorDir ".cache"
    $cacheFile = Join-Path $cacheDir "cursor-digest.json"
    $logFile = Join-Path $cacheDir "cursor-digest.log"
    $killSwitch = Join-Path $cursorDir "disable-cursor-digest"
    $today = (Get-Date).ToString("yyyy-MM-dd")

    function Emit-HookOutput {
        param([string]$AdditionalContext = "")
        $payload = @{}
        if (-not [string]::IsNullOrWhiteSpace($AdditionalContext)) {
            $payload.additional_context = $AdditionalContext
        }
        [Console]::Out.WriteLine(($payload | ConvertTo-Json -Compress))
    }

    function Write-DigestLog {
        param([string]$Action)
        try {
            if (-not (Test-Path $cacheDir)) { New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null }
            $line = "{0}`t{1}" -f ((Get-Date).ToString("s")), $Action
            $lines = @()
            if (Test-Path $logFile) {
                try { $lines = Get-Content -Path $logFile -ErrorAction Stop } catch { $lines = @() }
            }
            $lines += $line
            if ($lines.Count -gt 50) { $lines = $lines[-50..-1] }
            Set-Content -Path $logFile -Value ($lines -join [Environment]::NewLine) -Encoding UTF8
        } catch {}
    }

    function Read-Cache {
        if (-not (Test-Path $cacheFile)) { return @{} }
        try {
            $raw = Get-Content -Path $cacheFile -Raw -ErrorAction Stop
            if ([string]::IsNullOrWhiteSpace($raw)) { return @{} }
            $obj = $raw | ConvertFrom-Json -ErrorAction Stop
            return @{
                last_check_date    = [string]$obj.last_check_date
                last_seen_version  = [string]$obj.last_seen_version
                last_digest_text   = [string]$obj.last_digest_text
                last_injected_date = [string]$obj.last_injected_date
            }
        } catch {
            return @{}
        }
    }

    function Save-Cache {
        param([hashtable]$Cache)
        try {
            if (-not (Test-Path $cacheDir)) { New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null }
            $payload = @{
                last_check_date    = [string]$Cache.last_check_date
                last_seen_version  = [string]$Cache.last_seen_version
                last_digest_text   = [string]$Cache.last_digest_text
                last_injected_date = [string]$Cache.last_injected_date
            }
            Set-Content -Path $cacheFile -Value ($payload | ConvertTo-Json -Compress) -Encoding UTF8
        } catch {}
    }

    function To-Version {
        param([string]$V)
        try {
            if ([string]::IsNullOrWhiteSpace($V)) { return [version]"0.0" }
            return [version]$V
        } catch {
            return [version]"0.0"
        }
    }

    if (Test-Path $killSwitch) {
        Write-DigestLog "skipped-killswitch"
        Emit-HookOutput
        exit 0
    }

    # Read stdin payload (best effort only).
    try {
        $stdinRaw = [Console]::In.ReadToEnd()
        if (-not [string]::IsNullOrWhiteSpace($stdinRaw)) { $null = $stdinRaw | ConvertFrom-Json -ErrorAction Stop }
    } catch {}

    $cache = Read-Cache
    # Retry on later session starts if no successful inject happened yet.
    if ($cache.last_injected_date -eq $today) {
        Write-DigestLog "skipped-cache"
        Emit-HookOutput
        exit 0
    }

    try {
        $resp = Invoke-WebRequest -Uri "https://cursor.com/changelog" -UseBasicParsing -TimeoutSec 6 -ErrorAction Stop
        $html = [string]$resp.Content

        $matches = [regex]::Matches($html, "Cursor\s+(\d+\.\d+)")
        if ($matches.Count -eq 0) {
            Write-DigestLog "network-failed"
            Emit-HookOutput
            exit 0
        }

        $versions = @()
        foreach ($m in $matches) { $versions += $m.Groups[1].Value }
        $latestVersion = ($versions | Sort-Object { To-Version $_ } -Descending | Select-Object -First 1)

        $latestDate = "date not found"
        $dateMatch = [regex]::Match($html, "([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})")
        if ($dateMatch.Success) { $latestDate = $dateMatch.Groups[1].Value }

        $featureBullets = @()
        $liMatches = [regex]::Matches($html, "<li[^>]*>(.*?)</li>", [System.Text.RegularExpressions.RegexOptions]::Singleline)
        foreach ($li in $liMatches) {
            $item = [regex]::Replace($li.Groups[1].Value, "<[^>]+>", " ")
            $item = ($item -replace "&nbsp;", " " -replace "&amp;", "&" -replace "&lt;", "<" -replace "&gt;", ">" -replace "\s+", " ").Trim()
            if ($item.Length -ge 8) { $featureBullets += $item }
            if ($featureBullets.Count -ge 5) { break }
        }
        if ($featureBullets.Count -eq 0) {
            $featureBullets = @(
                "Cursor changelog has recent updates",
                "Review changelog before high-impact workflow changes"
            )
        }

        $featureLines = ($featureBullets | ForEach-Object { "- $_" }) -join "`n"
        $digestText = @"
[CURSOR DIGEST - inject at chat start]

Latest Cursor update detected: $latestVersion ($latestDate)

Features detected:
$featureLines

INSTRUCTION FOR AGENT: Before answering the first user message in this chat, provide a detailed update summary in Thai and explain how each feature applies to Project YK (FastAPI + SQLite + HTMX + Driver PWA) and to the user's workflow (vibe-coding, payroll, billing, dispatch). Use a table format: feature | how it helps Project YK. Then answer the user question.

To disable: create empty file .cursor/disable-cursor-digest
"@

        $cache.last_check_date = $today
        $cache.last_seen_version = $latestVersion
        $cache.last_digest_text = $digestText
        $cache.last_injected_date = $today
        Save-Cache -Cache $cache

        Emit-HookOutput -AdditionalContext $digestText
        Write-DigestLog "fetched"
        exit 0
    } catch {
        Write-DigestLog "network-failed"
        # Do not lock out retries for the whole day when network is flaky.
        Emit-HookOutput
        exit 0
    }
} catch {
    try { Emit-HookOutput } catch {}
    exit 0
}

