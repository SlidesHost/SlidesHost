import asyncio, hashlib, json, os, re, secrets, socket, threading, time, uuid
from aiohttp import web, WSMsgType

DATA = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "SlidesHost")
os.makedirs(DATA, exist_ok=True)
DB = os.path.join(DATA, "devices.json")
WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1)); return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

def device_name(ua):
    m = re.search(r"Android [\d.]+; ([^;)]+)", ua); n = m.group(1).strip() if m else ""
    if n and n != "K": return n
    return "iPhone" if "iPhone" in ua else ("Android phone" if "Android" in ua else "Phone")

class Hub:
    """Local web server: pairing (one-time token + PC approval), device store, command + preview channel."""
    def __init__(self, on_change, ask, on_cmd, port=8765):
        self.on_change, self.ask, self.on_cmd, self.port = on_change, ask, on_cmd, port
        self.db = {"devices": {}, "default": None}   # memory only: the list is gone when the app closes
        try: os.remove(DB)                            # delete any list saved by older versions
        except OSError: pass
        self.online, self.active, self.preview = {}, None, False
        self.token, self.token_exp, self.grab = None, 0, None
        self.loop = asyncio.new_event_loop()

    def save(self): pass  # nothing is written to disk
    def new_token(self):
        self.token, self.token_exp = secrets.token_urlsafe(12), time.time() + 300
    def url(self): return f"http://{lan_ip()}:{self.port}/?t={self.token}"

    def changed(self):
        self.broadcast(); self.on_change()
    def broadcast(self):
        asyncio.run_coroutine_threadsafe(self._bc(), self.loop)
    async def _bc(self):
        for i, w in list(self.online.items()):
            try: await w.send_json({"type": "state", "active": i == self.active, "name": self.db["devices"].get(i, {}).get("name", "")})
            except Exception: pass

    def set_active(self, did):
        if did in self.online:
            self.active, self.preview = did, False; self.changed()
    def rename(self, did, name):
        if did in self.db["devices"] and name.strip():
            self.db["devices"][did]["name"] = name.strip()[:40]; self.save(); self.changed()
    def forget(self, did):
        self.db["devices"].pop(did, None)
        if self.db["default"] == did: self.db["default"] = None
        self.save()
        w = self.online.get(did)
        if w: asyncio.run_coroutine_threadsafe(w.close(), self.loop)
        self.changed()

    async def auth(self, ws, d, ua):
        if d.get("type") != "hello": return None
        tok, creds = d.get("token"), {}
        if tok:
            if not (self.token and secrets.compare_digest(tok, self.token) and time.time() < self.token_exp):
                await ws.send_json({"type": "error", "reason": "bad_token"}); return None
            self.token = None; self.on_change()          # one-time: consumed immediately
            await ws.send_json({"type": "pending"})
            fut = self.loop.create_future(); name = str(d.get("name") or "").strip()[:40] or device_name(ua)
            self.ask(name, lambda ok: self.loop.call_soon_threadsafe(fut.set_result, ok))
            if not await fut:
                await ws.send_json({"type": "denied"}); return None
            did, key = uuid.uuid4().hex[:8], secrets.token_urlsafe(24)
            used = [v["name"] for v in self.db["devices"].values()]; uname, n = name, 2
            while uname in used: uname, n = f"{name} ({n})", n + 1
            self.db["devices"][did] = {"name": uname, "key": hashlib.sha256(key.encode()).hexdigest()}
            self.save(); creds = {"deviceId": did, "key": key}
        else:
            did = d.get("deviceId"); dev = self.db["devices"].get(did)
            if not dev or hashlib.sha256(str(d.get("key")).encode()).hexdigest() != dev["key"]:
                await ws.send_json({"type": "error", "reason": "unknown_device"}); return None
        old = self.online.get(did); self.online[did] = ws
        if old is not None and old is not ws: await old.close()
        if self.active is None and (tok or self.db["default"] == did): self.active = did
        await ws.send_json({"type": "welcome", "active": self.active == did, "name": self.db["devices"][did]["name"], **creds})
        self.changed()
        return did

    async def ws(self, req):
        ws = web.WebSocketResponse(heartbeat=15); await ws.prepare(req); did = None
        async for m in ws:
            if m.type != WSMsgType.TEXT: continue
            d = json.loads(m.data)
            if did is None:
                did = await self.auth(ws, d, req.headers.get("User-Agent", ""))
                if did is None: break
            elif d.get("type") == "rename":
                self.rename(did, str(d.get("name", "")))
            elif did == self.active:
                if d.get("type") == "preview": self.preview = bool(d.get("on"))
                else: self.on_cmd(d)
            else:
                await ws.send_json({"type": "standby"})
        if did and self.online.get(did) is ws:
            del self.online[did]
            if self.active == did: self.active, self.preview = None, False
            self.changed()
        return ws

    async def frames(self):
        while True:
            await asyncio.sleep(0.25)
            w = self.online.get(self.active)
            if self.preview and w and self.grab:
                try: await w.send_bytes(await self.loop.run_in_executor(None, self.grab))
                except Exception: pass

    def start(self):
        def run():
            asyncio.set_event_loop(self.loop)
            app = web.Application(); app.router.add_get("/ws", self.ws)
            app.router.add_get("/logo.png", lambda r: web.FileResponse(os.path.join(WEB, "logo.png")))
            app.router.add_get("/", lambda r: web.FileResponse(os.path.join(WEB, "index.html"), headers={"Cache-Control": "no-store"}))
            app.router.add_get("/ping", lambda r: web.Response(text="ok"))
            app.router.add_get("/manifest.webmanifest", lambda r: web.json_response({"name": "SlidesHost", "short_name": "SlidesHost", "start_url": "/", "display": "standalone",
                "background_color": "#0e0e12", "theme_color": "#0e0e12", "icons": [{"src": f"/assets/icon-{n}.png", "sizes": f"{n}x{n}", "type": "image/png"} for n in (192, 512)]},
                content_type="application/manifest+json"))
            app.router.add_static("/assets", WEB)
            runner = web.AppRunner(app)
            self.loop.run_until_complete(runner.setup())
            self.loop.run_until_complete(web.TCPSite(runner, "0.0.0.0", self.port).start())
            self.loop.create_task(self.frames()); self.loop.run_forever()
        threading.Thread(target=run, daemon=True).start()
