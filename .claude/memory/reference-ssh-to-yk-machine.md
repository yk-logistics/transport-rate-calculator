---
name: reference-ssh-to-yk-machine
description: "SSH from โอ's main machine (Home/.178) into the second YK machine (YK/.197) — passwordless key login already set up"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 10bd7af4-3155-4a80-bedc-a6b93371b983
---

โอ set up SSH so Claude Code on the main machine can run commands on a second Windows machine.

- **Client (this machine):** hostname `Home`, LAN IP `192.168.1.178`. SSH key at `C:\Users\guole\.ssh\id_ed25519` (comment `home-to-yk`).
- **Server (target):** hostname `YK`, user `yklog`, LAN IP `192.168.1.197`. Win11 Pro. `sshd` Running + Automatic, firewall rule `OpenSSH-Server-In-TCP` Profile=Any.
- **Login:** passwordless via key. `yklog` is an admin, so the pubkey lives in `C:\ProgramData\ssh\administrators_authorized_keys` (NOT the user's `.ssh\authorized_keys`) with icacls restricted to Administrators+SYSTEM.
- **Tailscale (DONE — works off-LAN):** both machines on Tailscale, account `pongsakan@` (Microsoft login). Tailscale IPs: `home` = `100.71.13.122`, `yk` = `100.97.150.114`. **Prefer `ssh yklog@100.97.150.114`** — works on any network, not just same LAN. The `.197` LAN IP still works when on the same network.
- **Run a command:** `ssh yklog@100.97.150.114 "<cmd>"` (or `.197` on LAN). Remote default shell is now **PowerShell 5.1** (set `HKLM:\SOFTWARE\OpenSSH\DefaultShell` → `powershell.exe`; the key didn't exist and had to be created first). No pwsh 7 on YK.
- **Quoting gotcha:** the LOCAL PowerShell strips quotes / expands `$vars` before they cross SSH, so PS commands with `$` or quotes get mangled. **Most reliable pattern: Base64 EncodedCommand** — write the script in a `@'...'@` here-string, `[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($s))`, then `ssh ... "powershell -NoProfile -EncodedCommand $enc"`. (Harmless CLIXML progress noise comes back with it.) Short `$`-free commands can be sent inline.

**Why:** โอ wants to sit at the main machine and drive the YK machine's terminal, from anywhere.

**How to apply:** Use the Tailscale IP `100.97.150.114` by default. Tailscale does NOT conflict with the existing Cloudflare tunnel (`line.yklogistics.com`) — different layers, DNS untouched. Don't expose port 22 to the internet via router port-forward. Tailscale login may prompt for a security key (USB); cancel and use "sign-in options" → password/Authenticator instead.
