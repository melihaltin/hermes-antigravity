"""Standalone Google OAuth login for Antigravity.
Zero external dependencies (uses standard library http.server, urllib, webbrowser).
"""
import base64
import hashlib
import http.server
import json
import os
from pathlib import Path
import secrets
import sys
import time
import urllib.parse
import urllib.request
import webbrowser

CLIENT_ID = os.environ.get(
    "ANTIGRAVITY_CLIENT_ID",
    "1071006060591-tmhssin2h21lcre235vtolojh4g403ec.apps.googleusercontent.com"
)
CLIENT_SECRET = os.environ.get(
    "ANTIGRAVITY_CLIENT_SECRET",
    "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f"
)
REDIRECT_URI = "http://localhost:51121/oauth-callback"
SCOPES = [
    "https://www.googleapis.com/auth/aicode",
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/cclog",
    "https://www.googleapis.com/auth/experimentsandconfigs",
]


def main():
    print("=" * 60)
    print(" Hermes Antigravity — Google OAuth Girişi")
    print("=" * 60)

    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    state = secrets.token_urlsafe(32)

    auth_params = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    })
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{auth_params}"

    auth_code = None

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal auth_code
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/oauth-callback":
                qs = urllib.parse.parse_qs(parsed.query)
                if qs.get("state", [None])[0] == state and "code" in qs:
                    auth_code = qs["code"][0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    html = """
                    <html>
                    <body style="font-family: sans-serif; text-align: center; padding-top: 50px; background-color: #f4f6f8;">
                        <h1 style="color: #2e7d32;">Giriş Başarılı!</h1>
                        <p style="font-size: 18px; color: #37474f;">Hermes Antigravity yetkilendirmesi tamamlandı.</p>
                        <p style="color: #78909c;">Bu pencereyi kapatıp terminalinize geri dönebilirsiniz.</p>
                    </body>
                    </html>
                    """
                    self.wfile.write(html.encode("utf-8"))
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Giris basarisiz veya hatali dogrulama.")

        def log_message(self, *args):
            pass

    try:
        server = http.server.HTTPServer(("127.0.0.1", 51121), CallbackHandler)
    except OSError as e:
        print(f"\n[HATA] 51121 portu kullanılamıyor: {e}", file=sys.stderr)
        print("Lütfen bu portu kullanan başka bir uygulama varsa kapatıp tekrar deneyin.\n")
        sys.exit(1)

    print("\nTarayıcınız açılıyor, lütfen Google hesabınızla giriş yapın...")
    print(f"Eğer otomatik açılmazsa şu adresi tarayıcınıza yapıştırın:\n\n{auth_url}\n")
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    while auth_code is None:
        server.handle_request()
    server.server_close()

    print("Yetki kodu başarıyla alındı, token talep ediliyor...")
    token_payload = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code_verifier": verifier,
    }).encode("utf-8")

    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=token_payload, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            tokens = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"\n[HATA] Token alınamadı: {e}", file=sys.stderr)
        sys.exit(1)

    # Get user email
    user_email = None
    try:
        email_req = urllib.request.Request(
            "https://www.googleapis.com/oauth2/v1/userinfo?alt=json",
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        with urllib.request.urlopen(email_req) as resp:
            uinfo = json.loads(resp.read().decode("utf-8"))
            user_email = uinfo.get("email")
    except Exception:
        pass

    print(f"Giriş yapan kullanıcı: {user_email or 'Bilinmiyor'}")
    print("CloudCode projesi belirleniyor...")

    proj_req = urllib.request.Request(
        "https://daily-cloudcode-pa.googleapis.com/v1internal:loadCodeAssist",
        data=json.dumps({"metadata": {"ideType": "ANTIGRAVITY"}}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {tokens['access_token']}",
            "Content-Type": "application/json",
            "User-Agent": "antigravity/cli/1.4.0 (aidev_client; os_type=linux; arch=amd64; cl=982146307; auth_method=consumer)",
        },
        method="POST"
    )

    project_id = None
    try:
        with urllib.request.urlopen(proj_req) as resp:
            pdata = json.loads(resp.read().decode("utf-8"))
            project_id = pdata.get("cloudaicompanionProject", {}).get("id") or pdata.get("projectId") or pdata.get("project")
    except Exception:
        pass

    if not project_id:
        import uuid
        project_id = str(uuid.uuid4())

    entry = {
        "type": "oauth",
        "access": tokens["access_token"],
        "refresh": tokens["refresh_token"],
        "expires": int(time.time() * 1000 + tokens.get("expires_in", 3600) * 1000 - 300000),
        "projectId": project_id,
        "email": user_email,
    }

    # 1. Primary destination: ~/.hermes/antigravity-auth.json
    hermes_dir = Path.home() / ".hermes"
    hermes_dir.mkdir(parents=True, exist_ok=True)
    hermes_auth = hermes_dir / "antigravity-auth.json"
    hermes_auth.write_text(json.dumps(entry, indent=2), encoding="utf-8")

    # 2. Compatibility destination: ~/.pi/agent/auth.json (if directory exists or can be written)
    try:
        pi_dir = Path.home() / ".pi" / "agent"
        pi_dir.mkdir(parents=True, exist_ok=True)
        pi_file = pi_dir / "auth.json"
        existing = {}
        if pi_file.exists():
            try:
                existing = json.loads(pi_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        existing["antigravity"] = entry
        pi_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    except Exception:
        pass

    print("\n" + "=" * 60)
    print(" [✓] Başarıyla giriş yapıldı ve kimlik bilgileri kaydedildi!")
    print(f" Hedef dosya: {hermes_auth}")
    print("=" * 60)
    print("\nModeli kullanmak için:")
    print("  hermes model antigravity/gemini-3.8-flash")
    print("  veya")
    print("  hermes model antigravity/claude-sonnet-4-6\n")


if __name__ == "__main__":
    main()
