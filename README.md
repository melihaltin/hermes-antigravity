# Hermes Antigravity

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![Hermes](https://img.shields.io/badge/Hermes%20Agent-Plugin-purple.svg)](https://hermes-agent.nousresearch.com)

**Hermes Antigravity** is a standalone model provider plugin for [Hermes Agent](https://github.com/nousresearch/hermes-agent). It connects Hermes directly to Google Cloud Code / Antigravity endpoints over HTTPS.

### Key Features
- **Zero Node.js or Pi Dependency**: No Node runtime, npm packages, daemon processes, CLI bridges, or proxy servers. Pure Python using Hermes's built-in client.
- **Direct & Fast**: Hermes streams directly to Google endpoints with Server-Sent Events (SSE).
- **Native Models**: Access to `gemini-3.8-flash`, `claude-sonnet-4-6`, and other Antigravity models.
- **Full Tool Calling & Prompt Caching**: Preserves function declarations, arguments, and native reasoning tokens.
- **Multiplatform**: Runs cleanly on Windows (PowerShell), macOS, and Linux.

---

## ⚡ Quick Start

### 1. One-Liner Installation

#### Windows (PowerShell)
Open PowerShell and run:
```powershell
irm https://raw.githubusercontent.com/melihaltin/hermes-antigravity/main/install.ps1 | iex
```

#### Linux & macOS (Bash)
Open your terminal and run:
```bash
curl -fsSL https://raw.githubusercontent.com/melihaltin/hermes-antigravity/main/install.sh | bash
```

---

### 2. Manual Installation

If you prefer doing it step-by-step:

1. Clone or download the files into your Hermes plugins directory:
   - **Windows:** `$env:USERPROFILE\.hermes\plugins\model-providers\antigravity`
   - **Linux / macOS:** `~/.hermes/plugins/model-providers/antigravity`

   ```bash
   git clone https://github.com/melihaltin/hermes-antigravity.git ~/.hermes/plugins/model-providers/antigravity
   ```

2. Log in with your Google account:
   ```bash
   python ~/.hermes/plugins/model-providers/antigravity/login.py
   ```
   *Your browser will open automatically. Complete Google sign-in and return to your terminal.*

3. Enable the plugin in Hermes:
   ```bash
   hermes plugins enable antigravity
   ```

---

## 🚀 Model Selection

Once installed and logged in, switch to your preferred model:

```bash
# Gemini 3.8 Flash (fast, recommended for general tasks)
hermes model antigravity/gemini-3.8-flash

# Claude Sonnet 4.6 (reasoning & complex coding)
hermes model antigravity/claude-sonnet-4-6
```

You can also use it in one-shot prompts or custom invocations:
```bash
hermes -m antigravity/gemini-3.8-flash -z "Explain quantum computing in one sentence."
```

---

## 🔒 Security & Privacy

- **No Third-Party Intermediaries**: Your requests go directly between your machine and Google's endpoints (`daily-cloudcode-pa.googleapis.com`).
- **OAuth Credentials**: Kept strictly local under `~/.hermes/antigravity-auth.json` (with standard restricted file permissions).
- **Public Desktop Client**: Uses Google's standard public Antigravity client configuration with PKCE verification. No secret application tokens are needed.

---

## 🛠️ Troubleshooting

### Windows: `python` not found
On Windows, Python may not be directly in your system `PATH`. You can run the login script using Hermes's built-in Python:
```powershell
$py = (Get-ChildItem -Path "$env:LOCALAPPDATA\hermes", "$env:USERPROFILE\.hermes" -Filter "python.exe" -Recurse | Select-Object -First 1).FullName
& $py "$env:USERPROFILE\.hermes\plugins\model-providers\antigravity\login.py"
```

### Port 51121 is already in use
The login script uses port `51121` for the temporary OAuth redirect. Ensure no other application or process is using this port during login.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
Authored by [Melih Altın](https://github.com/melihaltin).
