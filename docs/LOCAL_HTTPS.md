# HTTPS on your own network (dev)

A phone's browser only allows the microphone on `https://` (or `localhost`), so the softphone can't
make calls from another device over `http://192.168.x.x:8080`. The dev stack therefore includes a
small Caddy (`deploy/Caddyfile.dev`) that serves everything over HTTPS on port **8443**:

| URL | What |
|---|---|
| `https://<LAN IP>:8443/` | parent app, `/phone/` softphone and `/api` |
| `https://<LAN IP>:8443/ws` | secure WebSocket to Asterisk (ARI is never forwarded) |
| `https://<LAN IP>:8443/ca.crt` | the certificate authority to trust on a phone |

## Setup

1. Put this machine's LAN address in `.env` (git-ignored) at the repo root, so the certificate is made for it:
   `TREELINE_LAN_IP=192.168.1.179`
   and the address a parent's phone should open (this is what the pairing QR code sends them to):
   `TREELINE_PUBLIC_ORIGIN=https://192.168.1.179:8443`
2. `./dev up` (starts Caddy; its authority is created in `data/caddy` on first start).
3. Windows with WSL: allow the port in an Administrator PowerShell:
   `New-NetFirewallRule -DisplayName "Treeline dev HTTPS" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8443 -Profile Any`
4. On the other device, open `https://<LAN IP>:8443/ca.crt`, accept the browser warning once to download it, and install it:
   Android: Settings → Security → Encryption & credentials → Install a certificate → **CA certificate**.
   iPhone: open the file, install the profile, then Settings → General → About → Certificate Trust Settings → enable it.
   Then open `https://<LAN IP>:8443/` again: no warning, and the softphone can use the microphone.

**Android can't connect at all?** Recent Android versions need a permission for a browser to reach devices on your
local network. Settings → Apps → Chrome → Permissions → allow **Nearby devices** or **Local network**. Without it the page
just fails to load (we saw "too many retries" on a Pixel) while other devices on the same Wi-Fi work. Chrome's
"Always use secure connections" setting can also upgrade plain `http://` to `https://`, which fails against port 8080.

If the address changes (a new DHCP lease), update `.env` and `docker compose up -d caddy`; the certificate is reissued.

## Test it

`TREELINE_TEST_BASE=https://localhost:8443 ./dev web phone_calls.py` runs the real browser calls through this proxy
(over `https` and `wss`). Certificate errors are ignored there because the authority is Caddy's own.

Never use this in production: `deploy/Caddyfile` gets a real certificate for a real domain.
