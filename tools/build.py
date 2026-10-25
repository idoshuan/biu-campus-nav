import json, sys, math, re, collections
sys.path.insert(0, sys.argv[2])
from pdf_buildings import B, OSM_NAME_TO_NUM

# Label positions (px) of buildings on the illustrated map (page 1 rendered at ~1969x1378)
PX = {"1300A":(1112,77),"1300B":(1328,87),"1105":(877,103),"1104":(834,111),"1103":(791,118),"1102":(747,126),
"1005":(628,171),"1004":(563,192),"1002":(478,197),"1501":(1067,248),"1401":(1032,397),"902":(553,326),"905":(527,370),
"901":(619,380),"1502":(710,387),"802":(583,494),"801":(639,548),"506":(815,509),"507":(727,548),"510":(474,556),
"509":(437,567),"508":(494,588),"505":(873,576),"604":(694,609),"605":(632,625),"504":(908,603),"503":(773,658),
"502":(595,674),"411":(1028,662),"407":(1237,651),"410":(899,694),"406":(1293,688),"501":(535,705),"405":(1041,734),
"404":(811,744),"409":(648,744),"408":(692,770),"403":(887,765),"402":(965,780),"306":(1292,744),"217":(541,762),
"216":(623,817),"305":(1373,801),"303":(1483,825),"401":(959,830),"213":(703,830),"212":(749,850),"307":(1112,850),
"302":(1572,849),"304":(1218,861),"206":(846,884),"301":(1341,867),"300":(1414,876),"215":(607,876),"210":(1046,887),
"214":(639,901),"202":(933,918),"209":(680,922),"203":(1008,934),"108":(1435,931),"110":(1168,946),"208":(728,957),
"205":(767,970),"204":(810,977),"107":(1325,966),"106":(1215,983),"105":(1099,999),"103":(655,1041),"104":(853,1053),
"101":(766,1079),"102":(940,1078),"100":(1064,1115)}

d = json.load(open(sys.argv[1]))["elements"]
N = {e["id"]: (e["lat"], e["lon"]) for e in d if e["type"] == "node"}
NT = {e["id"]: e.get("tags", {}) for e in d if e["type"] == "node"}
W = {e["id"]: e for e in d if e["type"] == "way"}
LAT0, LON0 = 32.0700, 34.8452
KX = 111320 * math.cos(math.radians(LAT0)); KY = 110574
def xy(p): return (round((p[1]-LON0)*KX, 1), round(-(p[0]-LAT0)*KY, 1))  # metres, y down
def ll(q): return (LAT0 - q[1]/KY, LON0 + q[0]/KX)
campus = [xy(N[n]) for n in W[48629331]["nodes"]]
def inside(p, poly=campus):
    x, y = p; c = False
    for i in range(len(poly)):
        x1, y1 = poly[i]; x2, y2 = poly[i-1]
        if (y1 > y) != (y2 > y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1: c = not c
    return c
def centroid(pts):
    a = cx = cy = 0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]+pts[:1]):
        f = x1*y2-x2*y1; a += f; cx += (x1+x2)*f; cy += (y1+y2)*f
    if abs(a) < 1e-6: return (sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts))
    return (round(cx/(3*a), 1), round(cy/(3*a), 1))
xs = [p[0] for p in campus]; ys = [p[1] for p in campus]
BOX = (min(xs)-80, min(ys)-80, max(xs)+80, max(ys)+80)
ZONE_M = 500  # routes may start this far outside the campus fence (bus stops, parking across the road)
def campus_dist(p):
    if inside(p): return 0.0
    best = float("inf")
    for (x1, y1), (x2, y2) in zip(campus, campus[1:] + campus[:1]):
        dx, dy = x2 - x1, y2 - y1; t = max(0, min(1, ((p[0]-x1)*dx + (p[1]-y1)*dy) / (dx*dx + dy*dy or 1)))
        best = min(best, math.hypot(p[0] - x1 - t*dx, p[1] - y1 - t*dy))
    return best
def inzone(p, extra=60): return campus_dist(p) <= ZONE_M + extra

pdf = {b[0]: b for b in B}
# --- buildings from OSM
osm_b = []
for w in W.values():
    t = w.get("tags", {})
    if "building" not in t: continue
    pts = [xy(N[n]) for n in w["nodes"][:-1] if n in N]
    if len(pts) < 3: continue
    c = centroid(pts)
    if not inside(c): continue
    num = None
    for cand in (t.get("ref"), t.get("addr:housenumber")):
        if cand and cand.strip() in pdf: num = cand.strip()
    if not num:
        m = re.match(r"\s*(\d{3,4}[AB]?)\b", t.get("name", "") + " ") or re.match(r"\s*(\d{3,4}[AB]?)\b", t.get("name:en", "") + " ")
        if m and m.group(1) in pdf: num = m.group(1)
    how = "osm-number" if num else None
    if not num:
        for k, v in OSM_NAME_TO_NUM.items():
            if k in t.get("name", "") or k in t.get("name:en", ""): num, how = v, "osm-name"; break
    osm_b.append(dict(num=num, how=how, poly=pts, c=c, he=t.get("name"), en=t.get("name:en"), wid=w["id"]))

# --- homography illustration px -> metres, from buildings numbered in OSM
def solve(A, b):
    n = len(A); M = [r[:] + [v] for r, v in zip(A, b)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(M[r][i])); M[i], M[p] = M[p], M[i]
        for r in range(n):
            if r != i:
                f = M[r][i]/M[i][i]; M[r] = [a - f*c for a, c in zip(M[r], M[i])]
    return [M[i][n]/M[i][i] for i in range(n)]
def fit(pairs):
    AtA = [[0]*8 for _ in range(8)]; Atb = [0]*8
    for (u, v), (X, Y) in pairs:
        for row, rhs in (([u, v, 1, 0, 0, 0, -u*X, -v*X], X), ([0, 0, 0, u, v, 1, -u*Y, -v*Y], Y)):
            for i in range(8):
                Atb[i] += row[i]*rhs
                for j in range(8): AtA[i][j] += row[i]*row[j]
    return solve(AtA, Atb)
def H(h, u, v):
    w = h[6]*u + h[7]*v + 1
    return ((h[0]*u + h[1]*v + h[2])/w, (h[3]*u + h[4]*v + h[5])/w)
bynum = collections.defaultdict(list)
for b in osm_b:
    if b["num"]: bynum[b["num"]].append(b)
def numc(num):  # centroid of all polygons tagged with that number
    ps = bynum[num]; return (sum(p["c"][0] for p in ps)/len(ps), sum(p["c"][1] for p in ps)/len(ps))
pairs = [(PX[n], numc(n)) for n in bynum if n in PX and all(p["how"] == "osm-number" for p in bynum[n])]
h = fit(pairs)
for _ in range(2):  # drop outliers and refit
    res = sorted(((math.dist(H(h, *u), X), u, X) for u, X in pairs), reverse=True)
    pairs = [(u, X) for r, u, X in res if r < 45]; h = fit(pairs)
res = [math.dist(H(h, *PX[n]), numc(n)) for n in bynum if n in PX and bynum[n][0]["how"] == "osm-number"]
print("homography from", len(pairs), "points; median residual %.0fm, max %.0fm" % (sorted(res)[len(res)//2], max(res)), file=sys.stderr)
for n in sorted(bynum):
    if bynum[n][0]["how"] == "osm-name" and n in PX:
        print("  name-matched %s residual %.0fm" % (n, math.dist(H(h, *PX[n]), numc(n))), file=sys.stderr)

# local affine from the nearest known buildings (illustration is not a true projection)
CTRL = [(PX[n], numc(n), n) for n in bynum if n in PX]
def local(uv, skip=None, k=6):
    near = sorted((c for c in CTRL if c[2] != skip), key=lambda c: math.dist(c[0], uv))[:k]
    for axis in (0, 1):
        pass
    A = [[0]*3 for _ in range(3)]; bx = [0]*3; by = [0]*3
    for (u, v), (X, Y), _ in near:
        w = 1/(math.dist((u, v), uv) + 20); r = [u, v, 1]
        for i in range(3):
            bx[i] += w*r[i]*X; by[i] += w*r[i]*Y
            for j in range(3): A[i][j] += w*r[i]*r[j]
    ax = solve(A, bx); ay = solve(A, by)
    return (ax[0]*uv[0]+ax[1]*uv[1]+ax[2], ay[0]*uv[0]+ay[1]*uv[1]+ay[2])
loo = sorted(math.dist(local(u, skip=n), X) for u, X, n in CTRL)
print("local fit, leave-one-out error over %d buildings: median %.0fm, 80%% %.0fm, max %.0fm" % (len(loo), loo[len(loo)//2], loo[int(len(loo)*.8)], loo[-1]), file=sys.stderr)
print("  worst:", sorted(((round(math.dist(local(u, skip=n), X)), n) for u, X, n in CTRL), reverse=True)[:6], file=sys.stderr)

# --- walk graph
WALK = {"footway","path","pedestrian","steps","service","unclassified","residential","living_street","corridor","tertiary","tertiary_link",
        "secondary","secondary_link","primary","primary_link","track","crossing"}
nid = {}; nodes = []; edges = {}; draw = []
def node(osm):
    if osm not in nid: nid[osm] = len(nodes); nodes.append(xy(N[osm]))
    return nid[osm]
for w in W.values():
    t = w.get("tags", {}); hw = t.get("highway")
    if hw not in WALK or t.get("foot") == "no" or t.get("area") == "yes": continue
    ns = [n for n in w["nodes"] if n in N]
    if not any(inzone(xy(N[n])) for n in ns): continue
    kind = "steps" if hw == "steps" else ("foot" if hw in ("footway","path","pedestrian","corridor","track") else "road")
    draw.append([kind, [node(n) for n in ns]])
    for a, b in zip(ns, ns[1:]):
        ia, ib = node(a), node(b); L = math.dist(nodes[ia], nodes[ib])
        edges[(min(ia, ib), max(ia, ib))] = [ia, ib, round(L, 1), 1 if kind == "steps" else 0]
# keep the component that covers campus
adj = collections.defaultdict(list)
for a, b, L, s in edges.values(): adj[a].append(b); adj[b].append(a)
comp = {};
for s in range(len(nodes)):
    if s in comp: continue
    st = [s]; comp[s] = s
    while st:
        x = st.pop()
        for y in adj[x]:
            if y not in comp: comp[y] = s; st.append(y)
main = collections.Counter(comp.values()).most_common(1)[0][0]
inmain = [i for i in range(len(nodes)) if comp.get(i) == main]
def nearest(p, pool=inmain):
    return min(pool, key=lambda i: (nodes[i][0]-p[0])**2 + (nodes[i][1]-p[1])**2)

# --- final building list
out = []
for num, area, en, he in B:
    polys = [b["poly"] for b in bynum.get(num, [])]
    if polys:
        c = numc(num); approx = False
    elif num in PX:
        c = tuple(round(v, 1) for v in local(PX[num])); approx = True
    else:
        continue
    # entrance: graph node closest to any polygon vertex (or the centroid)
    cand = [p for poly in polys for p in poly] or [c]
    best = min(((math.dist(p, nodes[nearest(p)]), nearest(p)) for p in cand))[1]
    out.append(dict(n=num, a=area, en=en, he=he, c=[round(c[0], 1), round(c[1], 1)], p=polys, g=best, approx=approx))
others = [dict(he=b["he"], en=b["en"], p=b["poly"]) for b in osm_b if not b["num"]]
print("buildings: %d total, %d from OSM, %d estimated from illustration, %d unknown" % (
    len(out), sum(not b["approx"] for b in out), sum(b["approx"] for b in out), len(B)-len(out)), file=sys.stderr)
print("  estimated:", " ".join(b["n"] for b in out if b["approx"]), file=sys.stderr)
print("  unknown:", " ".join(n for n, *_ in B if n not in {b["n"] for b in out}), file=sys.stderr)

# --- points of interest
POI_KIND = {"cafe":"cafe","restaurant":"food","fast_food":"food","toilets":"toilets","drinking_water":"water",
            "parking":"parking","atm":"atm","place_of_worship":"worship","library":"library","vending_machine":"vending"}
pois = []
for e in d:
    t = e.get("tags", {})
    if e["type"] == "node": p = xy(N[e["id"]])
    elif e["type"] == "way": p = centroid([xy(N[n]) for n in e["nodes"][:-1] if n in N]) if len(e["nodes"]) > 2 else None
    else: continue
    if not p or not inside(p): continue
    k = POI_KIND.get(t.get("amenity")) or ("shop" if t.get("shop") else None) or ("gate" if t.get("barrier") in ("gate","turnstile","entrance") else None)
    if not k: continue
    if k == "gate" and t.get("foot") == "no": continue
    pois.append(dict(k=k, name=t.get("name") or t.get("name:he") or t.get("name:en"), c=[round(p[0], 1), round(p[1], 1)], g=nearest(p)))

# gates: name OSM gates after the nearest numbered gate on the illustration; add the ones OSM lacks
GATE_PX = {"1":(1413,698),"2":(1351,667),"5":(761,443),"10":(1101,247),"15":(1226,113),"20":(693,163),"25":(445,511),"30":(540,994),"40":(1621,912)}
# names and pedestrian opening hours from biu.ac.il/useful-information/orientation/transport-and-parking
# w = Sun-Thu, f = Friday/holiday eve, s = Saturday; "24" always open, None closed
GATE_INFO = {
 "1": ("פיצ'וטו", {"w": "24", "f": "00:00-15:30", "s": None}),  # closes about an hour before Shabbat
 "2": ("", {"w": "24", "f": "24", "s": "24"}),
 "5": ("דקלים", {"w": "06:30-18:00", "f": "06:30-13:00", "s": None}),
 "10": ("דהאן", {"w": "06:30-18:00", "f": "06:30-14:00", "s": None}),
 "15": ("מעונות", {"w": "24", "f": "24", "s": "24"}),
 "20": ("מוסיקה", {"w": "06:30-20:00", "f": None, "s": None}),
 "25": ("הרצוג", {"w": "06:30-18:00", "f": "06:30-13:00", "s": None}),
 "30": ("גהה", {"w": "06:30-21:00", "f": "06:30-13:00", "s": None}),
 "40": ("אונו", {"w": None, "f": None, "s": None}),
}
osm_gates = [p for p in pois if p["k"] == "gate"]
pois = [p for p in pois if p["k"] != "gate"]
est = {g: local(uv) for g, uv in GATE_PX.items()}
pairs = sorted(((math.dist(q["c"], e), g, i) for g, e in est.items() for i, q in enumerate(osm_gates) if math.dist(q["c"], e) < 70))
taken, match = set(), {}
for dist_, g, i in pairs:  # each OSM gate matches at most one numbered gate, closest pairs first
    if g not in match and i not in taken: match[g] = i; taken.add(i)
for g in GATE_PX:
    if g in match: c = osm_gates[match[g]]["c"]; approx = False
    else: c = [round(est[g][0], 1), round(est[g][1], 1)]; approx = True
    nick, hours = GATE_INFO[g]
    pois.append(dict(k="gate", name="שער " + g, nick=nick, hours=hours, c=c, g=nearest(c), approx=approx))
    print("  gate %s: %s" % (g, "estimated" if approx else "matched OSM gate"), file=sys.stderr)

# places marked on the official campus map (px in the same frame as PX); positions estimated with local()
PDF_POI = [
 ("food", None, [(565,211),(913,163),(525,390),(686,626),(721,566),(651,762),(701,847),(940,744),(856,827),(1293,762),(809,956),(1325,986)]),
 ("atm", None, [(702,626),(1294,707)]),
 ("worship", "בית כנסת", [(1106,151)]), ("worship", "חדר תפילה למוסלמים", [(1316,151),(460,608)]), ("worship", "חדר תפילה לנוצרים", [(1331,151)]),
 ("service", "מרכז שירות וגיוס *9392", [(581,630)]),
]
SHUTTLE_PX = {"0":(929,149),"1":(788,181),"2":(419,328),"3":(473,504),"4":(373,632),"5":(427,757),"6":(501,897),"8":(1362,1009),
 "9":(1597,918),"10":(1425,739),"11":(846,673),"12":(500,753),"13":(421,666),"14":(498,484),"15":(475,352),"16":(1074,264)}
def nearest_bnum(c): return min(out, key=lambda b: math.dist(b["c"], c))["n"]
added = collections.Counter()
# the university's four paid lots (same page), matched to OSM outlines by gate and street; prices from that page
PRICE = "30 ₪ ליום · 15 ₪ עם דמי רווחה"
OFFICIAL_LOTS = [
 (59374860, "חניון מרכז וואהל", "מול שער 5 · " + PRICE + " · כניסה חופשית אחרי 20:00 ובסופ\"ש (לפי OSM)", False),
 (940525950, "חניון ספורט", "ליד שער 10 · " + PRICE, False),
 (955804722, "חניון מוסיקה", "רח' ז'בוטינסקי, מאחורי בניין 1005 · " + PRICE, False),
 (135308564, "חניון יהודית", "רח' מקס ואנה ווב · " + PRICE + " · זיהוי החניון משוער", True),
]
lots = []
for wid, name, info, guess in OFFICIAL_LOTS:
    poly = [xy(N[n]) for n in W[wid]["nodes"][:-1] if n in N]; c = centroid(poly)
    lots.append(dict(k="parking", name=name, info=info, official=True, approx=guess, c=[round(c[0], 1), round(c[1], 1)],
                     p=[[round(x, 1), round(y, 1)] for x, y in poly], g=nearest(c)))
def near_lot(c): return any(math.dist(L["c"], c) < 90 or inside(c, L["p"]) for L in lots)
pois = [q for q in pois if q["k"] != "parking"] + lots  # only the official lots; other spots were unreliable estimates
for k, name, pxs in PDF_POI:
    for uv in pxs:
        c = [round(v, 1) for v in local(uv)]
        same = ("cafe", "food") if k == "food" else (k,)
        if any(q["k"] in same and math.dist(q["c"], c) < (50 if k == "parking" else 40) for q in pois): continue
        if k == "parking" and near_lot(c): continue
        pois.append(dict(k=k, name=name, c=c, g=nearest(c), approx=True)); added[k] += 1
for num, uv in SHUTTLE_PX.items():
    c = [round(v, 1) for v in local(uv)]
    info = "הורדה בלבד" if num == "16" else "מתחם הנדסה · השאטל האחרון יוצא מכאן" if num == "0" else ""
    info = " · ".join(x for x in (info, "כל 5–7 דק' · א'–ה' 07:30–20:00 · ו' 07:30–12:00") if x)
    pois.append(dict(k="shuttle", name="תחנת הסעות " + num, info=info, c=c, g=nearest(c), approx=True)); added["shuttle"] += 1
for q in pois:  # give unnamed places a name people can find: type + nearest building
    if not q.get("name"):
        q["name"] = {"cafe": "בית קפה", "food": "מזנון", "atm": "כספומט", "parking": "חניון", "toilets": "שירותים", "water": "ברזיית מים"}.get(q["k"], q["k"])
    if q["k"] in ("cafe", "food", "atm", "toilets", "water"): q["near"] = nearest_bnum(q["c"])
for e in d:
    t = e.get("tags", {})
    if e["type"] == "node" and (t.get("highway") == "bus_stop" or t.get("public_transport") == "platform" and t.get("bus") == "yes"):
        c = xy(N[e["id"]])
        if campus_dist(c) <= ZONE_M and not any(q["k"] == "bus" and math.dist(q["c"], c) < 25 for q in pois):
            pois.append(dict(k="bus", name="תחנת אוטובוס" + (" " + t["name"] if t.get("name") else ""), c=[round(c[0], 1), round(c[1], 1)], g=nearest(c)))
            added["bus"] += 1
print("added from the campus map:", dict(added), file=sys.stderr)

used = set(inmain)
remap = {o: i for i, o in enumerate(sorted(used))}
data = dict(
    origin=[LAT0, LON0], k=[round(KX, 3), KY],
    campus=campus, zone=ZONE_M,
    nodes=[nodes[i] for i in sorted(used)],
    edges=[[remap[a], remap[b], L, s] for a, b, L, s in edges.values() if a in remap and b in remap],
    draw=[[k, [remap[i] for i in ids if i in remap]] for k, ids in draw],
    buildings=[dict(b, g=remap[b["g"]]) for b in out],
    others=others,
    pois=[dict(p, g=remap[p["g"]]) for p in pois],
)
json.dump(data, open(sys.argv[3], "w"), ensure_ascii=False, separators=(",", ":"))
print("pois:", collections.Counter(p["k"] for p in pois), file=sys.stderr)
