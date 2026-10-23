import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageOps
import numpy as np
import onnxruntime as ort
import sqlite3
from datetime import datetime, timedelta
import pydeck as pdk
import pandas as pd
import time
import json
import math
import os
import unicodedata
import tempfile
import sys
import types
import hashlib
import io
import csv
import threading
import html
from collections import OrderedDict
import re
import uuid
import disease_data as disease_guide_data

# --- SETUP & CONFIGURATION ---
st.set_page_config(
    page_title="CropGuard AI",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================
# --- EMBEDDED DATA INTEGRITY MODULE (di) ---
# ==============================================================
di_module = types.ModuleType("data_integrity")
sys.modules["data_integrity"] = di_module

di_module.DB_PATH = "cropguard_surveillance.db"
di_module.SEED_CSV = "reference_image_hashes.csv"
di_module.BLOCK_SCORE = 60
di_module.REVIEW_SCORE = 25
di_module.LOG_REVIEW_TIER = False
di_module.MAX_CAPTURE_AGE_DAYS = 30
di_module.MIN_LONG_SIDE_PX = 800
di_module.COARSE_JPEG_QTABLE_MEAN = 18.0
di_module.PHASH_MAX_DISTANCE = 4

di_module.STANDARD_SIZES = {
    (224, 224), (227, 227), (256, 256), (299, 299), (331, 331), (384, 384), (512, 512),
    (500, 375), (500, 333), (800, 600), (2048, 1365),
    (640, 480), (1024, 768), (1280, 720), (1280, 853), (1920, 1080), (1920, 1280),
    (1200, 800), (1200, 630), (1000, 1000), (1024, 1024), (1080, 1080), (600, 400),
}

di_module.FLAG_POINTS = {
    "NO_CAMERA_EXIF": 30,
    "STANDARD_DIMENSIONS": 30,
    "LOW_RESOLUTION": 15,
    "WEB_COMPRESSION": 15,
    "EDITED_OR_LICENSED": 20,
    "STALE_CAPTURE_DATE": 30,
    "STOCK_MARKER": 100,
    "UNREADABLE_IMAGE": 100,
}

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
di_module.IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_PHASH_RE = re.compile(r"^[0-9a-f]{16}$")
_LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS")

di_module.INTEGRITY_TEXT = {
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
    if (long_side, short_side) in di_module.STANDARD_SIZES:
        flags.append(("STANDARD_DIMENSIONS", {"w": width, "h": height}))
    if long_side < di_module.MIN_LONG_SIDE_PX:
        flags.append(("LOW_RESOLUTION", {"w": width, "h": height}))

    if img.format == "JPEG":
        progressive = bool(img.info.get("progressive") or img.info.get("progression"))
        qmean = _mean_luma_quantiser(getattr(img, "quantization", None))
        if progressive or (qmean is not None and qmean >= di_module.COARSE_JPEG_QTABLE_MEAN):
            flags.append(("WEB_COMPRESSION", {}))

    if _EDITOR_RE.search(_s(exif.get(0x0131))) or _s(exif.get(0x8298)).strip("\x00 "):
        flags.append(("EDITED_OR_LICENSED", {}))

    if captured and (captured < now - timedelta(days=di_module.MAX_CAPTURE_AGE_DAYS) or captured > now + timedelta(days=1)):
        flags.append(("STALE_CAPTURE_DATE", {"date": captured.strftime("%Y-%m-%d"), "limit": di_module.MAX_CAPTURE_AGE_DAYS}))

    if _STOCK_RE.search(raw[:262144]):
        flags.append(("STOCK_MARKER", {}))

    return _finish(report, flags)

def _finish(report, flags):
    items = [{"code": c, "points": di_module.FLAG_POINTS[c], "params": p} for c, p in flags]
    score = sum(i["points"] for i in items)
    report["flags"] = items
    report["score"] = score
    report["verdict"] = "REJECT" if score >= di_module.BLOCK_SCORE else "REVIEW" if score >= di_module.REVIEW_SCORE else "PASS"
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

def _connect(db_path=di_module.DB_PATH):
    conn = sqlite3.connect(db_path, timeout=10, check_same_thread=False)
    conn.execute(_DDL)
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

def import_csv(path, db_path=di_module.DB_PATH):
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

def export_csv(path, db_path=di_module.DB_PATH):
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

def init_registry(db_path=di_module.DB_PATH, seed_csv=di_module.SEED_CSV):
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

def check_registry(fp, db_path=di_module.DB_PATH):
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
                    if dist <= di_module.PHASH_MAX_DISTANCE:
                        offer(category, source, False, dist)
    finally:
        conn.close()
    return out

def claim_field_image(fp, user_id, hub_region, db_path=di_module.DB_PATH):
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

def release_field_image(sha256, db_path=di_module.DB_PATH):
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM image_hash_registry WHERE sha256 = ? AND category = 'FIELD_LOGGED'", (sha256,))
        conn.commit()
    finally:
        conn.close()

def registry_stats(db_path=di_module.DB_PATH):
    conn = _connect(db_path)
    try:
        counts = dict(conn.execute("SELECT category, COUNT(*) FROM image_hash_registry GROUP BY category"))
    finally:
        conn.close()
    return {"reference": counts.get("REFERENCE_DATASET", 0), "field": counts.get("FIELD_LOGGED", 0)}

_MEMO = OrderedDict()
_MEMO_LOCK = threading.Lock()
_MEMO_MAX, _MEMO_TTL = 64, 600

def assess_upload(raw, db_path=di_module.DB_PATH):
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
    elif verdict == "REVIEW" and not di_module.LOG_REVIEW_TIER:
        blockers.append({"code": "INTEGRITY_REVIEW", "params": {}})
    return {"allow": not blockers, "blockers": blockers}

def _fmt(T, key, params=None):
    template = T.get(key) or di_module.INTEGRITY_TEXT["English"].get(key, key)
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

# Attach functions to di_module
di_module.inspect_image_bytes = inspect_image_bytes
di_module.fingerprint_image_bytes = fingerprint_image_bytes
di_module.import_csv = import_csv
di_module.export_csv = export_csv
di_module.init_registry = init_registry
di_module.check_registry = check_registry
di_module.claim_field_image = claim_field_image
di_module.release_field_image = release_field_image
di_module.registry_stats = registry_stats
di_module.assess_upload = assess_upload
di_module.logging_decision = logging_decision
di_module.render_assessment = render_assessment
di_module.render_log_outcome = render_log_outcome

# --- EXHAUSTIVE MULTILINGUAL TRANSLATION DICTIONARY ---
TRANSLATIONS = {
    "English": {
        "nav_diag": "🌱 Diagnostic & Advisory Hub",
        "nav_map": "🗺️ B2G Epidemiological Heatmap Dashboard",
        "nav_ai": "🤖 Agritech Virtual AI Assistant",
        "nav_forum": "💬 Regional Farmer Community Forum",
        "nav_acc": "🔐 Farmer Account & History Portal",
        "settings": "⚙️ Settings / Configuration",
        "nav_header": "🧭 Platform Navigation",
        "select_portal": "Select Portal View",
        "select_hub_label": "Select Farm Town / Region Worldwide",
        "select_lang_label": "Choose Language / Langue / Idioma",
        "climate_header": "🌦️ Micro-Climate Risk Advisory",
        "b2g_header": "🏛️ Ministry & Bio-Security Portal",
        "about_header": "About CropGuard AI",
        "about_text": "Empowering farmers and agricultural ministries worldwide with instant AI-driven crop diagnostics, syndromic outbreak surveillance, and dynamic extension support.",
        "active_vectors": "Total Active Tracked Vectors:",
        "no_telemetry_sidebar": "No regional cluster telemetry logged yet in current session.",
        "outbreak_warning": "Outbreak Alert",
        "reg_early_warning": "🚨 Regional Outbreak Early-Warning",
        "phytosanitary_feed": "National Epidemiological Surveillance Feed",
        "gps_btn_label": "📍 Auto-Detect GPS",
        "acc_title": "🔐 Farmer Account & Secure Farm History",
        "acc_subtitle": "Manage your credentials (Google OAuth / Phone) and review your complete, persistent agronomic scan history.",
        "profile_header": "👤 Active Account Profile",
        "login_prompt": "🔐 Please sign in with your Google account to access and track your persistent farm history across sessions.",
        "login_btn": "🔗 Sign In with Google",
        "logout_btn": "🚪 Log Out",
        "alt_phone_expander": "📲 Alternative: Phone Number OTP (Simulation)",
        "phone_label": "Phone Number (e.g. +254 712...):",
        "otp_btn": "Send Verification SMS (OTP)",
        "otp_input": "Enter 4-Digit OTP Code:",
        "verify_otp_btn": "Verify Phone OTP",
        "history_header": "📋 Persistent Farm Scan History",
        "history_info": "All field scans and disease severity scores performed under your account are securely preserved here across sessions.",
        "timeline_header": "📈 Infection Severity Timeline Analysis",
        "auth_success": "Successfully authenticated as",
        "email_lbl": "Email:",
        "user_id_lbl": "User Account ID:",
        "no_history_msg": "No scan history logged yet for this account. Run a scan in the Diagnostic Hub!",
        "phone_sent_msg": "OTP sent to {phone}. (Enter code '1234')",
        "phone_success_msg": "Phone sign-in successful!",
        "phone_error_msg": "Invalid OTP. Enter '1234'.",
        "col_time": "Timestamp",
        "col_hub": "Hub Region",
        "col_crop": "Crop",
        "col_disease": "Detected Disease",
        "col_conf": "Confidence (%)",
        "col_stage": "Severity Stage",
        "col_sev_pct": "Severity (%)",
        "map_title": "🗺️ National & Global Epidemiological Heatmap",
        "map_subtitle": "B2G Bio-Security Surveillance & Disease Prevalence Mapping",
        "map_cluster_header": "📊 Live Phytosanitary Outbreak Clusters",
        "filter_crop": "Filter Heatmap by Crop Category:",
        "all_crops_opt": "All Crops",
        "sev_key_title": "🗺️ Outbreak Severity Key:",
        "sev_1": "🟢 Stage 1: Mild (<40% visual discoloration)",
        "sev_2": "🟠 Stage 2: Moderate (40% - 70% visual discoloration)",
        "sev_3": "🔴 Stage 3: High (>70% visual discoloration)",
        "sev_note": "* Circle size scales with infection severity",
        "audit_header": "📑 Telemetry Surveillance Audit Trail",
        "no_map_data": "No regional scan telemetry has been recorded yet in this session.",
        "no_crop_match": "No recorded telemetry matches the selected crop filter.",
        "ai_title": "🤖 CropGuard AI — Virtual Expert Assistant",
        "ai_subtitle": "Real-Time Agronomic Advisory & Pathology Consultation",
        "chat_header": "💬 Interactive Agritech Chat Desk",
        "chat_info": "Ask any question regarding crop diseases, soil health, fungicide dosage, or pest management. Calibrated for {hub} in {lang}.",
        "chat_welcome": "Hello {user}! I am your CropGuard AI virtual agronomist assistant. How can I help you optimize crop health or manage plant pathology in {hub} today?",
        "chat_input_ph": "Ask about crop diseases, pest mitigation, or agronomic advice...",
        "forum_title": "💬 Regional Farmer Community Forum",
        "forum_subtitle": "Connect, Share & Collaborate with Nearby Farmers in",
        "broadcast_header": "✍️ Broadcast to Local Farmers",
        "author_label": "Your Name / Farm Name:",
        "tag_label": "Topic Tag:",
        "msg_label": "Share an update, ask a question, or warn neighbors...",
        "forum_media_label": "Add a picture or video (optional)",
        "forum_media_help": "Share one image or video with your regional community. Images up to 15 MB; videos up to 50 MB.",
        "forum_media_too_large": "This file is too large. Images must be 15 MB or smaller; videos must be 50 MB or smaller.",
        "forum_media_invalid": "This file could not be read as a supported image. Choose a valid JPG, PNG, or WebP image.",
        "forum_post_empty": "Add a message or attach a picture/video before sharing.",
        "forum_media_name": "Attachment",
        "share_btn": "📢 Share with Community",
        "feed_header": "📰 Live Community Feed",
        "post_posted_msg": "Your message has been posted to the regional hub feed!",
        "post_empty_msg": "Please type a message before submitting.",
        "no_posts_msg": "No community posts yet in {hub}. Be the first farmer to share an update!",
        "diag_title": "🌱 CropGuard AI",
        "diag_subtitle": "Advanced Computer Vision Agritech Assistant (Global Edition)",
        "tour_btn": "How to use CropGuard",
        "crop_select_prompt": "Select Target Crop Type (Hub Priority):",
        "crop_select_header": "🌾 Select Crop Context",
        "upload_header": "📥 1.",
        "upload_label_text": "Upload or snap an image of an affected crop leaf...",
        "analyze_btn": "Run Diagnostic Analysis",
        "results_header": "Diagnostic Results",
        "treatment_header": "Agritech Management & Regional Resource Directory",
        "hub_support_header": "📍 Hub Support & Extension Directory",
        "analysis_complete_msg": "Image analysis complete.",
        "crop_context_lbl": "Target Crop Context:",
        "pattern_match_lbl": "Primary Pattern Match:",
        "ai_conf_lbl": "Model Score (not calibrated)",
        "ai_margin_lbl": "Lead over next class (percentage points)",
        "inf_sev_lbl": "Visual Discoloration Estimate",
        "prog_status_lbl": "Progression Status:",
        "stage3_alert": "Visual discoloration is high. Confirm with a local agricultural extension officer before treating or removing plants.",
        "stage2_alert": "Visual discoloration is moderate. Confirm the cause with a local agricultural extension officer before treatment.",
        "stage1_alert": "Visual discoloration is limited. Continue monitoring and confirm the diagnosis if symptoms progress.",
        "diagnosis_disclaimer": "Screening aid only: this model was trained on PlantVillage images and supports maize, potato, and tomato. It may be unreliable on field photos or other crops. The disease guide is reference advice; it does not add model classes or retrain the classifier. Discoloration is a rough image estimate, not measured disease severity.",
        "unsupported_crop_msg": "This model cannot diagnose the selected crop. It supports maize, potato, and tomato only; no diagnosis was logged.",
        "low_confidence_msg": "The model could not identify this crop image with sufficient confidence. Retake a clear leaf photo or consult an agricultural extension officer; no diagnosis was logged.",
        "healthy_class_msg": "No disease class was identified for this crop. This screening result is not proof that the plant is disease-free.",
        "quality_block_title": "Image quality is too poor for a reliable scan.",
        "quality_retake": "Retake the photo in focus with good light, keep the leaf close, and avoid digital zoom.",
        "quality_review_title": "Image quality may reduce model reliability.",
        "quality_metrics": "Quality check: {width}×{height}px · sharpness {sharpness:.1f} · brightness {brightness:.0f}/255 · contrast {contrast:.1f}.",
        "quality_confidence_caution": "Image-quality checks are heuristic, not a trained quality model. The model score is uncalibrated and is not a probability of a correct diagnosis.",
        "hub_support_info": "Showing verified agricultural extension services and input providers matched to your selected hub:",
        "diagnostic_empty_prompt": "👈 Select your region, pick your crop context, upload an image on the left, and click Run Diagnostic Analysis to view insights here.",
        "footer_text": "CropGuard AI — National Phytosanitary Surveillance & Global Agronomic Network"
    },
    "Kiswahili": {
        "nav_diag": "🌱 Vituo vya Uchunguzi na Ushauri",
        "nav_map": "🗺️ Ramani ya Magonjwa na Mlipuko (B2G)",
        "nav_ai": "🤖 Msaidizi wa AI wa Kilimo",
        "nav_forum": "💬 Jukwaa la Jamii ya Wakulima",
        "nav_acc": "🔐 Akaunti ya Mkulima na Kumbukumbu",
        "settings": "⚙️ Mipangilio / Udhibiti",
        "nav_header": "🧭 Uelekezaji wa Mfumo",
        "select_portal": "Chagua Eneo la Tovuti",
        "select_hub_label": "Chagua Mji wa Kilimo Duniani",
        "select_lang_label": "Chagua Lugha",
        "climate_header": "🌦️ Hali ya Hewa na Hatari ya Magonjwa",
        "b2g_header": "🏛️ Wizara ya Kilimo & Usalama wa Biorasilimali",
        "about_header": "Kuhusu CropGuard AI",
        "about_text": "Kuwawezesha wakulima na wizara za kilimo duniani kote kwa uchunguzi wa haraka wa mimea unaoendeshwa na AI, ufuatiliaji wa milipuko, na ushauri wa kitaalamu.",
        "active_vectors": "Jumla ya Magonjwa Inayofuatiliwa:",
        "no_telemetry_sidebar": "Hakuna takwimu za ufuatiliaji zilizorekodiwa katika kipindi hiki.",
        "outbreak_warning": "Tahadhari ya Mlipuko",
        "reg_early_warning": "🚨 Tahadhari ya Mapema ya Mlipuko wa Kanda",
        "phytosanitary_feed": "Mtiririko wa Kitaifa wa Ufuatiliaji wa Magonjwa",
        "gps_btn_label": "📍 Tafuta GPS",
        "acc_title": "🔐 Akaunti ya Mkulima & Historia Salama ya Shamba",
        "acc_subtitle": "Dhibiti utambulisho wako (Google OAuth / Nambari ya Simu) na ukague historia yako kamili ya uchunguzi wa shamba.",
        "profile_header": "👤 Profaili ya Akaunti",
        "login_prompt": "🔐 Tafadhali ingia ukitumia akaunti yako ya Google ili kufikia na kufuatilia historia ya shamba lako.",
        "login_btn": "🔗 Ingia na Google",
        "logout_btn": "🚪 Toka Nje",
        "alt_phone_expander": "📲 Njia Mbadala: Nambari ya Simu OTP (Uigaji)",
        "phone_label": "Nambari ya Simu (mf. +254 712...):",
        "otp_btn": "Tuma SMS ya Uthibitisho (OTP)",
        "otp_input": "Weka Nambari ya Tarakimu 4 ya OTP:",
        "verify_otp_btn": "Thibitisha OTP ya Simu",
        "history_header": "📋 Historia ya Uchunguzi wa Shamba",
        "history_info": "Uchunguzi wote wa mashamba na viwango vya ukali wa magonjwa vilivyofanywa chini ya akaunti yako vimehifadhiwa salama hapa.",
        "timeline_header": "📈 Uchambuzi wa Mwelekeo wa Ukali wa Maambukizi",
        "auth_success": "Imethibitishwa kikamilifu kama",
        "email_lbl": "Barua pepe:",
        "user_id_lbl": "Nambari ya Akaunti ya Mtumiaji:",
        "no_history_msg": "Hakuna historia ya uchunguzi iliyorekodiwa kwa akaunti hii. Fanya uchunguzi kwenye Kituo cha Uchunguzi!",
        "phone_sent_msg": "OTP imetumwa kwa {phone}. (Weka nambari '1234')",
        "phone_success_msg": "Uingiaji wa simu umefanikiwa!",
        "phone_error_msg": "OTP si sahihi. Weka '1234'.",
        "col_time": "Muda",
        "col_hub": "Eneo la Kituo",
        "col_crop": "Mmea",
        "col_disease": "Ugonjwa Uliotambulika",
        "col_conf": "Uhakika (%)",
        "col_stage": "Hatua ya Ukali",
        "col_sev_pct": "Ukali (%)",
        "map_title": "🗺️ Ramani ya Kitaifa na Kimataifa ya Magonjwa",
        "map_subtitle": "Ufuatiliaji wa Usalama wa B2G & Taswira ya Kuenea kwa Magonjwa",
        "map_cluster_header": "📊 Vikundi Vikuu vya Milipuko ya Phytosanitary",
        "filter_crop": "Chuja Ramani kwa Aina ya Mmea:",
        "all_crops_opt": "Mazao Yote",
        "sev_key_title": "🗺️ Ufunguo wa Ukali wa Mlipuko:",
        "sev_1": "🟢 Hatua ya 1: Dalili kidogo za kubadilika kwa rangi",
        "sev_2": "🟠 Hatua ya 2: Dalili za wastani za kubadilika kwa rangi",
        "sev_3": "🔴 Hatua ya 3: Dalili nyingi za kubadilika kwa rangi",
        "sev_note": "* Ukubwa wa duara unaendana na ukali wa maambukizi",
        "audit_header": "📑 Njia ya Ukaguzi wa Telemetry",
        "no_map_data": "Hakuna takwimu za uchunguzi wa eneo zilizorekodiwa bado katika kipindi hiki.",
        "no_crop_match": "Hakuna takwimu zinazolingana na mmea ulichaguliwa.",
        "ai_title": "🤖 CropGuard AI — Msaidizi wa Kitaalamu",
        "ai_subtitle": "Ushauri wa Kilimo wa Wakati Halisi & Utaalamu wa Magonjwa",
        "chat_header": "💬 Jedwali la Mazungumzo ya Kilimo cha Kisasa",
        "chat_info": "Uliza swali lolote kuhusu magonjwa ya mimea, afya ya udongo, au udhibiti wa wadudu. Imewekwa maalum kwa {hub} katika {lang}.",
        "chat_welcome": "Jambo {user}! Mimi ni msaidizi wako wa AI wa kilimo katika CropGuard AI. Ninawezaje kukusaidia kuboresha afya ya mazao yako katika {hub} leo?",
        "chat_input_ph": "Uliza kuhusu magonjwa ya mimea, udhibiti wa wadudu, au ushauri...",
        "forum_title": "💬 Jukwaa la Jamii ya Wakulima wa Kanda",
        "forum_subtitle": "Unganisha, Shiriki na Ushirikiane na Wakulima wa Karibu katika",
        "broadcast_header": "✍️ Tangaza kwa Wakulima wa Eneo Lako",
        "author_label": "Jina Lako / Jina la Shamba:",
        "tag_label": "Lebo ya Mada:",
        "msg_label": "Shiriki taarifa, uliza swali, au tahadharisha majirani...",
        "forum_media_label": "Ongeza picha au video (si lazima)",
        "forum_media_help": "Shiriki picha au video moja na jamii ya eneo lako. Picha hadi MB 15; video hadi MB 50.",
        "forum_media_too_large": "Faili hili ni kubwa mno. Picha lazima ziwe MB 15 au chini; video MB 50 au chini.",
        "forum_media_invalid": "Faili hili halijasomeka kama picha inayotumika. Chagua picha halali ya JPG, PNG au WebP.",
        "forum_post_empty": "Andika ujumbe au ambatisha picha/video kabla ya kushiriki.",
        "forum_media_name": "Kiambatisho",
        "share_btn": "📢 Shiriki na Jamii",
        "feed_header": "📰 Mtiririko wa Moja kwa Moja wa Jamii",
        "post_posted_msg": "Ujumbe wako umechapishwa kwenye mtandao wa wakulima wa eneo lako!",
        "post_empty_msg": "Tafadhali andika ujumbe kabla ya kutuma.",
        "no_posts_msg": "Bado hakuna machapisho ya jamii katika {hub}. Kuwa mkulima wa kwanza kushiriki!",
        "diag_title": "🌱 CropGuard AI",
        "diag_subtitle": "Msaidizi wa Juu wa Maono ya Kompyuta wa Kilimo (Toleo la Dunia)",
        "tour_btn": "Jinsi ya kutumia CropGuard",
        "crop_select_prompt": "Chagua Aina ya Mmea unaochunguzwa:",
        "crop_select_header": "🌾 Chagua Muktadha wa Mmea",
        "upload_header": "📥 1.",
        "upload_label_text": "Pakia au piga picha ya jani la mmea lenye maambukizi...",
        "analyze_btn": "Fanya Uchunguzi wa AI",
        "results_header": "Matokeo ya Uchunguzi",
        "treatment_header": "Usimamizi wa Kilimo na Saraka ya Rasilimali za Kanda",
        "hub_support_header": "📍 Usaidizi wa Kituo na Saraka ya Ugani",
        "analysis_complete_msg": "Uchambuzi wa picha umekamilika.",
        "crop_context_lbl": "Muktadha wa Mmea Lengo:",
        "pattern_match_lbl": "Ulinganifu Mkuu wa Ugonjwa:",
        "ai_conf_lbl": "Alama ya modeli (haijathibitishwa)",
        "ai_margin_lbl": "Tofauti dhidi ya kundi linalofuata (alama za asilimia)",
        "inf_sev_lbl": "Makadirio ya Kubadilika kwa Rangi",
        "prog_status_lbl": "Hali ya Maendeleo:",
        "stage3_alert": "Mabadiliko ya rangi ni mengi. Thibitisha na afisa wa ugani wa kilimo kabla ya kutibu au kuondoa mimea.",
        "stage2_alert": "Mabadiliko ya rangi ni ya wastani. Thibitisha chanzo na afisa wa ugani wa kilimo kabla ya matibabu.",
        "stage1_alert": "Mabadiliko ya rangi ni machache. Endelea kufuatilia na uthibitishe ikiwa dalili zitaongezeka.",
        "diagnosis_disclaimer": "Matokeo ni uchunguzi wa awali tu: modeli ilifunzwa kwa picha za PlantVillage na inasaidia mahindi, viazi na nyanya. Huenda isiwe sahihi kwa picha za shambani au mazao mengine. Mwongozo wa magonjwa ni taarifa za rejea; hauongezi makundi ya modeli wala kuifunza upya modeli. Mabadiliko ya rangi ni makadirio ya picha, si kipimo cha ukali wa ugonjwa.",
        "unsupported_crop_msg": "Modeli hii haiwezi kuchunguza zao lililochaguliwa. Inasaidia mahindi, viazi na nyanya pekee; hakuna utambuzi uliohifadhiwa.",
        "low_confidence_msg": "Modeli haikuweza kutambua picha hii kwa uhakika wa kutosha. Piga picha wazi ya jani tena au wasiliana na afisa wa ugani; hakuna utambuzi uliohifadhiwa.",
        "healthy_class_msg": "Hakuna kundi la ugonjwa lililotambuliwa kwa zao hili. Matokeo haya ya awali hayathibitishi kwamba mmea hauna ugonjwa.",
        "quality_block_title": "Ubora wa picha ni mdogo mno kwa uchunguzi wa kuaminika.",
        "quality_retake": "Piga picha tena ikiwa imeangaziwa vizuri na imelenga jani lililo karibu; epuka kukuza picha kidijitali.",
        "quality_review_title": "Ubora wa picha unaweza kupunguza uaminifu wa modeli.",
        "quality_metrics": "Ukaguzi wa ubora: pikseli {width}×{height} · ukali {sharpness:.1f} · mwangaza {brightness:.0f}/255 · utofauti {contrast:.1f}.",
        "quality_confidence_caution": "Ukaguzi wa ubora wa picha ni makadirio, si modeli iliyofunzwa. Alama ya modeli haijathibitishwa na si uwezekano wa utambuzi kuwa sahihi.",
        "hub_support_info": "Inaonyesha huduma zilizothibitishwa za ushauri wa kilimo na wauzaji wa pembejeo katika kituo chako:",
        "diagnostic_empty_prompt": "👈 Chagua eneo lako, chagua aina ya mmea, pakia picha upande wa kushoto, na ubonyeze Fanya Uchunguzi wa AI ili kuona matokeo hapa.",
        "footer_text": "CropGuard AI — Mtandao wa Kitaifa wa Ufuatiliaji wa Magonjwa ya Mimea na Kilimo Duniani"
    },
    "French": {
        "nav_diag": "🌱 Centre de Diagnostic & Conseil",
        "nav_map": "🗺️ Carte Épidémiologique B2G",
        "nav_ai": "🤖 Assistant Virtuel Agritech AI",
        "nav_forum": "💬 Forum Communautaire Agricole",
        "nav_acc": "🔐 Portail Compte & Historique Agence",
        "settings": "⚙️ Paramètres / Configuration",
        "nav_header": "🧭 Navigation de la Plateforme",
        "select_portal": "Sélectionner la Vue du Portail",
        "select_hub_label": "Sélectionner la Région Agricole Mondiale",
        "select_lang_label": "Choisir la Langue",
        "climate_header": "🌦️ Risque Micro-Climatique",
        "b2g_header": "🏛️ Ministère B2G & Sécurité Biologique",
        "about_header": "À propos de CropGuard AI",
        "about_text": "Permettre aux agriculteurs et aux ministères de l'agriculture du monde entier de bénéficier d'un diagnostic instantané des cultures.",
        "active_vectors": "Total des Vecteurs Suivis :",
        "no_telemetry_sidebar": "Aucune télémétrie enregistrée pour le moment.",
        "outbreak_warning": "Alerte d'Épidémie",
        "reg_early_warning": "🚨 Alerte Précoce d'Épidémie Régionale",
        "phytosanitary_feed": "Flux National de Surveillance Épidémiologique",
        "gps_btn_label": "📍 Détecter GPS",
        "acc_title": "🔐 Compte Agriculteur & Historique Sécurisé",
        "acc_subtitle": "Gérez vos identifiants et consultez l'historique complet et persistant de vos scans agronomiques.",
        "profile_header": "👤 Profil du Compte Actif",
        "login_prompt": "🔐 Veuillez vous connecter avec votre compte Google pour accéder à votre historique persistant.",
        "login_btn": "🔗 Se connecter avec Google",
        "logout_btn": "🚪 Se déconnecter",
        "alt_phone_expander": "📲 Alternative : Numéro de Téléphone OTP (Simulation)",
        "phone_label": "Numéro de téléphone (ex. +254 712...):",
        "otp_btn": "Envoyer le SMS de Vérification (OTP)",
        "otp_input": "Entrez le code OTP à 4 chiffres :",
        "verify_otp_btn": "Vérifier l'OTP du Téléphone",
        "history_header": "📋 Historique des Scans de la Ferme",
        "history_info": "Tous les scans de terrain et scores de sévérité de maladies sont conservés ici en toute sécurité.",
        "timeline_header": "📈 Analyse Chronologique de la Sévérité des Infections",
        "auth_success": "Authentifié avec succès en tant que",
        "email_lbl": "E-mail :",
        "user_id_lbl": "ID du Compte Utilisateur :",
        "no_history_msg": "Aucun historique de scan enregistré pour ce compte. Effectuez un scan dans le Centre de Diagnostic !",
        "phone_sent_msg": "OTP envoyé au {phone}. (Entrez le code '1234')",
        "phone_success_msg": "Connexion par téléphone réussie !",
        "phone_error_msg": "OTP invalide. Entrez '1234'.",
        "col_time": "Horodatage",
        "col_hub": "Région du Hub",
        "col_crop": "Culture",
        "col_disease": "Maladie Détectée",
        "col_conf": "Confiance (%)",
        "col_stage": "Stade de Sévérité",
        "col_sev_pct": "Sévérité (%)",
        "map_title": "🗺️ Carte Épidémiologique Nationale & Mondiale",
        "map_subtitle": "Surveillance de la Sécurité B2G & Cartographie de la Prévalence",
        "map_cluster_header": "📊 Foyers Épidémiologiques Phytosanitaires en Direct",
        "filter_crop": "Filtrer la Carte par Catégorie de Culture :",
        "all_crops_opt": "Toutes les Cultures",
        "sev_key_title": "🗺️ Clé de Sévérité de l'Épidémie :",
        "sev_1": "🟢 Stade 1 : Peu de décoloration visible",
        "sev_2": "🟠 Stade 2 : Décoloration visible modérée",
        "sev_3": "🔴 Stade 3 : Forte décoloration visible",
        "sev_note": "* La taille du cercle varie selon la sévérité de l'infection",
        "audit_header": "📑 Piste d'Audit de Télémétrie de Surveillance",
        "no_map_data": "Aucune télémétrie de scan régional n'a encore été enregistrée dans cette session.",
        "no_crop_match": "Aucune télémétrie enregistrée ne correspond au filtre de culture sélectionné.",
        "ai_title": "🤖 CropGuard AI — Assistant Expert Virtuel",
        "ai_subtitle": "Conseil Agronomique en Temps Réel & Consultation en Pathologie",
        "chat_header": "💬 Bureau de Discussion Agritech Interactif",
        "chat_info": "Posez une question sur les maladies des cultures, la santé des sols ou les ravageurs. Calibré pour {hub} en {lang}.",
        "chat_welcome": "Bonjour {user} ! Je suis votre assistant agronome virtuel CropGuard AI. Comment puis-je vous aider à optimiser la santé de vos cultures à {hub} aujourd'hui ?",
        "chat_input_ph": "Posez une question sur les maladies des cultures, les ravageurs...",
        "forum_title": "💬 Forum Communautaire Agricole Régional",
        "forum_subtitle": "Connectez-vous et collaborez avec les agriculteurs voisins à",
        "broadcast_header": "✍️ Diffuser aux Agriculteurs Locaux",
        "author_label": "Votre Nom / Nom de la Ferme :",
        "tag_label": "Étiquette de Sujet :",
        "msg_label": "Partagez une mise à jour, posez une question ou alertez...",
        "forum_media_label": "Ajouter une image ou une vidéo (facultatif)",
        "forum_media_help": "Partagez une image ou une vidéo avec votre communauté régionale. Images jusqu’à 15 Mo ; vidéos jusqu’à 50 Mo.",
        "forum_media_too_large": "Fichier trop volumineux. Les images doivent faire 15 Mo maximum et les vidéos 50 Mo maximum.",
        "forum_media_invalid": "Impossible de lire ce fichier comme image. Choisissez une image JPG, PNG ou WebP valide.",
        "forum_post_empty": "Ajoutez un message ou joignez une image/vidéo avant de partager.",
        "forum_media_name": "Pièce jointe",
        "share_btn": "📢 Partager avec la Communauté",
        "feed_header": "📰 Fil Communautaire en Direct",
        "post_posted_msg": "Votre message a été publié sur le fil régional !",
        "post_empty_msg": "Veuillez saisir un message avant d'envoyer.",
        "no_posts_msg": "Aucune publication pour le moment à {hub}. Soyez le premier à partager !",
        "diag_title": "🌱 CropGuard AI",
        "diag_subtitle": "Assistant Agritech Avancé par Vision par Ordinateur (Édition Mondiale)",
        "tour_btn": "Comment utiliser CropGuard",
        "crop_select_prompt": "Sélectionnez le type de culture cible :",
        "crop_select_header": "🌾 Contexte de la Culture",
        "upload_header": "📥 1.",
        "upload_label_text": "Téléchargez ou prenez une photo d'une feuille de culture affectée...",
        "analyze_btn": "Lancer l'Analyse Diagnostique",
        "results_header": "Résultats du Diagnostic",
        "treatment_header": "Gestion Agronomique & Répertoire Régional",
        "hub_support_header": "📍 Support du Hub et Répertoire d'Extension",
        "analysis_complete_msg": "Analyse de l’image terminée.",
        "crop_context_lbl": "Contexte de la Culture Cible :",
        "pattern_match_lbl": "Correspondance Principale :",
        "ai_conf_lbl": "Score du modèle (non calibré)",
        "ai_margin_lbl": "Écart avec la classe suivante (points de pourcentage)",
        "inf_sev_lbl": "Estimation de la décoloration visible",
        "prog_status_lbl": "Statut de Progression :",
        "stage3_alert": "La décoloration visible est importante. Consultez un conseiller agricole local avant tout traitement ou arrachage.",
        "stage2_alert": "La décoloration visible est modérée. Faites confirmer sa cause par un conseiller agricole avant tout traitement.",
        "stage1_alert": "La décoloration visible est limitée. Surveillez la plante et faites confirmer le diagnostic si les symptômes progressent.",
        "diagnosis_disclaimer": "Outil de dépistage uniquement : ce modèle a été entraîné sur des images PlantVillage et couvre le maïs, la pomme de terre et la tomate. Il peut être peu fiable sur des photos de terrain ou d’autres cultures. Le guide des maladies fournit des conseils de référence ; il n’ajoute pas de classes et ne réentraîne pas le modèle. La décoloration est une estimation visuelle, pas une mesure de la gravité de la maladie.",
        "unsupported_crop_msg": "Ce modèle ne peut pas diagnostiquer la culture sélectionnée. Il couvre uniquement le maïs, la pomme de terre et la tomate ; aucun diagnostic n’a été enregistré.",
        "low_confidence_msg": "Le modèle n’a pas identifié cette image avec une confiance suffisante. Reprenez une photo nette de la feuille ou consultez un conseiller agricole ; aucun diagnostic n’a été enregistré.",
        "healthy_class_msg": "Aucune classe de maladie n’a été identifiée pour cette culture. Ce dépistage ne prouve pas que la plante est saine.",
        "quality_block_title": "La qualité de l’image est trop faible pour un dépistage fiable.",
        "quality_retake": "Reprenez la photo avec une bonne mise au point et une lumière suffisante, en rapprochant la feuille ; évitez le zoom numérique.",
        "quality_review_title": "La qualité de l’image peut réduire la fiabilité du modèle.",
        "quality_metrics": "Contrôle qualité : {width}×{height}px · netteté {sharpness:.1f} · luminosité {brightness:.0f}/255 · contraste {contrast:.1f}.",
        "quality_confidence_caution": "Le contrôle qualité est heuristique, et non un modèle entraîné. Le score du modèle n’est pas calibré et ne représente pas la probabilité d’un diagnostic correct.",
        "hub_support_info": "Affichage des services de vulgarisation agricole vérifiés et des fournisseurs d'intrants correspondant à votre hub :",
        "diagnostic_empty_prompt": "👈 Sélectionnez votre région, choisissez votre culture, téléchargez une image sur la gauche et cliquez sur Lancer l'Analyse Diagnostique pour afficher les résultats ici.",
        "footer_text": "CropGuard AI — Network National de Surveillance Phytosanitaire & Réseau Agronomique Mondial"
    }
}

GPS_TEXT = {
    "English": {
        "gps_ok": "📍 Location found ({lat}, {lon}) → {hub}, {km} km from the hub centre.",
        "gps_global": "📍 Location found ({lat}, {lon}). No regional hub is within {max_km} km, so the Global / Universal Zone is selected.",
        "gps_denied": "Location access is blocked. Allow location for this site in your browser settings, then press Auto-Detect GPS again, or pick your region below.",
        "gps_insecure": "Location needs a secure connection. Open this app at an https:// address (or on localhost), then try again.",
        "gps_failed": "Your location could not be read. Turn on location services on your device and try again, or pick your region below.",
    },
    "Kiswahili": {
        "gps_ok": "📍 Eneo limepatikana ({lat}, {lon}) → {hub}, umbali wa km {km} kutoka katikati ya kituo.",
        "gps_global": "📍 Eneo limepatikana ({lat}, {lon}). Hakuna kituo cha kanda ndani ya km {max_km}, kwa hiyo Eneo la Kimataifa / Jumla limechaguliwa.",
        "gps_denied": "Ufikiaji wa eneo umezuiwa. Ruhusu eneo kwa tovuti hii kwenye mipangilio ya kivinjari chako, kisha bonyeza Auto-Detect GPS tena, au chagua eneo lako hapa chini.",
        "gps_insecure": "Utambuzi wa eneo unahitaji muunganisho salama. Fungua programu hii kwenye anwani ya https:// (au localhost), kisha ujaribu tena.",
        "gps_failed": "Eneo lako halikuweza kusomwa. Washa huduma za eneo kwenye kifaa chako kisha ujaribu tena, au chagua eneo lako hapa chini.",
    },
    "French": {
        "gps_ok": "📍 Position trouvée ({lat}, {lon}) → {hub}, à {km} km du centre du hub.",
        "gps_global": "📍 Position trouvée ({lat}, {lon}). Aucun hub régional à moins de {max_km} km : la Zone Mondiale / Universelle est sélectionnée.",
        "gps_denied": "L'accès à la position est bloqué. Autorisez la localisation pour ce site dans les paramètres du navigateur, puis appuyez de nouveau sur Auto-Detect GPS, ou choisissez votre région ci-dessous.",
        "gps_insecure": "La localisation nécessite une connexion sécurisée. Ouvrez cette application à une adresse https:// (ou sur localhost), puis réessayez.",
        "gps_failed": "Votre position n'a pas pu être lue. Activez la localisation sur votre appareil puis réessayez, ou choisissez votre région ci-dessous.",
    },
}
for _lang, _msgs in GPS_TEXT.items():
    if _lang in TRANSLATIONS:
        TRANSLATIONS[_lang].update(_msgs)

# --- EPI TEXT TRANSLATION MERGE ---
EPI_TEXT = {
    "English": {
        "sev_note": "* Circle size = number of reports; colour = average severity",
        "epi_period": "Reporting period",
        "epi_last_days": "Last {d} days",
        "epi_reports": "Reports",
        "epi_prev": "previous period",
        "epi_top": "Main threat",
        "epi_avg_sev": "Avg severity",
        "epi_col_reporters": "Farmers",
        "epi_col_prev": "Prev. period",
        "epi_col_last": "Last report",
        "epi_col_status": "Status",
        "epi_status_counted": "Counted",
        "epi_status_unverified": "Unverified label",
        "epi_status_demo": "Sample data",
        "epi_none_period": "No scans recorded in this period.",
        "epi_no_verified": "No verified crop-disease reports in this period.",
        "epi_q_counted": "{n} scans counted",
        "epi_q_unverified": "{n} excluded (unrecognised or low-confidence disease label)",
        "epi_q_demo": "{n} sample scans (never trigger alerts)",
        "epi_q_nogps": "{n} placed at hub centre (no GPS)",
        "epi_unmapped": "{n} reports from the Global Zone have no GPS position and are not drawn.",
        "epi_agg_header": "Reports by hub and disease",
    },
    "Kiswahili": {
        "sev_note": "* Ukubwa wa duara = idadi ya ripoti; rangi = wastani wa ukali",
        "epi_period": "Kipindi cha ripoti",
        "epi_last_days": "Siku {d} zilizopita",
        "epi_reports": "Ripoti",
        "epi_prev": "kipindi kilichotangulia",
        "epi_top": "Tishio kuu",
        "epi_avg_sev": "Wastani wa ukali",
        "epi_col_reporters": "Wakulima",
        "epi_col_prev": "Kipindi kilichopita",
        "epi_col_last": "Ripoti ya mwisho",
        "epi_col_status": "Hali",
        "epi_status_counted": "Imehesabiwa",
        "epi_status_unverified": "Jina la ugonjwa halijathibitishwa",
        "epi_status_demo": "Data ya mfano",
        "epi_none_period": "Hakuna uchunguzi uliorekodiwa katika kipindi hiki.",
        "epi_no_verified": "Hakuna ripoti zilizothibitishwa za magonjwa ya mimea katika kipindi hiki.",
        "epi_q_counted": "Uchunguzi {n} umehesabiwa",
        "epi_q_unverified": "{n} haukujumuishwa (jina la ugonjwa halitambuliki au uhakika ni mdogo)",
        "epi_q_demo": "Uchunguzi {n} wa mfano (hautoi tahadhari)",
        "epi_q_nogps": "{n} umewekwa katikati ya kituo (hakuna GPS)",
        "epi_unmapped": "Ripoti {n} za Eneo la Dunia hazina nafasi ya GPS na hazijachorwa.",
        "epi_agg_header": "Ripoti kwa kituo na ugonjwa",
    },
    "French": {
        "sev_note": "* Taille du cercle = nombre de rapports ; couleur = sévérité moyenne",
        "epi_period": "Période de rapport",
        "epi_last_days": "{d} derniers jours",
        "epi_reports": "Rapports",
        "epi_prev": "période précédente",
        "epi_top": "Menace principale",
        "epi_avg_sev": "Sévérité moyenne",
        "epi_col_reporters": "Agriculteurs",
        "epi_col_prev": "Période préc.",
        "epi_col_last": "Dernier rapport",
        "epi_col_status": "Statut",
        "epi_status_counted": "Comptabilisé",
        "epi_status_unverified": "Libellé non vérifié",
        "epi_status_demo": "Données d'exemple",
        "epi_none_period": "Aucun scan enregistré sur cette période.",
        "epi_no_verified": "Aucun rapport vérifié de maladie des cultures sur cette période.",
        "epi_q_counted": "{n} scans comptabilisés",
        "epi_q_unverified": "{n} exclus (libellé de maladie non reconnu ou confiance faible)",
        "epi_q_demo": "{n} scans d'exemple (ne déclenchent jamais d'alerte)",
        "epi_q_nogps": "{n} placés au centre du hub (pas de GPS)",
        "epi_unmapped": "{n} rapports de la Zone Mondiale n'ont pas de position GPS et ne sont pas affichés.",
        "epi_agg_header": "Rapports par hub et par maladie",
    },
}
for _lang, _msgs in EPI_TEXT.items():
    if _lang in TRANSLATIONS:
        TRANSLATIONS[_lang].update(_msgs)

# --- INTEGRITY MODULE INITIALIZATION ---
import data_integrity as di
for _lang, _msgs in di.INTEGRITY_TEXT.items():
    if _lang in TRANSLATIONS:
        TRANSLATIONS[_lang].update(_msgs)
di.init_registry()

GPS_AUTO_ON_LOAD = True
GPS_FALLBACK_HUB = "Global / Universal Zone"
GPS_MAX_HUB_KM = 1000

# --- B2G EPIDEMIOLOGICAL & FARMER HISTORY DATABASE ---
def init_epidemiological_db():
    conn = sqlite3.connect('cropguard_surveillance.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_type TEXT NOT NULL,
            identifier TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_telemetry (
            scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp TEXT NOT NULL,
            hub_region TEXT NOT NULL,
            target_crop TEXT NOT NULL,
            detected_disease TEXT NOT NULL,
            confidence_score REAL NOT NULL,
            severity_stage TEXT NOT NULL,
            severity_percentage REAL NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')

    cursor.execute("PRAGMA table_info(scan_telemetry)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'user_id' not in columns:
        try:
            cursor.execute("ALTER TABLE scan_telemetry ADD COLUMN user_id INTEGER;")
            conn.commit()
        except Exception as e:
            print(f"Migration notice: {e}")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regional_alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            hub_region TEXT NOT NULL,
            disease_name TEXT NOT NULL,
            threat_level TEXT NOT NULL,
            advisory_message TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS farmer_community_posts (
            post_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            hub_region TEXT NOT NULL,
            author_name TEXT NOT NULL,
            category_tag TEXT NOT NULL,
            message TEXT NOT NULL,
            media_name TEXT,
            media_type TEXT,
            media_data BLOB
        )
    ''')
    cursor.execute("PRAGMA table_info(farmer_community_posts)")
    community_post_columns = {column[1] for column in cursor.fetchall()}
    for column_name, column_type in (
        ("media_name", "TEXT"),
        ("media_type", "TEXT"),
        ("media_data", "BLOB"),
    ):
        if column_name not in community_post_columns:
            cursor.execute(
                f"ALTER TABLE farmer_community_posts ADD COLUMN {column_name} {column_type}"
            )
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO users (account_type, identifier, display_name, created_at)
            VALUES (?, ?, ?, ?)
        ''', ('Google', 'morara.emmanuel@cropguard.ai', 'Dr. Morara', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM scan_telemetry")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT user_id FROM users LIMIT 1")
        row_user = cursor.fetchone()
        default_uid = row_user[0] if row_user else 1
        
        sample_data = [
            (default_uid, "2026-10-08 08:30:00", "Kumasi, Ghana (Cocoa & Grain Belt)", "Cocoa", "Black Pod Blight", 94.5, "Stage 3: Severe / Terminal", 85.0),
            (default_uid, "2026-10-08 09:15:00", "Kumasi, Ghana (Cocoa & Grain Belt)", "Cocoa", "Black Pod Blight", 91.2, "Stage 2: Moderate / Spreading", 45.0),
            (default_uid, "2026-10-09 11:20:00", "Kisii, Kenya (Highland Zone)", "Mahindi (Maize)", "Fall Armyworm", 89.4, "Stage 2: Moderate / Spreading", 55.0),
            (default_uid, "2026-10-09 14:10:00", "Kisii, Kenya (Highland Zone)", "Mahindi (Maize)", "Fall Armyworm", 92.1, "Stage 3: Severe / Terminal", 82.0),
            (default_uid, "2026-10-10 07:45:00", "Ibadan, Nigeria (Agricultural Research & Maize Belt)", "Maize", "Mosaic Virus", 88.9, "Stage 2: Moderate / Spreading", 40.0),
        ]
        cursor.executemany('''
            INSERT INTO scan_telemetry (user_id, timestamp, hub_region, target_crop, detected_disease, confidence_score, severity_stage, severity_percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_data)
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM farmer_community_posts")
    if cursor.fetchone()[0] == 0:
        sample_posts = [
            ("2026-10-11 09:00", "Kisii, Kenya (Highland Zone)", "Mzee Juma", "🚨 Outbreak Alert", "Noticed early Fall Armyworm activity on maize stalks near Kenyenya. Inspect fields before evening rains!"),
            ("2026-10-11 11:30", "Kisii, Kenya (Highland Zone)", "Dr. Morara", "🌾 Crop Advice", "Applying copper-based fungicides early morning helps reduce spore germination during high humidity weeks."),
            ("2026-10-11 14:15", "Kumasi, Ghana (Cocoa & Grain Belt)", "Kwame Mensah", "🛒 Marketplace / Trade", "Looking for bulk organic nematicides delivered near Kumasi central hub. Reach out if available.")
        ]
        cursor.executemany('''
            INSERT INTO farmer_community_posts (timestamp, hub_region, author_name, category_tag, message)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_posts)
        conn.commit()
        
    conn.close()

# ==============================================================
# --- EPI LAYER: surveillance data handling + aggregated heatmap
# ==============================================================
EPI_DB_PATH = "cropguard_surveillance.db"
EPI_TS_FMT = "%Y-%m-%d %H:%M:%S"

EPI_WINDOW_DAYS = 14
EPI_BASELINE_WINDOWS = 4
EPI_MIN_CASES = 3
EPI_MIN_REPORTERS = 3
EPI_ALERT_TTL_DAYS = 14

EPI_MODEL_TAG = "mobilenetv2-plantvillage-38"
EPI_REQUIRE_KNOWN_LABEL = True
EPI_MIN_CONFIDENCE = 50.0
EPI_SHOW_DEMO_DATA = True

EPI_PERIOD_OPTIONS = [7, 30, 90, 365]
EPI_GRID_DEG = 0.1
EPI_COORD_DECIMALS = 2

EPI_KNOWN_LABELS = {
    "healthy",
    "apple scab", "cedar apple rust", "cercospora leaf spot gray leaf spot",
    "esca (black measles)", "leaf blight (isariopsis leaf spot)",
    "haunglongbing (citrus greening)", "leaf mold",
    "spider mites two-spotted spider mite", "target spot",
    "tomato mosaic virus", "tomato yellow leaf curl virus",
    "fall armyworm", "maize lethal necrosis", "maize streak virus", "gray leaf spot",
    "grey leaf spot", "northern leaf blight", "common rust", "mosaic virus",
    "stem rust", "yellow rust", "leaf rust", "septoria leaf spot",
    "late blight", "early blight", "bacterial wilt", "leaf curl virus",
    "bacterial spot", "tuta absoluta",
    "bean rust", "angular leaf spot", "anthracnose", "common bacterial blight",
    "groundnut rosette", "early leaf spot", "late leaf spot",
    "coffee leaf rust", "coffee berry disease", "blister blight",
    "black sigatoka", "banana xanthomonas wilt", "panama disease",
    "rice blast", "bacterial leaf blight", "brown spot",
    "cassava mosaic disease", "cassava brown streak disease", "cassava bacterial blight",
    "black pod blight", "cocoa swollen shoot virus",
    "black rot", "diamondback moth", "powdery mildew", "downy mildew", "leaf spot",
    "yam anthracnose",
}

EPI_CROP_CANON = {
    "mahindi (maize)": "Maize", "maize": "Maize",
    "viazi mviringo (irish potato)": "Irish potato", "irish potato": "Irish potato",
    "karanga (groundnuts)": "Groundnut", "groundnuts / peanuts": "Groundnut",
    "maharagwe (beans)": "Beans", "beans": "Beans", "common bean": "Beans",
    "chai (tea)": "Tea", "kahawa (coffee)": "Coffee",
    "ndizi (bananas)": "Banana", "plantain": "Plantain",
    "kales / sukuma wiki": "Kale", "chinsaka (spider plant)": "Spider plant",
    "managu (nightshade)": "African nightshade",
    "wheat (ngano)": "Wheat", "rice (mpunga)": "Rice",
    "cassava (mhogo)": "Cassava", "cassava": "Cassava",
    "tomatoes": "Tomato", "tomato": "Tomato", "cabbage": "Cabbage",
    "yam": "Yam", "cowpea": "Cowpea", "cocoa": "Cocoa",
    "mimea mingine / jumla": "Other / general", "other crop / general": "Other / general",
}

_EPI_DEMO_SEEDS = [
    ("2026-10-08 08:30:00", "Kumasi, Ghana (Cocoa & Grain Belt)", "Black Pod Blight"),
    ("2026-10-08 09:15:00", "Kumasi, Ghana (Cocoa & Grain Belt)", "Black Pod Blight"),
    ("2026-10-09 11:20:00", "Kisii, Kenya (Highland Zone)", "Fall Armyworm"),
    ("2026-10-09 14:10:00", "Kisii, Kenya (Highland Zone)", "Fall Armyworm"),
    ("2026-10-10 07:45:00", "Ibadan, Nigeria (Agricultural Research & Maize Belt)", "Mosaic Virus"),
]

_EPI_SCAN_COLUMNS = {
    "lat": "REAL",
    "lon": "REAL",
    "loc_source": "TEXT",
    "reporter_key": "TEXT",
    "crop_canon": "TEXT",
    "label_ok": "INTEGER",
    "is_demo": "INTEGER NOT NULL DEFAULT 0",
    "model_tag": "TEXT",
}

def _epi_conn(autocommit=False):
    conn = sqlite3.connect(EPI_DB_PATH, timeout=15, check_same_thread=False,
                           isolation_level=None if autocommit else "")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn

def _epi_norm(label):
    return re.sub(r"[\s_]+", " ", str(label or "").strip().lower())

def epi_canon_crop(raw):
    text = str(raw or "").strip()
    return EPI_CROP_CANON.get(text.lower(), text or "Other / general")

def epi_label_ok(label, confidence):
    if not EPI_REQUIRE_KNOWN_LABEL:
        return True
    try:
        conf = float(confidence)
    except (TypeError, ValueError):
        return False
    return _epi_norm(label) in EPI_KNOWN_LABELS and conf >= EPI_MIN_CONFIDENCE

def _epi_apply_label_rule(conn, only_unset=True):
    where = "WHERE label_ok IS NULL" if only_unset else ""
    if not EPI_REQUIRE_KNOWN_LABEL:
        conn.execute(f"UPDATE scan_telemetry SET label_ok = 1 {where}")
        return
    known = sorted(EPI_KNOWN_LABELS)
    marks = ",".join("?" * len(known))
    conn.execute(
        f"""UPDATE scan_telemetry SET label_ok = CASE
               WHEN lower(trim(replace(detected_disease, '_', ' '))) IN ({marks})
                AND confidence_score >= ? THEN 1 ELSE 0 END {where}""",
        (*known, EPI_MIN_CONFIDENCE),
    )

def ensure_epi_schema():
    conn = _epi_conn()
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        have = {r[1] for r in conn.execute("PRAGMA table_info(scan_telemetry)")}
        for col, ddl in _EPI_SCAN_COLUMNS.items():
            if col not in have:
                conn.execute(f"ALTER TABLE scan_telemetry ADD COLUMN {col} {ddl}")
        alert_cols = {r[1] for r in conn.execute("PRAGMA table_info(regional_alerts)")}
        if "expires_at" not in alert_cols:
            conn.execute("ALTER TABLE regional_alerts ADD COLUMN expires_at TEXT")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_ts ON scan_telemetry(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_hub_dis_ts "
                     "ON scan_telemetry(hub_region, detected_disease, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scan_user ON scan_telemetry(user_id, scan_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_lookup "
                     "ON regional_alerts(hub_region, disease_name, timestamp)")

        conn.executemany(
            "UPDATE scan_telemetry SET is_demo = 1 "
            "WHERE timestamp = ? AND hub_region = ? AND detected_disease = ?", _EPI_DEMO_SEEDS)
        conn.execute("UPDATE scan_telemetry SET reporter_key = 'u' || user_id WHERE reporter_key IS NULL")
        for (raw,) in conn.execute(
                "SELECT DISTINCT target_crop FROM scan_telemetry WHERE crop_canon IS NULL").fetchall():
            conn.execute("UPDATE scan_telemetry SET crop_canon = ? "
                         "WHERE target_crop = ? AND crop_canon IS NULL", (epi_canon_crop(raw), raw))
        _epi_apply_label_rule(conn, only_unset=True)
        conn.commit()
    finally:
        conn.close()

def epi_reporter_key():
    authed = bool(st.user.get("is_logged_in", False))
    if authed or st.session_state.get("auth_method") == "Phone OTP":
        return f"u{st.session_state.get('logged_in_user_id', 1)}"
    if "epi_anon_id" not in st.session_state:
        st.session_state["epi_anon_id"] = uuid.uuid4().hex[:12]
    return f"a{st.session_state['epi_anon_id']}"

def epi_scan_location(hub_label):
    gs = st.session_state.get("gps_status") or {}
    kind = gs.get("kind")
    if (kind == "ok" and gs.get("hub") == hub_label) or (kind == "global" and hub_label == GPS_FALLBACK_HUB):
        try:
            return {"lat": round(float(gs["lat"]), EPI_COORD_DECIMALS),
                    "lon": round(float(gs["lon"]), EPI_COORD_DECIMALS),
                    "loc_source": "gps"}
        except (KeyError, TypeError, ValueError):
            pass
    return {"lat": None, "lon": None, "loc_source": "manual"}

def _epi_clear_caches():
    get_active_regional_alerts.clear()
    get_government_epidemiological_summary.clear()
    epi_registry_stats.clear()
    epi_map_points.clear()
    epi_crop_options.clear()
    epi_quality_counts.clear()
    epi_recent_rows.clear()

def log_scan_telemetry(hub_region, target_crop, disease_name, confidence, severity_stage, severity_pct,
                       lat=None, lon=None, loc_source="manual"):
    label_ok = epi_label_ok(disease_name, confidence)
    conn = None
    try:
        conn = _epi_conn()
        conn.execute(
            """INSERT INTO scan_telemetry
               (user_id, timestamp, hub_region, target_crop, detected_disease, confidence_score,
                severity_stage, severity_percentage, lat, lon, loc_source, reporter_key,
                crop_canon, label_ok, is_demo, model_tag)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (st.session_state.get("logged_in_user_id", 1), datetime.now().strftime(EPI_TS_FMT),
             hub_region, target_crop, disease_name, confidence, severity_stage, severity_pct,
             lat, lon, loc_source, epi_reporter_key(), epi_canon_crop(target_crop),
             1 if label_ok else 0, EPI_MODEL_TAG),
        )
        conn.commit()
    except Exception as e:
        print(f"Telemetry logging error: {e}")
        return False
    finally:
        if conn is not None:
            conn.close()
    _epi_clear_caches()
    if label_ok:
        try:
            evaluate_outbreak_cluster(hub_region, disease_name)
        except Exception as e:
            print(f"Outbreak evaluation error: {e}")
    return True

def evaluate_outbreak_cluster(hub_region, disease_name, now=None):
    if hub_region == GPS_FALLBACK_HUB or _epi_norm(disease_name) == "healthy":
        return False
    now = now or datetime.now()
    t_now = now.strftime(EPI_TS_FMT)
    t_recent = (now - timedelta(days=EPI_WINDOW_DAYS)).strftime(EPI_TS_FMT)
    t_base = (now - timedelta(days=EPI_WINDOW_DAYS * (1 + EPI_BASELINE_WINDOWS))).strftime(EPI_TS_FMT)
    conn = _epi_conn(autocommit=True)
    try:
        conn.execute("BEGIN IMMEDIATE")
        n_recent, reporters, n_base = conn.execute(
            """SELECT COALESCE(SUM(timestamp >= :r), 0),
                      COUNT(DISTINCT CASE WHEN timestamp >= :r
                                          THEN COALESCE(reporter_key, 'u' || user_id) END),
                      COALESCE(SUM(timestamp < :r), 0)
               FROM scan_telemetry
               WHERE hub_region = :h AND detected_disease = :d AND label_ok = 1 AND is_demo = 0
                 AND timestamp >= :b AND timestamp <= :n""",
            {"r": t_recent, "h": hub_region, "d": disease_name, "b": t_base, "n": t_now},
        ).fetchone()
        baseline = n_base / EPI_BASELINE_WINDOWS
        threshold = max(EPI_MIN_CASES, math.ceil(baseline + 2 * math.sqrt(baseline)))
        if n_recent < threshold or reporters < EPI_MIN_REPORTERS:
            conn.execute("COMMIT")
            return False
        still_open = conn.execute(
            """SELECT 1 FROM regional_alerts
               WHERE hub_region = ? AND disease_name = ? AND threat_level = 'CRITICAL OUTBREAK'
                 AND COALESCE(expires_at, datetime(timestamp, ?)) > ? LIMIT 1""",
            (hub_region, disease_name, f"+{EPI_ALERT_TTL_DAYS} days", t_now),
        ).fetchone()
        if still_open:
            conn.execute("COMMIT")
            return False
        advisory = (f"CRITICAL SURGE: {n_recent} reports of {disease_name} from {reporters} farmers in "
                    f"{hub_region} in the last {EPI_WINDOW_DAYS} days (normal level about {baseline:.1f}). "
                    f"Immediate preventative containment advised.")
        conn.execute(
            """INSERT INTO regional_alerts
               (timestamp, hub_region, disease_name, threat_level, advisory_message, expires_at)
               VALUES (?, ?, ?, 'CRITICAL OUTBREAK', ?, ?)""",
            (t_now, hub_region, disease_name, advisory,
             (now + timedelta(days=EPI_ALERT_TTL_DAYS)).strftime(EPI_TS_FMT)),
        )
        conn.execute("COMMIT")
        return True
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()

@st.cache_data(ttl=30, show_spinner=False)
def get_active_regional_alerts(hub_region):
    conn = _epi_conn()
    try:
        return conn.execute(
            """SELECT timestamp, disease_name, advisory_message FROM regional_alerts
               WHERE hub_region = ? AND threat_level = 'CRITICAL OUTBREAK'
                 AND COALESCE(expires_at, datetime(timestamp, ?)) > ?
               ORDER BY alert_id DESC LIMIT 3""",
            (hub_region, f"+{EPI_ALERT_TTL_DAYS} days", datetime.now().strftime(EPI_TS_FMT)),
        ).fetchall()
    finally:
        conn.close()

@st.cache_data(ttl=60, show_spinner=False)
def get_government_epidemiological_summary(days=30):
    since = (datetime.now() - timedelta(days=days)).strftime(EPI_TS_FMT)
    conn = _epi_conn()
    try:
        return conn.execute(
            """SELECT hub_region, detected_disease, COUNT(*) AS freq, AVG(severity_percentage)
               FROM scan_telemetry
               WHERE timestamp >= ? AND label_ok = 1 AND (is_demo = 0 OR ?)
                 AND lower(detected_disease) <> 'healthy'
               GROUP BY hub_region, detected_disease ORDER BY freq DESC""",
            (since, 1 if EPI_SHOW_DEMO_DATA else 0),
        ).fetchall()
    finally:
        conn.close()

@st.cache_data(ttl=60, show_spinner=False)
def epi_registry_stats():
    return di.registry_stats()

@st.cache_data(ttl=60, show_spinner=False)
def epi_map_points(days, crop, include_demo):
    now = datetime.now()
    params = {
        "g": EPI_GRID_DEG, "demo": 1 if include_demo else 0, "crop": crop,
        "t1": (now - timedelta(days=days)).strftime(EPI_TS_FMT),
        "t0": (now - timedelta(days=2 * days)).strftime(EPI_TS_FMT),
    }
    sql = """
        SELECT hub_region,
               CAST(ROUND(lat / :g) AS INTEGER) AS ilat,
               CAST(ROUND(lon / :g) AS INTEGER) AS ilon,
               detected_disease AS disease,
               SUM(timestamp >= :t1) AS n,
               SUM(timestamp <  :t1) AS n_prev,
               COUNT(DISTINCT CASE WHEN timestamp >= :t1
                                   THEN COALESCE(reporter_key, 'u' || user_id) END) AS reporters,
               AVG(CASE WHEN timestamp >= :t1 THEN severity_percentage END) AS avg_sev,
               MAX(timestamp) AS last_seen
        FROM scan_telemetry
        WHERE timestamp >= :t0 AND label_ok = 1
          AND lower(detected_disease) <> 'healthy'
          AND (is_demo = 0 OR :demo = 1)
          AND (:crop IS NULL OR crop_canon = :crop)
        GROUP BY hub_region, ilat, ilon, detected_disease
        HAVING n > 0"""
    conn = _epi_conn()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()

@st.cache_data(ttl=60, show_spinner=False)
def epi_crop_options(days, include_demo):
    since = (datetime.now() - timedelta(days=days)).strftime(EPI_TS_FMT)
    conn = _epi_conn()
    try:
        rows = conn.execute(
            """SELECT DISTINCT crop_canon FROM scan_telemetry
               WHERE timestamp >= ? AND label_ok = 1 AND (is_demo = 0 OR ?) AND crop_canon IS NOT NULL
               ORDER BY crop_canon""", (since, 1 if include_demo else 0)).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()

@st.cache_data(ttl=60, show_spinner=False)
def epi_quality_counts(days, include_demo):
    since = (datetime.now() - timedelta(days=days)).strftime(EPI_TS_FMT)
    conn = _epi_conn()
    try:
        row = conn.execute(
            """SELECT COUNT(*),
                      COALESCE(SUM(label_ok = 1 AND (is_demo = 0 OR :demo = 1)), 0),
                      COALESCE(SUM(is_demo = 1), 0),
                      COALESCE(SUM(COALESCE(label_ok, 0) = 0 AND is_demo = 0), 0),
                      COALESCE(SUM(label_ok = 1 AND lat IS NULL AND (is_demo = 0 OR :demo = 1)), 0)
               FROM scan_telemetry WHERE timestamp >= :since""",
            {"demo": 1 if include_demo else 0, "since": since}).fetchone()
        return dict(zip(("total", "counted", "demo", "unverified", "no_gps"), row))
    finally:
        conn.close()

@st.cache_data(ttl=30, show_spinner=False)
def epi_recent_rows(limit=200):
    conn = _epi_conn()
    try:
        return pd.read_sql_query(
            """SELECT timestamp, hub_region, COALESCE(crop_canon, target_crop) AS crop,
                      detected_disease, confidence_score, severity_percentage,
                      CASE WHEN is_demo = 1 THEN 'demo'
                           WHEN COALESCE(label_ok, 0) = 1 THEN 'counted'
                           ELSE 'unverified' END AS status
               FROM scan_telemetry ORDER BY scan_id DESC LIMIT ?""", conn, params=(limit,))
    finally:
        conn.close()

def _epi_severity_color(sev):
    if sev > 70:
        return [211, 47, 47, 220]
    if sev > 40:
        return [245, 124, 0, 220]
    return [56, 142, 60, 220]

def epi_build_bubbles(df):
    if df is None or df.empty:
        return pd.DataFrame(), 0
    d = df.copy()
    for c in ("ilat", "ilon", "n", "n_prev", "avg_sev"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    hub_lat = pd.to_numeric(d["hub_region"].map(lambda h: GLOBAL_AGRICULTURAL_HUBS.get(h, {}).get("lat")), errors="coerce")
    hub_lon = pd.to_numeric(d["hub_region"].map(lambda h: GLOBAL_AGRICULTURAL_HUBS.get(h, {}).get("lon")), errors="coerce")
    d["lat"] = (d["ilat"] * EPI_GRID_DEG).fillna(hub_lat)
    d["lon"] = (d["ilon"] * EPI_GRID_DEG).fillna(hub_lon)
    no_pos = d["ilat"].isna() & (d["hub_region"] == GPS_FALLBACK_HUB)
    unmapped = int(d.loc[no_pos, "n"].sum())
    d = d[~no_pos & d["lat"].notna() & d["lon"].notna()].copy()
    if d.empty:
        return pd.DataFrame(), unmapped
    d["w"] = d["avg_sev"].fillna(0) * d["n"]
    keys = ["hub_region", "lat", "lon"]
    g = d.groupby(keys, as_index=False).agg(
        n=("n", "sum"), n_prev=("n_prev", "sum"), w=("w", "sum"), last_seen=("last_seen", "max"))
    top = (d.sort_values("n", ascending=False).drop_duplicates(keys)[keys + ["disease"]]
           .rename(columns={"disease": "top_disease"}))
    g = g.merge(top, on=keys, how="left")
    g["n"] = g["n"].astype(int)
    g["n_prev"] = g["n_prev"].astype(int)
    g["avg_sev"] = (g["w"] / g["n"]).round(0).astype(int)
    g["hub"] = g["hub_region"]
    g["color"] = g["avg_sev"].apply(_epi_severity_color)
    g["radius_px"] = g["n"].apply(lambda n: min(48.0, 8.0 + 6.0 * math.sqrt(n)))
    return g.drop(columns=["w"]), unmapped

def _epi_fit_view(lats, lons):
    span = max(max(lats) - min(lats), max(lons) - min(lons), 0.5)
    zoom = max(2.0, min(7.0, math.log2(560.0 / (span * 1.4))))
    return pdk.ViewState(latitude=(min(lats) + max(lats)) / 2, longitude=(min(lons) + max(lons)) / 2,
                         zoom=zoom, pitch=0)

def _epi_legend(T):
    sev_key = T.get("sev_key_title", "🗺️ Outbreak Severity Key:")
    s1 = T.get("sev_1", "🟢 Stage 1: Mild (<40% severity)")
    s2 = T.get("sev_2", "🟠 Stage 2: Moderate (40% - 70% severity)")
    s3 = T.get("sev_3", "🔴 Stage 3: Terminal (>70% severity)")
    sev_note = T.get("sev_note", "* Circle size scales with infection severity")
    st.markdown(f"""
    <style>
    .severity-key-card {{
        background-color: #1E4620 !important; border: 2px solid #76FF03 !important;
        border-radius: 12px; padding: 16px 24px; margin: 20px 0;
        box-shadow: 0 6px 20px rgba(0,0,0,0.8);
    }}
    .severity-key-card * {{ color: #FFFFFF !important; text-shadow: 1px 1px 3px #000000 !important; }}
    .severity-legend-note {{ color: #76FF03 !important; }}
    </style>
    <div class="severity-key-card" style="display:flex; align-items:center; justify-content:space-around; flex-wrap:wrap; gap:14px;">
        <span style="font-weight:800; font-size:1.1rem;">{sev_key}</span>
        <span style="font-weight:700; font-size:1rem;">{s1}</span>
        <span style="font-weight:700; font-size:1rem;">{s2}</span>
        <span style="font-weight:700; font-size:1rem;">{s3}</span>
        <span class="severity-legend-note" style="font-size:0.95rem; font-style:italic; font-weight:600;">{sev_note}</span>
    </div>""", unsafe_allow_html=True)

def epi_render_heatmap(T):
    col_a, col_b = st.columns(2)
    period_label = T.get("epi_period", "Reporting period")
    last_days_fmt = T.get("epi_last_days", "Last {d} days")
    filter_crop_lbl = T.get("filter_crop", "Filter Heatmap by Crop Category:")
    all_crops_lbl = T.get("all_crops_opt", "All Crops")

    days = col_a.selectbox(period_label, EPI_PERIOD_OPTIONS, index=1,
                           format_func=lambda d: last_days_fmt.format(d=d))
    crop_opts = epi_crop_options(days, EPI_SHOW_DEMO_DATA)
    choice = col_b.selectbox(filter_crop_lbl, [all_crops_lbl] + crop_opts)
    crop = None if choice == all_crops_lbl else choice

    q = epi_quality_counts(days, EPI_SHOW_DEMO_DATA)
    if q["total"] == 0:
        st.info(T.get("epi_none_period", "No scans recorded in this period."))
        return
    parts = [T.get("epi_q_counted", "{n} scans counted").format(n=q["counted"])]
    for key, tkey in (("unverified", "epi_q_unverified"), ("demo", "epi_q_demo"), ("no_gps", "epi_q_nogps")):
        if q[key]:
            parts.append(T.get(tkey, "{n}").format(n=q[key]))
    st.caption(" · ".join(parts))

    points = epi_map_points(days, crop, EPI_SHOW_DEMO_DATA)
    bubbles, unmapped = epi_build_bubbles(points)
    if bubbles.empty:
        st.warning(T.get("no_crop_match", "No recorded telemetry matches the selected crop filter.") if crop else T.get("epi_no_verified", "No verified crop-disease reports in this period."))
        if unmapped:
            st.caption(T.get("epi_unmapped", "{n} reports unmapped").format(n=unmapped))
        return

    now_n, prev_n = int(bubbles["n"].sum()), int(bubbles["n_prev"].sum())
    m1, m2 = st.columns(2)
    reports_lbl = T.get("epi_reports", "Reports")
    top_threat_lbl = T.get("epi_top", "Main threat")
    m1.metric(reports_lbl, now_n, delta=now_n - prev_n, delta_color="inverse")
    m2.metric(top_threat_lbl, str(bubbles.sort_values("n", ascending=False).iloc[0]["top_disease"]))

    _epi_legend(T)

    layer = pdk.Layer(
        "ScatterplotLayer", data=bubbles,
        get_position=["lon", "lat"], get_radius="radius_px", radius_units="pixels",
        get_fill_color="color", get_line_color=[255, 255, 255, 200],
        stroked=True, line_width_min_pixels=1, opacity=0.85,
        pickable=True, auto_highlight=True)
    
    prev_lbl = T.get("epi_prev", "previous period")
    avg_sev_lbl = T.get("epi_avg_sev", "Avg severity")
    tooltip = {"text": ("{hub}\n" + reports_lbl + ": {n} (" + prev_lbl + ": {n_prev})\n"
                        + top_threat_lbl + ": {top_disease}\n" + avg_sev_lbl + ": {avg_sev}%")}
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=_epi_fit_view(list(bubbles["lat"]), list(bubbles["lon"])),
                             map_style="dark", tooltip=tooltip))
    if unmapped:
        st.caption(T.get("epi_unmapped", "{n} reports unmapped").format(n=unmapped))

    st.markdown(f"### {T.get('epi_agg_header', 'Reports by hub and disease')}")
    table = points.sort_values("n", ascending=False)[
        ["hub_region", "disease", "n", "reporters", "n_prev", "avg_sev", "last_seen"]].copy()
    table["avg_sev"] = table["avg_sev"].round(1)
    table.columns = [T.get("col_hub", "Hub Region"), T.get("col_disease", "Detected Disease"), reports_lbl, T.get("epi_col_reporters", "Farmers"),
                     T.get("epi_col_prev", "Prev. period"), T.get("col_sev_pct", "Severity (%)"), T.get("epi_col_last", "Last report")]
    st.dataframe(table, use_container_width=True, hide_index=True)

    with st.expander(T.get("audit_header", "📑 Telemetry Surveillance Audit Trail")):
        raw = epi_recent_rows(200)
        if not raw.empty:
            raw["status"] = raw["status"].map({"counted": T.get("epi_status_counted", "Counted"),
                                               "unverified": T.get("epi_status_unverified", "Unverified label"),
                                               "demo": T.get("epi_status_demo", "Sample data")})
            raw["confidence_score"] = raw["confidence_score"].round(1)
            raw["severity_percentage"] = raw["severity_percentage"].round(1)
            raw.columns = [T.get("col_time", "Timestamp"), T.get("col_hub", "Hub Region"), T.get("col_crop", "Crop"), T.get("col_disease", "Detected Disease"),
                           T.get("col_conf", "Confidence (%)"), T.get("col_sev_pct", "Severity (%)"), T.get("epi_col_status", "Status")]
            st.dataframe(raw, use_container_width=True, hide_index=True)

@st.cache_resource(show_spinner=False)
def _epi_bootstrap():
    init_epidemiological_db()
    ensure_epi_schema()
    return True

_epi_bootstrap()

if 'logged_in_user_id' not in st.session_state:
    st.session_state['logged_in_user_id'] = 1
    st.session_state['user_identifier'] = 'morara.emmanuel@cropguard.ai'
    st.session_state['user_display_name'] = 'Dr. Morara'
    st.session_state['auth_method'] = 'Google'

if 'selected_hub_label' not in st.session_state:
    st.session_state['selected_hub_label'] = "Kisii, Kenya (Highland Zone)"

if 'selected_language' not in st.session_state:
    st.session_state['selected_language'] = "English"

@st.cache_resource
def load_vision_model():
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.onnx")
    return ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

session = load_vision_model()

def load_vision_labels():
    labels_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plant_disease_labels.txt")
    with open(labels_path, encoding="utf-8") as labels_file:
        labels = [line.strip() for line in labels_file if line.strip()]
    if len(labels) != 38:
        raise ValueError(f"Expected 38 plant-disease labels, found {len(labels)}.")
    return labels

plant_disease_labels = load_vision_labels()

def supported_class_indices(crop_name):
    crop = str(crop_name).casefold()
    if "maize" in crop or "corn" in crop or "mahindi" in crop:
        crop_prefix = "Corn_(maize)___"
    elif "potato" in crop or "viazi" in crop:
        crop_prefix = "Potato___"
    elif "tomato" in crop:
        crop_prefix = "Tomato___"
    else:
        return []
    return [
        index for index, label in enumerate(plant_disease_labels)
        if label.startswith(crop_prefix)
    ]

def split_plant_disease_label(label):
    crop, _, condition = label.partition("___")
    crop = crop.replace("_(including_sour)", "").replace("_(maize)", " (Maize)")
    crop = crop.replace(",_bell", "").replace("_", " ").strip()
    condition = condition.replace("_", " ").strip()
    if condition.casefold() == "healthy":
        return crop, None
    return crop, condition

def _normalize_guide_text(value):
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()

def _guide_crop_family(crop_name):
    normalized_crop = f" {_normalize_guide_text(crop_name)} "
    matching_families = []
    for family, crop_info in disease_guide_data.CROP_FAMILIES.items():
        synonyms = crop_info[3]
        for synonym in synonyms:
            normalized_synonym = _normalize_guide_text(synonym)
            if normalized_synonym and f" {normalized_synonym} " in normalized_crop:
                matching_families.append((len(normalized_synonym), family))
    return max(matching_families)[1] if matching_families else None

def find_disease_guide_key(crop_name, disease_name):
    family = _guide_crop_family(crop_name)
    normalized_disease = _normalize_guide_text(disease_name)
    if not family or not normalized_disease:
        return None

    matches = []
    padded_disease = f" {normalized_disease} "
    for key, entry in disease_guide_data.DISEASES.items():
        if entry["crops"] and family not in entry["crops"]:
            continue
        variants = [entry["epi"], *entry["name"], *entry["alias"]]
        for variant in variants:
            normalized_variant = _normalize_guide_text(variant)
            if len(normalized_variant) < 4:
                continue
            if normalized_variant == normalized_disease:
                score = 10000 + len(normalized_variant)
            elif f" {normalized_variant} " in padded_disease:
                score = 1000 + len(normalized_variant)
            elif padded_disease in f" {normalized_variant} ":
                score = 500 + len(normalized_disease)
            else:
                continue
            matches.append((score, key))
    return max(matches)[1] if matches else None

def render_disease_guide(guide_key, crop_name, language, severity_stage):
    entry = disease_guide_data.DISEASES.get(guide_key)
    if not entry:
        return

    lang_index = {"English": 0, "Kiswahili": 1, "French": 2}.get(language, 0)
    labels = {
        "English": {
            "title": "🌿 Disease reference guide",
            "signs": "Common signs",
            "now": "What to do now",
            "cult": "Field practices",
            "bio": "Biological options",
            "chem": "Chemical options",
            "prev": "Prevention",
            "severe": "Severe cases",
            "caution": "Follow local product labels and regulations; confirm diagnosis and treatment with an agricultural extension officer.",
        },
        "Kiswahili": {
            "title": "🌿 Mwongozo wa rejea ya ugonjwa",
            "signs": "Dalili za kawaida",
            "now": "Hatua za kuchukua sasa",
            "cult": "Mbinu za shambani",
            "bio": "Chaguo za kibayolojia",
            "chem": "Chaguo za kemikali",
            "prev": "Kinga",
            "severe": "Hali kali",
            "caution": "Fuata lebo na kanuni za bidhaa za eneo lako; thibitisha utambuzi na matibabu kwa afisa wa ugani wa kilimo.",
        },
        "French": {
            "title": "🌿 Guide de référence sur la maladie",
            "signs": "Signes fréquents",
            "now": "Mesures immédiates",
            "cult": "Pratiques culturales",
            "bio": "Options biologiques",
            "chem": "Options chimiques",
            "prev": "Prévention",
            "severe": "Cas graves",
            "caution": "Respectez les étiquettes et règles locales ; faites confirmer le diagnostic et le traitement par un conseiller agricole.",
        },
    }[language if language in ("English", "Kiswahili", "French") else "English"]

    st.markdown(f"#### {labels['title']}")
    st.markdown(f"**{entry['name'][lang_index]}**")
    st.markdown(f"**{labels['signs']}:** {entry['signs'][lang_index]}")

    sections = [
        ("now", "now"),
        ("cult", "cult"),
        ("bio", "bio"),
        ("chem", "chem"),
        ("prev", "prev"),
    ]
    if severity_stage.startswith("Stage 3"):
        sections.append(("severe", "severe"))

    family = _guide_crop_family(crop_name)
    family_actions = entry.get("extra", {}).get(family, {})
    shown_any = False
    for section_key, label_key in sections:
        codes = list(entry.get(section_key, []))
        codes.extend(family_actions.get(section_key, []))
        sentences = list(dict.fromkeys(
            disease_guide_data.ACTIONS[code][lang_index]
            for code in codes
            if code in disease_guide_data.ACTIONS
        ))
        if sentences:
            shown_any = True
            st.markdown(f"**{labels[label_key]}**")
            st.markdown("\n".join(f"- {sentence}" for sentence in sentences))
            if section_key == "chem":
                st.caption(labels["caution"])
    if entry.get("report") and not shown_any:
        st.caption(labels["caution"])

def assess_image_quality(image):
    width, height = image.size
    scale = min(1.0, 512 / max(width, height))
    sample_size = (max(3, round(width * scale)), max(3, round(height * scale)))
    grayscale = np.asarray(
        image.convert("L").resize(sample_size, Image.Resampling.BILINEAR),
        dtype=np.float32,
    )
    brightness = float(np.mean(grayscale))
    contrast = float(np.std(grayscale))
    laplacian = (
        grayscale[:-2, 1:-1]
        + grayscale[2:, 1:-1]
        + grayscale[1:-1, :-2]
        + grayscale[1:-1, 2:]
        - 4 * grayscale[1:-1, 1:-1]
    )
    sharpness = float(np.var(laplacian))

    blocked_reasons = []
    review_reasons = []
    short_side = min(width, height)
    if short_side < 128:
        blocked_reasons.append("resolution")
    elif short_side < 256:
        review_reasons.append("resolution")
    if sharpness < 4.5:
        blocked_reasons.append("blur")
    elif sharpness < 30:
        review_reasons.append("blur")
    if brightness < 3 or brightness > 252:
        blocked_reasons.append("exposure")
    elif brightness < 25 or brightness > 230:
        review_reasons.append("exposure")
    if contrast < 12:
        review_reasons.append("contrast")

    return {
        "width": width,
        "height": height,
        "sharpness": sharpness,
        "brightness": brightness,
        "contrast": contrast,
        "blocked": bool(blocked_reasons),
        "blocked_reasons": blocked_reasons,
        "review_reasons": review_reasons,
    }

def render_image_quality_feedback(quality, translations):
    st.caption(translations["quality_metrics"].format(**quality))
    if quality["blocked"]:
        st.error(translations["quality_block_title"])
        st.caption(translations["quality_retake"])
    elif quality["review_reasons"]:
        st.warning(translations["quality_review_title"])
        st.caption(translations["quality_retake"])

def analyze_leaf_severity(image):
    img_resized = image.resize((150, 150))
    img_np = np.asarray(img_resized)
    
    if img_np.ndim == 2:
        img_np = np.stack((img_np,)*3, axis=-1)
    elif img_np.shape[2] == 4:
        img_np = img_np[:, :, :3]
        
    rgb = img_np.astype(np.float32) / 255.0
    red, green, blue = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    value = np.max(rgb, axis=2)
    minimum = np.min(rgb, axis=2)
    delta = value - minimum

    hue = np.zeros_like(value)
    non_gray = delta > 0
    red_max = non_gray & (value == red)
    green_max = non_gray & (value == green)
    blue_max = non_gray & (value == blue)
    hue[red_max] = ((green[red_max] - blue[red_max]) / delta[red_max]) % 6
    hue[green_max] = ((blue[green_max] - red[green_max]) / delta[green_max]) + 2
    hue[blue_max] = ((red[blue_max] - green[blue_max]) / delta[blue_max]) + 4
    hue = hue * 30
    saturation = np.divide(delta, value, out=np.zeros_like(delta), where=value > 0)
    
    green_mask = (hue >= 25) & (hue <= 85) & (saturation > 0.2) & (value > 0.2)
    total_pixels = green_mask.size
    healthy_pixels = np.sum(green_mask)
    diseased_pixels = total_pixels - healthy_pixels
    
    severity_ratio = (diseased_pixels / total_pixels) * 100
    severity_percentage = float(np.clip(severity_ratio, 8.0, 92.0))
    
    if severity_percentage < 40:
        stage = "Stage 1: Early / Localized (Mild)"
    elif severity_percentage <= 70:
        stage = "Stage 2: Moderate / Spreading"
    else:
        stage = "Stage 3: Severe / Terminal"
        
    return stage, severity_percentage

def render_tts_audio_controls(text_to_speak, lang_code):
    clean_text = text_to_speak.replace('"', '\\"').replace('\n', '. ')
    js_code = f"""
    <div style="margin: 15px 0; display: flex; gap: 10px;">
        <button id="playPauseBtn" onclick="togglePlayPause()" style="flex: 2; background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%); color: white; border: none; padding: 0.6rem 1rem; border-radius: 8px; font-weight: bold; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; gap: 6px; font-size: 0.95rem;">
            🔊 Play Audio Summary
        </button>
        <button onclick="stopAudio()" style="flex: 1; background: #D32F2F; color: white; border: none; padding: 0.6rem 1rem; border-radius: 8px; font-weight: bold; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; gap: 6px; font-size: 0.95rem;">
            ⏹ Stop
        </button>
    </div>
    <script>
        let isPlaying = false;
        let isPaused = false;

        function togglePlayPause() {{
            const btn = document.getElementById('playPauseBtn');
            if (!('speechSynthesis' in window)) {{
                alert("Speech synthesis is not supported on this browser.");
                return;
            }}

            if (!isPlaying && !isPaused) {{
                window.speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance("{clean_text}");
                utterance.lang = "{lang_code}";
                utterance.rate = 0.92;
                
                utterance.onend = function() {{
                    isPlaying = false;
                    isPaused = false;
                    btn.innerHTML = "🔊 Play Audio Summary";
                }};

                window.speechSynthesis.speak(utterance);
                isPlaying = true;
                isPaused = false;
                btn.innerHTML = "⏸ Pause";
            }} else if (isPlaying && !isPaused) {{
                window.speechSynthesis.pause();
                isPaused = true;
                isPlaying = false;
                btn.innerHTML = "▶ Resume";
            }} else if (!isPlaying && isPaused) {{
                window.speechSynthesis.resume();
                isPaused = false;
                isPlaying = true;
                btn.innerHTML = "⏸ Pause";
            }}
        }}

        function stopAudio() {{
            if ('speechSynthesis' in window) {{
                window.speechSynthesis.cancel();
                isPlaying = false;
                isPaused = false;
                const btn = document.getElementById('playPauseBtn');
                if (btn) btn.innerHTML = "🔊 Play Audio Summary";
            }}
        }}
    </script>
    """
    components.html(js_code, height=65)

def render_guided_tour(lang_name, force_start=False):
    if lang_name == "Kiswahili":
        steps = [
            {"selector": "#tour-target-hub", "title": "Chagua eneo", "text": "Chagua eneo la shamba lako. Unaweza pia kutumia utambuzi wa eneo."},
            {"selector": "#tour-target-crop", "title": "Chagua zao", "text": "Chagua aina ya zao unalotaka kuchunguza."},
            {"selector": "#tour-target-upload", "title": "Pakia picha ya jani", "text": "Pakia picha iliyo wazi ya jani, kisha uanze uchunguzi."},
            {"selector": "#tour-target-results", "title": "Angalia matokeo", "text": "Baada ya uchunguzi, utapata ugonjwa uliotambuliwa na ushauri."}
        ]
    elif lang_name == "French":
        steps = [
            {"selector": "#tour-target-hub", "title": "Choisir une région", "text": "Choisissez la région de votre ferme ou utilisez la détection automatique."},
            {"selector": "#tour-target-crop", "title": "Choisir une culture", "text": "Sélectionnez la culture que vous souhaitez examiner."},
            {"selector": "#tour-target-upload", "title": "Ajouter une photo", "text": "Ajoutez une photo nette de la feuille, puis lancez l’analyse."},
            {"selector": "#tour-target-results", "title": "Lire les résultats", "text": "Après l’analyse, vous verrez le diagnostic et des conseils."}
        ]
    else:
        steps = [
            {"selector": "#tour-target-hub", "title": "Choose your region", "text": "Select your farm region, or use automatic location detection."},
            {"selector": "#tour-target-crop", "title": "Choose a crop", "text": "Select the crop you want to check."},
            {"selector": "#tour-target-upload", "title": "Add a leaf photo", "text": "Upload a clear leaf photo, then run the diagnostic."},
            {"selector": "#tour-target-results", "title": "Review the results", "text": "After analysis, you’ll see the diagnosis and advice here."}
        ]

    steps_json = json.dumps(steps)
    force_js = "true" if force_start else "false"
    tour_labels = {
        "close": "Funga" if lang_name == "Kiswahili" else "Fermer" if lang_name == "French" else "Close",
        "back": "Nyuma" if lang_name == "Kiswahili" else "Retour" if lang_name == "French" else "Back",
        "next": "Endelea" if lang_name == "Kiswahili" else "Suivant" if lang_name == "French" else "Next",
        "finish": "Maliza" if lang_name == "Kiswahili" else "Terminer" if lang_name == "French" else "Finish",
        "step": "Hatua" if lang_name == "Kiswahili" else "Étape" if lang_name == "French" else "Step",
        "of": "ya" if lang_name == "Kiswahili" else "sur" if lang_name == "French" else "of",
    }

    tour_html = f"""
    <script>
        const steps = {steps_json};
        const isForceStart = {force_js};
        const labels = {json.dumps(tour_labels, ensure_ascii=False)};
        let currentStep = 0;
        let lastHighlightedEl = null;
        let lastHighlightedStyle = null;

        function checkAndInitTour() {{
            const parentDoc = window.parent.document;
            const tourSeen = parentDoc.defaultView.localStorage.getItem("cropguard_tour_seen");

            if (isForceStart || !tourSeen) {{
                parentDoc.defaultView.localStorage.setItem("cropguard_tour_seen", "true");
                setTimeout(createTourCard, 400);
            }}
        }}

        function createTourCard() {{
            const parentDoc = window.parent.document;
            const existingBox = parentDoc.getElementById("cg-tour-box");
            if (existingBox) existingBox.remove();
            const existingStyle = parentDoc.getElementById("cg-tour-style");
            if (existingStyle) existingStyle.remove();
            clearHighlighting();

            const tourStyle = parentDoc.createElement("style");
            tourStyle.id = "cg-tour-style";
            tourStyle.textContent = `
                #cg-tour-box {{ position:fixed; right:24px; bottom:24px; width:min(360px, calc(100vw - 32px)); padding:20px; box-sizing:border-box; border:1px solid #DCE5DC; border-radius:14px; background:#FFFFFF; color:#1F2937; box-shadow:0 8px 28px rgba(15, 23, 42, .16); font-family:system-ui, sans-serif; z-index:2147483003; }}
                #cg-tour-box button {{ min-height:38px; padding:8px 14px; border:1px solid #D1D5DB; border-radius:8px; background:#FFFFFF; color:#374151; font:inherit; font-weight:600; cursor:pointer; }}
                #cg-tour-box button:focus-visible {{ outline:3px solid #86B98A; outline-offset:2px; }}
                #cg-tour-box #cg-btn-next {{ border-color:#2F6B3B; background:#2F6B3B; color:#FFFFFF; }}
                #cg-tour-box button:disabled {{ opacity:.45; cursor:default; }}
                @media (max-width: 520px) {{
                    #cg-tour-box {{ right:12px; bottom:12px; width:calc(100vw - 24px); }}
                }}
            `;

            const box = parentDoc.createElement("div");
            box.id = "cg-tour-box";
            box.setAttribute("role", "dialog");
            box.setAttribute("aria-live", "polite");
            box.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:14px;">
                    <span id="cg-tour-progress" style="color:#526052; font-size:.85rem; font-weight:600;"></span>
                    <button id="cg-tour-close" type="button"></button>
                </div>
                <div style="height:4px; margin-bottom:16px; overflow:hidden; border-radius:4px; background:#E8EEE8;">
                    <div id="cg-tour-progress-fill" style="height:100%; border-radius:4px; background:#4B8B55; transition:width .2s ease;"></div>
                </div>
                <h3 id="cg-tour-title" style="margin:0 0 8px; color:#1F2937; font-size:1.1rem;"></h3>
                <p id="cg-tour-description" style="margin:0; color:#4B5563; font-size:.95rem; line-height:1.5;"></p>
                <div style="display:flex; justify-content:space-between; gap:8px; margin-top:18px;">
                    <button id="cg-btn-back" type="button"></button>
                    <button id="cg-btn-next" type="button"></button>
                </div>
            `;

            parentDoc.head.appendChild(tourStyle);
            parentDoc.body.appendChild(box);
            parentDoc.getElementById("cg-tour-close").textContent = labels.close;
            parentDoc.getElementById("cg-tour-close").onclick = exitTour;
            parentDoc.getElementById("cg-btn-back").textContent = labels.back;
            parentDoc.getElementById("cg-btn-back").onclick = () => showStep(currentStep - 1);
            parentDoc.getElementById("cg-btn-next").onclick = () => {{
                if (currentStep < steps.length - 1) showStep(currentStep + 1);
                else exitTour();
            }};
            window.parent.addEventListener('keydown', handleTourKeydown);
            showStep(0);
        }}

        function clearHighlighting() {{
            const parentDoc = window.parent.document;
            if (lastHighlightedEl) {{
                lastHighlightedEl.style.outline = lastHighlightedStyle.outline;
                lastHighlightedEl.style.boxShadow = lastHighlightedStyle.boxShadow;
                lastHighlightedEl.style.borderRadius = lastHighlightedStyle.borderRadius;
                lastHighlightedEl.style.transition = lastHighlightedStyle.transition;
                lastHighlightedEl = null;
                lastHighlightedStyle = null;
            }}
        }}

        function showStep(index) {{
            const parentDoc = window.parent.document;
            if (index < 0 || index >= steps.length) return;
            clearHighlighting();

            currentStep = index;
            const step = steps[index];
            const targetEl = parentDoc.querySelector(step.selector);
            parentDoc.getElementById("cg-tour-progress").textContent = `${{labels.step}} ${{index + 1}} ${{labels.of}} ${{steps.length}}`;
            parentDoc.getElementById("cg-tour-progress-fill").style.width = `${{((index + 1) / steps.length) * 100}}%`;
            parentDoc.getElementById("cg-tour-title").textContent = step.title;
            parentDoc.getElementById("cg-tour-description").textContent = step.text;
            parentDoc.getElementById("cg-btn-back").disabled = index === 0;
            parentDoc.getElementById("cg-btn-next").textContent = index === steps.length - 1 ? labels.finish : labels.next;

            if (targetEl) {{
                targetEl.scrollIntoView({{ behavior: 'smooth', block: 'center' }});

                lastHighlightedStyle = {{
                    outline: targetEl.style.outline,
                    boxShadow: targetEl.style.boxShadow,
                    borderRadius: targetEl.style.borderRadius,
                    transition: targetEl.style.transition
                }};
                targetEl.style.outline = "2px solid #4B8B55";
                targetEl.style.boxShadow = "0 0 0 4px rgba(75, 139, 85, .12)";
                targetEl.style.borderRadius = "6px";
                targetEl.style.transition = "outline .2s ease, box-shadow .2s ease";
                lastHighlightedEl = targetEl;
            }}
        }}

        function handleTourKeydown(event) {{
            if (event.key === "Escape") exitTour();
        }}

        function exitTour() {{
            const parentDoc = window.parent.document;
            clearHighlighting();
            const box = parentDoc.getElementById("cg-tour-box");
            const tourStyle = parentDoc.getElementById("cg-tour-style");

            if (box) box.remove();
            if (tourStyle) tourStyle.remove();

            window.parent.removeEventListener('keydown', handleTourKeydown);
        }}

        setTimeout(checkAndInitTour, 500);
    </script>
    """
    components.html(tour_html, height=0)

GLOBAL_AGRICULTURAL_HUBS = {
    "Kisii, Kenya (Highland Zone)": {
        "lat": -0.6817, "lon": 34.7743,
        "languages": ["English", "Kiswahili"],
        "temp": 18.5, "humidity": 88, "risk": "High Fungal Spore & Blight Watch",
        "crops": ["Mahindi (Maize)", "Viazi Mviringo (Irish Potato)", "Karanga (Groundnuts)", "Maharagwe (Beans)", "Chai (Tea)", "Kahawa (Coffee)", "Ndizi (Bananas)", "Kales / Sukuma Wiki", "Chinsaka (Spider Plant)", "Managu (Nightshade)", "Mimea Mingine / Jumla"],
        "resources": [{"name": "Kisii Central Agro-Vet & Inputs Ltd", "location": "Kisii Town", "contact": "+254 712 345 678", "specialty": "Certified Copper Fungicides & Seeds"}, {"name": "KALRO Regional Research Center", "location": "Highland Network", "contact": "+254 20 2023130", "specialty": "Highland Crop Pathology"}]
    },
    "Eldoret, Kenya (Rift Valley Grain Basket)": {
        "lat": 0.5143, "lon": 35.2698,
        "languages": ["English", "Kiswahili"],
        "temp": 17.0, "humidity": 75, "risk": "High Rust & Cereal Blight Watch",
        "crops": ["Mahindi (Maize)", "Wheat (Ngano)", "Karanga (Groundnuts)", "Irish Potato", "Maharagwe (Beans)", "Kales / Sukuma Wiki", "Mimea Mingine / Jumla"],
        "resources": [{"name": "Uasin Gishu Grain Growers Agro-Store", "location": "Eldoret", "contact": "+254 722 000 111", "specialty": "Bulk Fertilizers & Cereal Fungicides"}, {"name": "National Cereals and Produce Board (NCPB)", "location": "Eldoret Depot", "contact": "+254 53 20331", "specialty": "Post-Harvest Storage & Quality Testing"}]
    },
    "Nakuru, Kenya (Rift Valley Horticultural Hub)": {
        "lat": -0.3031, "lon": 36.0800,
        "languages": ["English", "Kiswahili"],
        "temp": 19.0, "humidity": 72, "risk": "Moderate Blight & Aphid Watch",
        "crops": ["Viazi Mviringo (Irish Potato)", "Mahindi (Maize)", "Karanga (Groundnuts)", "Beans", "Tomatoes", "Cabbage", "Kales / Sukuma Wiki", "Mimea Mingine / Jumla"],
        "resources": [{"name": "Nakuru Agricultural Extension Bureau", "location": "Nakuru Hub", "contact": "+254 711 222 333", "specialty": "Horticultural Pest Surveillance"}, {"name": "Egerton University Crop Protection Desk", "location": "Njoro", "contact": "+254 51 22177", "specialty": "Agronomic Research & Diagnostics"}]
    },
    "Morogoro, Tanzania (Agricultural Research Hub)": {
        "lat": -6.8235, "lon": 37.6614,
        "languages": ["English", "Kiswahili"],
        "temp": 26.5, "humidity": 82, "risk": "High Tropical Humidity & Leaf Spot Watch",
        "crops": ["Mahindi (Maize)", "Karanga (Groundnuts)", "Rice (Mpunga)", "Cassava (Mhogo)", "Common Bean", "Kales / Sukuma Wiki", "Mimea Mingine / Jumla"],
        "resources": [{"name": "Sokoine University of Agriculture Advisory", "location": "Morogoro", "contact": "+255 23 260 3511", "specialty": "Crop Science & Plant Pathology"}, {"name": "Tanzania Agricultural Research Institute (TARI)", "location": "Uyole / Morogoro", "contact": "+255 26 232 0000", "specialty": "Seed Certification & Pathology"}]
    },
    "Ibadan, Nigeria (Agricultural Research & Maize Belt)": {
        "lat": 7.3775, "lon": 3.9470,
        "languages": ["English", "French"],
        "temp": 28.0, "humidity": 84, "risk": "High Humid Spore & Mosaic Virus Watch",
        "crops": ["Maize", "Cassava", "Yam", "Groundnuts / Peanuts", "Cowpea", "Other Crop / General"],
        "resources": [{"name": "IITA (International Institute of Tropical Agriculture)", "location": "Ibadan", "contact": "+234 2 241 2626", "specialty": "Global Tropical Crop Improvement & Virology"}, {"name": "Oyo State Agricultural Development Programme", "location": "Ibadan", "contact": "+234 803 555 0199", "specialty": "Extension Services"}]
    },
    "Kumasi, Ghana (Cocoa & Grain Belt)": {
        "lat": 6.6885, "lon": -1.6244,
        "languages": ["English", "French"],
        "temp": 27.0, "humidity": 85, "risk": "High Black Pod & Leaf Blight Risk",
        "crops": ["Cocoa", "Maize", "Cassava", "Groundnuts / Peanuts", "Plantain", "Other Crop / General"],
        "resources": [{"name": "Cocoa Research Institute of Ghana (CRIG)", "location": "Tafo / Kumasi", "contact": "+233 30 297 3251", "specialty": "Tree Crop Pathology & Protection"}, {"name": "Ministry of Food and Agriculture (MoFA)", "location": "Kumasi Hub", "contact": "+254 32 202 3341", "specialty": "Farmer Field Schools"}]
    },
    "Global / Universal Zone": {
        "lat": -0.6817, "lon": 34.7743,
        "languages": ["English", "French", "Spanish", "Portuguese", "Kiswahili"],
        "temp": 22.0, "humidity": 75, "risk": "Active Regional Spore Monitoring",
        "crops": ["Mahindi (Maize)", "Viazi Mviringo (Irish Potato)", "Tomato", "Maharagwe (Beans)", "Karanga (Groundnuts)", "Ndizi (Bananas)", "Rice (Mpunga)", "Chai (Tea)", "Kahawa (Coffee)", "Kales / Sukuma Wiki", "Mimea Mingine / Jumla"],
        "resources": [{"name": "FAO International Plant Protection Convention", "location": "Global / UN", "contact": "www.fao.org", "specialty": "Global Plant Health Standards"}, {"name": "CABI Plantwise Global Knowledge Bank", "location": "International", "contact": "www.cabi.org", "specialty": "Worldwide Pest Management"}]
    }
}

# --- TWO-WAY GPS COMPONENT SETUP ---
GPS_COMPONENT_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body { margin: 0; padding: 0; background: transparent; }
  #gpsBtn {
    width: 100%;
    background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%);
    color: #ffffff;
    border: none;
    padding: 0.6rem 0.5rem;
    border-radius: 8px;
    font: bold 0.9rem "Source Sans Pro", "Segoe UI", Roboto, Arial, sans-serif;
    white-space: nowrap;
    cursor: pointer;
    box-shadow: 0 3px 8px rgba(0,0,0,0.3);
  }
  #gpsBtn:disabled { opacity: 0.75; cursor: wait; }
</style>
</head>
<body>
<button id="gpsBtn" type="button">📍 Auto-Detect GPS</button>
<script>
(function () {
  var btn = document.getElementById("gpsBtn");
  var label = btn.textContent;
  var autoOnLoad = true;
  var autoTried = false;
  var busy = false;

  function post(type, data) {
    window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type: type }, data), "*");
  }
  function sendValue(value) {
    post("streamlit:setComponentValue", { value: value, dataType: "json" });
  }

  function release() {
    busy = false;
    btn.disabled = false;
    btn.textContent = label;
  }

  function getPosition(options) {
    return new Promise(function (resolve, reject) {
      navigator.geolocation.getCurrentPosition(resolve, reject, options);
    });
  }

  async function detect(source) {
    if (busy) return;
    var auto = source === "auto";
    if (!window.isSecureContext) {
      if (!auto) sendValue({ error: "insecure", source: source, t: Date.now() });
      return;
    }
    if (!navigator.geolocation) {
      if (!auto) sendValue({ error: "failed", source: source, t: Date.now() });
      return;
    }
    busy = true;
    btn.disabled = true;
    btn.textContent = "⏳ Locating…";
    var watchdog = setTimeout(release, 35000);
    try {
      var pos;
      try {
        pos = await getPosition({ enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 });
      } catch (e) {
        if (e && e.code === 1) throw e;
        pos = await getPosition({ enableHighAccuracy: true, timeout: 20000, maximumAge: 0 });
      }
      sendValue({
        lat: pos.coords.latitude,
        lon: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
        source: source,
        t: Date.now()
      });
    } catch (e) {
      if (!auto) sendValue({ error: (e && e.code === 1) ? "denied" : "failed", source: source, t: Date.now() });
    } finally {
      clearTimeout(watchdog);
      release();
    }
  }

  function maybeAutoDetect() {
    if (autoTried || !autoOnLoad) return;
    autoTried = true;
    if (!navigator.permissions || !navigator.permissions.query) return;
    navigator.permissions.query({ name: "geolocation" })
      .then(function (p) { if (p.state === "granted") detect("auto"); })
      .catch(function () {});
  }

  btn.addEventListener("click", function () { detect("click"); });

  window.addEventListener("message", function (event) {
    var d = event.data;
    if (!d || d.type !== "streamlit:render") return;
    var args = d.args || {};
    if (args.label) { label = args.label; if (!busy) btn.textContent = label; }
    autoOnLoad = args.auto !== false;
    if (d.theme && d.theme.base) document.documentElement.style.colorScheme = d.theme.base;
    post("streamlit:setFrameHeight", { height: 52 });
    maybeAutoDetect();
  });

  post("streamlit:componentReady", { apiVersion: 1 });
})();
</script>
</body>
</html>"""

@st.cache_resource(show_spinner=False)
def _declare_gps_component(html: str):
    comp_dir = os.path.join(tempfile.gettempdir(), "cropguard_gps_component")
    os.makedirs(comp_dir, exist_ok=True)
    with open(os.path.join(comp_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)
    return components.declare_component("cropguard_gps", path=comp_dir)

gps_detector = _declare_gps_component(GPS_COMPONENT_HTML)

def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371.0088 * math.asin(min(1.0, math.sqrt(a)))

def find_nearest_hub(lat, lon):
    dist = {
        hub_name: haversine_km(lat, lon, hub["lat"], hub["lon"])
        for hub_name, hub in GLOBAL_AGRICULTURAL_HUBS.items()
        if hub_name != GPS_FALLBACK_HUB
    }
    best = min(dist, key=dist.get)
    return best, dist[best]

def apply_gps_reading(reading):
    if reading.get("error"):
        st.session_state["gps_status"] = {"kind": reading["error"]}
        return
    if reading.get("source") == "auto":
        if st.session_state.get("_gps_auto_done"):
            return
        st.session_state["_gps_auto_done"] = True
    try:
        lat, lon = float(reading["lat"]), float(reading["lon"])
    except (KeyError, TypeError, ValueError):
        st.session_state["gps_status"] = {"kind": "failed"}
        return
    nearest, km = find_nearest_hub(lat, lon)
    if km > GPS_MAX_HUB_KM:
        st.session_state["selected_hub_label"] = GPS_FALLBACK_HUB
        st.session_state["gps_status"] = {"kind": "global", "lat": lat, "lon": lon}
    else:
        st.session_state["selected_hub_label"] = nearest
        st.session_state["gps_status"] = {"kind": "ok", "lat": lat, "lon": lon, "hub": nearest, "km": km}

# --- REORGANIZED SIDEBAR SETUP ---
active_zone_data = GLOBAL_AGRICULTURAL_HUBS[st.session_state.get("selected_hub_label", "Kisii, Kenya (Highland Zone)")]
if st.session_state.get("selected_language") not in active_zone_data["languages"]:
    st.session_state["selected_language"] = active_zone_data["languages"][0]
T = TRANSLATIONS.get(st.session_state["selected_language"], TRANSLATIONS["English"])

# Keep the sidebar visual system independent from page-specific main-panel themes.
st.sidebar.markdown("""
<style>
section[data-testid="stSidebar"] {
    background:
        radial-gradient(ellipse at 100% 0%, rgba(141, 196, 135, .2), transparent 38%),
        linear-gradient(165deg, #f4f8ef 0%, #e9f1e4 58%, #e1eddd 100%) !important;
    border-right: 1px solid rgba(40, 86, 55, .15);
}
section[data-testid="stSidebar"] > div {
    background: transparent !important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h4,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] label p {
    color: #203a2b !important;
    text-shadow: none !important;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
    margin: .65rem 0 .5rem;
    font-size: 1rem;
    font-weight: 750;
    letter-spacing: .01em;
}
section[data-testid="stSidebar"] hr {
    margin: .85rem 0;
    border-color: rgba(55, 99, 64, .16);
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    padding: .45rem .6rem;
    margin: .12rem 0;
    border: 1px solid transparent;
    border-radius: 11px;
    transition: background-color .2s ease, border-color .2s ease, transform .2s ease;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(255, 255, 255, .72);
    border-color: rgba(68, 125, 78, .2);
    transform: translateX(2px);
}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] label {
    color: #49634f !important;
    font-size: .82rem;
    font-weight: 650;
}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: rgba(255, 255, 255, .82);
    border-color: rgba(55, 99, 64, .22);
    border-radius: 10px;
}
section[data-testid="stSidebar"] [data-testid="stAlert"] {
    border-radius: 12px;
    border: 1px solid rgba(55, 99, 64, .14);
}
section[data-testid="stSidebar"] [data-testid="stExpander"] {
    overflow: hidden;
    border: 1px solid rgba(55, 99, 64, .18);
    border-radius: 12px;
    background: rgba(255, 255, 255, .48);
}
.cg-brand-card {
    position: relative;
    display: flex;
    align-items: center;
    gap: 12px;
    overflow: hidden;
    margin: .3rem 0 .8rem;
    padding: 15px 14px;
    border: 1px solid rgba(255, 255, 255, .18);
    border-radius: 17px;
    color: #f5fff3;
    background: linear-gradient(125deg, #174c35 0%, #287247 58%, #438d50 100%);
    box-shadow: 0 9px 22px rgba(31, 87, 50, .2);
}
.cg-brand-card::after {
    position: absolute;
    top: -38px;
    right: 8px;
    width: 110px;
    height: 110px;
    border: 1px solid rgba(226, 255, 211, .16);
    border-radius: 50%;
    content: "";
}
.cg-brand-mark {
    z-index: 1;
    display: grid;
    width: 44px;
    height: 44px;
    flex: 0 0 44px;
    place-items: center;
    border: 1px solid rgba(241, 255, 232, .35);
    border-radius: 14px;
    background: rgba(255, 255, 255, .12);
    font-size: 1.65rem;
    animation: cgSproutSway 3.4s ease-in-out infinite;
}
.cg-brand-copy { z-index: 1; min-width: 0; }
.cg-brand-title {
    color: #fff;
    font-size: 1.05rem;
    font-weight: 800;
    letter-spacing: -.02em;
}
.cg-brand-tagline {
    margin-top: 3px;
    color: rgba(239, 255, 235, .78);
    font-size: .66rem;
    font-weight: 700;
    letter-spacing: .13em;
}
.cg-brand-seed {
    position: absolute;
    right: 25px;
    bottom: 15px;
    color: #d4f5a3;
    font-size: .8rem;
    animation: cgSeedDrift 3.6s ease-in-out infinite;
}
.cg-brand-seed-two {
    right: 49px;
    bottom: 28px;
    color: #f0d986;
    font-size: .6rem;
    animation-delay: -1.7s;
}
.cg-climate-card {
    position: relative;
    overflow: hidden;
    margin: .3rem 0;
    padding: 13px;
    border: 1px solid rgba(57, 111, 67, .16);
    border-radius: 14px;
    background: rgba(255, 255, 255, .64);
    box-shadow: 0 5px 16px rgba(37, 78, 45, .06);
}
.cg-climate-title {
    margin-bottom: 10px;
    color: #24583a;
    font-size: .9rem;
    font-weight: 750;
}
.cg-climate-meta {
    margin-bottom: 8px;
    color: #526b57;
    font-size: .76rem;
    line-height: 1.5;
}
.cg-climate-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 9px;
}
.cg-climate-stat {
    padding: 8px;
    border-radius: 10px;
    background: #f0f6ec;
}
.cg-climate-stat-label {
    color: #687c68;
    font-size: .67rem;
    font-weight: 650;
}
.cg-climate-stat-value {
    margin-top: 2px;
    color: #274e35;
    font-size: .9rem;
    font-weight: 750;
}
.cg-climate-risk {
    display: flex;
    align-items: flex-start;
    gap: 7px;
    padding-top: 8px;
    border-top: 1px solid rgba(55, 99, 64, .12);
    color: #6a5930;
    font-size: .75rem;
    line-height: 1.4;
}
.cg-climate-pulse {
    width: 7px;
    height: 7px;
    flex: 0 0 7px;
    margin-top: 4px;
    border-radius: 50%;
    background: #d99b32;
    box-shadow: 0 0 0 0 rgba(217, 155, 50, .35);
    animation: cgRiskPulse 2.2s ease-out infinite;
}
@keyframes cgSproutSway {
    0%, 100% { transform: rotate(-4deg) translateY(0); }
    50% { transform: rotate(4deg) translateY(-2px); }
}
@keyframes cgSeedDrift {
    0%, 100% { transform: translate3d(0, 3px, 0) rotate(-8deg); opacity: .58; }
    50% { transform: translate3d(-5px, -5px, 0) rotate(8deg); opacity: 1; }
}
@keyframes cgRiskPulse {
    0% { box-shadow: 0 0 0 0 rgba(217, 155, 50, .38); }
    70%, 100% { box-shadow: 0 0 0 6px rgba(217, 155, 50, 0); }
}
@media (prefers-reduced-motion: reduce) {
    .cg-brand-mark, .cg-brand-seed, .cg-climate-pulse {
        animation: none !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadio"] label {
        transition: none;
    }
}
</style>
""", unsafe_allow_html=True)

# 1. Branding & Identity (Top)
st.sidebar.markdown("""
<div class="cg-brand-card">
    <div class="cg-brand-mark" aria-hidden="true">🌱</div>
    <div class="cg-brand-copy">
        <div class="cg-brand-title">CropGuard AI</div>
        <div class="cg-brand-tagline">GROW · MONITOR · PROTECT</div>
    </div>
    <span class="cg-brand-seed" aria-hidden="true">✦</span>
    <span class="cg-brand-seed cg-brand-seed-two" aria-hidden="true">✧</span>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

# 2. Primary Navigation
st.sidebar.subheader(T.get("nav_header", "🧭 Platform Navigation"))
app_mode = st.sidebar.radio(
    T.get("select_portal", "Select Portal View"), 
    [
        T["nav_diag"],
        T["nav_map"],
        T["nav_ai"],
        T["nav_forum"],
        T["nav_acc"]
    ],
    key="app_mode_radio"
)

st.sidebar.markdown("---")

# 3. Region & Language Calibration
st.sidebar.markdown("<div id='tour-target-hub'></div>", unsafe_allow_html=True)
st.sidebar.subheader("🌍 Region & Language Calibration")

with st.sidebar:
    gps_reading = gps_detector(label="📍 Auto-Detect GPS", auto=GPS_AUTO_ON_LOAD, key="cg_gps_detector")
    gps_status_slot = st.container()

if isinstance(gps_reading, dict) and gps_reading.get("t") != st.session_state.get("_gps_last_t"):
    st.session_state["_gps_last_t"] = gps_reading.get("t")
    apply_gps_reading(gps_reading)

hub_keys = list(GLOBAL_AGRICULTURAL_HUBS.keys())
if st.session_state.get("selected_hub_label") not in hub_keys:
    st.session_state["selected_hub_label"] = hub_keys[0]

selected_hub_label = st.sidebar.selectbox(
    "Select Farm Town / Region Worldwide",
    options=hub_keys,
    key="selected_hub_label"
)
active_zone_data = GLOBAL_AGRICULTURAL_HUBS[selected_hub_label]

language = st.sidebar.selectbox(
    "Choose Language / Langue / Idioma", 
    options=active_zone_data["languages"],
    key="selected_language"
)

T = TRANSLATIONS.get(language, TRANSLATIONS["English"])

gps_status = st.session_state.get("gps_status")
if gps_status:
    _gps_kind = gps_status["kind"]
    with gps_status_slot:
        if _gps_kind == "ok":
            if selected_hub_label == gps_status["hub"]:
                st.success(T["gps_ok"].format(
                    lat=f"{gps_status['lat']:.3f}", lon=f"{gps_status['lon']:.3f}",
                    hub=gps_status["hub"], km=f"{gps_status['km']:.0f}"))
        elif _gps_kind == "global":
            if selected_hub_label == GPS_FALLBACK_HUB:
                st.info(T["gps_global"].format(
                    lat=f"{gps_status['lat']:.3f}", lon=f"{gps_status['lon']:.3f}",
                    max_km=GPS_MAX_HUB_KM))
        else:
            st.warning(T.get(f"gps_{_gps_kind}", T["gps_failed"]))

st.sidebar.markdown("---")

# 4. Real-Time Environmental & Threat Intel
st.sidebar.markdown(f"""
<div class="cg-climate-card">
    <div class="cg-climate-title">{html.escape(T["climate_header"])}</div>
    <div class="cg-climate-meta">📍 {html.escape(selected_hub_label)}</div>
    <div class="cg-climate-stats">
        <div class="cg-climate-stat">
            <div class="cg-climate-stat-label">🌡️ Temperature</div>
            <div class="cg-climate-stat-value">{html.escape(str(active_zone_data['temp']))}°C</div>
        </div>
        <div class="cg-climate-stat">
            <div class="cg-climate-stat-label">💧 Humidity</div>
            <div class="cg-climate-stat-value">{html.escape(str(active_zone_data['humidity']))}%</div>
        </div>
    </div>
    <div class="cg-climate-risk">
        <span class="cg-climate-pulse" aria-hidden="true"></span>
        <span>{html.escape(str(active_zone_data['risk']))}</span>
    </div>
</div>
""", unsafe_allow_html=True)

active_alerts = get_active_regional_alerts(selected_hub_label)
if active_alerts:
    st.sidebar.markdown("---")
    st.sidebar.subheader(T["reg_early_warning"])
    for alert_time, disease_name, msg in active_alerts:
        st.sidebar.warning(f"**{disease_name} {T['outbreak_warning']}**\n\n{msg}")

st.sidebar.markdown("---")

# 5. Advanced / B2G Ministry & Bio-Security Portal
with st.sidebar.expander(T["b2g_header"]):
    st.markdown(f"**{T['phytosanitary_feed']}**")
    st.caption(T["integ_registry_stats"].format(**epi_registry_stats()))
    summary_records = get_government_epidemiological_summary()
    if summary_records:
        st.write(f"{T['active_vectors']} {len(summary_records)}")
        for rec in summary_records[:5]:
            st.markdown(f"- **{rec[0]}**: `{rec[1]}` (Reports: {rec[2]}, Avg Sev: {rec[3]:.1f}%)")
    else:
        st.info(T["no_telemetry_sidebar"])

st.sidebar.markdown("---")

# 6. About CropGuard AI (Bottom)
st.sidebar.subheader(T["about_header"])
st.sidebar.info(T["about_text"])

if language == "Kiswahili":
    tts_lang = "sw-KE"
elif language == "French":
    tts_lang = "fr-FR"
else:
    tts_lang = "en-US"

# ==========================================
# VIEW 1.5: FARMER ACCOUNT & HISTORY PORTAL
# ==========================================
if app_mode == T["nav_acc"]:
    st.title(T["acc_title"])
    st.markdown(f"<p style='font-size: 1.2rem; font-weight: 500;'>{T['acc_subtitle']}</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col_acc1, col_acc2 = st.columns([1, 1.6], gap="large")

    with col_acc1:
        with st.container(border=True):
            st.markdown(f"### {T['profile_header']}")
            
            if not st.user.get("is_logged_in", False):
                st.info(T["login_prompt"])
                if st.button(T["login_btn"], type="primary", use_container_width=True):
                    st.login("google")
            else:
                google_email = st.user.email
                google_name = st.user.name if hasattr(st.user, 'name') and st.user.name else google_email
                
                conn = sqlite3.connect('cropguard_surveillance.db', check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users WHERE identifier = ?", (google_email,))
                user_row = cursor.fetchone()
                
                if user_row:
                    st.session_state['logged_in_user_id'] = user_row[0]
                else:
                    cursor.execute("INSERT INTO users (account_type, identifier, display_name, created_at) VALUES (?, ?, ?, ?)",
                                   ('Google', google_email, google_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    cursor.execute("SELECT last_insert_rowid()")
                    st.session_state['logged_in_user_id'] = cursor.fetchone()[0]
                conn.close()

                st.session_state['user_display_name'] = google_name
                st.session_state['user_identifier'] = google_email
                st.session_state['auth_method'] = 'Google OIDC'

                st.success(f"{T['auth_success']} {google_name}!")
                st.write(f"**{T['email_lbl']}** `{google_email}`")
                st.write(f"**{T['user_id_lbl']}** `F{st.session_state.get('logged_in_user_id', 1):05d}`")
                
                st.markdown("---")
                if st.button(T["logout_btn"], use_container_width=True):
                    st.logout()

            st.markdown("---")
            with st.expander(T["alt_phone_expander"]):
                phone_num = st.text_input(T["phone_label"], value="")
                if st.button(T["otp_btn"], use_container_width=True):
                    if phone_num.strip():
                        st.success(T["phone_sent_msg"].format(phone=phone_num))
                
                otp_code = st.text_input(T["otp_input"], type="password")
                if st.button(T["verify_otp_btn"], use_container_width=True):
                    if otp_code == "1234" and phone_num.strip():
                        conn = sqlite3.connect('cropguard_surveillance.db', check_same_thread=False)
                        cursor = conn.cursor()
                        cursor.execute("SELECT user_id, display_name FROM users WHERE identifier = ?", (phone_num,))
                        user_row = cursor.fetchone()
                        
                        if user_row:
                            st.session_state['logged_in_user_id'] = user_row[0]
                            st.session_state['user_display_name'] = user_row[1]
                            st.session_state['user_identifier'] = phone_num
                            st.session_state['auth_method'] = 'Phone OTP'
                        else:
                            cursor.execute("INSERT INTO users (account_type, identifier, display_name, created_at) VALUES (?, ?, ?, ?)",
                                           ('Phone', phone_num, 'Farmer ' + phone_num[-4:], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                            conn.commit()
                            cursor.execute("SELECT last_insert_rowid()")
                            st.session_state['logged_in_user_id'] = cursor.fetchone()[0]
                            st.session_state['user_display_name'] = 'Farmer ' + phone_num[-4:]
                            st.session_state['user_identifier'] = phone_num
                            st.session_state['auth_method'] = 'Phone OTP'
                        conn.close()
                        st.success(T["phone_success_msg"])
                        st.rerun()
                    else:
                        st.warning(T["phone_error_msg"])

    with col_acc2:
        with st.container(border=True):
            st.markdown(f"### {T['history_header']} ({st.session_state.get('user_display_name', 'Dr. Morara')})")
            st.info(T["history_info"])
            
            conn = sqlite3.connect('cropguard_surveillance.db', check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, hub_region, target_crop, detected_disease, confidence_score, severity_stage, severity_percentage 
                FROM scan_telemetry 
                WHERE user_id = ? 
                ORDER BY scan_id DESC
            ''', (st.session_state.get('logged_in_user_id', 1),))
            history_rows = cursor.fetchall()
            conn.close()

            if not history_rows:
                st.warning(T["no_history_msg"])
            else:
                df_history = pd.DataFrame(history_rows, columns=[
                    T["col_time"], T["col_hub"], T["col_crop"], T["col_disease"], 
                    T["col_conf"], T["col_stage"], T["col_sev_pct"]
                ])
                st.dataframe(df_history, use_container_width=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"### {T['timeline_header']}")
                st.line_chart(df_history.set_index(T["col_time"])[T["col_sev_pct"]])

# ==========================================
# VIEW 1: B2G EPIDEMIOLOGICAL HEATMAP DASHBOARD
# ==========================================
elif app_mode == T["nav_map"]:
    st.title(T["map_title"])
    st.markdown(f"<p style='font-size: 1.2rem; font-weight: 500;'>{T['map_subtitle']}</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(f"### {T['map_cluster_header']}")
        epi_render_heatmap(T)

# ==========================================
# VIEW 3: AGRITECH VIRTUAL AI ASSISTANT
# ==========================================
elif app_mode == T["nav_ai"]:
    st.title(T["ai_title"])
    st.markdown(f"<p style='font-size: 1.2rem; font-weight: 500;'>{T['ai_subtitle']} ({selected_hub_label})</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(f"### {T['chat_header']}")
        st.info(T["chat_info"].format(hub=selected_hub_label, lang=language))

        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": T["chat_welcome"].format(
                    user=st.session_state.get('user_display_name', 'Dr. Morara'),
                    hub=selected_hub_label
                )}
            ]

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input(T["chat_input_ph"]):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            prompt_lower = prompt.lower()
            if "maize" in prompt_lower or "mahindi" in prompt_lower:
                bot_reply = f"For maize crops in {selected_hub_label}, monitor closely for Fall Armyworm or Maize Lethal Necrosis. For early stage symptoms (Stage 1-2), apply recommended foliar insecticides or certified bio-pesticides. Check our verified local provider **{active_zone_data['resources'][0]['name']}** ({active_zone_data['resources'][0]['contact']}) for inputs."
            elif "blight" in prompt_lower or "fungus" in prompt_lower or "rot" in prompt_lower:
                bot_reply = f"Fungal blights thrive under current conditions in {selected_hub_label} (Temp: {active_zone_data['temp']}°C, Humidity: {active_zone_data['humidity']}%). Ensure proper spacing, avoid overhead irrigation, and apply a broad-spectrum copper fungicide if tissue damage exceeds 20%."
            elif "hello" in prompt_lower or "hi" in prompt_lower:
                bot_reply = f"Greetings! As your agritech consultant for {selected_hub_label}, I'm ready to assist with crop diagnostics, disease prevention, and extension coordination."
            else:
                bot_reply = f"That is a vital agronomic inquiry for {selected_hub_label}. Based on current micro-climate risk ({active_zone_data['risk']}), I recommend inspecting root zones and consulting local extension services at **{active_zone_data['resources'][0]['name']}** via `{active_zone_data['resources'][0]['contact']}`."

            with st.chat_message("assistant"):
                st.markdown(bot_reply)
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})

# ==========================================
# VIEW 4: REGIONAL FARMER COMMUNITY FORUM
# ==========================================
elif app_mode == T["nav_forum"]:
    st.title(T["forum_title"])
    st.markdown(f"<p style='font-size: 1.2rem; font-weight: 500;'>{T['forum_subtitle']} <b>{selected_hub_label}</b></p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col_post, col_feed = st.columns([1, 2], gap="large")

    with col_post:
        with st.container(border=True):
            st.markdown(f"### {T['broadcast_header']}")
            author = st.text_input(T["author_label"], value=st.session_state.get('user_display_name', 'Dr. Morara'))
            tag = st.selectbox(T["tag_label"], ["🚨 Outbreak Alert", "🌾 Crop Advice", "🚜 Equipment & Inputs", "🛒 Marketplace / Trade"])
            message_text = st.text_area(T["msg_label"], height=120)
            forum_media = st.file_uploader(
                T["forum_media_label"],
                type=["jpg", "jpeg", "png", "webp", "mp4", "mov", "webm"],
                accept_multiple_files=False,
                key="forum_media_upload",
                help=T["forum_media_help"],
            )
            
            if st.button(T["share_btn"], type="primary", use_container_width=True):
                media_bytes = forum_media.getvalue() if forum_media is not None else None
                media_extension = (
                    os.path.splitext(forum_media.name)[1].lower()
                    if forum_media is not None else ""
                )
                media_is_video = media_extension in {".mp4", ".mov", ".webm"}
                media_limit = 50 * 1024 * 1024 if media_is_video else 15 * 1024 * 1024
                if forum_media is not None and len(media_bytes) > media_limit:
                    st.error(T["forum_media_too_large"])
                elif message_text.strip() or forum_media is not None:
                    media_type = None
                    if forum_media is not None:
                        if media_is_video:
                            media_type = "video"
                        else:
                            try:
                                with Image.open(io.BytesIO(media_bytes)) as media_image:
                                    media_image.verify()
                            except (OSError, Image.DecompressionBombError):
                                st.error(T["forum_media_invalid"])
                                st.stop()
                            media_type = "image"
                    conn = sqlite3.connect('cropguard_surveillance.db', check_same_thread=False)
                    cursor = conn.cursor()
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                    cursor.execute('''
                        INSERT INTO farmer_community_posts
                            (timestamp, hub_region, author_name, category_tag, message,
                             media_name, media_type, media_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        ts,
                        selected_hub_label,
                        author.strip() or st.session_state.get('user_display_name', 'Farmer'),
                        tag,
                        message_text.strip(),
                        forum_media.name if forum_media is not None else None,
                        media_type,
                        sqlite3.Binary(media_bytes) if media_bytes is not None else None,
                    ))
                    conn.commit()
                    conn.close()
                    st.success(T["post_posted_msg"])
                    st.rerun()
                else:
                    st.warning(T["forum_post_empty"])

    with col_feed:
        st.markdown(f"### {T['feed_header']} ({selected_hub_label})")
        
        conn = sqlite3.connect('cropguard_surveillance.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT author_name, category_tag, message, timestamp,
                   media_name, media_type, media_data
            FROM farmer_community_posts 
            WHERE hub_region = ? 
            ORDER BY post_id DESC
        ''', (selected_hub_label,))
        posts = cursor.fetchall()
        conn.close()

        if not posts:
            st.info(T["no_posts_msg"].format(hub=selected_hub_label))
        else:
            for p_author, p_tag, p_msg, p_ts, media_name, media_type, media_data in posts:
                with st.container(border=True):
                    st.markdown(
                        f"**{html.escape(p_author)}** `{html.escape(p_tag)}` &nbsp;•&nbsp; "
                        f"<span style='font-size: 0.85rem; color: #A5D6A7;'>"
                        f"{html.escape(p_ts)}</span>",
                        unsafe_allow_html=True,
                    )
                    if p_msg:
                        st.write(p_msg)
                    if media_data:
                        if media_type == "image":
                            st.image(media_data, caption=media_name, use_container_width=True)
                        elif media_type == "video":
                            st.video(media_data)
                            st.caption(f"{T['forum_media_name']}: {media_name}")

# ==========================================
# VIEW 2: FARMER DIAGNOSTIC & ADVISORY HUB (DEFAULT)
# ==========================================
else:
    st.markdown("""
        <style>
        div.stButton > button {
            white-space: nowrap !important;
            word-break: normal !important;
            min-width: max-content !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if "tour_force_trigger" not in st.session_state:
        st.session_state["tour_force_trigger"] = False

    header_col1, header_col2 = st.columns([2.5, 1.5], gap="medium")
    
    with header_col1:
        st.title(T["diag_title"])
        st.markdown(f"<p style='font-size: 1.2rem; font-weight: 500;'>{T['diag_subtitle']} ({selected_hub_label})</p>", unsafe_allow_html=True)
        
    with header_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(T["tour_btn"], type="primary", use_container_width=True):
            st.session_state["tour_force_trigger"] = True

    render_guided_tour(language, force_start=st.session_state["tour_force_trigger"])
    st.session_state["tour_force_trigger"] = False

    st.markdown("<br>", unsafe_allow_html=True)

    @st.fragment
    def diagnostic_workflow():
        if 'analysis_done' not in st.session_state:
            st.session_state['analysis_done'] = False
        if 'last_prediction' not in st.session_state:
            st.session_state['last_prediction'] = None
        if 'last_confidence' not in st.session_state:
            st.session_state['last_confidence'] = None
        if 'last_confidence_margin' not in st.session_state:
            st.session_state['last_confidence_margin'] = None
        if 'last_severity_stage' not in st.session_state:
            st.session_state['last_severity_stage'] = None
        if 'last_severity_pct' not in st.session_state:
            st.session_state['last_severity_pct'] = None
        if 'last_diagnosis_notice' not in st.session_state:
            st.session_state['last_diagnosis_notice'] = None
        if 'last_diagnosis_available' not in st.session_state:
            st.session_state['last_diagnosis_available'] = False
        if 'last_language' not in st.session_state:
            st.session_state['last_language'] = language
        if 'selected_crop' not in st.session_state:
            st.session_state['selected_crop'] = None

        left_col, right_col = st.columns(2, gap="large")

        with left_col:
            with st.container(border=True):
                crop_list = active_zone_data["crops"]

                st.markdown("<div id='tour-target-crop'></div>", unsafe_allow_html=True)
                st.markdown(f"### {T['crop_select_header']}")
                selected_crop = st.selectbox(T["crop_select_prompt"], crop_list, label_visibility="collapsed")
                st.markdown("<br>", unsafe_allow_html=True)

                st.markdown("<div id='tour-target-upload'></div>", unsafe_allow_html=True)
                st.markdown(f"### {T['upload_header']} {T['upload_label_text']}")
                uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png"], label_visibility="collapsed", key="file_upload")
                
                assessment = None
                image_quality = None
                sample_source_type = "Verified Farm Field Sample"
                analyze_triggered = False
                if uploaded_file is not None:
                    st.markdown("<br>", unsafe_allow_html=True)
                    upload_bytes = uploaded_file.getvalue()
                    upload_digest = hashlib.sha256(upload_bytes).hexdigest()
                    if st.session_state.get("_last_upload_digest") != upload_digest:
                        st.session_state["_last_upload_digest"] = upload_digest
                        st.session_state["analysis_done"] = False
                        st.session_state["last_prediction"] = None
                        st.session_state["last_confidence"] = None
                        st.session_state["last_confidence_margin"] = None
                        st.session_state["last_severity_stage"] = None
                        st.session_state["last_severity_pct"] = None
                        st.session_state["last_diagnosis_notice"] = None
                        st.session_state["last_diagnosis_available"] = False
                        st.session_state["last_disease_guide"] = None
                    image = ImageOps.exif_transpose(Image.open(uploaded_file))
                    image_quality = assess_image_quality(image)
                    st.image(image, caption=f"Field Sample Preview ({selected_crop.split(' ')[0]})", width="stretch")
                    render_image_quality_feedback(image_quality, T)
                    
                    sample_source_type = st.radio(
                        "Select Sample Origin (Telemetry Integrity Check):",
                        ["🌱 Verified Farm Field Sample (Log to B2G Surveillance)", "🔬 Reference / Internet Sample (Test Only - Do Not Log)"],
                        index=0,
                        help="Prevents reference or internet photos from skewing regional disease outbreak statistics."
                    )
                    
                    assessment = di.assess_upload(upload_bytes)
                    is_field_sample = "Verified Farm Field Sample" in sample_source_type
                    
                    if is_field_sample:
                        di.render_assessment(st, T, assessment, attested=True)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    analyze_triggered = st.button(
                        T["analyze_btn"],
                        type="primary",
                        use_container_width=True,
                        disabled=image_quality["blocked"],
                    )

        is_active = (uploaded_file is not None)
        play_state = "paused" if is_active else "running"

        primary_color = "#00897B"
        accent_green = "#A5D6A7"
        upload_button_color = "#F57C00" 
        
        st.markdown(f"""
        <style>
        section.main > div, [data-testid="stSidebar"] > div, .block-container {{
            opacity: 1 !important;
            transition: none !important;
        }}
        [data-testid="stStatusWidget"], [data-testid="stSkeleton"] {{
            display: none !important;
        }}

        .bg-container {{
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            z-index: -999;
            background-color: #1E4620;
        }}
        
        .bg-slide {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background-size: cover; background-position: center; background-repeat: no-repeat;
            opacity: 0; animation-timing-function: ease-in-out; animation-iteration-count: infinite;
            animation-duration: 30s; animation-play-state: {play_state}; will-change: transform, opacity;
        }}
        
        .slide-1 {{ background-image: linear-gradient(rgba(0, 30, 15, 0.7), rgba(0, 15, 5, 0.9)), url("https://images.unsplash.com/photo-1500937386664-56d1dfef3854?auto=format&fit=crop&w=2070&q=80"); animation-name: fadeSlide1; }}
        .slide-2 {{ background-image: linear-gradient(rgba(0, 30, 15, 0.7), rgba(0, 15, 5, 0.9)), url("https://images.unsplash.com/photo-1625246333195-78d9c38ad449?auto=format&fit=crop&w=2070&q=80"); animation-name: fadeSlide2; }}
        .slide-3 {{ background-image: linear-gradient(rgba(0, 30, 15, 0.7), rgba(0, 15, 5, 0.9)), url("https://images.unsplash.com/photo-1550989460-0adf9ea622e2?auto=format&fit=crop&w=2070&q=80"); animation-name: fadeSlide3; }}
        .slide-4 {{ background-image: linear-gradient(rgba(0, 30, 15, 0.7), rgba(0, 15, 5, 0.9)), url("https://images.unsplash.com/photo-1592841202223-1ef5caa383b3?auto=format&fit=crop&w=2070&q=80"); animation-name: fadeSlide4; }}
        .slide-5 {{ background-image: linear-gradient(rgba(0, 30, 15, 0.7), rgba(0, 15, 5, 0.9)), url("https://images.unsplash.com/photo-1592417817098-8f3d6eb2660d?auto=format&fit=crop&w=2070&q=80"); animation-name: fadeSlide5; }}

        @keyframes fadeSlide1 {{ 0% {{ opacity: 1; transform: scale(1); }} 18% {{ opacity: 1; transform: scale(1.03); }} 24% {{ opacity: 0; transform: scale(1.04); }} 94% {{ opacity: 0; transform: scale(1); }} 100% {{ opacity: 1; transform: scale(1); }} }}
        @keyframes fadeSlide2 {{ 0% {{ opacity: 0; transform: scale(1); }} 18% {{ opacity: 0; transform: scale(1); }} 24% {{ opacity: 1; transform: scale(1); }} 42% {{ opacity: 1; transform: scale(1.03); }} 48% {{ opacity: 0; transform: scale(1.04); }} 100% {{ opacity: 0; transform: scale(1); }} }}
        @keyframes fadeSlide3 {{ 0% {{ opacity: 0; transform: scale(1); }} 42% {{ opacity: 0; transform: scale(1); }} 48% {{ opacity: 1; transform: scale(1); }} 66% {{ opacity: 1; transform: scale(1.03); }} 72% {{ opacity: 0; transform: scale(1.04); }} 100% {{ opacity: 0; transform: scale(1); }} }}
        @keyframes fadeSlide4 {{ 0% {{ opacity: 0; transform: scale(1); }} 66% {{ opacity: 0; transform: scale(1); }} 72% {{ opacity: 1; transform: scale(1); }} 90% {{ opacity: 1; transform: scale(1.03); }} 96% {{ opacity: 0; transform: scale(1.04); }} 100% {{ opacity: 0; transform: scale(1); }} }}
        @keyframes fadeSlide5 {{ 0% {{ opacity: 0; transform: scale(1); }} 90% {{ opacity: 0; transform: scale(1); }} 96% {{ opacity: 1; transform: scale(1); }} 100% {{ opacity: 1; transform: scale(1.02); }} }}

        .stApp {{ background: transparent !important; }}
        .main .block-container {{ background-color: transparent; padding: 2rem 3rem; }}
        section[data-testid="stSidebar"] {{ background: linear-gradient(180deg, rgba(232, 245, 233, 0.9) 0%, rgba(200, 230, 201, 0.9) 100%); }}
        
        h1, h2, h3, h4, h5, h6, p, span, li, label, div[data-testid="stMarkdownContainer"] {{
            color: #FFFFFF !important;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.9) !important;
        }}
        
        [data-testid="stVerticalBlock"] [data-testid="stContainer"] {{
            background-color: rgba(4, 25, 12, 0.95) !important;
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 14px;
            padding: 1.5rem;
            box-shadow: 0 10px 35px 0 rgba(0, 0, 0, 0.5);
        }}
        
        .stButton>button {{
            background: linear-gradient(135deg, {primary_color} 0%, #2E7D32 100%);
            color: white; border-radius: 8px; border: none; padding: 0.7rem 2rem;
            font-weight: bold; letter-spacing: 0.5px;
            transition: all 0.2s ease;
        }}
        .stButton>button:hover {{
            background: linear-gradient(135deg, #00695C 0%, #1B5E20 100%);
            transform: translateY(-2px);
        }}
        
        [data-testid="stMetricValue"] {{
            color: {accent_green} !important; font-weight: 700;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.95);
        }}
        
        [data-testid="stFileUploader"] {{
            background-color: rgba(15, 40, 22, 0.85); padding: 1rem;
            border-radius: 12px; border: 2px dashed #81C784;
        }}
        
        [data-testid="stFileUploader"] button {{
            background-color: {upload_button_color} !important;
            color: white !important;
            border: none !important;
        }}
        </style>
        
        <div class="bg-container">
            <div class="bg-slide slide-1"></div>
            <div class="bg-slide slide-2"></div>
            <div class="bg-slide slide-3"></div>
            <div class="bg-slide slide-4"></div>
            <div class="bg-slide slide-5"></div>
        </div>
        """, unsafe_allow_html=True)

        if uploaded_file is None or st.session_state['last_language'] != language:
            st.session_state['analysis_done'] = False
            st.session_state['last_prediction'] = None
            st.session_state['last_confidence'] = None
            st.session_state['last_confidence_margin'] = None
            st.session_state['last_severity_stage'] = None
            st.session_state['last_severity_pct'] = None
            st.session_state['last_diagnosis_notice'] = None
            st.session_state['last_diagnosis_available'] = False
            st.session_state['last_language'] = language

        if analyze_triggered and uploaded_file is not None:
            st.session_state['analysis_done'] = True
            st.session_state['selected_crop'] = selected_crop
            class_indices = supported_class_indices(selected_crop)
            diagnosis_available = bool(class_indices)
            is_healthy_prediction = False
            epidemiological_label = None
            diagnosis_guide_key = None
            if not diagnosis_available:
                predicted_label = T["unsupported_crop_msg"]
                confidence_val = 0.0
                confidence_margin_val = 0.0
                stage, pct = "Not available", 0.0
                diagnosis_notice = T["unsupported_crop_msg"]
            else:
                input_meta = session.get_inputs()[0]
                input_shape = input_meta.shape
                if len(input_shape) != 4:
                    raise ValueError(f"Expected a 4D image input, got model input shape {input_shape}.")

                channels_first = input_shape[1] == 3 and input_shape[-1] != 3
                height_axis, width_axis = (2, 3) if channels_first else (1, 2)
                input_height = input_shape[height_axis] if isinstance(input_shape[height_axis], int) else 224
                input_width = input_shape[width_axis] if isinstance(input_shape[width_axis], int) else 224
                img_resized = image.convert("RGB").resize((input_width, input_height), Image.Resampling.BILINEAR)
                img_array = np.asarray(img_resized, dtype=np.float32) / 255.0
                img_array = (img_array - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array(
                    [0.229, 0.224, 0.225], dtype=np.float32
                )
                if channels_first:
                    img_array = np.transpose(img_array, (2, 0, 1))
                processed_image_array = np.expand_dims(img_array, axis=0).astype(np.float32)

                predictions = session.run(None, {input_meta.name: processed_image_array})[0]
                prediction_scores = np.asarray(predictions, dtype=np.float32).reshape(-1)
                if prediction_scores.size != len(plant_disease_labels):
                    raise ValueError(
                        f"Model returned {prediction_scores.size} scores for "
                        f"{len(plant_disease_labels)} configured labels."
                    )
                if not np.all(np.isfinite(prediction_scores)):
                    raise ValueError("Model returned non-finite classification scores.")
                if np.all((prediction_scores >= 0) & (prediction_scores <= 1)) and np.isclose(
                    np.sum(prediction_scores), 1.0, atol=1e-3
                ):
                    probabilities = prediction_scores
                else:
                    shifted_scores = prediction_scores - np.max(prediction_scores)
                    exp_scores = np.exp(shifted_scores)
                    probabilities = exp_scores / np.sum(exp_scores)

                predicted_index = max(class_indices, key=lambda index: probabilities[index])
                confidence_val = float(probabilities[predicted_index]) * 100
                supported_scores = sorted(
                    (float(probabilities[index]) for index in class_indices),
                    reverse=True,
                )
                confidence_margin_val = (
                    (supported_scores[0] - supported_scores[1]) * 100
                    if len(supported_scores) > 1 else supported_scores[0] * 100
                )
                crop_label, disease_label = split_plant_disease_label(plant_disease_labels[predicted_index])
                is_healthy_prediction = disease_label is None
                if confidence_val < 55.0:
                    predicted_label = T["low_confidence_msg"]
                    diagnosis_available = False
                    stage, pct = "Not available", 0.0
                    diagnosis_notice = T["low_confidence_msg"]
                elif is_healthy_prediction:
                    predicted_label = f"Healthy {crop_label}"
                    diagnosis_guide_key = "healthy"
                    stage, pct = "No disease class identified", 0.0
                    diagnosis_notice = T["healthy_class_msg"]
                else:
                    predicted_label = f"{crop_label}: {disease_label}"
                    diagnosis_guide_key = find_disease_guide_key(selected_crop, disease_label)
                    epidemiological_label = (
                        disease_guide_data.DISEASES[diagnosis_guide_key]["epi"]
                        if diagnosis_guide_key else disease_label
                    )
                    stage, pct = analyze_leaf_severity(image)
                    diagnosis_notice = None

            st.session_state['last_prediction'] = predicted_label
            st.session_state['last_confidence'] = confidence_val
            st.session_state['last_confidence_margin'] = confidence_margin_val
            st.session_state['last_severity_stage'] = stage
            st.session_state['last_severity_pct'] = pct
            st.session_state['last_diagnosis_notice'] = diagnosis_notice
            st.session_state['last_diagnosis_available'] = diagnosis_available
            st.session_state['last_disease_guide'] = diagnosis_guide_key

            log_outcome = None
            if diagnosis_available and not is_healthy_prediction:
                decision = di.logging_decision(assessment, "Verified Farm Field Sample" in sample_source_type)
                log_outcome = {"status": "BLOCKED", "blockers": decision["blockers"]}
                if decision["allow"]:
                    fingerprint = assessment["fingerprint"]
                    if not di.claim_field_image(fingerprint, st.session_state.get('logged_in_user_id', 1), selected_hub_label):
                        log_outcome["blockers"] = [{"code": "DUPLICATE", "params": {}}]
                    elif log_scan_telemetry(
                        hub_region=selected_hub_label,
                        target_crop=selected_crop,
                        disease_name=epidemiological_label,
                        confidence=confidence_val,
                        severity_stage=stage,
                        severity_pct=pct,
                        **epi_scan_location(selected_hub_label)
                    ):
                        log_outcome = {"status": "LOGGED", "blockers": []}
                    else:
                        di.release_field_image(fingerprint["sha256"])
                        log_outcome = {"status": "FAILED", "blockers": []}
            st.session_state['last_log_outcome'] = log_outcome

        with right_col:
            st.markdown("<div id='tour-target-results'></div>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown(f"### 📊 2. {T['results_header']}")
                
                if st.session_state['analysis_done']:
                    raw_label = st.session_state['last_prediction']
                    confidence = st.session_state['last_confidence']
                    chosen_crop = st.session_state['selected_crop']
                    sev_stage = st.session_state['last_severity_stage']
                    sev_pct = st.session_state['last_severity_pct']
                    
                    st.info(T["analysis_complete_msg"])
                    di.render_log_outcome(st, T, st.session_state.get('last_log_outcome'))
                    st.info(f"**{T['crop_context_lbl']}** {chosen_crop}")
                    if st.session_state.get('last_diagnosis_available'):
                        st.info(f"**{T['pattern_match_lbl']}** {raw_label}")
                    if st.session_state.get('last_diagnosis_notice'):
                        st.warning(st.session_state['last_diagnosis_notice'])
                    st.caption(T["diagnosis_disclaimer"])
                    
                    if st.session_state.get('last_diagnosis_available'):
                        m_col1, m_col2 = st.columns(2)
                        m_col1.metric(T["ai_conf_lbl"], f"{confidence:.1f}%")
                        m_col2.metric(T["inf_sev_lbl"], f"{sev_pct:.1f}%")
                        confidence_margin = st.session_state.get("last_confidence_margin")
                        if confidence_margin is not None:
                            st.caption(
                                f"{T['ai_margin_lbl']}: {confidence_margin:.1f}. "
                                f"{T['quality_confidence_caution']}"
                            )
                        st.markdown(f"**{T['prog_status_lbl']}** `{sev_stage}`")
                        render_disease_guide(
                            st.session_state.get("last_disease_guide"),
                            chosen_crop,
                            language,
                            sev_stage,
                        )

                    if not st.session_state.get('last_diagnosis_notice'):
                        st.markdown("---")
                        st.markdown(f"### 3. {T['treatment_header']}")
                        if language == "Kiswahili":
                            audio_text = f"Matokeo ya uchunguzi wa {chosen_crop}. Ugonjwa uliotambuliwa ni {raw_label} kwa uhakika wa asilimia {confidence:.0f}. Mabadiliko ya rangi yanakadiriwa kuwa asilimia {sev_pct:.0f}."
                        elif language == "French":
                            audio_text = f"Résultats du dépistage pour {chosen_crop}. Classe identifiée : {raw_label}, confiance {confidence:.0f} pour cent. Décoloration visible estimée à {sev_pct:.0f} pour cent."
                        else:
                            audio_text = f"Screening result for {chosen_crop}: {raw_label}, with {confidence:.1f} percent model confidence. Estimated visible discoloration is {sev_pct:.1f} percent."
                        if sev_stage.startswith("Stage 3"):
                            st.error(T["stage3_alert"])
                        elif sev_stage.startswith("Stage 2"):
                            st.warning(T["stage2_alert"])
                        elif sev_stage.startswith("Stage 1"):
                            st.success(T["stage1_alert"])
                        render_tts_audio_controls(audio_text, tts_lang)

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown(f"### {T['hub_support_header']} ({selected_hub_label})")
                    st.info(T["hub_support_info"])
                    
                    for av in active_zone_data["resources"]:
                        with st.expander(f"🏪 {av['name']} ({av['location']})"):
                            st.write(f"**Location / Scope:** {av['location']}")
                            st.write(f"**Primary Contact:** `{av['contact']}`")
                            st.write(f"**Specialization:** {av['specialty']}")
                else:
                    st.info(T["diagnostic_empty_prompt"])
                    st.markdown("<br><br><br>", unsafe_allow_html=True)

    diagnostic_workflow()

# --- FOOTER ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f"<div style='text-align: center; color: #FFFFFF; text-shadow: 1px 1px 3px rgba(0,0,0,0.9); font-weight: 500;'>"
    f"{T['footer_text']} ({selected_hub_label})"
    f"</div>", 
    unsafe_allow_html=True
)