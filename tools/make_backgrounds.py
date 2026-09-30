"""Generate the section background art in assets/bg/ (pure standard library).

    python tools/make_backgrounds.py

Each scene is a context-matched SVG: topographic contours (hydrology), a turbine
stator blueprint (engineering), a LiDAR-style point cloud (data), PCB traces
(skills) and an audio spectrum (side projects). Deterministic: same seed, same art.
"""
import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "bg"
W, H = 1600, 900


def svg(body, w=W, h=H, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid slice">'
            f'<defs>{defs}</defs>{body}</svg>')


def f(x):
    return f"{x:.1f}".rstrip("0").rstrip(".")


# --- Terrain field shared by contours and point cloud -------------------------
def terrain(seed=7):
    rnd = random.Random(seed)
    hills = [(rnd.uniform(0, 1), rnd.uniform(0, 1), rnd.uniform(0.06, 0.22), rnd.uniform(-0.6, 1.0)) for _ in range(14)]

    def z(x, y):
        v = 0.25 * math.sin(3.1 * x + 1.3) * math.cos(2.3 * y + 0.4) + 0.12 * math.sin(7.0 * x + 5.1 * y)
        for hx, hy, s, a in hills:
            v += a * math.exp(-((x - hx) ** 2 + (y - hy) ** 2) / (2 * s * s))
        return v
    return z


def marching_squares(z, nx, ny, level):
    """Return line segments of the iso-line at `level` over the unit square."""
    xs = [i / nx for i in range(nx + 1)]
    ys = [j / ny for j in range(ny + 1)]
    g = [[z(x, y) for x in xs] for y in ys]
    segs = []

    def lerp(p, q, a, b):
        t = (level - a) / (b - a) if b != a else 0.5
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)

    for j in range(ny):
        for i in range(nx):
            c = [(xs[i], ys[j]), (xs[i + 1], ys[j]), (xs[i + 1], ys[j + 1]), (xs[i], ys[j + 1])]
            v = [g[j][i], g[j][i + 1], g[j + 1][i + 1], g[j + 1][i]]
            idx = sum(1 << k for k in range(4) if v[k] > level)
            if idx in (0, 15):
                continue
            e = {}
            for k in range(4):
                a, b = k, (k + 1) % 4
                if (v[a] > level) != (v[b] > level):
                    e[k] = lerp(c[a], c[b], v[a], v[b])
            pts = list(e.values())
            if len(pts) == 2:
                segs.append((pts[0], pts[1]))
            elif len(pts) == 4:
                segs.append((pts[0], pts[1]))
                segs.append((pts[2], pts[3]))
    return segs


def join(segs):
    """Chain segments into polylines so the SVG stays small."""
    key = lambda p: (round(p[0], 6), round(p[1], 6))
    ends = {}
    for s in segs:
        for p in s:
            ends.setdefault(key(p), []).append(s)
    used, lines = set(), []
    for s in segs:
        if id(s) in used:
            continue
        used.add(id(s))
        line = [s[0], s[1]]
        for forward in (True, False):
            while True:
                tip = line[-1] if forward else line[0]
                nxt = next((t for t in ends.get(key(tip), []) if id(t) not in used), None)
                if not nxt:
                    break
                used.add(id(nxt))
                other = nxt[1] if key(nxt[0]) == key(tip) else nxt[0]
                line.append(other) if forward else line.insert(0, other)
        lines.append(line)
    return lines


def contours():
    z = terrain()
    nx, ny = 160, 90
    levels = [-0.5 + i * 0.075 for i in range(22)]
    paths = []
    for n, lv in enumerate(levels):
        d = []
        for line in join(marching_squares(z, nx, ny, lv)):
            d.append("M" + " ".join(f"{f(x * W)} {f(y * H)}" for x, y in line))
        index = n % 5 == 0
        paths.append(f'<path d="{"".join(d)}" fill="none" stroke="#5eead4" stroke-opacity="{0.55 if index else 0.22}" stroke-width="{1.3 if index else 0.8}"/>')
    rnd = random.Random(3)
    labels = []
    for _ in range(9):
        x, y = rnd.uniform(0.1, 0.9), rnd.uniform(0.1, 0.9)
        labels.append(f'<g transform="translate({f(x * W)} {f(y * H)})"><path d="M-4 0H4M0 -4V4" stroke="#99f6e4" stroke-opacity=".7"/>'
                      f'<text x="7" y="-5" font-family="monospace" font-size="11" fill="#99f6e4" fill-opacity=".6">{200 + z(x, y) * 40:.1f}</text></g>')
    return svg("".join(paths) + "".join(labels))


# --- Engineering blueprint: stator vane cascade --------------------------------
def airfoil(cx, cy, chord, angle, camber=0.09, thick=0.11, n=28):
    up, lo = [], []
    for i in range(n + 1):
        x = (1 - math.cos(math.pi * i / n)) / 2
        yt = 5 * thick * (0.2969 * math.sqrt(x) - 0.126 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1036 * x ** 4)
        yc = camber * 4 * x * (1 - x)
        up.append((x, yc + yt))
        lo.append((x, yc - yt))
    pts = up + lo[::-1]
    a = math.radians(angle)
    out = []
    for x, y in pts:
        X, Y = (x - 0.5) * chord, -y * chord
        out.append((cx + X * math.cos(a) - Y * math.sin(a), cy + X * math.sin(a) + Y * math.cos(a)))
    return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in out) + "Z"


def blueprint():
    c = "#7cb4ff"
    minor = "".join(f'<path d="M{x} 0V{H}" />' for x in range(0, W + 1, 20)) + "".join(f'<path d="M0 {y}H{W}" />' for y in range(0, H + 1, 20))
    major = "".join(f'<path d="M{x} 0V{H}" />' for x in range(0, W + 1, 100)) + "".join(f'<path d="M0 {y}H{W}" />' for y in range(0, H + 1, 100))
    body = [f'<g stroke="{c}" stroke-opacity=".06" stroke-width="1">{minor}</g>',
            f'<g stroke="{c}" stroke-opacity=".12" stroke-width="1">{major}</g>']
    # Annulus with radial vanes (front view), right side
    hx, hy, r0, r1 = 1180, 470, 150, 330
    ring = [f'<circle cx="{hx}" cy="{hy}" r="{r}" />' for r in (r0, r0 - 18, r1, r1 + 16)]
    vanes = []
    for k in range(36):
        a = 2 * math.pi * k / 36
        p = [(hx + r * math.cos(a + (r - r0) / r1 * 0.35), hy + r * math.sin(a + (r - r0) / r1 * 0.35)) for r in range(r0, r1 + 1, 30)]
        vanes.append("M" + " L".join(f"{f(x)} {f(y)}" for x, y in p))
    body.append(f'<g fill="none" stroke="{c}" stroke-opacity=".5" stroke-width="1.2">{"".join(ring)}<path d="{" ".join(vanes)}"/></g>')
    body.append(f'<g stroke="{c}" stroke-opacity=".45" stroke-dasharray="24 5 3 5"><path d="M{hx - 380} {hy}H{hx + 380}M{hx} {hy - 380}V{hy + 380}"/></g>')
    # Cascade (section A-A), left side
    foils = "".join(f'<path d="{airfoil(260 + i * 70, 250 + i * 95, 170, 28)}"/>' for i in range(5))
    body.append(f'<g fill="{c}" fill-opacity=".05" stroke="{c}" stroke-opacity=".7" stroke-width="1.3">{foils}</g>')
    # Dimension lines and callouts
    dims = f'''
      <g stroke="{c}" stroke-opacity=".55" fill="none" stroke-width="1">
        <path d="M150 190V760M142 250H160M142 725H160"/>
        <path d="M{hx} {hy}L{hx + 233} {hy - 233}M{hx + 233} {hy - 233}H{hx + 330}"/>
        <path d="M{hx - r1} {hy + 380}H{hx + r1}M{hx - r1} {hy + 370}V{hy + 390}M{hx + r1} {hy + 370}V{hy + 390}"/>
        <rect x="1300" y="790" width="280" height="90"/><path d="M1300 820H1580M1440 820V880"/>
      </g>
      <g font-family="monospace" font-size="12" fill="{c}" fill-opacity=".75">
        <text x="120" y="480" transform="rotate(-90 120 480)">PITCH 95.00</text>
        <text x="{hx + 240}" y="{hy - 240}">R 330.00 TYP</text>
        <text x="{hx - 40}" y="{hy + 372}">Ø 660.00</text>
        <text x="230" y="170">SECTION A-A · VANE CASCADE</text>
        <text x="1310" y="810">STATOR VANE ASSY</text>
        <text x="1310" y="845">SCALE 1:2</text><text x="1450" y="845">REV C</text>
        <text x="1310" y="868">UNITS MM</text><text x="1450" y="868">SHT 1/1</text>
      </g>'''
    body.append(dims)
    return svg("".join(body))


# --- LiDAR-style point cloud ---------------------------------------------------
def pointcloud():
    z = terrain(21)
    rnd = random.Random(5)
    bands = [[] for _ in range(8)]
    for _ in range(3200):
        u, v = rnd.random(), rnd.random()
        h = z(u, v)
        X = 800 + (u - v) * 900            # isometric-ish projection
        Y = 180 + (u + v) * 380 - h * 180
        t = max(0, min(0.999, (h + 0.4) / 1.3))
        bands[int(t * 8)].append(f'<circle cx="{round(X)}" cy="{round(Y)}" r="{f(0.9 + t * 1.2)}"/>')
    groups = []
    for b, circles in enumerate(bands):
        t = b / 7
        col = f"#{int(34 + t * 120):02x}{int(211 - t * 90):02x}{int(238 - t * 20):02x}"
        groups.append(f'<g fill="{col}" fill-opacity="{f(0.35 + t * 0.5)}">{"".join(circles)}</g>')
    return svg("".join(groups))


# --- PCB traces ----------------------------------------------------------------
def circuit():
    rnd = random.Random(11)
    step = 20
    traces, pads = [], []
    for _ in range(70):
        x, y = rnd.randrange(0, W, step), rnd.randrange(0, H, step)
        d = [f"M{x} {y}"]
        dx, dy = rnd.choice([(1, 0), (0, 1), (-1, 0), (0, -1)])
        for _ in range(rnd.randint(3, 7)):
            n = rnd.randint(2, 9)
            x += dx * step * n
            y += dy * step * n
            d.append(f"L{x} {y}")
            # 45-degree jog
            if rnd.random() < 0.6:
                j = step * rnd.randint(1, 3)
                dx2, dy2 = (dy, dx) if rnd.random() < 0.5 else (-dy, -dx)
                x += dx * j + dx2 * j
                y += dy * j + dy2 * j
                d.append(f"L{x} {y}")
        traces.append("".join(d))
        pads.append(f'<circle cx="{x}" cy="{y}" r="4"/>')
    chips = "".join(f'<rect x="{rnd.randrange(100, W - 200, 20)}" y="{rnd.randrange(100, H - 150, 20)}" width="{rnd.choice([80, 120])}" height="{rnd.choice([60, 80])}" rx="3"/>' for _ in range(6))
    return svg(f'<g fill="none" stroke="#818cf8" stroke-opacity=".35" stroke-width="1.6" stroke-linejoin="round"><path d="{"".join(traces)}"/></g>'
               f'<g fill="#0a0b10" stroke="#a5b4fc" stroke-opacity=".6" stroke-width="1.4">{"".join(pads)}</g>'
               f'<g fill="#0e1020" stroke="#818cf8" stroke-opacity=".4">{chips}</g>')


# --- Audio spectrum (DJ / RGB) --------------------------------------------------
def spectrum():
    rnd = random.Random(9)
    bars = []
    n = 96
    bw = W / n
    for i in range(n):
        env = math.exp(-((i - n * 0.3) ** 2) / (2 * (n * 0.22) ** 2)) * 0.8 + 0.2
        h = (0.25 + 0.75 * rnd.random()) * env * 360
        x = i * bw + 2
        bars.append(f'<rect x="{f(x)}" y="{f(H / 2 - h)}" width="{f(bw - 5)}" height="{f(h * 2)}" rx="2"/>')
    wave = "M0 450" + "".join(
        f" L{f(x)} {f(450 + 80 * math.sin(x / 38) * math.sin(x / 210) * math.cos(x / 97))}" for x in range(0, W + 1, 8))
    defs = ('<linearGradient id="rgb" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{W}" y2="0"><stop offset="0" stop-color="#ff3d6e"/><stop offset=".25" stop-color="#ffb13d"/>'
            '<stop offset=".5" stop-color="#3dffa2"/><stop offset=".75" stop-color="#3db8ff"/><stop offset="1" stop-color="#b13dff"/></linearGradient>')
    return svg(f'<g fill="url(#rgb)" fill-opacity=".32">{"".join(bars)}</g>'
               f'<path d="{wave}" fill="none" stroke="url(#rgb)" stroke-width="2" stroke-opacity=".8"/>', defs=defs)


# --- Campaign map (project leadership / Barbarossa) ----------------------------
def opsmap():
    rnd = random.Random(41)
    c, a = "#a5b4fc", "#828fff"
    grid = "".join(f'<path d="M{x} 0V{H}"/>' for x in range(0, W + 1, 80)) + "".join(f'<path d="M0 {y}H{W}"/>' for y in range(0, H + 1, 80))
    body = [f'<g stroke="{c}" stroke-opacity=".08">{grid}</g>']
    axes, dots = [], []
    for k, y0 in enumerate((200, 430, 660)):
        pts, x, y = [], 120, y0
        while x < 1350:
            pts.append((x, y))
            x += rnd.uniform(90, 150)
            y += rnd.uniform(-35, 35) + (k - 1) * 8
        d = "M" + " L".join(f"{f(px)} {f(py)}" for px, py in pts)
        axes.append(f'<path d="{d}" marker-end="url(#ah)"/>')
        for px, py in pts[1:-1]:
            for _ in range(rnd.randint(2, 5)):
                dots.append(f'<rect x="{f(px + rnd.uniform(-26, 26))}" y="{f(py + rnd.uniform(-22, 22))}" width="7" height="5"/>')
    body.append(f'<g fill="none" stroke="{a}" stroke-width="2.2" stroke-opacity=".75">{"".join(axes)}</g>')
    body.append(f'<g fill="{c}" fill-opacity=".55">{"".join(dots)}</g>')
    front = "M1180 60 C1230 220 1320 330 1270 480 S1200 700 1250 860"
    body.append(f'<path d="{front}" fill="none" stroke="#ef5b62" stroke-opacity=".45" stroke-width="1.5" stroke-dasharray="6 6"/>')
    body.append(f'<g font-family="monospace" font-size="12" fill="{c}" fill-opacity=".7"><text x="120" y="180">AG NORTH</text>'
                f'<text x="120" y="410">AG CENTER</text><text x="120" y="640">AG SOUTH</text><text x="1290" y="80">FRONT · T+84</text></g>')
    defs = f'<marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="{a}"/></marker>'
    return svg("".join(body), defs=defs)


# --- Code minimap (development) ------------------------------------------------
def codemap():
    rnd = random.Random(2)
    cols = ["#828fff", "#5eead4", "#f0b23a", "#c6cbd6", "#8a909d", "#ef5b62"]
    rects = []
    y, indent = 40, 0
    while y < H - 20:
        x = 60 + indent * 28
        for _ in range(rnd.randint(1, 6)):
            w = rnd.randint(18, 110)
            if x + w > W - 60:
                break
            col = rnd.choices(cols, weights=[3, 2, 1, 4, 5, 0.4])[0]
            rects.append(f'<rect x="{x}" y="{y}" width="{w}" height="8" rx="2" fill="{col}"/>')
            x += w + 10
        y += 18
        r = rnd.random()
        indent = min(indent + 1, 6) if r < 0.25 else max(indent - 1, 0) if r < 0.45 else indent
        if rnd.random() < 0.08:
            y += 18
    return svg(f'<g fill-opacity=".5">{"".join(rects)}</g>')


# --- Career route map (experience) ---------------------------------------------
def routes():
    c = "#a5b4fc"
    # Rough relative positions of Chicago, West Lafayette, Indianapolis and Plainfield
    nodes = {"ORD": (1180, 170), "LAF": (1080, 470), "IND": (1270, 690), "PLN": (1160, 720)}
    body = []
    for r in range(80, 900, 80):
        body.append(f'<circle cx="1180" cy="170" r="{r}" fill="none" stroke="{c}" stroke-opacity="{f(0.12 - r / 9000)}" stroke-dasharray="2 6"/>')
    legs = [("PLN", "IND"), ("IND", "LAF"), ("LAF", "ORD"), ("PLN", "LAF")]
    for a, b in legs:
        (x1, y1), (x2, y2) = nodes[a], nodes[b]
        mx, my = (x1 + x2) / 2 - (y2 - y1) * 0.25, (y1 + y2) / 2 + (x2 - x1) * 0.25
        body.append(f'<path d="M{x1} {y1} Q{f(mx)} {f(my)} {x2} {y2}" fill="none" stroke="#828fff" stroke-opacity=".55" stroke-width="1.6" stroke-dasharray="8 6"/>')
    for k, (x, y) in nodes.items():
        body.append(f'<g transform="translate({x} {y})"><circle r="5" fill="#828fff"/><circle r="14" fill="none" stroke="#828fff" stroke-opacity=".4"/>'
                    f'<text x="20" y="4" font-family="monospace" font-size="13" fill="{c}" fill-opacity=".8">{k}</text></g>')
    return svg("".join(body))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in [("contours", contours), ("blueprint", blueprint), ("pointcloud", pointcloud), ("circuit", circuit), ("spectrum", spectrum), ("opsmap", opsmap), ("codemap", codemap), ("routes", routes)]:
        data = fn()
        (OUT / f"{name}.svg").write_text(data, encoding="utf-8")
        print(f"assets/bg/{name}.svg", len(data) // 1024, "KB")
