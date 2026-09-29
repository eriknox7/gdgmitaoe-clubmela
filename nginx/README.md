# Password Finder — nginx Reverse Proxy

Standalone nginx config that proxies `neal.fun/password-game/` and strips
framing-restriction headers so it can be embedded in an iframe from **any origin**.

## Quick Start

```bash
# Start nginx (from project root)
nginx -c $(pwd)/nginx/passwordfinder-rp.conf

# Verify it's running
curl -I http://localhost:8080/password-game/
```

## Iframe URL

Use this as the iframe `src` in your app:

```
http://<your-server>:8080/password-game/
```

For local testing: `http://localhost:8080/password-game/`

## How It Works

- nginx listens on **port 8080**
- `/password-game/` → proxied to `neal.fun/password-game/` with full browser header forwarding
- CSP `frame-ancestors`, `X-Frame-Options`, and `Strict-Transport-Security` headers are **stripped**
- `Access-Control-Allow-Origin: *` is added so any origin can iframe it
- Fallback locations handle dynamic JS asset requests (`/_nuxt/`, `/cdn-cgi/`, `/general/`, `/favicons/`)
- **No `sub_filter`** — JS is passed through untouched so Nuxt.js hydration works correctly

## Stop / Reload

```bash
# Reload config after edits
nginx -c $(pwd)/nginx/passwordfinder-rp.conf -s reload

# Stop
nginx -c $(pwd)/nginx/passwordfinder-rp.conf -s stop
```
