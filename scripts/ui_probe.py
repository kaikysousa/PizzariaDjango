"""Mede UI real via Chrome DevTools Protocol: overflow, contraste, toque e metadados."""

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import websocket

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

PROBE_JS = r"""
(() => {
  const visible = (el) => {
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity) > 0.05 && r.width > 0 && r.height > 0;
  };
  const parse = (value) => {
    const m = value.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const parts = m[1].split(',').map((v) => parseFloat(v.trim()));
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
  };
  const lum = ({ r, g, b }) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const ratio = (a, b) => {
    const l1 = lum(a), l2 = lum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  };
  const bgOf = (el) => {
    let node = el;
    while (node) {
      const c = parse(getComputedStyle(node).backgroundColor);
      if (c && c.a > 0.85) return c;
      node = node.parentElement;
    }
    return { r: 255, g: 255, b: 255, a: 1 };
  };

  const ids = [...document.querySelectorAll('[id]')].map((el) => el.id);
  const duplicates = [...new Set(ids.filter((id, i) => ids.indexOf(id) !== i))];

  const tapTargets = [...document.querySelectorAll('button, a, input[type="submit"]')]
    .filter(visible)
    .map((el) => {
      const r = el.getBoundingClientRect();
      return { text: (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 40), w: Math.round(r.width), h: Math.round(r.height) };
    });
  const smallTapTargets = tapTargets.filter((t) => t.w < 44 || t.h < 44);

  const inputsWithoutLabel = [...document.querySelectorAll('input:not([type="hidden"]), textarea, select')]
    .filter(visible)
    .filter((el) => {
      if (el.getAttribute('aria-label') || el.getAttribute('aria-labelledby')) return false;
      if (el.id && document.querySelector(`label[for="${el.id}"]`)) return false;
      return !el.closest('label');
    })
    .map((el) => el.name || el.id || el.tagName);

  const imagesWithoutAlt = [...document.querySelectorAll('img')]
    .filter((img) => !img.hasAttribute('alt'))
    .map((img) => img.getAttribute('src') || '(sem src)');

  const contrastFailures = [];
  const nodes = [...document.querySelectorAll('h1,h2,h3,h4,p,a,button,label,span,li')].filter(visible).slice(0, 80);
  for (const el of nodes) {
    const text = (el.innerText || '').trim();
    if (!text) continue;
    const style = getComputedStyle(el);
    const fg = parse(style.color);
    if (!fg || fg.a < 0.5) continue;
    const bg = bgOf(el);
    const size = parseFloat(style.fontSize);
    const bold = parseInt(style.fontWeight, 10) >= 700;
    const large = size >= 24 || (size >= 18.66 && bold);
    const r = ratio(fg, bg);
    const min = large ? 3 : 4.5;
    if (r < min) {
      contrastFailures.push({
        text: text.slice(0, 40),
        tag: el.tagName.toLowerCase(),
        ratio: Math.round(r * 100) / 100,
        min,
        fg: style.color,
        bg: `rgb(${bg.r}, ${bg.g}, ${bg.b})`,
      });
    }
  }

  const localCss = [...document.querySelectorAll('link[rel="stylesheet"]')]
    .map((l) => l.href)
    .filter((href) => href.startsWith(location.origin));

  const cartDialog = document.querySelector("dialog#carrinho");

  return {
    title: document.title,
    lang: document.documentElement.lang,
    metaDescription: (document.querySelector('meta[name="description"]') || {}).content || '',
    overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    duplicates,
    smallTapTargets,
    inputsWithoutLabel,
    imagesWithoutAlt,
    contrastFailures,
    localCss,
    hiddenBroken: [...document.querySelectorAll("[hidden]")]
      .filter((el) => getComputedStyle(el).display !== "none")
      .map((el) => el.id || el.className),
    cartDialog: Boolean(cartDialog),
    cartDialogLabelled: Boolean(cartDialog && cartDialog.getAttribute("aria-labelledby")),
    headings: [...document.querySelectorAll('h1,h2,h3')].map((h) => `${h.tagName}:${(h.innerText || '').trim().slice(0, 40)}`),
    formsWithoutCsrf: [...document.querySelectorAll('form[method="post"]')].filter((f) => !f.querySelector('input[name="csrfmiddlewaretoken"]')).length,
  };
})()
"""


def find_chrome():
    for candidate in CHROME_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    raise RuntimeError("Chrome/Edge não encontrado")


def wait_for_port(port, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1) as response:
                return json.load(response)
        except Exception:
            time.sleep(0.2)
    raise RuntimeError("Chrome não abriu a porta de depuração")


def new_target(port, url="about:blank"):
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/json/new?{urllib.parse.quote(url, safe=':/?=&')}",
        method="PUT",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=60)
        self.seq = 0

    def call(self, method, **params):
        self.seq += 1
        self.ws.send(json.dumps({"id": self.seq, "method": method, "params": params}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") == self.seq:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message.get("result", {})

    def evaluate(self, expression):
        result = self.call(
            "Runtime.evaluate",
            expression=expression,
            returnByValue=True,
            awaitPromise=True,
        )
        return result.get("result", {}).get("value")

    def navigate(self, url):
        self.call("Page.navigate", url=url)
        for _ in range(100):
            time.sleep(0.1)
            if self.evaluate("document.readyState") == "complete":
                return
        raise RuntimeError(f"timeout carregando {url}")

    def screenshot(self, path):
        data = self.call("Page.captureScreenshot", format="png")["data"]
        with open(path, "wb") as handle:
            handle.write(base64.b64decode(data))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", default=os.path.join(os.environ.get("TEMP", "."), "opencode", "shots"))
    parser.add_argument("--label", default="probe")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--port", type=int, default=9333)
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    chrome = find_chrome()
    profile = tempfile.mkdtemp(prefix="ui-probe-")
    process = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            f"--remote-debugging-port={args.port}",
            f"--user-data-dir={profile}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    results = {}
    try:
        wait_for_port(args.port)
        target = new_target(args.port)
        cdp = CDP(target["webSocketDebuggerUrl"])
        cdp.call("Page.enable")
        cdp.call("Runtime.enable")

        for width, height in ((390, 844), (768, 1024), (1280, 900)):
            cdp.call(
                "Emulation.setDeviceMetricsOverride",
                width=width,
                height=height,
                deviceScaleFactor=1,
                mobile=width < 600,
            )
            cdp.navigate(args.url)
            time.sleep(0.4)
            data = cdp.evaluate(PROBE_JS)
            results[str(width)] = data
            cdp.screenshot(os.path.join(args.out, f"{args.label}-{width}.png"))

        css_text = ""
        for href in results["1280"].get("localCss", []):
            try:
                with urllib.request.urlopen(href, timeout=10) as response:
                    css_text += response.read().decode("utf-8", "replace")
            except Exception:
                pass

        summary = {
            "url": args.url,
            "viewports": results,
            "reducedMotionCss": "prefers-reduced-motion" in css_text,
            "before": args.label,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))

        if args.check:
            failures = []
            mobile = results["390"]
            if mobile["overflow"]:
                failures.append(f"overflow em 390px: {mobile['scrollWidth']} > {mobile['innerWidth']}")
            if mobile["duplicates"]:
                failures.append(f"IDs duplicados: {mobile['duplicates']}")
            if mobile["smallTapTargets"]:
                failures.append(f"alvos de toque pequenos: {mobile['smallTapTargets']}")
            if mobile["inputsWithoutLabel"]:
                failures.append(f"campos sem label: {mobile['inputsWithoutLabel']}")
            if mobile["imagesWithoutAlt"]:
                failures.append(f"imagens sem alt: {mobile['imagesWithoutAlt']}")
            if mobile["hiddenBroken"]:
                failures.append(f"[hidden] ainda visível: {mobile['hiddenBroken']}")
            if not mobile["cartDialog"] or not mobile["cartDialogLabelled"]:
                failures.append("drawer sem dialog nativo ou sem aria-labelledby")
            if mobile["contrastFailures"]:
                failures.append(f"contraste: {mobile['contrastFailures']}")
            if not mobile["lang"].lower().startswith("pt"):
                failures.append(f"lang={mobile['lang']!r}")
            if not mobile["metaDescription"]:
                failures.append("meta description ausente")
            if not summary["reducedMotionCss"]:
                failures.append("CSS sem prefers-reduced-motion")
            if mobile["formsWithoutCsrf"]:
                failures.append(f"{mobile['formsWithoutCsrf']} form(s) POST sem CSRF")
            if failures:
                for failure in failures:
                    print(f"FAIL: {failure}")
                sys.exit(1)
            print("GATE_UI ok")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except Exception:
            process.kill()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
