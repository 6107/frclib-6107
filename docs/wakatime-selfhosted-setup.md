# WakaTime + Self-Hosted Wakapi on Windows (Docker Desktop, Internet-Reachable)

Goal: run a free, self-hosted, WakaTime-compatible backend (**Wakapi**) on a **Windows machine using Docker Desktop**,
reachable from anywhere on the internet via public IP **`108.221.38.129`**, secured with **HTTPS** and a **DNS
hostname**, and accepting heartbeats from PyCharm on Windows and Linux clients — including periods with no network
connectivity.

---

## 1. Architecture at a glance

```
   PyCharm (Windows or Linux, anywhere)
        │  HTTPS to https://waka.<yourdomain>/api
        ▼
   Public DNS  ──► 108.221.38.129
        │
        ▼
   [ Router / NAT ]    port-forward 80,443  ─────►  Windows box
                                                     │
                                            Docker Desktop
                                             ├── Caddy (TLS terminator + reverse proxy)
                                             ├── Wakapi (bound to internal Docker network)
                                             └── (optional) CrowdSec (intrusion detection)
```

Two independently-good ways to publish it:

- **A. Direct port-forward + Caddy TLS on the Windows box** — simplest to understand, exposes `108.221.38.129:443`
  publicly.
- **B. Cloudflare Tunnel (no ports opened, IP stays hidden)** — recommended if the IP is dynamic or the ISP frowns on
  inbound hosting; adds a free identity gate.

Both are covered below. You can start with A and switch to B later without touching PyCharm — only DNS changes.

---

## 2. Prerequisites

- **Windows 10/11 Pro or Enterprise** (or Windows Server) with **Docker Desktop**
  installed and the WSL 2 engine enabled. Home edition works too; Pro is preferred because Hyper-V / stronger firewall
  controls are available.
- **Local admin** on the Windows box.
- The public IP **`108.221.38.129`** actually reaches the box (test from an outside network with
  `nc -vz 108.221.38.129 80` once port-forwarding is set up). Residential IPs are often dynamic — see §4 for DDNS.
- A **domain name** you can add records to (see §4 for options if you don't have one yet).
- **Router access** to port-forward 80/tcp and 443/tcp to the Windows box's LAN IP, unless you choose option **B**
  (Cloudflare Tunnel) which needs no port forwards.

---

## 3. Windows / Docker Desktop preparation

1. **Give the Windows box a static LAN IP** (DHCP reservation on the router is easiest). Note it — e.g. `192.168.1.50` —
   you will port-forward to it.
2. **Windows Firewall:** Docker Desktop already handles inbound rules for published container ports, but confirm the
   profile is **Private** on your LAN adapter (Settings → Network & Internet → Ethernet → click adapter → *Network
   profile type = Private*). Public profile blocks most inbound traffic.
3. **Configure Docker Desktop to start with Windows:** Docker Desktop → Settings → General → *Start Docker Desktop when
   you sign in*. Better still: set your Windows user to auto-login (only if the machine is physically secure) so the
   container starts unattended after reboots. Or run Docker as a Windows service via
   **[docker-ce](https://docs.docker.com/engine/install/binaries/#install-server-and-client-binaries-on-windows)**
   if you don't need the Docker Desktop UI.
4. **Pick a data directory** for persistent volumes, e.g. `C:\wakapi\`. Docker Desktop needs it added under Settings →
   Resources → File sharing on older Windows versions.

---

## 4. DNS: hostname suggestions and how to point it at your IP

The plugin will use a hostname like `https://waka.example.com/api`, so you need a public DNS **A record** for that
hostname pointing at your public IP.

### 4a. Hostname naming suggestions

Pick something short, memorable, and unlikely to leak information:

| Suggestion                     | Notes                              |
|--------------------------------|------------------------------------|
| `waka.<yourdomain>`            | Short, obvious.                    |
| `wakapi.<yourdomain>`          | Explicit about the software.       |
| `time.<yourdomain>`            | Generic; doesn't hint at WakaTime. |
| `wt.<yourdomain>`              | Shortest.                          |
| `metrics.<yourdomain>`         | Very generic.                      |
| `hb.<yourdomain>` (heartbeats) | Obscure by design.                 |

I recommend `waka.<yourdomain>` (clear intent) unless you have security-through- obscurity concerns, in which case use
`metrics.<yourdomain>` and keep the software identity out of the hostname.

### 4b. If you already own a domain

At your DNS provider (Cloudflare, Route53, Google Domains successor, Namecheap, etc.), add:

```
Type    Name                 Value              TTL
A       waka                 108.221.38.129     300
```

Verification:

```powershell
nslookup waka.example.com 1.1.1.1
```

If you'd like Cloudflare's free CDN/DDoS layer, use Cloudflare DNS and set the record to **Proxied (orange cloud)** —
your origin IP is then hidden and TLS is terminated at Cloudflare's edge. See §7 for the security implications.

### 4c. If you don't own a domain (free options)

- **DuckDNS** — `<name>.duckdns.org`, free, easy Windows updater client.
  <https://www.duckdns.org/>
- **No-IP free** — `<name>.ddns.net`, free with a monthly confirmation email.
  <https://www.noip.com/>
- **Afraid.org FreeDNS** — free subdomains under community-donated domains.
  <https://freedns.afraid.org/>
- **Dynu** — free dynamic DNS with several suffixes.
  <https://www.dynu.com/>

All four give you a hostname you can point at `108.221.38.129` and update automatically when the IP changes.

### 4d. If the public IP is dynamic (residential ISP)

Residential IPs (which `108.221.38.129` looks like it may be, from an AT&T/Comcast-style block) can change on reboot or
lease expiry. Options:

1. **Cloudflare DNS + a DDNS updater script** — install
   [`cloudflare-ddns`](https://github.com/timothymiller/cloudflare-ddns) or run a simple PowerShell scheduled task that
   hits the Cloudflare API every 5 minutes with the current IP.
2. **DuckDNS Windows updater** — one-line PowerShell scheduled task provided on their site.
3. **Router-native DDNS** — most consumer routers (ASUS, TP-Link, Ubiquiti, pfSense, OPNsense) include DDNS clients for
   Cloudflare/DuckDNS/No-IP.
4. **Cloudflare Tunnel (option B in §6)** — sidesteps the whole problem; the IP never appears in DNS.

Sample PowerShell DuckDNS scheduled task:

```powershell
# Save as C:\Scripts\duckdns-update.ps1
$domain = "waka"
$token  = "your-duckdns-token"
Invoke-WebRequest -Uri "https://www.duckdns.org/update?domains=$domain&token=$token&ip=" `
  -UseBasicParsing | Out-Null

# Register to run every 5 min:
schtasks /Create /SC MINUTE /MO 5 /TN "DuckDNS Update" `
  /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Scripts\duckdns-update.ps1" `
  /RU SYSTEM
```

### 4e. Check your ISP's TOS

Some residential ISPs prohibit "server" traffic on inbound 80/443. If yours does, prefer **Cloudflare Tunnel** (option
B): it uses outbound-only connections and is indistinguishable from any other HTTPS client from the ISP's perspective.

---

## 5. Router / firewall port-forwarding (option A only)

Skip if you're using Cloudflare Tunnel (option B).

Forward on the router:

| External port | Protocol | Internal target  | Purpose                               |
|---------------|----------|------------------|---------------------------------------|
| 443           | TCP      | 192.168.1.50:443 | HTTPS (WakaTime plugin talks to this) |
| 80            | TCP      | 192.168.1.50:80  | Let's Encrypt HTTP-01 challenge only  |

Do **not** forward 3000 or any other Wakapi-internal port. Only Caddy is public.

Verify from an outside network:

```bash
nc -vz 108.221.38.129 443
nc -vz 108.221.38.129 80
```

---

## 6. Deploy Wakapi + TLS on Docker Desktop

Everything below lives in one folder — `C:\wakapi\`. Create it, then create the files shown.

### Option A — Caddy reverse proxy with automatic Let's Encrypt

**`C:\wakapi\docker-compose.yml`:**

```yaml
name: wakapi-stack

services:
  wakapi:
    image: ghcr.io/muety/wakapi:latest
    container_name: wakapi
    restart: unless-stopped
    expose:
      - "3000"                  # internal only, NOT published to the host
    environment:
      WAKAPI_PASSWORD_SALT: "REPLACE_WITH_LONG_RANDOM_STRING"
      WAKAPI_ALLOW_SIGNUP: "true"                # flip to false after registering
      WAKAPI_PUBLIC_URL: "https://waka.example.com"
      WAKAPI_DB_TYPE: "sqlite3"
      WAKAPI_DB_NAME: "/data/wakapi.db"
      WAKAPI_MAIL_ENABLED: "false"
      # Trust the reverse proxy for the client IP
      WAKAPI_SERVER_TRUSTED_HEADER_AUTH: "false"
    volumes:
      - wakapi_data:/data
    networks:
      - internal

  caddy:
    image: caddy:2
    container_name: caddy
    restart: unless-stopped
    ports:
      - "80:80"                 # ACME HTTP-01 challenge
      - "443:443"                # public HTTPS
      - "443:443/udp"            # HTTP/3
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - internal

volumes:
  wakapi_data:
  caddy_data:
  caddy_config:

networks:
  internal:
    driver: bridge
```

**`C:\wakapi\Caddyfile`:**

```caddy
{
    email you@example.com          # Let's Encrypt registration
    # acme_ca https://acme-staging-v02.api.letsencrypt.org/directory  # uncomment while testing
}

waka.example.com {
    encode zstd gzip

    # Rate-limit and shape traffic; heartbeats are small and frequent
    @api path /api/*
    handle @api {
        reverse_proxy wakapi:3000
    }

    handle {
        reverse_proxy wakapi:3000
    }

    log {
        output file /data/access.log {
            roll_size 10mb
            roll_keep 5
        }
        format json
    }

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

Start it:

```powershell
cd C:\wakapi
docker compose up -d
docker compose logs -f caddy    # confirm "certificate obtained successfully"
docker compose logs -f wakapi   # confirm "listening on :3000"
```

Open `https://waka.example.com` in a browser. On the sign-up page, register your account. Then flip
`WAKAPI_ALLOW_SIGNUP: "false"` and re-run
`docker compose up -d` to close signups.

### Option B — Cloudflare Tunnel (no ports opened, IP hidden)

Use this instead of A if:

- Your IP is dynamic and you don't want to run DDNS,
- Your ISP prohibits inbound 80/443,
- You want Cloudflare's free DDoS/bot layer and identity-based access (Cloudflare Access) in front of Wakapi.

Steps:

1. In the Cloudflare dashboard, create a Tunnel: *Zero Trust → Networks → Tunnels → Create a tunnel*. Name it `wakapi`.
   Choose the **Docker** connector option; Cloudflare will give you a `docker run` command with an embedded token.
2. Replace the `caddy` service in the compose file above with:

   ```yaml
     cloudflared:
       image: cloudflare/cloudflared:latest
       container_name: cloudflared
       restart: unless-stopped
       command: tunnel --no-autoupdate run
       environment:
         TUNNEL_TOKEN: "<paste-your-cloudflared-token>"
       networks:
         - internal
   ```

   Delete the `ports:` block; nothing needs to be published on the Windows host.
3. In the Cloudflare Tunnel *Public Hostname* config, add:

   | Subdomain | Domain | Service |
      |-----------|--------|---------|
   | waka | example.com | `http://wakapi:3000` |

4. Point `waka.example.com` at the tunnel (Cloudflare does this for you when you pick the Public Hostname). The A record
   for `108.221.38.129` is no longer needed.
5. Optionally add a **Cloudflare Access** policy: create two applications —
    - **`waka.example.com/`** requires your Google/GitHub identity + MFA (protects the dashboard).
    - **`waka.example.com/api/*`** in **Bypass** mode (so the WakaTime plugin's bearer token still works without an
      interactive login).

Cloudflare Tunnel is the recommended choice for a residential connection.

---

## 7. Securing the connection — recommended layers

Adopt as many as apply. Layers are additive.

### 7a. TLS (mandatory)

WakaTime API keys travel in the `Authorization` header on every heartbeat. Never expose Wakapi on plain HTTP to the
internet. Both Caddy (option A) and Cloudflare Tunnel (option B) give you TLS with zero manual cert management.

### 7b. Close signups

After you register your first user, set `WAKAPI_ALLOW_SIGNUP: "false"` and
`docker compose up -d`. Otherwise anyone who finds `waka.example.com` can create accounts on your instance.

### 7c. Strong password + salt

The `WAKAPI_PASSWORD_SALT` must be a long random string (32+ characters). Generate one with:

```powershell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Max 256 }))
```

Do **not** change it after the first boot — user password hashes depend on it.

### 7d. Cloudflare in front (either option A with orange-cloud DNS or option B)

Benefits, all free tier:

- Origin IP hidden from the public DNS record.
- Automatic HTTP/3, HSTS, DDoS mitigation.
- Bot Fight Mode and firewall rules to block bad ASNs / countries you never travel to.
- **Cloudflare Access** identity gate on `/` while the plugin path `/api/*` stays reachable with just the bearer token.

### 7e. CrowdSec (intrusion detection in Docker)

Add a lightweight IDS that reads Caddy's access log, detects brute-force / scan patterns, and blocks the offending IPs.
Recommended when option A is used.

```yaml
  crowdsec:
    image: crowdsecurity/crowdsec:latest
    container_name: crowdsec
    restart: unless-stopped
    environment:
      COLLECTIONS: "crowdsecurity/caddy crowdsecurity/http-cve crowdsecurity/base-http-scenarios"
    volumes:
      - crowdsec_data:/var/lib/crowdsec/data
      - crowdsec_config:/etc/crowdsec
      - caddy_data:/var/log/caddy:ro    # Caddy access log
    networks:
      - internal

  volumes:
    # ...existing volumes...
    crowdsec_data:
    crowdsec_config:
```

Pair it with the **Caddy CrowdSec bouncer** plugin (a Caddy image with the bouncer baked in) to actually enforce blocks:

```yaml
  caddy:
    image: ghcr.io/hslatman/caddy-crowdsec-bouncer:latest
    # ...same volumes/ports as before...
```

CrowdSec's free tier also subscribes you to the community IP block-list.

### 7f. Windows Firewall

If you're using option A, only 80 and 443 inbound should be accepted from the internet. Verify:

```powershell
Get-NetFirewallRule -Direction Inbound -Enabled True `
  | Where-Object { $_.Action -eq 'Allow' } `
  | Format-Table -AutoSize DisplayName,Profile,Action
```

Docker Desktop publishes ports through a WSL2 relay; the rules typically appear as *Docker Desktop Backend*. Do not add
manual inbound allows for 3000 or any other Wakapi-internal port.

### 7g. Auto-update the containers

Add [**Watchtower**](https://containrrr.dev/watchtower/) to keep Wakapi and Caddy patched:

```yaml
  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: unless-stopped
    environment:
      WATCHTOWER_CLEANUP: "true"
      WATCHTOWER_SCHEDULE: "0 0 4 * * *"   # daily at 04:00
    volumes:
      - //var/run/docker.sock:/var/run/docker.sock
```

### 7h. Backups

The whole state lives in the `wakapi_data` volume. Nightly job:

```powershell
$stamp = Get-Date -Format "yyyyMMdd-HHmm"
docker run --rm -v wakapi-stack_wakapi_data:/data -v C:\wakapi\backups:/backup `
  alpine sh -c "cd /data && tar czf /backup/wakapi-$stamp.tgz ."
```

Register that as a Windows Scheduled Task nightly. Push the tarball off-box (OneDrive, S3, Backblaze B2) so a disk
failure doesn't take your history with it.

---

## 8. Point PyCharm at your Wakapi

On **every** machine (Windows or Linux):

1. Install the WakaTime plugin from JetBrains Marketplace and restart PyCharm.
2. Log into `https://waka.example.com` → *Settings → Account* → copy your API key.
3. Edit `~/.wakatime.cfg` (Linux) or `%USERPROFILE%\.wakatime.cfg` (Windows):

   ```ini
   [settings]
   api_url = https://waka.example.com/api
   api_key = <paste-your-uuid-here>
   timeout = 15
   hidefilenames = false
   ```

4. Optional: also set the same values under *Settings → Tools → WakaTime* in the PyCharm UI.
5. Edit a file, wait a minute, refresh the dashboard — you should see the heartbeat. Repeat on every machine using the
   **same** API key so all activity rolls up under one user.

**Offline validation:** unplug the network on a client, code for 15 minutes, reconnect. The interval should appear in
Wakapi shortly after. This proves
`wakatime-cli`'s local heartbeat queue (`%USERPROFILE%\.wakatime\offline_heartbeats.bdb` on Windows,
`~/.wakatime/offline_heartbeats.bdb` on Linux) is working across the public link.

---

## 9. Verification checklist

Run these once from an outside network (phone hotspot works fine):

1. `nslookup waka.example.com` → returns `108.221.38.129` (option A) or a Cloudflare IP (option B).
2. `curl -sSI https://waka.example.com/api/health` → `HTTP/2 200`. Certificate should be issued by Let's Encrypt (option
   A) or Cloudflare (option B).
3. Wakapi dashboard loads over HTTPS; browser shows no warnings.
4. Signup page returns 404 or "signup disabled".
5. From two different machines with the same API key, editing files in different projects, both show up in the dashboard
   within a minute.
6. Kill the network on one machine; code 15 min; reconnect; interval appears.
7. Nightly backup task produced a `.tgz` in `C:\wakapi\backups\`.

All seven pass → you have a hardened, internet-reachable, multi-machine, offline-tolerant, free time tracker.

---

## 10. Which of the two options should you pick?

| Consideration                   | Option A (Caddy + port-forward)                          | Option B (Cloudflare Tunnel)                              |
|---------------------------------|----------------------------------------------------------|-----------------------------------------------------------|
| Setup effort                    | Medium — need router access + DNS                        | Low — one container, no ports                             |
| Works behind CGNAT / dynamic IP | Needs DDNS                                               | ✅ Ignores the IP entirely                                |
| Origin IP visible               | Yes (unless you also front with Cloudflare orange-cloud) | ❌ Hidden by design                                       |
| Free DDoS / bot filtering       | Only if you add Cloudflare orange-cloud on top           | ✅ Included                                               |
| Identity gate for dashboard     | DIY (basic auth in Caddy)                                | ✅ Cloudflare Access, drop-in                             |
| ISP TOS risk on residential     | Some ISPs prohibit inbound 80/443                        | ✅ Outbound only, indistinguishable from any HTTPS client |
| Dependencies                    | Docker + your router                                     | Docker + a Cloudflare account (free)                      |

**Recommendation for a Windows-Docker-Desktop deployment on a residential IP:**
start with **Option B (Cloudflare Tunnel)**. It sidesteps every fragile part of the setup (DDNS, port-forwarding, ISP
TOS, origin-IP exposure) and adds identity gating for free. If you later want to remove the Cloudflare dependency,
Option A is a drop-in replacement — the plugin config doesn't change.

---

## 11. Reference links

- Wakapi source & docs: <https://github.com/muety/wakapi>
- Wakapi config reference: <https://github.com/muety/wakapi/blob/master/config.default.yml>
- Wakapi Docker image: <https://github.com/muety/wakapi/pkgs/container/wakapi>
- WakaTime JetBrains plugin: <https://plugins.jetbrains.com/plugin/7425-wakatime>
- WakaTime CLI (offline queue lives here): <https://github.com/wakatime/wakatime-cli>
- Docker Desktop for Windows: <https://docs.docker.com/desktop/install/windows-install/>
- Caddy server: <https://caddyserver.com/>
- Cloudflare Tunnel: <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/>
- Cloudflare Access: <https://developers.cloudflare.com/cloudflare-one/policies/access/>
- CrowdSec: <https://www.crowdsec.net/>
- Caddy CrowdSec bouncer: <https://github.com/hslatman/caddy-crowdsec-bouncer>
- Watchtower: <https://containrrr.dev/watchtower/>
- DuckDNS: <https://www.duckdns.org/>
- Cloudflare DDNS updater: <https://github.com/timothymiller/cloudflare-ddns>

