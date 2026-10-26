import csv
import hashlib
import io
import os
import re
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta

from PIL import Image, ImageOps

from database_concurrency import (
    connect_database,
    database_write_lock,
    serialized_database_write,
)

DB_PATH = "cropguard_surveillance.db"
SEED_CSV = "reference_image_hashes.csv"
BLOCK_SCORE = 60
REVIEW_SCORE = 25
LOG_REVIEW_TIER = False
MAX_CAPTURE_AGE_DAYS = 30
MIN_LONG_SIDE_PX = 800
COARSE_JPEG_QTABLE_MEAN = 18.0
PHASH_MAX_DISTANCE = 4
STANDARD_SIZES = {
    (224, 224), (227, 227), (256, 256), (299, 299), (331, 331), (384, 384), (512, 512),
    (500, 375), (500, 333), (800, 600), (2048, 1365),
    (640, 480), (1024, 768), (1280, 720), (1280, 853), (1920, 1080), (1920, 1280),
    (1200, 800), (1200, 630), (1000, 1000), (1024, 1024), (1080, 1080), (600, 400),
}
FLAG_POINTS = {
    "NO_CAMERA_EXIF": 30,
    "STANDARD_DIMENSIONS": 30,
    "LOW_RESOLUTION": 15,
    "WEB_COMPRESSION": 15,
    "EDITED_OR_LICENSED": 20,
    "STALE_CAPTURE_DATE": 30,
    "STOCK_MARKER": 100,
    "UNREADABLE_IMAGE": 100,
}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_PHASH_RE = re.compile(r"^[0-9a-f]{16}$")
_LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
_STOCK_RE = re.compile(
    rb"shutterstock|getty ?images|istock|adobe ?stock|alamy|dreamstime|depositphotos|123rf|bigstock|"
    rb"stock ?photo|royalty[- ]?free|unsplash|pexels|pixabay|wikimedia|flickr|creative ?commons|"
    rb"plant ?village|plantdoc|kaggle|imagenet",
    re.IGNORECASE,
)
_EDITOR_RE = re.compile(
    r"photoshop|lightroom|illustrator|indesign|canva|gimp|paint\.net|affinity|figma|corel|pixlr|fotor",
    re.IGNORECASE,
)

INTEGRITY_TEXT = {
    "English": {
        "integ_header": "🛡️ Image integrity check: details",
        "integ_pass": "✅ Integrity check passed: the file looks like a genuine camera capture.",
        "integ_review": "⚠️ Unverified: this image has no reliable camera provenance.",
        "integ_reject": "⛔ Probable reference, stock or internet image.",
        "integ_wont_log": "This scan will NOT be logged to B2G surveillance:",
        "flag_NO_CAMERA_EXIF": "No camera make, model and capture time in the metadata (stripped, screenshot or web download).",
        "flag_STANDARD_DIMENSIONS": "Dimensions {w}×{h} match a standard web or dataset image size.",
        "flag_LOW_RESOLUTION": "Resolution {w}×{h} is too low for a phone-camera photo.",
        "flag_WEB_COMPRESSION": "JPEG compression typical of web-optimised images.",
        "flag_EDITED_OR_LICENSED": "Metadata shows design-software editing or a copyright notice.",
        "flag_STALE_CAPTURE_DATE": "Capture date {date} is outside the last {limit} days.",
        "flag_STOCK_MARKER": "Stock-photo, licence or public-dataset marker found in the file metadata.",
        "flag_UNREADABLE_IMAGE": "The image file could not be read.",
        "block_SELF_DECLARED_REFERENCE": "You marked this as a reference / test sample.",
        "block_REFERENCE_MATCH": "It matches a known public reference-dataset image ({source}).",
        "block_DUPLICATE": "The same image was already logged, so it is not counted twice.",
        "block_INTEGRITY_REJECT": "Automated checks flag it as a probable reference, stock or internet image.",
        "block_INTEGRITY_REVIEW": "Its camera provenance cannot be verified (missing metadata, old capture date or web-style properties). Upload the original photo taken with your phone camera.",
        "log_outcome_ok": "✅ Logged to B2G surveillance.",
        "log_outcome_blocked": "Diagnosis shown, but this scan was NOT logged to B2G surveillance:",
        "log_outcome_failed": "⚠️ The scan could not be saved to the surveillance database. Please try again.",
        "integ_registry_stats": "Integrity registry: {reference} reference-dataset hashes · {field} field images logged",
    },
    "Kiswahili": {
        "integ_header": "🛡️ Ukaguzi wa uadilifu wa picha: maelezo",
        "integ_pass": "✅ Ukaguzi wa uadilifu umefaulu: faili linaonekana kuwa picha halisi ya kamera.",
        "integ_review": "⚠️ Haijathibitishwa: picha hii haina uthibitisho wa kuaminika wa kamera.",
        "integ_reject": "⛔ Huenda ni picha ya marejeo, ya duka la picha (stock) au ya mtandaoni.",
        "integ_wont_log": "Uchunguzi huu HAUTAHIFADHIWA kwenye ufuatiliaji wa B2G:",
        "flag_NO_CAMERA_EXIF": "Hakuna taarifa za kamera (chapa, modeli na muda wa kupiga picha) kwenye faili (zimeondolewa, picha ya skrini au imepakuliwa mtandaoni).",
        "flag_STANDARD_DIMENSIONS": "Ukubwa {w}×{h} unalingana na ukubwa wa kawaida wa picha za mtandaoni au seti za data.",
        "flag_LOW_RESOLUTION": "Ubora {w}×{h} ni mdogo mno kwa picha ya kamera ya simu.",
        "flag_WEB_COMPRESSION": "Ukandamizaji wa JPEG unaofanana na picha zilizoboreshwa kwa mtandao.",
        "flag_EDITED_OR_LICENSED": "Taarifa za faili zinaonyesha uhariri kwa programu za usanifu au notisi ya hakimiliki.",
        "flag_STALE_CAPTURE_DATE": "Tarehe ya kupigwa {date} iko nje ya siku {limit} zilizopita.",
        "flag_STOCK_MARKER": "Alama ya picha za duka (stock), leseni au seti ya data ya umma imepatikana kwenye taarifa za faili.",
        "flag_UNREADABLE_IMAGE": "Faili la picha halikuweza kusomwa.",
        "block_SELF_DECLARED_REFERENCE": "Uliiweka kama sampuli ya marejeo / majaribio.",
        "block_REFERENCE_MATCH": "Inalingana na picha inayojulikana ya seti ya data ya umma ({source}).",
        "block_DUPLICATE": "Picha hiyo hiyo ilishahifadhiwa, kwa hiyo haihesabiwi mara mbili.",
        "block_INTEGRITY_REJECT": "Ukaguzi wa kiotomatiki unaonyesha huenda ni picha ya marejeo, ya duka la picha au ya mtandaoni.",
        "block_INTEGRITY_REVIEW": "Uhalisia wa kamera hauwezi kuthibitishwa (taarifa hazipo, tarehe ya zamani au sifa za picha za mtandaoni). Pakia picha asili iliyopigwa na kamera ya simu yako.",
        "log_outcome_ok": "✅ Imehifadhiwa kwenye ufuatiliaji wa B2G.",
        "log_outcome_blocked": "Matokeo ya uchunguzi yameonyeshwa, lakini uchunguzi huu HAUKUHIFADHIWA kwenye ufuatiliaji wa B2G:",
        "log_outcome_failed": "⚠️ Uchunguzi haukuweza kuhifadhiwa kwenye hifadhidata ya ufuatiliaji. Tafadhali jaribu tena.",
        "integ_registry_stats": "Rejista ya uadilifu: hash {reference} za seti za data za marejeo · picha {field} za mashambani zimehifadhiwa",
    },
    "French": {
        "integ_header": "🛡️ Contrôle d'intégrité de l'image : détails",
        "integ_pass": "✅ Contrôle d'intégrité réussi : le fichier ressemble à une vraie photo d'appareil.",
        "integ_review": "⚠️ Non vérifiée : cette image n'a pas de provenance d'appareil photo fiable.",
        "integ_reject": "⛔ Image probablement de référence, de banque d'images ou issue d'internet.",
        "integ_wont_log": "Ce scan ne sera PAS enregistré dans la surveillance B2G :",
        "flag_NO_CAMERA_EXIF": "Aucune métadonnée d'appareil (marque, modèle, date de prise de vue) : supprimées, capture d'écran ou téléchargement web.",
        "flag_STANDARD_DIMENSIONS": "Les dimensions {w}×{h} correspondent à une taille standard d'image web ou de jeu de données.",
        "flag_LOW_RESOLUTION": "La résolution {w}×{h} est trop faible pour une photo de smartphone.",
        "flag_WEB_COMPRESSION": "Compression JPEG typique des images optimisées pour le web.",
        "flag_EDITED_OR_LICENSED": "Les métadonnées indiquent une retouche avec un logiciel de design ou une mention de copyright.",
        "flag_STALE_CAPTURE_DATE": "La date de prise de vue {date} est en dehors des {limit} derniers jours.",
        "flag_STOCK_MARKER": "Marqueur de banque d'images, de licence ou de jeu de données public trouvé dans les métadonnées.",
        "flag_UNREADABLE_IMAGE": "Le fichier image n'a pas pu être lu.",
        "block_SELF_DECLARED_REFERENCE": "Vous l'avez indiquée comme échantillon de référence / de test.",
        "block_REFERENCE_MATCH": "Elle correspond à une image connue d'un jeu de données public ({source}).",
        "block_DUPLICATE": "La même image a déjà été enregistrée : elle n'est pas comptée deux fois.",
        "block_INTEGRITY_REJECT": "Les contrôles automatiques la signalent comme probable image de référence, de banque d'images ou d'internet.",
        "block_INTEGRITY_REVIEW": "Sa provenance ne peut pas être vérifiée (métadonnées absentes, date ancienne ou propriétés d'image web). Téléversez la photo originale prise avec l'appareil de votre téléphone.",
        "log_outcome_ok": "✅ Enregistré dans la surveillance B2G.",
        "log_outcome_blocked": "Diagnostic affiché, mais ce scan n'a PAS été enregistré dans la surveillance B2G :",
        "log_outcome_failed": "⚠️ Le scan n'a pas pu être enregistré dans la base de surveillance. Veuillez réessayer.",
        "integ_registry_stats": "Registre d'intégrité : {reference} empreintes de jeux de données de référence · {field} images de terrain enregistrées",
    },
}

def _s(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "ignore")
    return str(value)

def _parse_exif_dt(value):
    text = _s(value).strip("\x00 ")
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    return None

def _mean_luma_quantiser(tables):
    try:
        table = tables[0]
        return sum(table) / len(table)
    except Exception:
        return None

def inspect_image_bytes(raw, now=None):
    now = now or datetime.now()
    flags = []
    report = {"ok": True, "format": None, "width": 0, "height": 0, "size_bytes": len(raw)}
    try:
        img = Image.open(io.BytesIO(raw))
        width, height = img.size
        report.update(format=img.format, width=width, height=height)
    except Exception:
        report["ok"] = False
        return _finish(report, [("UNREADABLE_IMAGE", {})])

    exif, exif_ifd = {}, {}
    try:
        ex = img.getexif()
        exif = dict(ex)
        try:
            exif_ifd = dict(ex.get_ifd(0x8769))
        except Exception:
            exif_ifd = {}
    except Exception:
        pass
    make, model = _s(exif.get(0x010F)).strip("\x00 "), _s(exif.get(0x0110)).strip("\x00 ")
    captured = _parse_exif_dt(exif_ifd.get(0x9003) or exif_ifd.get(0x9004) or exif.get(0x0132))
    if not ((make or model) and captured):
        flags.append(("NO_CAMERA_EXIF", {}))

    long_side, short_side = max(width, height), min(width, height)
    if (long_side, short_side) in STANDARD_SIZES:
        flags.append(("STANDARD_DIMENSIONS", {"w": width, "h": height}))
    if long_side < MIN_LONG_SIDE_PX:
        flags.append(("LOW_RESOLUTION", {"w": width, "h": height}))

    if img.format == "JPEG":
        progressive = bool(img.info.get("progressive") or img.info.get("progression"))
        qmean = _mean_luma_quantiser(getattr(img, "quantization", None))
        if progressive or (qmean is not None and qmean >= COARSE_JPEG_QTABLE_MEAN):
            flags.append(("WEB_COMPRESSION", {}))

    if _EDITOR_RE.search(_s(exif.get(0x0131))) or _s(exif.get(0x8298)).strip("\x00 "):
        flags.append(("EDITED_OR_LICENSED", {}))

    if captured and (captured < now - timedelta(days=MAX_CAPTURE_AGE_DAYS) or captured > now + timedelta(days=1)):
        flags.append(("STALE_CAPTURE_DATE", {"date": captured.strftime("%Y-%m-%d"), "limit": MAX_CAPTURE_AGE_DAYS}))

    if _STOCK_RE.search(raw[:262144]):
        flags.append(("STOCK_MARKER", {}))

    return _finish(report, flags)

def _finish(report, flags):
    items = [{"code": c, "points": FLAG_POINTS[c], "params": p} for c, p in flags]
    score = sum(i["points"] for i in items)
    report["flags"] = items
    report["score"] = score
    report["verdict"] = "REJECT" if score >= BLOCK_SCORE else "REVIEW" if score >= REVIEW_SCORE else "PASS"
    return report

def fingerprint_image_bytes(raw):
    sha = hashlib.sha256(raw).hexdigest()
    phash = None
    try:
        img = Image.open(io.BytesIO(raw))
        if img.format == "JPEG":
            img.draft("L", (64, 64))
        img = ImageOps.exif_transpose(img)
        px = img.convert("L").resize((9, 8), _LANCZOS).tobytes()
        bits = 0
        for row in range(8):
            for col in range(8):
                bits = (bits << 1) | (1 if px[row * 9 + col] > px[row * 9 + col + 1] else 0)
        phash = f"{bits:016x}"
    except Exception:
        phash = None
    return {"sha256": sha, "phash": phash}

def _hamming(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")

def _informative(phash):
    return 10 <= bin(int(phash, 16)).count("1") <= 54

_DDL = """
CREATE TABLE IF NOT EXISTS image_hash_registry (
    sha256       TEXT PRIMARY KEY,
    phash        TEXT,
    category     TEXT NOT NULL,
    source_label TEXT,
    first_seen   TEXT NOT NULL,
    user_id      INTEGER,
    hub_region   TEXT
)"""
_SEED_STATE = {}

def _connect(db_path=DB_PATH):
    conn = connect_database(db_path)
    try:
        with database_write_lock():
            conn.execute(_DDL)
    except Exception:
        conn.close()
        raise
    return conn

def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _upsert_reference(conn, rows):
    conn.executemany(
        """INSERT INTO image_hash_registry (sha256, phash, category, source_label, first_seen)
           VALUES (?, ?, 'REFERENCE_DATASET', ?, ?)
           ON CONFLICT(sha256) DO UPDATE SET
               category = 'REFERENCE_DATASET',
               source_label = excluded.source_label,
               phash = COALESCE(excluded.phash, image_hash_registry.phash)""",
        [(sha, ph, src, _now_str()) for sha, ph, src in rows],
    )

def _count(conn):
    return conn.execute("SELECT COUNT(*) FROM image_hash_registry").fetchone()[0]

@serialized_database_write
def import_csv(path, db_path=DB_PATH):
    rows, skipped = [], 0
    if os.path.isfile(path):
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for rec in csv.DictReader(fh):
                sha = (rec.get("sha256") or "").strip().lower()
                ph = (rec.get("phash") or "").strip().lower() or None
                src = (rec.get("source") or "").strip() or "reference dataset"
                if not _SHA_RE.match(sha) or (ph is not None and not _PHASH_RE.match(ph)):
                    skipped += 1
                    continue
                rows.append((sha, ph, src))
    conn = _connect(db_path)
    try:
        before = _count(conn)
        _upsert_reference(conn, rows)
        conn.commit()
        return {"read": len(rows), "skipped": skipped, "added": _count(conn) - before}
    finally:
        conn.close()

def export_csv(path, db_path=DB_PATH):
    conn = _connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT sha256, phash, source_label FROM image_hash_registry")
        rows = cursor.fetchall()
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["sha256", "phash", "source"])
            writer.writerows(rows)
    finally:
        conn.close()

def init_registry(db_path=DB_PATH, seed_csv=SEED_CSV):
    conn = _connect(db_path)
    conn.close()
    candidates = [seed_csv, os.path.join(os.path.dirname(os.path.abspath(__file__)), seed_csv)]
    for path in candidates:
        if path and os.path.isfile(path):
            mtime = os.path.getmtime(path)
            if _SEED_STATE.get((db_path, path)) != mtime:
                result = import_csv(path, db_path)
                _SEED_STATE[(db_path, path)] = mtime
                return result
            return None
    return None

def check_registry(fp, db_path=DB_PATH):
    out = {"reference": None, "duplicate": None}
    def offer(category, source, exact, distance):
        kind = "reference" if category == "REFERENCE_DATASET" else "duplicate"
        if out[kind] is None or distance < out[kind]["distance"]:
            out[kind] = {"source": source or "", "exact": exact, "distance": distance}

    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT category, source_label FROM image_hash_registry WHERE sha256 = ?", (fp["sha256"],)
        ).fetchone()
        if row:
            offer(row[0], row[1], True, 0)
        phash = fp.get("phash")
        if phash and _informative(phash):
            for category, source, other in conn.execute(
                "SELECT category, source_label, phash FROM image_hash_registry WHERE phash IS NOT NULL"
            ):
                if _informative(other):
                    dist = _hamming(phash, other)
                    if dist <= PHASH_MAX_DISTANCE:
                        offer(category, source, False, dist)
    finally:
        conn.close()
    return out

@serialized_database_write
def claim_field_image(fp, user_id, hub_region, db_path=DB_PATH):
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            """INSERT OR IGNORE INTO image_hash_registry
               (sha256, phash, category, source_label, first_seen, user_id, hub_region)
               VALUES (?, ?, 'FIELD_LOGGED', 'farm field capture', ?, ?, ?)""",
            (fp["sha256"], fp.get("phash"), _now_str(), user_id, hub_region),
        )
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()

@serialized_database_write
def release_field_image(sha256, db_path=DB_PATH):
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM image_hash_registry WHERE sha256 = ? AND category = 'FIELD_LOGGED'", (sha256,))
        conn.commit()
    finally:
        conn.close()

def registry_stats(db_path=DB_PATH):
    conn = _connect(db_path)
    try:
        counts = dict(conn.execute("SELECT category, COUNT(*) FROM image_hash_registry GROUP BY category"))
    finally:
        conn.close()
    return {"reference": counts.get("REFERENCE_DATASET", 0), "field": counts.get("FIELD_LOGGED", 0)}

_MEMO = OrderedDict()
_MEMO_LOCK = threading.Lock()
_MEMO_MAX, _MEMO_TTL = 64, 600

def assess_upload(raw, db_path=DB_PATH):
    key = hashlib.sha256(raw).hexdigest()
    with _MEMO_LOCK:
        hit = _MEMO.get(key)
        if hit and time.time() - hit[0] > _MEMO_TTL:
            hit = None
        if hit:
            _MEMO.move_to_end(key)
    if hit is None:
        hit = (time.time(), inspect_image_bytes(raw), fingerprint_image_bytes(raw))
        with _MEMO_LOCK:
            _MEMO[key] = hit
            while len(_MEMO) > _MEMO_MAX:
                _MEMO.popitem(last=False)
    _, report, fingerprint = hit
    return {"report": report, "fingerprint": fingerprint, "registry": check_registry(fingerprint, db_path)}

def logging_decision(assessment, attested_field_sample):
    blockers = []
    if not attested_field_sample:
        blockers.append({"code": "SELF_DECLARED_REFERENCE", "params": {}})
    registry = assessment["registry"]
    if registry["reference"]:
        blockers.append({"code": "REFERENCE_MATCH", "params": {"source": registry["reference"]["source"]}})
    if registry["duplicate"]:
        blockers.append({"code": "DUPLICATE", "params": {}})
    verdict = assessment["report"]["verdict"]
    if verdict == "REJECT":
        blockers.append({"code": "INTEGRITY_REJECT", "params": {}})
    elif verdict == "REVIEW" and not LOG_REVIEW_TIER:
        blockers.append({"code": "INTEGRITY_REVIEW", "params": {}})
    return {"allow": not blockers, "blockers": blockers}

def _fmt(T, key, params=None):
    template = T.get(key) or INTEGRITY_TEXT["English"].get(key, key)
    try:
        return template.format(**(params or {}))
    except (KeyError, IndexError, ValueError):
        return template

def render_assessment(st, T, assessment, attested=True):
    report, fp = assessment["report"], assessment["fingerprint"]
    verdict = report["verdict"]
    if verdict == "PASS":
        st.success(_fmt(T, "integ_pass"))
    elif verdict == "REVIEW":
        st.warning(_fmt(T, "integ_review"))
    else:
        st.error(_fmt(T, "integ_reject"))

    blockers = logging_decision(assessment, attested)["blockers"]
    if blockers:
        lines = [_fmt(T, "integ_wont_log"), ""]
        lines += ["- " + _fmt(T, "block_" + b["code"], b["params"]) for b in blockers]
        st.markdown("\n".join(lines))

    with st.expander(_fmt(T, "integ_header")):
        if report["flags"]:
            st.markdown("\n".join("- " + _fmt(T, "flag_" + f["code"], f["params"]) for f in report["flags"]))
        st.caption(
            f"{report['width']}×{report['height']} · {report['format']} · score {report['score']} · "
            f"SHA-256 {fp['sha256'][:16]}… · dHash {fp['phash'] or 'n/a'}"
        )

def render_log_outcome(st, T, outcome):
    if not outcome:
        return
    if outcome["status"] == "LOGGED":
        st.success(_fmt(T, "log_outcome_ok"))
    elif outcome["status"] == "FAILED":
        st.error(_fmt(T, "log_outcome_failed"))
    else:
        lines = [_fmt(T, "log_outcome_blocked"), ""]
        lines += ["- " + _fmt(T, "block_" + b["code"], b["params"]) for b in outcome["blockers"]]
        st.warning("\n".join(lines))
