from flask import Flask, render_template, abort, request, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import urllib3
import json
import os
import random as _random
import urllib.parse as _urlparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

TIMER_SECONDS = 5 * 60  # 5 minutes

PROXY_HEADERS = {
    "User-Agent":                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language":           "en-US,en;q=0.9",
    "Accept-Encoding":           "identity",
    "Cache-Control":             "no-cache",
    "Sec-Ch-Ua":                 '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile":          "?0",
    "Sec-Ch-Ua-Platform":        '"Windows"',
    "Sec-Fetch-Dest":            "document",
    "Sec-Fetch-Mode":            "navigate",
    "Sec-Fetch-Site":            "none",
    "Sec-Fetch-User":            "?1",
    "Upgrade-Insecure-Requests": "1",
}

PROXY_TARGETS = {
    "wiki": "https://wikispeedruns.com",
}

PROXY_HOSTS = {
    "wiki": {"wikispeedruns.com", "www.wikispeedruns.com"},
}

HOST_TO_SLOT = {}
for _slot, _hosts in PROXY_HOSTS.items():
    for _h in _hosts:
        HOST_TO_SLOT[_h] = _slot

# ── Wiki Speedrun — random article pair generator ──────────────────────────────
WIKI_TOPICS = [
    ('Pizza',                '24768'),    ('Dinosaur',             '8895'),
    ('Bitcoin',              '25439577'), ('William Shakespeare',  '32897'),
    ('Volcano',              '32757'),    ('Ninja',                '21473'),
    ('Chocolate',            '6094'),     ('Apollo 11',            '1633'),
    ('Titanic',              '18916591'), ('Nikola Tesla',         '33189'),
    ('Egyptian pyramid',     '234419'),   ('Dolphin',              '8616'),
    ('Jazz',                 '16042'),    ('Samurai',              '27187'),
    ('Earthquake',           '9309'),     ('Piracy',               '23766'),
    ('Coffee',               '6195'),     ('Monopoly (game)',      '3638'),
    ('Tornado',              '30768'),    ('Cleopatra',            '7598'),
    ('Skateboarding',        '27847'),    ('Compass',              '6237'),
    ('Marathon',             '20118'),    ('Lighthouse',           '18130'),
    ('Origami',              '22490'),    ('Velociraptor',         '32547'),
    ('Spaghetti',            '29098'),    ('Egyptian hieroglyphs', '9879'),
    ('Tsunami',              '30769'),    ('Accordion',            '778'),
    ('Guillotine',           '13175'),    ('Telescope',            '30421'),
    ('Pompeii',              '23817'),    ('Karate',               '17269'),
    ('Saffron',              '27425'),    ('Gondola',              '12878'),
    ('Trebuchet',            '30896'),    ('Platypus',             '23660'),
    ('Abacus',               '167'),      ('Lego',                 '17743'),
    ('Graffiti',             '12598'),    ('Monsoon',              '20178'),
    ('Labyrinth',            '17490'),    ('Ukulele',              '31955'),
    ('Bonsai',               '4788'),     ('Catapult',             '6097'),
    ('Kimono',               '17118'),    ('Quicksand',            '25283'),
    ('Maelstrom',            '19064'),    ('Fjord',                '11090'),
]

def random_wiki_url():
    start, end = _random.sample(WIKI_TOPICS, 2)
    state = {
        'startingArticle': {'pageid': start[1], 'title': start[0]},
        'endingArticle':   {'pageid': end[1],   'title': end[0]},
    }
    encoded = _urlparse.quote(json.dumps(state, separators=(',', ':')))
    return f'https://wikispeedrun.org/settings?state={encoded}'

# ── Game config ────────────────────────────────────────────────────────────────
#   redirect → opens real URL in new tab + fullscreen timer page
#   local    → self-contained HTML file in templates/games/
GAMES = {
    "wikispeedrun": {
        "name":  "Wiki Speedrun",
        "type":  "redirect",
        "url":   "DYNAMIC",
        "icon":  "🌐",
        "color": "#4285F4",
    },
    "passwordfinder": {
        "name":  "Password Finder",
        "type":  "proxy",
        "url":   "https://notlocal.sahayakapp.dev/password-game/",
        "icon":  "🔐",
        "color": "#EA4335",
    },
    "typeracer": {
        "name":  "Type Racer",
        "type":  "redirect",
        "url":   "https://play.typeracer.com/",
        "icon":  "⌨️",
        "color": "#34A853",
    },
    "techtruth": {
        "name":     "Tech Truth or Myth",
        "type":     "local",
        "template": "games/techtruth.html",
        "icon":     "🧠",
        "color":    "#FBBC05",
    },
    "oldvsnew": {
        "name":     "Old vs New Tech",
        "type":     "local",
        "template": "games/oldvsnew.html",
        "icon":     "🕹️",
        "color":    "#4285F4",
    },
    "guesstheapp": {
        "name":     "Guess The App by Emoji",
        "type":     "local",
        "template": "games/guesstheapp.html",
        "icon":     "📱",
        "color":    "#EA4335",
    },
}


# ── Proxy helpers ──────────────────────────────────────────────────────────────

def make_proxy_url(slot, path, query=""):
    url = f"/proxy/{slot}{path}"
    if query:
        url += "?" + query
    return url


def rewrite_url(url, slot, origin):
    if not url:
        return url
    if url.startswith("//"):
        url = "https:" + url
    if url.startswith(("javascript:", "mailto:", "data:", "#")):
        return url
    abs_url = urljoin(origin, url)
    parsed = urlparse(abs_url)
    host = parsed.netloc.lower().split(":")[0]
    if host in HOST_TO_SLOT:
        s = HOST_TO_SLOT[host]
        return make_proxy_url(s, parsed.path or "/", parsed.query)
    return abs_url


def rewrite_html(html, slot, origin):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(href=True):
        tag["href"] = rewrite_url(tag["href"], slot, origin)
    for tag in soup.find_all(src=True):
        tag["src"] = rewrite_url(tag["src"], slot, origin)
    for tag in soup.find_all(action=True):
        tag["action"] = rewrite_url(tag["action"], slot, origin)
    for tag in soup.find_all(attrs={"data-src": True}):
        tag["data-src"] = rewrite_url(tag["data-src"], slot, origin)
    for tag in soup.find_all(srcset=True):
        parts = tag["srcset"].split(",")
        new_parts = []
        for part in parts:
            bits = part.strip().split()
            if bits:
                bits[0] = rewrite_url(bits[0], slot, origin)
            new_parts.append(" ".join(bits))
        tag["srcset"] = ", ".join(new_parts)
    for meta in soup.find_all("meta", attrs={"http-equiv": True}):
        if meta["http-equiv"].lower() in (
            "x-frame-options", "content-security-policy", "x-content-type-options"
        ):
            meta.decompose()
    for script in soup.find_all("script"):
        if script.string:
            js = script.string
            for h in PROXY_HOSTS[slot]:
                s = HOST_TO_SLOT[h]
                js = js.replace(f"https://{h}", f"/proxy/{s}")
                js = js.replace(f"http://{h}", f"/proxy/{s}")
            script.string = js
    return str(soup)


def rewrite_css(css, slot, origin):
    def _replace(m):
        inner = m.group(1).strip("'\" ")
        return f"url({rewrite_url(inner, slot, origin)})"
    return re.sub(r"url\(\s*([^)]+)\s*\)", _replace, css)


def proxy_fetch(slot, path):
    origin = PROXY_TARGETS[slot]
    qs = request.query_string.decode()
    target_url = origin + path + ("?" + qs if qs else "")

    hdrs = dict(PROXY_HEADERS)
    hdrs["Referer"] = origin + "/"
    hdrs["Origin"] = origin
    for h in ("Cookie", "Accept", "Accept-Language", "X-Requested-With", "Content-Type"):
        if h in request.headers:
            hdrs[h] = request.headers[h]

    try:
        upstream = requests.request(
            method=request.method,
            url=target_url,
            headers=hdrs,
            data=request.get_data(),
            timeout=20,
            allow_redirects=True,
            verify=False,
        )
    except requests.exceptions.RequestException as exc:
        return Response(
            f"""<html><body style="font-family:monospace;padding:40px;background:#111;color:#eee;">
            <h2 style="color:#EA4335">⚠ Proxy fetch failed</h2>
            <p><b>Target:</b> {target_url}</p>
            <pre style="color:#f88;margin-top:12px">{exc}</pre>
            </body></html>""",
            status=502, content_type="text/html",
        )

    ct = upstream.headers.get("Content-Type", "")

    if "text/html" in ct:
        if upstream.status_code == 403:
            return Response(
                f"""<html><body style="font-family:monospace;padding:40px;background:#111;color:#eee;">
                <h2 style="color:#FBBC05">⚠ 403 Blocked</h2>
                <p>Site <b>{origin}</b> is blocking the proxy request.</p>
                </body></html>""",
                status=403, content_type="text/html",
            )
        body = rewrite_html(upstream.text, slot, origin)
        resp = Response(body, status=upstream.status_code,
                        content_type="text/html; charset=utf-8")
    elif "text/css" in ct:
        body = rewrite_css(upstream.text, slot, origin)
        resp = Response(body, status=upstream.status_code, content_type=ct)
    elif "javascript" in ct or "ecmascript" in ct:
        js = upstream.text
        for h in PROXY_HOSTS[slot]:
            s = HOST_TO_SLOT[h]
            js = js.replace(f"https://{h}", f"/proxy/{s}")
            js = js.replace(f"http://{h}", f"/proxy/{s}")
        resp = Response(js, status=upstream.status_code, content_type=ct)
    else:
        strip_hdrs = {
            "content-encoding", "content-length", "transfer-encoding",
            "x-frame-options", "content-security-policy",
            "x-content-type-options", "strict-transport-security",
        }
        headers = {k: v for k, v in upstream.headers.items()
                   if k.lower() not in strip_hdrs}
        resp = Response(upstream.content, status=upstream.status_code,
                        headers=headers, content_type=ct)

    for h in ("X-Frame-Options", "Content-Security-Policy",
              "X-Content-Type-Options", "Strict-Transport-Security"):
        resp.headers.discard(h)

    raw_cookies = upstream.headers.get("Set-Cookie")
    if raw_cookies:
        resp.headers.add("Set-Cookie", raw_cookies)

    return resp


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    links = "".join(
        f'<a href="/game/{gid}" style="display:block;margin:10px 0;padding:14px 18px;'
        f'border-radius:12px;background:{g["color"]};color:#fff;text-decoration:none;'
        f'font-weight:800">{g["icon"]} {g["name"]}</a>'
        for gid, g in GAMES.items()
    )
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Club Mela Games</title></head>'
        '<body style="font-family:sans-serif;background:#0d0d0d;color:#fff;'
        'max-width:420px;margin:0 auto;padding:24px">'
        '<h1>🎮 Club Mela Games</h1>' + links +
        '<a href="/leaderboard" style="display:block;margin-top:20px;color:#FBBC05">'
        '🏆 Leaderboard</a></body></html>'
    )


@app.route("/game/<game_id>")
def game(game_id):
    if game_id not in GAMES:
        abort(404)
    g = GAMES[game_id]

    # ?ends=<unix_ms> is stamped by the dashboard when generating the QR.
    # If missing (e.g. direct browser visit), fall back to TIMER_SECONDS from now.
    import time as _time
    try:
        ends_at = int(request.args.get("ends", 0))
        if ends_at <= 0:
            raise ValueError
    except (ValueError, TypeError):
        ends_at = int(_time.time() * 1000) + TIMER_SECONDS * 1000

    if g["type"] == "proxy":
        iframe_src = g["url"]
        return render_template("iframe_game.html", game=g, game_id=game_id,
                               ends_at=ends_at, iframe_src=iframe_src)
    elif g["type"] == "redirect":
        # Wiki Speedrun gets a fresh random prefilled URL each visit
        game_url = random_wiki_url() if game_id == "wikispeedrun" else g["url"]
        g_copy = dict(g, url=game_url)
        return render_template("redirect_game.html", game=g_copy, game_id=game_id,
                               ends_at=ends_at)
    else:
        # local — render the game's own HTML directly
        return render_template(g["template"], ends_at=ends_at)


# ── Proxy routes ───────────────────────────────────────────────────────────────

@app.route("/proxy/<slot>/", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/proxy/<slot>/<path:path>",              methods=["GET", "POST"])
def generic_proxy(slot, path):
    if slot not in PROXY_TARGETS:
        abort(404)
    return proxy_fetch(slot, "/" + path)


# ── Debug ──────────────────────────────────────────────────────────────────────

@app.route("/debug/proxy/<slot>")
def debug_proxy(slot):
    if not os.environ.get("ENABLE_DEBUG_ROUTES"):
        abort(404)
    if slot not in PROXY_TARGETS:
        return f"Unknown slot. Valid: {list(PROXY_TARGETS.keys())}", 400
    origin = PROXY_TARGETS[slot]
    url = origin + "/"
    hdrs = dict(PROXY_HEADERS)
    hdrs["Referer"] = origin + "/"
    try:
        r = requests.get(url, headers=hdrs, timeout=15, allow_redirects=True, verify=False)
        return f"""<html><body style="font-family:monospace;padding:24px;background:#111;color:#eee;">
        <h2 style="color:#34A853">✅ Fetch succeeded</h2>
        <p><b>Final URL:</b> {r.url}</p>
        <p><b>Status:</b> {r.status_code}</p>
        <p><b>Content-Type:</b> {r.headers.get('Content-Type','?')}</p>
        <p><b>X-Frame-Options:</b> {r.headers.get('X-Frame-Options','(not set)')}</p>
        <p><b>Body length:</b> {len(r.content)} bytes</p>
        <hr style="border-color:#333;margin:16px 0"/>
        <pre style="color:#aaa;white-space:pre-wrap;font-size:0.8rem">{r.text[:3000]}</pre>
        </body></html>"""
    except Exception as exc:
        return f"""<html><body style="font-family:monospace;padding:24px;background:#111;color:#eee;">
        <h2 style="color:#EA4335">❌ Fetch FAILED</h2>
        <p><b>URL:</b> {url}</p>
        <pre style="color:#f88">{exc}</pre>
        </body></html>"""


@app.errorhandler(404)
def not_found(e):
    return "<h2 style='font-family:sans-serif'>404 — Not found</h2>", 404



# ── Google Sheets score submission ─────────────────────────────────────────────
from flask import jsonify
from google.oauth2.service_account import Credentials as _Creds
from googleapiclient.discovery import build as _build
import datetime as _dt

SHEET_ID    = os.environ.get("SHEET_ID", "1AFDTYKICc3oeqAEiI51RyFesUgCqjfykK5ZrJw9a_rc")
SHEET_TAB   = os.environ.get("SHEET_TAB", "Sheet1")
SHEET_RANGE = f"{SHEET_TAB}!A:F"
CREDS_FILE  = os.path.join(os.path.dirname(__file__), "credentials.json")
SCOPES      = ["https://www.googleapis.com/auth/spreadsheets"]
IST         = _dt.timezone(_dt.timedelta(hours=5, minutes=30))  # Vercel runs in UTC


def _get_sheets_service():
    # On Vercel: set GOOGLE_CREDENTIALS_JSON env var (full JSON contents).
    # Locally: falls back to credentials.json next to this file.
    raw = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if raw:
        creds = _Creds.from_service_account_info(json.loads(raw), scopes=SCOPES)
    else:
        creds = _Creds.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    return _build("sheets", "v4", credentials=creds, cache_discovery=False).spreadsheets()


def _clean_cell(value, max_len=60):
    """Trim + cap length. Values are written with RAW, so formulas never execute."""
    return str(value).strip()[:max_len]


@app.route("/api/submit_score", methods=["POST"])
def submit_score():
    data = request.get_json(silent=True) or {}
    name  = _clean_cell(data.get("name", ""))
    phone = _clean_cell(data.get("phone", ""), 15)
    game  = str(data.get("game", "")).strip()

    if not name or not phone:
        return jsonify({"error": "Name and phone are required"}), 400

    valid_games = {g["name"] for g in GAMES.values()}
    if game not in valid_games:
        return jsonify({"error": "Unknown game"}), 400

    try:
        score = int(data.get("score"))
        total = int(data.get("total"))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid score"}), 400
    if total <= 0 or score < 0 or score > total:
        return jsonify({"error": "Invalid score"}), 400

    timestamp = _dt.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    row = [[timestamp, name, phone, game, f"{score}/{total}", f"{round(score / total * 100)}%"]]

    try:
        svc = _get_sheets_service()
        svc.values().append(
            spreadsheetId=SHEET_ID,
            range=SHEET_RANGE,
            valueInputOption="RAW",          # RAW: nothing gets evaluated as a formula
            insertDataOption="INSERT_ROWS",
            body={"values": row},
        ).execute()
        return jsonify({"ok": True}), 200
    except Exception as e:
        app.logger.exception("Sheets append failed")
        return jsonify({"error": "Could not save score, tell the organiser"}), 500


@app.route("/leaderboard")
def leaderboard():
    return render_template("leaderboard.html", games=GAMES)


def _pct(score_str):
    try:
        a, b = str(score_str).split("/")
        return int(a) / int(b) if int(b) > 0 else 0
    except (ValueError, ZeroDivisionError):
        return 0


@app.route("/api/leaderboard")
def api_leaderboard():
    try:
        svc = _get_sheets_service()
        result = svc.values().get(spreadsheetId=SHEET_ID, range=SHEET_RANGE).execute()
        rows = result.get("values", [])
        if rows and rows[0] and str(rows[0][0]).lower() in ("timestamp", "time", "date"):
            rows = rows[1:]

        # One entry per person per game (best score wins) - phone is used only
        # for de-duplication and is NEVER sent to the browser.
        best = {}
        for r in rows:
            if len(r) < 6:
                continue
            key = (r[2].strip(), r[3])
            cur = best.get(key)
            if cur is None or _pct(r[4]) > _pct(cur[4]):
                best[key] = r

        entries = [
            {"timestamp": r[0], "name": r[1], "game": r[3], "score": r[4], "pct": r[5]}
            for r in best.values()
        ]
        return jsonify({"entries": entries}), 200
    except Exception:
        app.logger.exception("Sheets read failed")
        return jsonify({"error": "Could not load leaderboard"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)