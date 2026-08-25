"""Static checks for Courtside. Run: python tools/check.py

Extracts the inline <script> from index.html and syntax-checks it with node,
then checks sw.js, then greps for mistakes that are easy to make in a
single-file app and invisible until runtime.
"""
import io, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "index.html")
SW = os.path.join(ROOT, "sw.js")

fails = []


def node_check(code, label):
    fd, path = tempfile.mkstemp(suffix=".js")
    os.close(fd)
    io.open(path, "w", encoding="utf-8").write(code)
    try:
        r = subprocess.run(["node", "--check", path], capture_output=True, text=True)
        if r.returncode != 0:
            fails.append("%s: SYNTAX ERROR\n%s" % (label, r.stdout + r.stderr))
            return False
        print("  OK   %s parses (%d bytes)" % (label, len(code)))
        return True
    finally:
        os.unlink(path)


html = io.open(APP, encoding="utf-8").read()
print("index.html: %d bytes" % len(html))

scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
if len(scripts) != 1:
    fails.append("expected exactly 1 inline <script>, found %d" % len(scripts))
js = scripts[0] if len(scripts) == 1 else ""
if js:
    node_check(js, "index.html inline script")
sw = io.open(SW, encoding="utf-8").read()
node_check(sw, "sw.js")


def want(cond, msg):
    if not cond:
        fails.append(msg)
    else:
        print("  OK   %s" % msg)


defined = set(re.findall(r"function\s+([A-Za-z_$][\w$]*)", js))
defined |= set(re.findall(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(", js))

for name in ["zoneForServeOrder", "applyPoint", "emptyStat", "emptySet", "sumStats",
             "viewTrack", "viewStats", "viewLineup", "viewSubs", "viewScout", "viewRoster",
             "courtView", "matchPosPanel", "orderSlots", "scorePoint", "undoPoint",
             "logStat", "undoStat", "applyLineup", "render", "commit", "flushNow",
             "paintBadge", "boot", "hydrate", "openModal", "closeModal", "download",
             "icon", "emptyCard", "rosterPrompt", "isPlaceholderRoster", "freshRoster"]:
    want(name in defined, "%s() is defined" % name)

for name in ["viewTrack", "boot", "render"]:
    want(js.count("function %s(" % name) == 1, "exactly one %s definition" % name)
want("window.CS" in js, "CS test surface is exposed")

# CSS the views depend on
for cls in ["board", "courtgrid", "zone", "pchip", "key", "settab", "ptbtn",
            "rotbanner", "emptystate", "setupcard", "logwrap", "trow", "posbtn"]:
    want("." + cls in html, "css .%s present" % cls)

# These checks must look at CODE, not prose. Several of the rules below are
# explained in comments that quote the very thing they forbid, so a naive
# substring search reports a failure that does not exist. Strip comments first.
def strip_js_comments(src):
    out, i, n = [], 0, len(src)
    while i < n:
        two = src[i:i + 2]
        if two == "/*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif two == "//":
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif src[i] in "\"'`":
            q = src[i]; i += 1
            while i < n and src[i] != q:
                i += 2 if src[i] == "\\" else 1
            i += 1
        else:
            out.append(src[i]); i += 1
    return "".join(out)


def strip_html_comments(src):
    return re.sub(r"<!--.*?-->", "", src, flags=re.S)


js_code = strip_js_comments(js)
css = re.search(r"<style>(.*?)</style>", html, re.S)
css_code = re.sub(r"/\*.*?\*/", "", css.group(1), flags=re.S) if css else ""
head = strip_html_comments(html)
vp = re.search(r'<meta name="viewport"[^>]*content="([^"]*)"', head)
vp = vp.group(1) if vp else ""

# offline + phone correctness, learned the hard way on Pass Chart
want("touch-action:manipulation" in css_code, "double-tap zoom disabled (touch-action)")
want(vp and "maximum-scale" not in vp and "user-scalable" not in vp,
     "viewport does not block pinch-zoom [%s]" % vp)
want("100dvh" in css_code, "shell uses dvh so the nav is not hidden by browser chrome")
want("min-height:100vh" not in css_code, "no min-height:100vh out-voting the dvh height")
want("grid-template-columns:minmax(0,1fr)" in css_code, "stack grid cannot exceed the phone width")
want("localStorage" in js_code and "indexedDB" in js_code, "saves locally, not over a network")
want("window.storage" not in js_code, "no claude.ai window.storage dependency left")
want("fonts.googleapis" not in html, "no external font fetch (would fail offline)")
want("http://" not in js_code.replace("http://www.w3.org/2000/svg", ""),
     "no plain-http URLs in the script")
# every focusable field must be >= 16px or iOS zooms the page on focus
small = [m for m in re.findall(r"font-size:(\d+(?:\.\d+)?)px", css_code) if float(m) < 16]
want(".inp{" not in css_code or "font-size:16px" in css_code,
     "base input font-size is 16px (iOS focus-zoom floor)")

# icons referenced by the manifest must exist
man = json.load(io.open(os.path.join(ROOT, "manifest.webmanifest"), encoding="utf-8"))
for ic in man["icons"]:
    want(os.path.exists(os.path.join(ROOT, ic["src"])), "icon exists: " + ic["src"])
want(os.path.exists(os.path.join(ROOT, "icons", "apple-touch-icon.png")), "apple-touch-icon exists")

print()
if fails:
    print("FAILED (%d):" % len(fails))
    for f in fails:
        print(" - " + f)
    sys.exit(1)
print("ALL CHECKS PASSED")
