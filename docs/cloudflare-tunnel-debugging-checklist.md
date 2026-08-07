# Cloudflare Tunnel Debugging Checklist for Wakapi

**Status Check Date:** 2026-08-06  
**Result:** ✅ Tunnel is established and healthy

---

## Current Status Summary

### ✅ Container Status

```
wakapi        ghcr.io/muety/wakapi:latest     Up 27 minutes (healthy)   3000/tcp
cloudflared   cloudflare/cloudflared:latest   Up 27 minutes
```

**Wakapi:**

- IP Address: `172.18.0.2`
- Port: `3000` (internal only)
- Status: Healthy
- Listening on: `0.0.0.0:3000`

**Cloudflared:**

- IP Address: `172.18.0.3`
- Tunnel ID: `35250348-87dc-4b02-bfd9-598fa95f09d8`
- Status: Connected with 4 tunnel connections
- Locations: bna01 (Nashville), atl13/atl14 (Atlanta)
- Protocol: QUIC
- Connectivity Pre-checks: ALL PASSED ✅

---

## Debugging Steps & Verification

### 1. Verify Containers Are Running

```powershell
wsl.exe docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
```

**Expected Output:**

- Both `wakapi` and `cloudflared` should show `Up X minutes`
- Wakapi should show `(healthy)` status
- Wakapi exposes `3000/tcp` internally only (no host ports)

**✅ Current Status:** Both containers running and healthy

---

### 2. Check Cloudflared Tunnel Connection

```powershell
wsl.exe docker logs cloudflared --tail 50
```

**What to Look For:**

- ✅ `Starting tunnel tunnelID=...`
- ✅ `Registered tunnel connection` (should see 4 connections)
- ✅ `CONNECTIVITY PRE-CHECKS` all showing `PASS`
- ✅ `Environment is healthy. cloudflared will use 'quic' as primary protocol`
- ❌ Any `ERR` or `WARN` messages

**✅ Current Status:** All 4 tunnel connections registered successfully

- Connection 0: bna01 (198.41.192.37)
- Connection 1: atl13 (198.41.200.53)
- Connection 2: bna01 (198.41.192.227)
- Connection 3: atl14 (198.41.200.43)

**Interpretation:**

- Multiple connections = redundancy and load balancing
- QUIC protocol = faster than HTTP/2
- Locations in BNA (Nashville) and ATL (Atlanta) are geographically close to your location

---

### 3. Check Wakapi Service Health

```powershell
wsl.exe docker logs wakapi --tail 30
```

**What to Look For:**

- ✅ `Listening for HTTP... ✅ address="0.0.0.0:3000"`
- ✅ Database migrations completed (`no need to migrate`)
- ✅ Job queues created successfully
- ✅ Scheduled tasks initialized
- ❌ Any error messages about database or configuration

**✅ Current Status:** Wakapi fully initialized and listening on port 3000

---

### 4. Verify Network Connectivity Between Containers

```powershell
# Test wakapi accessibility from cloudflared's perspective
wsl.exe docker exec cloudflared wget -O- --spider http://wakapi:3000 2>&1 | grep -i "remote file exists"
```

**Expected:** Should show remote file exists or HTTP 200/301/302

```powershell
# Alternative: Test direct IP connectivity
wsl.exe docker exec cloudflared wget -O- --spider http://172.18.0.2:3000 2>&1
```

---

### 5. Check Cloudflare Tunnel Dashboard Configuration

**Go to:** Cloudflare Dashboard → Zero Trust → Networks → Tunnels

**Verify:**

1. **Tunnel Status:**
    - ✅ Tunnel should show "Healthy" with green indicator
    - ✅ Should show multiple active connectors
    - Tunnel ID matches logs: `35250348-87dc-4b02-bfd9-598fa95f09d8`

2. **Public Hostname Configuration:**
   | Setting | Expected Value | |---------|----------------| | Subdomain | `waka` (or your chosen subdomain) | |
   Domain | Your domain (e.g., `example.com`) | | Service Type | `HTTP` | | URL | `http://wakapi:3000` or
   `http://172.18.0.2:3000` |

   **Common Mistakes:**
    - ❌ Using `https://wakapi:3000` (wrong - wakapi doesn't have TLS internally)
    - ❌ Using `localhost:3000` (wrong - localhost refers to cloudflared container)
    - ❌ Using container ID instead of service name
    - ✅ Correct: `http://wakapi:3000` (Docker service name)

3. **Additional Settings (Optional):**
    - **HTTP Host Header:** (leave empty or set to your public domain)
    - **TLS Settings:** Cloudflare handles external TLS automatically
    - **WAF/Firewall Rules:** Check if any rules block API traffic

---

### 6. DNS Verification

```powershell
# Check DNS resolution
nslookup waka.yourdomain.com 1.1.1.1
```

**Expected:**

- Should resolve to Cloudflare proxy IPs (NOT 108.221.38.129)
- Typical Cloudflare IP ranges: 104.x.x.x, 172.x.x.x, 188.x.x.x

**Alternative Check:**

```powershell
# Use curl to see which IP responds
curl -I https://waka.yourdomain.com
```

---

### 7. Test Public Accessibility

#### From External Network (Not Your LAN)

```powershell
# Test from your current machine (may need to use mobile hotspot or ask friend)
curl -I https://waka.yourdomain.com

# Expected: HTTP/2 200 or 302 redirect
# Should NOT timeout or show connection refused
```

#### Test API Endpoint

```powershell
# Test the WakaTime API endpoint
curl -i https://waka.yourdomain.com/api/heartbeat

# Expected: 401 Unauthorized (means API is responding, just needs auth)
# Bad: Timeout, connection refused, 502/503 error
```

---

### 8. Test From PyCharm/IDE

**Configure WakaTime Plugin:**

1. Open PyCharm → Settings → Plugins → WakaTime
2. Enter API Key (get from Wakapi web dashboard)
3. **Important:** Set Custom API URL:
   ```
   https://waka.yourdomain.com/api
   ```
   (Must include `/api` at the end!)

**Verify Plugin Connection:**

- Check WakaTime plugin logs (usually in IDE logs or `~/.wakatime.log`)
- Should see successful heartbeat sends
- Check Wakapi dashboard - activity should appear within minutes

---

### 9. Common Issues & Solutions

#### Issue: Tunnel shows "Disconnected" in Dashboard

**Solutions:**

1. Check container is running: `wsl.exe docker ps`
2. Restart cloudflared: `wsl.exe docker restart cloudflared`
3. Check TUNNEL_TOKEN is correct in docker-compose.yml
4. Check logs for errors: `wsl.exe docker logs cloudflared`

#### Issue: 502 Bad Gateway Error

**Causes & Solutions:**

1. **Wakapi container not running**
    - Check: `wsl.exe docker ps`
    - Fix: `wsl.exe docker start wakapi`

2. **Wrong service URL in Cloudflare Tunnel config**
    - Should be: `http://wakapi:3000` (NOT https, NOT localhost)
    - Fix: Update Public Hostname in Cloudflare dashboard

3. **Network connectivity issue**
    - Test: `wsl.exe docker exec cloudflared ping wakapi`
    - Fix: Ensure both containers on same Docker network

#### Issue: 401 Unauthorized on All Requests

**This is actually GOOD** - means the API is working!

- 401 on `/api/heartbeat` = needs valid API key
- 401 on dashboard = needs login
- Generate API key from Wakapi dashboard after logging in

#### Issue: Can't Access Wakapi Dashboard Web UI

**Solution:**
Check Public Hostname routes both dashboard AND API:

- Dashboard: `https://waka.yourdomain.com/`
- API: `https://waka.yourdomain.com/api/*`

If using Cloudflare Access, ensure API paths are in "Bypass" mode:

- Create policy for `waka.yourdomain.com/api/*` → Bypass
- Create policy for `waka.yourdomain.com/*` → Require auth (optional)

#### Issue: PyCharm Plugin Can't Connect

**Checklist:**

1. ✅ API URL includes `/api`: `https://waka.yourdomain.com/api`
2. ✅ API key copied correctly (no spaces)
3. ✅ Using HTTPS (not HTTP)
4. ✅ Domain resolves correctly: `nslookup waka.yourdomain.com`
5. ✅ External test works: `curl https://waka.yourdomain.com/api/heartbeat`

**Plugin Log Locations:**

- Windows: `%USERPROFILE%\.wakatime.log`
- Linux: `~/.wakatime.log`
- PyCharm: Help → Show Log in Explorer

---

### 10. Performance & Health Monitoring

```powershell
# Check container resource usage
wsl.exe docker stats wakapi cloudflared --no-stream

# Check container restart count (should be 0 if stable)
wsl.exe docker inspect wakapi -f '{{.RestartCount}}'
wsl.exe docker inspect cloudflared -f '{{.RestartCount}}'

# View real-time logs
wsl.exe docker logs -f wakapi
wsl.exe docker logs -f cloudflared
```

**Healthy Indicators:**

- Restart count = 0
- CPU usage < 5% when idle
- Memory usage stable
- No constant connection retries in logs

---

### 11. Backup & Recovery

#### Backup Wakapi Data

```powershell
# Find the volume name
wsl.exe docker volume ls | grep wakapi

# Backup database to Windows directory
wsl.exe docker run --rm -v wakapi-stack_wakapi_data:/data -v d:/backups:/backup alpine tar czf /backup/wakapi-backup-$(date +%Y%m%d).tar.gz -C /data .
```

#### Restore from Backup

```powershell
# Restore data volume
wsl.exe docker run --rm -v wakapi-stack_wakapi_data:/data -v d:/backups:/backup alpine tar xzf /backup/wakapi-backup-YYYYMMDD.tar.gz -C /data

# Restart wakapi
wsl.exe docker restart wakapi
```

---

### 12. Security Hardening (Optional)

#### Disable Signup After Registration

```yaml
# In docker-compose.yml
environment:
  WAKAPI_ALLOW_SIGNUP: "false"  # Change from "true"
```

Then restart:

```powershell
wsl.exe docker restart wakapi
```

#### Enable Cloudflare Access (Identity Gate)

1. Go to Cloudflare Zero Trust → Access → Applications
2. Create Application:
    - **Type:** Self-hosted
    - **Application domain:** `waka.yourdomain.com`
    - **Policy for dashboard:** Require email (your email)
    - **Policy for API:** Bypass (path: `waka.yourdomain.com/api/*`)

This adds SSO login (Google/GitHub) to dashboard while keeping API open for plugins.

---

## Quick Reference Commands

```powershell
# Docker command wrapper (if docker not in PATH)
function docker { wsl.exe docker $args }

# Check status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# View logs
docker logs cloudflared --tail 50
docker logs wakapi --tail 30

# Restart services
docker restart cloudflared
docker restart wakapi

# Stop everything
docker compose down

# Start everything
docker compose up -d

# View tunnel connections in real-time
docker logs -f cloudflared | grep -i "registered\|error\|warn"

# Check wakapi health endpoint
curl http://localhost:3000/health  # Only works if port published
docker exec wakapi wget -O- http://localhost:3000/health
```

---

## Cloudflare Dashboard Quick Links

- **Tunnels:** https://one.dash.cloudflare.com/ → Zero Trust → Networks → Tunnels
- **DNS:** https://dash.cloudflare.com/ → Select domain → DNS → Records
- **Access (SSO):** https://one.dash.cloudflare.com/ → Zero Trust → Access → Applications
- **Firewall:** https://dash.cloudflare.com/ → Select domain → Security → WAF

---

## Final Verification Checklist

Use this after making any configuration changes:

- [ ] Both containers running: `docker ps`
- [ ] Cloudflared shows 4 registered connections in logs
- [ ] Wakapi listening on port 3000
- [ ] Cloudflare Dashboard shows tunnel as "Healthy"
- [ ] Public Hostname configured with `http://wakapi:3000`
- [ ] DNS resolves to Cloudflare IPs
- [ ] `curl https://waka.yourdomain.com` returns 200 or 302
- [ ] `curl https://waka.yourdomain.com/api/heartbeat` returns 401 (correct!)
- [ ] PyCharm WakaTime plugin configured with custom API URL
- [ ] Heartbeats appearing in Wakapi dashboard

---

## Additional Resources

- **Wakapi Documentation:** https://wakapi.dev/
- **Cloudflare Tunnel Docs:** https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- **WakaTime Plugin Docs:** https://wakatime.com/plugins
- **Docker Compose Reference:** https://docs.docker.com/compose/compose-file/

---

## Your Current Configuration Status

✅ **Tunnel Established:** 4 active connections  
✅ **Wakapi Running:** Healthy and listening on port 3000  
✅ **Network Connectivity:** Both containers on same Docker network  
⏳ **Pending Verification:** Test external access from browser/IDE

**Next Steps:**

1. Open browser and visit `https://waka.yourdomain.com` (replace with actual domain)
2. Log in to Wakapi dashboard
3. Generate API key for WakaTime plugin
4. Configure PyCharm plugin with API URL and key
5. Write some code and verify heartbeats appear in dashboard
