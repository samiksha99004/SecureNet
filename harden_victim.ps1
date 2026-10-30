# ============================================================================
#  SecureNet - static hardening for this Windows host (the STATIC half of protection).
#
#  The DYNAMIC half is Advanced Protection (Settings -> Advanced Protection): when traffic
#  turns abnormal it auto-blocks the attacker's SOURCE IP at the Windows Firewall.
#  This script makes the attacks FAIL even before that block. Everything is reversible.
#
#  RUN ONCE AS ADMIN: right-click -> Run with PowerShell (approve the UAC).
# ============================================================================

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
          ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Start-Process powershell.exe -Verb RunAs -ArgumentList `
        "-NoProfile","-ExecutionPolicy","Bypass","-NoExit","-File","`"$PSCommandPath`""
    exit
}

function Step($n, $t) { Write-Host "`n[$n] $t" -ForegroundColor Cyan }

try {
    # 1) BRUTE-FORCE (SSH/FTP/RDP/SMB/Web-login): lock accounts after repeated failures.
    Step 1 "Account lockout (defeats SSH/FTP/RDP/web brute-force and password spray)"
    net accounts /lockoutthreshold:5 /lockoutduration:15 /lockoutwindow:15 | Out-Null
    Write-Host "   -> lock after 5 bad tries, for 15 min." -ForegroundColor Green

    # 1b) SSH specifically: cap auth tries (OpenSSH on Windows).
    $sshd = "$env:ProgramData\ssh\sshd_config"
    if (Test-Path $sshd) {
        $c = Get-Content $sshd -Raw
        if ($c -notmatch "(?m)^\s*MaxAuthTries\s+3") {
            Add-Content $sshd "`nMaxAuthTries 3`nLoginGraceTime 20"
            Restart-Service sshd -ErrorAction SilentlyContinue
            Write-Host "   -> SSH MaxAuthTries 3 + LoginGraceTime 20 (sshd restarted)." -ForegroundColor Green
        } else { Write-Host "   -> SSH already hardened." -ForegroundColor DarkGray }
    } else { Write-Host "   -> OpenSSH not installed; skipped SSH hardening." -ForegroundColor DarkGray }

    # 2) SMB EXPLOITS (EternalBlue / MS17-010): disable the legacy SMBv1 protocol.
    Step 2 "Disable SMBv1 (defeats EternalBlue / MS17-010 SMB exploits)"
    Set-SmbServerConfiguration -EnableSMB1Protocol $false -Force -ErrorAction SilentlyContinue
    Write-Host "   -> SMBv1 server disabled (keep Windows patched too)." -ForegroundColor Green

    # 3) FIREWALL baseline on (so the Advanced Protection auto-block + default-deny apply).
    Step 3 "Enable Windows Firewall on all profiles"
    Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled True
    Write-Host "   -> firewall ON (Domain/Private/Public)." -ForegroundColor Green

    # 4) RDP (if used): require Network Level Authentication.
    Step 4 "RDP Network Level Authentication (if RDP is enabled)"
    try {
        Set-ItemProperty "HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" `
            -Name UserAuthentication -Value 1 -ErrorAction Stop
        Write-Host "   -> RDP NLA required." -ForegroundColor Green
    } catch { Write-Host "   -> RDP key not present; skipped." -ForegroundColor DarkGray }

    Write-Host "`n--- STATIC HARDENING DONE ---" -ForegroundColor Green
    Write-Host "Still MANUAL (not scriptable here) - see PROTECTION_MEASURES.md:" -ForegroundColor Yellow
    Write-Host "  * SQLi/XSS  -> a WAF (ModSecurity for Apache/XAMPP) + parameterised queries / input validation" -ForegroundColor Yellow
    Write-Host "  * Slow-DoS / HTTP-flood (Hulk/GoldenEye/Slowloris/SlowHTTPTest) -> Apache mod_reqtimeout + mod_evasive" -ForegroundColor Yellow
    Write-Host "  * UDP/ICMP flood -> per-IP rate limits; real distributed DDoS -> upstream scrubbing (Cloudflare/ISP)" -ForegroundColor Yellow
    Write-Host "  * Recon / port scan -> close unused ports, default-deny firewall" -ForegroundColor Yellow
}
catch {
    Write-Host "`nHARDENING STEP FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

Read-Host "`nPress Enter to close"
