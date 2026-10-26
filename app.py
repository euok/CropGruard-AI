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
import importlib
import types
import hashlib
import io
import csv
import threading
import html
from html import escape as html_escape
import requests
from collections import OrderedDict
import re
import uuid
import disease_data as disease_guide_data
import cropguard_consensus

# --- SETUP & CONFIGURATION ---
st.set_page_config(
    page_title="CropGuard AI",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

def _google_oidc_is_configured():
    try:
        auth_config = st.secrets["auth"]
        google_config = auth_config["google"]
        return all((
            auth_config["redirect_uri"],
            auth_config["cookie_secret"],
            google_config["client_id"],
            google_config["client_secret"],
            google_config["server_metadata_url"],
        ))
    except (AttributeError, FileNotFoundError, KeyError, TypeError):
        return False


google_user = st.user
if not google_user.get("is_logged_in", False):
    st.markdown(
        """
        <style>
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            min-height: 100vh;
            background: linear-gradient(135deg, #0d1f14 0%, #10251a 48%, #121212 100%) !important;
        }
        [data-testid="stSidebar"],
        [data-testid="stHeader"] {
            display: none !important;
        }
        [data-testid="stMainBlockContainer"] {
            max-width: 1040px;
            min-height: 100vh;
            padding: 5vh 1.5rem 4vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .st-key-cg-login-card {
            max-width: 760px;
            width: 100%;
            margin: 0 auto;
            padding: clamp(1.5rem, 4vw, 3rem);
            background: linear-gradient(145deg, rgba(24, 46, 33, .82), rgba(17, 25, 20, .88));
            border: 1px solid rgba(190, 225, 196, .24);
            border-radius: 24px;
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            box-shadow: 0 28px 80px rgba(0, 0, 0, .48), inset 0 1px 0 rgba(255, 255, 255, .08);
            text-align: center;
        }
        .st-key-cg-login-card h1 {
            color: #f4fff5 !important;
            font-size: clamp(2.1rem, 5vw, 3.25rem);
            letter-spacing: -.045em;
            margin: 0 0 .5rem;
            text-shadow: none !important;
        }
        .st-key-cg-login-card p,
        .st-key-cg-login-card span {
            color: #d4e5d7 !important;
            text-shadow: none !important;
        }
        .cg-login-subtitle {
            margin: 0 auto 1.8rem;
            font-size: clamp(1rem, 2vw, 1.2rem);
            color: #b7d4bd !important;
            line-height: 1.6;
        }
        .cg-login-features {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: .8rem;
            margin: 1.5rem 0 1.75rem;
            text-align: left;
        }
        .cg-login-feature {
            min-height: 112px;
            padding: 1rem;
            border: 1px solid rgba(190, 225, 196, .16);
            border-radius: 14px;
            background: rgba(5, 18, 11, .42);
        }
        .cg-login-feature strong {
            display: block;
            margin-bottom: .4rem;
            color: #e4f6e7;
            font-size: .96rem;
        }
        .cg-login-feature span {
            display: block;
            color: #b9cdbd;
            font-size: .84rem;
            line-height: 1.45;
        }
        .st-key-cg-google-login button {
            width: 100%;
            min-height: 3.15rem;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: .7rem;
            background: #fff !important;
            color: #303134 !important;
            border: 1px solid #dadce0 !important;
            border-radius: 8px !important;
            box-shadow: 0 2px 5px rgba(0, 0, 0, .18) !important;
            font-size: 1rem !important;
            font-weight: 600 !important;
            text-shadow: none !important;
            transition: box-shadow .18s ease, background-color .18s ease, transform .18s ease;
        }
        .st-key-cg-google-login button::before {
            content: "";
            width: 22px;
            height: 22px;
            flex: 0 0 22px;
            background-repeat: no-repeat;
            background-position: center;
            background-size: contain;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Cpath fill='%23EA4335' d='M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z'/%3E%3Cpath fill='%234285F4' d='M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.76 7.18l7.73 6C44.42 37.96 46.98 31.86 46.98 24.55z'/%3E%3Cpath fill='%23FBBC05' d='M10.53 28.59A14.4 14.4 0 0 1 9.75 24c0-1.59.27-3.13.76-4.59l-7.98-6.19A23.9 23.9 0 0 0 0 24c0 3.87.93 7.54 2.56 10.78l7.97-6.19z'/%3E%3Cpath fill='%2334A853' d='M24 48c6.48 0 11.93-2.13 15.91-5.8l-7.73-6c-2.15 1.45-4.92 2.3-8.18 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z'/%3E%3C/svg%3E");
        }
        .st-key-cg-google-login button:hover {
            background: #f8faff !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, .28) !important;
            transform: translateY(-1px);
        }
        .st-key-cg-google-login button p {
            color: #303134 !important;
            text-shadow: none !important;
        }
        .st-key-cg-login-card [data-testid="stAlert"] {
            text-align: left;
        }
        .cg-login-footer {
            max-width: 590px;
            margin: 1.5rem auto 0;
            color: #a9c0ae !important;
            font-size: .82rem;
            line-height: 1.55;
        }
        @media (max-width: 680px) {
            [data-testid="stMainBlockContainer"] {
                padding: 1rem .75rem;
            }
            .st-key-cg-login-card {
                padding: 1.5rem 1.1rem;
                border-radius: 18px;
            }
            .cg-login-features {
                grid-template-columns: 1fr;
            }
            .cg-login-feature {
                min-height: auto;
            }
        }
        @media (prefers-reduced-motion: reduce) {
            .st-key-cg-google-login button { transition: none; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="cg-login-card"):
        st.markdown("# 🌱 CropGuard AI")
        st.markdown(
            '<p class="cg-login-subtitle">Climate-Smart Crop Pathology &amp; '
            'Extension Assistant</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="cg-login-features">
              <div class="cg-login-feature">
                <strong>⚡ Instant Diagnostics</strong>
                <span>AI-driven disease identification</span>
              </div>
              <div class="cg-login-feature">
                <strong>👨‍🌾 Farmer-First</strong>
                <span>Clear, jargon-free management plans</span>
              </div>
              <div class="cg-login-feature">
                <strong>🏪 Agro-Vet Network</strong>
                <span>Connect directly to local support &amp; cures</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="cg-login-subtitle" style="font-size:.95rem;margin-bottom:1rem">'
            "Sign in securely with Google to continue</p>",
            unsafe_allow_html=True,
        )
        if _google_oidc_is_configured():
            with st.container(key="cg-google-login"):
                if st.button(
                    "Continue with Google",
                    key="google_oidc_login",
                    use_container_width=True,
                ):
                    st.login("google")
        else:
            st.error(
                "Google sign-in is not configured. Add the OAuth settings to "
                "`.streamlit/secrets.toml` and register this app's redirect URI in Google Cloud."
            )
        st.markdown(
            '<p class="cg-login-footer">CropGuard AI • Protecting crops, securing yields, '
            'and scaling climate-smart food systems for farmers everywhere.</p>',
            unsafe_allow_html=True,
        )
    st.stop()

google_email = str(google_user.get("email", "")).strip()
if not google_email:
    st.error("Google sign-in did not provide an email address. Contact the administrator.")
    st.stop()
google_name = str(google_user.get("name") or google_email).strip()
st.session_state["user_email"] = google_email
st.session_state["user_display_name"] = google_name
st.session_state["auth_method"] = "Google OIDC"

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
        "tour_btn": "Replay guided tour",
        "crop_select_prompt": "Select Target Crop Type (Hub Priority):",
        "crop_select_header": "🌾 Select Crop Context",
        "upload_header": "📥 1.",
        "upload_label_text": "Upload or snap an image of an affected crop leaf...",
        "quality_integrity_header": "Quality & integrity checks",
        "leaf_upload_help": "Use a clear, well-lit photo of one affected leaf.",
        "image_open_error": "Could not open or assess this image: {error}",
        "scan_another_btn": "🔄 Scan Another Leaf",
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
        "hub_support_info": "Regional resources are selected automatically using your GPS-matched hub when location access is available; otherwise, the currently selected region is used.",
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
        "tour_btn": "Rudia ziara elekezi",
        "crop_select_prompt": "Chagua Aina ya Mmea unaochunguzwa:",
        "crop_select_header": "🌾 Chagua Muktadha wa Mmea",
        "upload_header": "📥 1.",
        "upload_label_text": "Pakia au piga picha ya jani la mmea lenye maambukizi...",
        "quality_integrity_header": "Ukaguzi wa ubora na uadilifu",
        "leaf_upload_help": "Tumia picha iliyo wazi na yenye mwanga mzuri ya jani lililoathirika.",
        "image_open_error": "Picha hii haikuweza kufunguliwa au kukaguliwa: {error}",
        "scan_another_btn": "🔄 Chunguza Jani Lingine",
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
        "hub_support_info": "Rasilimali za eneo huchaguliwa kiotomatiki kwa kutumia kituo kilicholinganishwa na GPS yako inapowezekana; vinginevyo, eneo lililochaguliwa ndilo hutumika.",
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
        "tour_btn": "Revoir la visite guidée",
        "crop_select_prompt": "Sélectionnez le type de culture cible :",
        "crop_select_header": "🌾 Contexte de la Culture",
        "upload_header": "📥 1.",
        "upload_label_text": "Téléchargez ou prenez une photo d'une feuille de culture affectée...",
        "quality_integrity_header": "Contrôles de qualité et d’intégrité",
        "leaf_upload_help": "Utilisez une photo nette et bien éclairée d’une feuille affectée.",
        "image_open_error": "Impossible d’ouvrir ou d’évaluer cette image : {error}",
        "scan_another_btn": "🔄 Analyser une autre feuille",
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
        "hub_support_info": "Les ressources régionales sont sélectionnées automatiquement selon le hub associé au GPS lorsque l’accès à la position est disponible ; sinon, la région sélectionnée est utilisée.",
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
            latitude REAL,
            longitude REAL,
            diagnosis_status TEXT,
            disease_key TEXT,
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
        ''', ('Guest', 'guest@cropguard.invalid', 'Farmer', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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
            ("2026-10-11 11:30", "Kisii, Kenya (Highland Zone)", "CropGuard Field Team", "🌾 Crop Advice", "Applying copper-based fungicides early morning helps reduce spore germination during high humidity weeks."),
            ("2026-10-11 14:15", "Kumasi, Ghana (Cocoa & Grain Belt)", "Kwame Mensah", "🛒 Marketplace / Trade", "Looking for bulk organic nematicides delivered near Kumasi central hub. Reach out if available.")
        ]
        cursor.executemany('''
            INSERT INTO farmer_community_posts (timestamp, hub_region, author_name, category_tag, message)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_posts)
        conn.commit()

    cursor.execute(
        """
        UPDATE farmer_community_posts
        SET author_name = ?
        WHERE author_name = ?
          AND category_tag = ?
          AND message = ?
        """,
        (
            "CropGuard Field Team",
            "Dr. Morara",
            "🌾 Crop Advice",
            "Applying copper-based fungicides early morning helps reduce spore germination during high humidity weeks.",
        ),
    )
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
    "latitude": "REAL",
    "longitude": "REAL",
    "diagnosis_status": "TEXT",
    "disease_key": "TEXT",
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
        conn.execute("UPDATE scan_telemetry SET latitude = lat WHERE latitude IS NULL AND lat IS NOT NULL")
        conn.execute("UPDATE scan_telemetry SET longitude = lon WHERE longitude IS NULL AND lon IS NOT NULL")
        for (raw,) in conn.execute(
                "SELECT DISTINCT target_crop FROM scan_telemetry WHERE crop_canon IS NULL").fetchall():
            conn.execute("UPDATE scan_telemetry SET crop_canon = ? "
                         "WHERE target_crop = ? AND crop_canon IS NULL", (epi_canon_crop(raw), raw))
        _epi_apply_label_rule(conn, only_unset=True)
        conn.execute(
            """UPDATE scan_telemetry
               SET diagnosis_status = CASE WHEN label_ok = 1 THEN 'LIKELY' ELSE 'POSSIBLE' END
               WHERE diagnosis_status IS NULL OR diagnosis_status = ''"""
        )
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
                severity_stage, severity_percentage, lat, lon, latitude, longitude, diagnosis_status,
                disease_key, loc_source, reporter_key, crop_canon, label_ok, is_demo, model_tag)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (st.session_state.get("logged_in_user_id", 1), datetime.now().strftime(EPI_TS_FMT),
             hub_region, target_crop, disease_name, confidence, severity_stage, severity_pct,
             lat, lon, lat, lon, "LIKELY" if label_ok else "POSSIBLE",
             find_disease_guide_key(target_crop, disease_name), loc_source, epi_reporter_key(),
             epi_canon_crop(target_crop), 1 if label_ok else 0, EPI_MODEL_TAG),
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
    st.markdown("""
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

def sync_google_user_profile(email, display_name):
    conn = sqlite3.connect("cropguard_surveillance.db", check_same_thread=False)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE identifier = ?", (email,))
        user_row = cursor.fetchone()
        if user_row:
            user_id = user_row[0]
            cursor.execute(
                "UPDATE users SET display_name = ? WHERE user_id = ?",
                (display_name, user_id),
            )
        else:
            cursor.execute(
                """
                INSERT INTO users (account_type, identifier, display_name, created_at)
                VALUES (?, ?, ?, ?)
                """,
                ("Google", email, display_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            user_id = cursor.lastrowid
        conn.commit()
        return user_id
    finally:
        conn.close()


st.session_state["logged_in_user_id"] = sync_google_user_profile(
    google_email,
    google_name,
)
st.session_state["user_identifier"] = google_email

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

MODEL_SCREENING_MIN_SCORE_PCT = 55.0
MODEL_SCREENING_MIN_MARGIN_PCT = 5.0


def _consensus_configuration():
    keys = (
        "GEMINI_API_KEY", "GEMINI_CHAT_MODEL",
        "OLLAMA_BASE_URL", "OLLAMA_MODEL",
        "SERPER_API_KEY", "AGENT_TIMEOUT_SECONDS",
    )
    configuration = {
        key: os.environ.get(key, "").strip()
        for key in keys
    }
    try:
        for key in keys:
            value = st.secrets.get(key)
            if not configuration[key] and isinstance(value, str) and value.strip():
                configuration[key] = value.strip()
    except (FileNotFoundError, KeyError, RuntimeError):
        pass
    try:
        timeout_seconds = float(configuration["AGENT_TIMEOUT_SECONDS"] or 30.0)
        if not 1.0 <= timeout_seconds <= 120.0:
            raise ValueError("timeout must be between 1 and 120 seconds")
        configuration["AGENT_TIMEOUT_SECONDS"] = timeout_seconds
    except ValueError as error:
        st.warning(f"Invalid AGENT_TIMEOUT_SECONDS setting ({error}); using 30 seconds.")
        configuration["AGENT_TIMEOUT_SECONDS"] = 30.0
    return configuration


def render_consensus_report(report, language, search_config=None):
    if not report:
        return

    labels = {
        "English": {
            "title": "🤝 Multi-agent screening consensus",
            "confidence": "Consensus index (not calibrated)",
            "agreement": "Agent agreement",
            "local_differs": "Secondary local cross-check available",
            "crosscheck_details": "Secondary cross-check details",
            "health": "Health status",
            "vision": "Vision assessment",
            "crosscheck": "Secondary cross-check",
            "grounding": "Live regional grounding",
            "symptoms": "Visible symptoms",
            "alternatives": "Lookalikes / alternatives",
            "not_configured": "Not configured",
            "no_symptoms": "No specific visual symptoms returned.",
            "no_alternatives": "No alternatives were returned.",
            "no_sources": "Live search is not configured or returned no usable sources.",
            "search_error": "Serper search error details",
            "search_not_requested": "Regional search has not been requested.",
            "search_confirm": "I want to run a regional web search (uses Serper credits).",
            "search_submit": "Run regional search",
            "notes": "Screening notes",
            "vision_error": "Image screening was unavailable; a local fallback was used",
        },
        "Kiswahili": {
            "title": "🤝 Makubaliano ya uchunguzi wa mawakala wengi",
            "confidence": "Kielezo cha makubaliano (hakijathibitishwa)",
            "agreement": "Makubaliano ya mawakala",
            "local_differs": "Ukaguzi wa pili wa ndani unapatikana",
            "crosscheck_details": "Maelezo ya ukaguzi wa pili",
            "health": "Hali ya afya",
            "vision": "Tathmini ya picha",
            "crosscheck": "Ukaguzi wa pili",
            "grounding": "Taarifa za moja kwa moja za eneo",
            "symptoms": "Dalili zinazoonekana",
            "alternatives": "Magonjwa yanayofanana / mbadala",
            "not_configured": "Haijawekwa",
            "no_symptoms": "Hakuna dalili maalum za picha zilizoripotiwa.",
            "no_alternatives": "Hakuna magonjwa mbadala yaliyoripotiwa.",
            "no_sources": "Utafutaji wa moja kwa moja haujawekwa au haujapata vyanzo.",
            "search_error": "Maelezo ya hitilafu ya utafutaji wa Serper",
            "search_not_requested": "Utafutaji wa eneo bado haujaombwa.",
            "search_confirm": "Nataka kutafuta kwenye wavuti wa eneo (hutumia salio la Serper).",
            "search_submit": "Anzisha utafutaji wa eneo",
            "notes": "Maelezo ya uchunguzi",
            "vision_error": "Uchunguzi wa picha haukupatikana; mfumo wa ndani umetumika",
        },
        "French": {
            "title": "🤝 Consensus de dépistage multi-agents",
            "confidence": "Indice de consensus (non calibré)",
            "agreement": "Accord des agents",
            "local_differs": "Vérification locale secondaire disponible",
            "crosscheck_details": "Détails de la vérification secondaire",
            "health": "État sanitaire",
            "vision": "Évaluation visuelle",
            "crosscheck": "Vérification secondaire",
            "grounding": "Sources régionales en direct",
            "symptoms": "Symptômes visibles",
            "alternatives": "Diagnostics ressemblants / alternatifs",
            "not_configured": "Non configuré",
            "no_symptoms": "Aucun symptôme visuel précis n'a été rapporté.",
            "no_alternatives": "Aucun diagnostic alternatif n'a été rapporté.",
            "no_sources": "La recherche en direct n'est pas configurée ou n'a fourni aucune source.",
            "search_error": "Détails de l'erreur de recherche Serper",
            "search_not_requested": "La recherche régionale n'a pas été demandée.",
            "search_confirm": "Je souhaite lancer une recherche régionale (utilise des crédits Serper).",
            "search_submit": "Lancer la recherche régionale",
            "notes": "Notes de dépistage",
            "vision_error": "L’analyse de l’image était indisponible ; un modèle local a été utilisé",
        },
    }
    text = labels.get(language, labels["English"])
    with st.expander(text["title"], expanded=True):
        vision_error = report.get("vision", {}).get("error")
        if vision_error:
            st.warning(text["vision_error"])
        vision_name = text["vision"]
        reasoner_name = text["crosscheck"]
        agreement_text = str(report.get("agreement") or "")
        local_disagreement = "disagree" in agreement_text.casefold()
        agreement_display = (
            agreement_text.replace("Gemini", "image assessment")
            .replace("gemini", "image assessment")
        )
        metrics = (
            (text["confidence"], f"{report['consensus_confidence_index']:.1f}%"),
            (text["health"], report["health_status"].replace("_", " ").title()),
        )
        if not local_disagreement:
            metrics += ((text["agreement"], agreement_display),)
        metric_cards = "".join(
            "<div style='flex:1 1 180px; min-width:0;'>"
            f"<div style='font-size:0.85rem; line-height:1.4; overflow-wrap:anywhere;'>"
            f"{html.escape(str(label))}</div>"
            f"<div style='font-size:1.5rem; font-weight:700; line-height:1.3; "
            f"overflow-wrap:anywhere; white-space:normal;'>{html.escape(str(value))}</div>"
            "</div>"
            for label, value in metrics
        )
        st.markdown(
            f"<div style='display:flex; flex-wrap:wrap; gap:1rem;'>{metric_cards}</div>",
            unsafe_allow_html=True,
        )

        st.markdown(f"**{report['detected_crop']} — {report['primary_diagnosis']}**")
        if local_disagreement:
            st.caption(text["local_differs"])
        tabs = st.tabs([text["vision"], text["crosscheck"], text["grounding"]])
        with tabs[0]:
            st.caption(f"{vision_name} · screening score {report['vision'].get('confidence_score', 0.0):.2f}")
            symptoms = report.get("visual_symptoms") or []
            st.markdown(
                "\n".join(f"- {symptom}" for symptom in symptoms)
                if symptoms else text["no_symptoms"]
            )
        with tabs[1]:
            reasoning = report["reasoning"]
            st.caption(reasoner_name)
            alternatives = reasoning.get("alternatives") or []
            explanation = reasoning.get("explanation") or text["not_configured"]
            if local_disagreement:
                with st.expander(text["crosscheck_details"]):
                    st.caption(explanation)
                    st.markdown(
                        f"**{text['alternatives']}**\n\n"
                        + (
                            "\n".join(f"- {name}" for name in alternatives)
                            if alternatives else text["no_alternatives"]
                        )
                    )
            else:
                st.write(explanation)
                st.markdown(
                    f"**{text['alternatives']}**\n\n"
                    + (
                        "\n".join(f"- {name}" for name in alternatives)
                        if alternatives else text["no_alternatives"]
                    )
                )
        with tabs[2]:
            grounding = report["web_grounding"]
            if grounding.get("message") == "Regional search has not been requested.":
                st.caption(text["search_not_requested"])
            with st.form("regional_search_request"):
                search_confirmed = st.checkbox(
                    text["search_confirm"],
                    value=False,
                    key="confirm_regional_search",
                )
                search_submitted = st.form_submit_button(text["search_submit"])
            if search_submitted and search_confirmed:
                vision_report = report.get("vision") or {}
                with st.spinner("Searching regional sources..."):
                    search_result = cropguard_consensus.run_regional_search(
                        selected_crop=report.get("detected_crop") or "",
                        region=report.get("region") or "",
                        diagnosis_hint=vision_report.get("primary_diagnosis")
                        or report.get("primary_diagnosis")
                        or "",
                        config=search_config or {},
                    )
                report = dict(report)
                report["web_grounding"] = {
                    "available": search_result.available,
                    "results": search_result.results,
                    "message": search_result.message,
                    "error": search_result.error,
                }
                st.session_state["last_consensus_report"] = report
            elif search_submitted:
                st.info(text["search_not_requested"])
            grounding = report["web_grounding"]
            st.info(grounding.get("message") or text["no_sources"])
            if grounding.get("error"):
                with st.expander(text["search_error"]):
                    st.code(grounding["error"])
            for result in grounding.get("results", []):
                with st.container(border=True):
                    st.markdown(f"**{result.get('title', 'Source')}**")
                    st.write(result.get("snippet", ""))
                    url = result.get("url", "")
                    if url.startswith(("https://", "http://")):
                        st.link_button("Open source", url)
        notes = [
            note for note in (report.get("notes") or [])
            if "gemini" not in str(note).casefold()
        ]
        if notes:
            with st.expander(text["notes"]):
                for note in notes:
                    st.caption(note)


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
    raw_crop = str(crop_name or "").casefold()
    normalized_crop = f" {_normalize_guide_text(raw_crop)} "
    matching_families = []
    for family, crop_info in disease_guide_data.CROP_FAMILIES.items():
        synonyms = crop_info[3]
        for synonym in synonyms:
            normalized_synonym = _normalize_guide_text(synonym)
            if family == "tea" and normalized_synonym == "the" and not re.search(
                r"\bthé\b", raw_crop
            ):
                continue
            if normalized_synonym and f" {normalized_synonym} " in normalized_crop:
                matching_families.append((len(normalized_synonym), family))
    if not matching_families:
        return None
    longest_match = max(length for length, _ in matching_families)
    best_families = {family for length, family in matching_families if length == longest_match}
    return next(iter(best_families)) if len(best_families) == 1 else None

def find_disease_guide_key(crop_name, disease_name):
    family = _guide_crop_family(crop_name)
    normalized_disease = _normalize_guide_text(disease_name)
    if not family or not normalized_disease:
        return None

    exact_matches = set()
    contained_matches = {}
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
                exact_matches.add(key)
            elif f" {normalized_variant} " in padded_disease:
                contained_matches[key] = max(
                    contained_matches.get(key, 0), len(normalized_variant)
                )
            elif padded_disease in f" {normalized_variant} ":
                contained_matches[key] = max(
                    contained_matches.get(key, 0), len(normalized_disease)
                )
    if len(exact_matches) == 1:
        return next(iter(exact_matches))
    if exact_matches:
        return None
    if not contained_matches:
        return None
    best_length = max(contained_matches.values())
    best_matches = {
        key for key, length in contained_matches.items() if length == best_length
    }
    return next(iter(best_matches)) if len(best_matches) == 1 else None


HUB_COUNTRIES = {
    "Kisii, Kenya (Highland Zone)": "Kenya",
    "Eldoret, Kenya (Rift Valley Grain Basket)": "Kenya",
    "Nakuru, Kenya (Rift Valley Horticultural Hub)": "Kenya",
    "Morogoro, Tanzania (Agricultural Research Hub)": "Tanzania",
    "Ibadan, Nigeria (Agricultural Research & Maize Belt)": "Nigeria",
    "Kumasi, Ghana (Cocoa & Grain Belt)": "Ghana",
}

# Kenya-specific chemical action codes reviewed for the listed crop families.
# Keep this allowlist limited to actions supported by local extension guidance.
VERIFIED_CHEMICAL_ACTIONS_BY_COUNTRY_AND_CROP = {
    "Kenya": {
        "maize": frozenset({
            "CHEM_COPPER", "CHEM_SYSTEMIC", "CHEM_CATERPILLAR", "CHEM_VECTOR",
        }),
        "potato": frozenset({
            "CHEM_COPPER", "CHEM_LATE_BLIGHT", "CHEM_PROTECTANT",
            "CHEM_SYSTEMIC", "CHEM_CATERPILLAR",
        }),
        "tomato": frozenset({
            "CHEM_COPPER", "CHEM_LATE_BLIGHT", "CHEM_PROTECTANT",
            "CHEM_SYSTEMIC", "CHEM_CATERPILLAR", "CHEM_VECTOR",
        }),
        "beans": frozenset({
            "CHEM_COPPER", "CHEM_PROTECTANT", "CHEM_SYSTEMIC", "CHEM_VECTOR",
        }),
        "tea": frozenset({"CHEM_COPPER", "CHEM_SYSTEMIC"}),
        "coffee": frozenset({"CHEM_COFFEE", "CHEM_COPPER"}),
        "banana": frozenset({
            "CHEM_COPPER", "CHEM_PROTECTANT", "CHEM_SYSTEMIC",
        }),
        "brassica": frozenset({
            "CHEM_COPPER", "CHEM_PROTECTANT", "CHEM_SYSTEMIC",
            "CHEM_CATERPILLAR",
        }),
    },
}

CHEMICAL_ACTION_CODES = frozenset(
    code
    for entry in disease_guide_data.DISEASES.values()
    for code in entry.get("chem", [])
)

_GUIDE_UI_TEXT = {
    "English": {
        "title": "🌿 Disease reference guide",
        "signs": "Common signs",
        "now": "What to do now",
        "cult": "Field practices",
        "bio": "Biological options",
        "chem": "Chemical options",
        "prev": "Prevention",
        "severe": "Severe cases",
        "caution": "Use only products registered for this crop and use in your country. Follow the product label, protective-equipment instructions, re-entry interval, and pre-harvest interval; confirm treatment with an agricultural extension officer.",
        "withheld": "Chemical options are withheld because CropGuard has no verified, crop-specific pesticide registration data for this country. Consult your national agricultural authority or extension officer.",
        "country_unknown": "Chemical options are withheld because the selected hub has no verified country registration mapping.",
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
        "caution": "Tumia bidhaa zilizosajiliwa kwa zao na matumizi haya nchini kwako pekee. Fuata lebo, maelekezo ya vifaa vya kujikinga, muda wa kuingia tena shambani na muda wa kusubiri kabla ya kuvuna; thibitisha matibabu kwa afisa wa ugani.",
        "withheld": "Chaguo za kemikali zimezuiwa kwa sababu CropGuard haina data iliyothibitishwa ya usajili wa viuatilifu kwa zao hili nchini. Wasiliana na mamlaka ya kilimo au afisa wa ugani wa nchi yako.",
        "country_unknown": "Chaguo za kemikali zimezuiwa kwa sababu kituo kilichochaguliwa hakina ulinganisho wa nchi uliothibitishwa.",
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
        "caution": "N'utilisez que des produits homologués pour cette culture et cet usage dans votre pays. Respectez l'étiquette, les équipements de protection, le délai de rentrée et le délai avant récolte ; faites confirmer le traitement par un conseiller agricole.",
        "withheld": "Les options chimiques sont masquées, car CropGuard ne dispose pas de données vérifiées d'homologation des pesticides pour cette culture dans ce pays. Consultez l'autorité agricole nationale ou un conseiller agricole.",
        "country_unknown": "Les options chimiques sont masquées, car le hub sélectionné n'a pas de correspondance pays vérifiée.",
    },
}


def build_disease_advisory(guide_key, crop_name, language, severity_stage, hub_label):
    entry = disease_guide_data.DISEASES.get(guide_key)
    if not entry:
        return None

    language = language if language in _GUIDE_UI_TEXT else "English"
    labels = _GUIDE_UI_TEXT[language]
    lang_index = {"English": 0, "Kiswahili": 1, "French": 2}[language]
    country = HUB_COUNTRIES.get(hub_label)
    family = _guide_crop_family(crop_name)
    allowed_chemical_codes = (
        VERIFIED_CHEMICAL_ACTIONS_BY_COUNTRY_AND_CROP
        .get(country, {})
        .get(family, frozenset())
    )

    sections = [
        ("now", "now"),
        ("cult", "cult"),
        ("bio", "bio"),
        ("chem", "chem"),
        ("prev", "prev"),
    ]
    if severity_stage.startswith("Stage 3"):
        sections.append(("severe", "severe"))

    family_actions = entry.get("extra", {}).get(family, {})
    rendered_sections = []
    has_chemical_advice = False
    allowed_chemical_advice = False
    for section_key, label_key in sections:
        codes = list(entry.get(section_key, []))
        codes.extend(family_actions.get(section_key, []))
        has_chemical_advice = has_chemical_advice or any(
            code in CHEMICAL_ACTION_CODES for code in codes
        )
        allowed_chemical_advice = allowed_chemical_advice or any(
            code in CHEMICAL_ACTION_CODES and code in allowed_chemical_codes
            for code in codes
        )
        sentences = []
        for code in codes:
            if code not in disease_guide_data.ACTIONS:
                continue
            if code in CHEMICAL_ACTION_CODES and code not in allowed_chemical_codes:
                continue
            sentences.append(disease_guide_data.ACTIONS[code][lang_index])
        sentences = list(dict.fromkeys(sentences))
        if sentences:
            rendered_sections.append((labels[label_key], sentences))
    return {
        "guide_key": guide_key,
        "crop_name": crop_name,
        "severity_stage": severity_stage,
        "title": labels["title"],
        "name": entry["name"][lang_index],
        "signs_label": labels["signs"],
        "signs": entry["signs"][lang_index],
        "sections": rendered_sections,
        "has_chemical_advice": has_chemical_advice,
        "chemical_allowed": allowed_chemical_advice,
        "chemical_notice": (
            labels["caution"] if allowed_chemical_advice
            else labels["withheld"] if country
            else labels["country_unknown"]
        ),
        "country": country,
    }


def render_disease_guide(guide_key, crop_name, language, severity_stage, hub_label):
    advisory = build_disease_advisory(
        guide_key, crop_name, language, severity_stage, hub_label
    )
    if not advisory:
        return

    st.markdown(f"#### {advisory['title']}")
    st.markdown(f"**{advisory['name']}**")
    st.markdown(f"**{advisory['signs_label']}:** {advisory['signs']}")
    if advisory["sections"]:
        action_tabs = st.tabs([heading for heading, _ in advisory["sections"]])
        for action_tab, (_, sentences) in zip(action_tabs, advisory["sections"]):
            with action_tab:
                st.markdown("\n".join(f"- {sentence}" for sentence in sentences))
    if advisory["has_chemical_advice"]:
        if advisory["chemical_allowed"]:
            st.caption(advisory["chemical_notice"])
        else:
            st.warning(advisory["chemical_notice"])


def render_missing_kb_advisory(
    advisory,
    language,
    region_resources=None,
    hub_label=None,
    crop_name=None,
    guide_key=None,
    severity_stage="",
):
    if not advisory:
        return

    headings = {
        "English": {
            "part1": "### Part 1: Farmer-Friendly Summary",
            "disease": "**Disease Detected:**",
            "cures": "**Cures & Management Options:**",
            "where": "**Where to Obtain Cures:**",
            "support": "**Regional Support Hubs & Contacts:**",
            "title": "Crop screening guidance (not a confirmed diagnosis)",
            "withheld": "No verified, crop- and country-specific chemical treatment is available here. Confirm approved options with your national agricultural authority or extension officer.",
            "verify": "Directory details and stock are not independently verified. Contact the organization before travel or purchase.",
            "no_suppliers": "No local agro-vet or input supplier is listed for this region. Ask an extension officer for a trusted supplier.",
            "no_support": "No regional extension or research contact is listed for this hub.",
            "location": "Location",
            "contact": "Contact",
            "specialty": "Specialization",
            "when_to_seek_help": "When to seek local help",
            "disclaimer": (
                "Screening guidance only—not a confirmed diagnosis. Verify treatment and "
                "local approval with a qualified agricultural extension officer."
            ),
        },
        "Kiswahili": {
            "part1": "### Sehemu ya 1: Muhtasari kwa Mkulima",
            "disease": "**Ugonjwa Uliogunduliwa:**",
            "cures": "**Tiba na Mbinu za Kudhibiti:**",
            "where": "**Mahali pa Kupata Tiba:**",
            "support": "**Vituo vya Usaidizi vya Eneo na Mawasiliano:**",
            "title": "Mwongozo wa uchunguzi wa zao (si utambuzi uliothibitishwa)",
            "withheld": "Hakuna matibabu ya kemikali yaliyothibitishwa kwa zao na nchi hii. Thibitisha chaguo zilizoidhinishwa kwa mamlaka ya kilimo au afisa wa ugani.",
            "verify": "Taarifa za mawasiliano na bidhaa hazijathibitishwa kwa kujitegemea. Wasiliana na taasisi kabla ya kusafiri au kununua.",
            "no_suppliers": "Hakuna muuzaji wa pembejeo aliyeorodheshwa katika eneo hili. Uliza afisa wa ugani akupe muuzaji anayeaminika.",
            "no_support": "Hakuna mawasiliano ya ugani au utafiti yaliyoorodheshwa kwa kituo hiki.",
            "location": "Eneo",
            "contact": "Mawasiliano",
            "specialty": "Utaalamu",
            "when_to_seek_help": "Wakati wa kutafuta msaada wa eneo",
            "disclaimer": (
                "Mwongozo wa uchunguzi pekee—si utambuzi uliothibitishwa. Thibitisha tiba "
                "na idhini yake kwa afisa wa ugani wa kilimo aliyehitimu."
            ),
        },
        "French": {
            "part1": "### Partie 1 : Résumé pour l’agriculteur",
            "disease": "**Maladie détectée :**",
            "cures": "**Traitements et méthodes de gestion :**",
            "where": "**Où trouver les traitements :**",
            "support": "**Centres d’assistance régionaux et contacts :**",
            "title": "Conseils de dépistage (diagnostic non confirmé)",
            "withheld": "Aucun traitement chimique vérifié pour cette culture et ce pays n’est disponible ici. Confirmez les options autorisées auprès de l’autorité agricole ou d’un conseiller.",
            "verify": "Les coordonnées et la disponibilité ne sont pas vérifiées indépendamment. Contactez l’organisme avant tout déplacement ou achat.",
            "no_suppliers": "Aucun fournisseur agricole local n’est répertorié. Demandez à un conseiller agricole un fournisseur fiable.",
            "no_support": "Aucun contact régional de conseil ou de recherche n’est répertorié pour ce hub.",
            "location": "Lieu",
            "contact": "Contact",
            "specialty": "Spécialité",
            "when_to_seek_help": "Quand demander une aide locale",
            "disclaimer": (
                "Conseils de dépistage uniquement—diagnostic non confirmé. Vérifiez les "
                "traitements et leur homologation auprès d’un conseiller agricole qualifié."
            ),
        },
    }
    labels = headings.get(language, headings["English"])
    st.markdown(labels["part1"])
    st.markdown(f"#### {labels['title']}")
    st.caption(labels["disclaimer"])
    st.markdown(labels["disease"])
    st.write(advisory["disease_detected_description"])
    st.markdown(labels["cures"])
    if advisory["management_options"]:
        st.markdown(
            "\n".join(
                f"{index}. {html.escape(item)}"
                for index, item in enumerate(advisory["management_options"], 1)
            )
        )
    else:
        st.write(labels["withheld"])

    reference_advisory = (
        build_disease_advisory(
            guide_key, crop_name, language, severity_stage, hub_label
        )
        if guide_key and hub_label and crop_name
        else None
    )
    chemical_label = {
        "English": "Chemical options",
        "Kiswahili": "Chaguo za kemikali",
        "French": "Options chimiques",
    }.get(language, "Chemical options")
    verified_chemical_options = []
    if reference_advisory:
        verified_chemical_options = next(
            (
                items for title, items in reference_advisory["sections"]
                if title == chemical_label
            ),
            [],
        )
    if verified_chemical_options:
        st.markdown("\n".join(
            f"- {html.escape(item)}" for item in verified_chemical_options
        ))
        st.caption(reference_advisory["chemical_notice"])
    else:
        st.info(labels["withheld"])

    st.markdown(labels["where"])
    st.write(advisory["where_to_obtain_cures"])
    resources = region_resources or []
    supplier_terms = ("agro-vet", "agrovet", "agro-store", "agro store", "input supplier")
    suppliers = [
        item for item in resources
        if any(
            term in f"{item.get('name', '')} {item.get('specialty', '')}".casefold()
            for term in supplier_terms
        )
    ]
    if suppliers:
        for resource in suppliers:
            st.markdown(
                f"- **{html.escape(str(resource.get('name', '')))}** — "
                f"{labels['location']}: {html.escape(str(resource.get('location', '')))}; "
                f"{labels['contact']}: {html.escape(str(resource.get('contact', '')))}"
            )
    else:
        st.write(labels["no_suppliers"])

    st.markdown(labels["support"])
    support_hubs = [item for item in resources if item not in suppliers]
    if support_hubs:
        for resource in support_hubs:
            st.markdown(
                f"- **{html.escape(str(resource.get('name', '')))}** — "
                f"{labels['location']}: {html.escape(str(resource.get('location', '')))}; "
                f"{labels['contact']}: {html.escape(str(resource.get('contact', '')))}; "
                f"{labels['specialty']}: {html.escape(str(resource.get('specialty', '')))}"
            )
        st.caption(labels["verify"])
    else:
        st.write(labels["no_support"])

def render_advisory_technical_analysis(advisory, language):
    if not advisory:
        return

    headings = {
        "English": (
            "### Part 2: Full Technical Analysis",
            "**Scientific classification:**",
            "**Pathological or physiological breakdown:**",
            "**Environmental and spore/vector dynamics:**",
            "**Mechanisms of action:**",
            "**When to seek local help:**",
        ),
        "Kiswahili": (
            "### Sehemu ya 2: Uchambuzi Kamili wa Kitaalamu",
            "**Uainishaji wa kisayansi:**",
            "**Maelezo ya ugonjwa au athari za kifiziolojia:**",
            "**Mienendo ya mazingira na spora/visambazaji:**",
            "**Mbinu za utendaji:**",
            "**Wakati wa kutafuta msaada wa eneo:**",
        ),
        "French": (
            "### Partie 2 : Analyse technique complète",
            "**Classification scientifique :**",
            "**Analyse pathologique ou physiologique :**",
            "**Dynamique environnementale et des spores/vecteurs :**",
            "**Mécanismes d’action :**",
            "**Quand demander une aide locale :**",
        ),
    }
    (
        title,
        classification_label,
        pathology_label,
        dynamics_label,
        mechanisms_label,
        help_label,
    ) = headings.get(language, headings["English"])
    st.markdown(title)
    for field_name, label in (
        ("scientific_classification", classification_label),
        ("pathology_physiology", pathology_label),
        ("environmental_dynamics", dynamics_label),
        ("mechanisms_of_action", mechanisms_label),
        ("when_to_seek_help", help_label),
    ):
        st.markdown(label)
        st.write(advisory[field_name])


def render_uncertain_assessment(assessment, language):
    if not assessment:
        return

    headings = {
        "English": {
            "title": "Additional screening estimate (unconfirmed)",
            "confidence": "Screening score (not calibrated)",
            "observations": "Visible observations",
            "next_steps": "Cautious next steps",
            "seek_help_when": "When to seek local help",
            "image_quality": "Image quality",
        },
        "Kiswahili": {
            "title": "Makadirio ya ziada ya uchunguzi (hayajathibitishwa)",
            "confidence": "Alama ya uchunguzi (haijathibitishwa)",
            "observations": "Dalili zinazoonekana",
            "next_steps": "Hatua za tahadhari",
            "seek_help_when": "Wakati wa kutafuta msaada wa eneo",
            "image_quality": "Ubora wa picha",
        },
        "French": {
            "title": "Estimation complémentaire (non confirmée)",
            "confidence": "Score de dépistage (non calibré)",
            "observations": "Observations visibles",
            "next_steps": "Étapes prudentes",
            "seek_help_when": "Quand demander une aide locale",
            "image_quality": "Qualité de l’image",
        },
    }
    labels = headings.get(language, headings["English"])
    st.markdown(f"#### {labels['title']}")
    st.write(assessment["assessment"])
    st.caption(
        f"{labels['confidence']}: {assessment['confidence']:.0%}. "
        f"{labels['image_quality']}: {assessment['image_quality']}"
    )
    for field_name in ("observations", "next_steps"):
        items = assessment[field_name]
        if items:
            st.markdown(f"**{labels[field_name]}**")
            st.markdown(
                "\n".join(f"- {html.escape(item)}" for item in items),
                unsafe_allow_html=True,
            )
    if assessment["severity_description"]:
        st.write(assessment["severity_description"])
    st.markdown(f"**{labels['seek_help_when']}**")
    st.write(assessment["seek_help_when"])


def render_hub_resource_directory(resources, hub_label, gps_status, language):
    headings = {
        "English": {
            "gps": "Resources matched automatically to your GPS region.",
            "selected": "Resources shown for the selected region. Allow location access to match a hub automatically.",
            "empty": "No resources are listed for this region.",
            "location": "Location",
            "contact": "Contact",
            "specialty": "Specialization",
        },
        "Kiswahili": {
            "gps": "Rasilimali zimechaguliwa kiotomatiki kulingana na eneo lako la GPS.",
            "selected": "Rasilimali za eneo lililochaguliwa zinaonyeshwa. Ruhusu ufikiaji wa eneo ili kulinganisha kituo kiotomatiki.",
            "empty": "Hakuna rasilimali zilizoorodheshwa kwa eneo hili.",
            "location": "Eneo",
            "contact": "Mawasiliano",
            "specialty": "Utaalamu",
        },
        "French": {
            "gps": "Ressources associées automatiquement à votre région GPS.",
            "selected": "Ressources de la région sélectionnée. Autorisez la localisation pour associer automatiquement un hub.",
            "empty": "Aucune ressource n’est répertoriée pour cette région.",
            "location": "Lieu",
            "contact": "Contact",
            "specialty": "Spécialité",
        },
    }
    labels = headings.get(language, headings["English"])
    gps_status = gps_status or {}
    gps_matches_hub = (
        gps_status.get("kind") == "ok"
        and gps_status.get("hub") == hub_label
    ) or (
        gps_status.get("kind") == "global"
        and hub_label == GPS_FALLBACK_HUB
    )
    st.caption(labels["gps"] if gps_matches_hub else labels["selected"])
    if not resources:
        st.info(labels["empty"])
        return

    for resource in resources:
        with st.expander(f"🌱 {resource['name']}"):
            st.write(f"**{labels['location']}:** {resource['location']}")
            st.write(f"**{labels['contact']}:** `{resource['contact']}`")
            st.write(f"**{labels['specialty']}:** {resource['specialty']}")


def current_disease_advisory(language, hub_label):
    if not st.session_state.get("last_diagnosis_available"):
        return None
    return build_disease_advisory(
        st.session_state.get("last_disease_guide"),
        st.session_state.get("selected_crop"),
        language,
        st.session_state.get("last_severity_stage") or "",
        hub_label,
    )


def render_current_disease_advisory(language, hub_label):
    advisory = current_disease_advisory(language, hub_label)
    if not advisory:
        return
    with st.expander(advisory["title"]):
        render_disease_guide(
            st.session_state.get("last_disease_guide"),
            st.session_state.get("selected_crop"),
            language,
            st.session_state.get("last_severity_stage") or "",
            hub_label,
        )


def disease_advisory_for_prompt(prompt, language, hub_label):
    explicit_family = _guide_crop_family(prompt)
    families = [explicit_family] if explicit_family else list(disease_guide_data.CROP_FAMILIES)
    matches = {}
    for family in families:
        guide_key = find_disease_guide_key(family, prompt)
        if guide_key:
            matches.setdefault(guide_key, family)
    if len(matches) != 1:
        return None
    guide_key, family = next(iter(matches.items()))
    crop_name = disease_guide_data.CROP_FAMILIES[family][0]
    return build_disease_advisory(
        guide_key, crop_name, language, "", hub_label
    )


def render_chat_disease_advisory(advisory):
    if not advisory:
        return
    with st.expander(advisory["title"]):
        st.markdown(f"**{advisory['name']}**")
        st.markdown(f"**{advisory['signs_label']}:** {advisory['signs']}")
        for heading, sentences in advisory["sections"]:
            st.markdown(f"**{heading}**")
            st.markdown("\n".join(f"- {sentence}" for sentence in sentences))
        if advisory["has_chemical_advice"]:
            if advisory["chemical_allowed"]:
                st.caption(advisory["chemical_notice"])
            else:
                st.warning(advisory["chemical_notice"])


def format_disease_advisory_context(advisory):
    if not advisory:
        return ""
    lines = [
        f"Reference guide for the current screening result: {advisory['name']}.",
        f"Visible signs from the reference guide: {advisory['signs']}",
    ]
    for heading, sentences in advisory["sections"]:
        lines.append(f"{heading}: " + " ".join(sentences))
    if advisory["has_chemical_advice"] and not advisory["chemical_allowed"]:
        lines.append(advisory["chemical_notice"])
    return "\n".join(lines)


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
                #cg-tour-box, #cg-tour-box * {{ text-shadow:none !important; -webkit-text-fill-color:currentColor !important; }}
                #cg-tour-box #cg-tour-progress {{ color:#526052 !important; }}
                #cg-tour-box #cg-tour-title {{ color:#1F2937 !important; }}
                #cg-tour-box #cg-tour-description {{ color:#4B5563 !important; }}
                #cg-tour-box button {{ min-height:38px; padding:8px 14px; border:1px solid #D1D5DB; border-radius:8px; background:#FFFFFF; color:#374151 !important; font:inherit; font-weight:600; cursor:pointer; }}
                #cg-tour-box button:focus-visible {{ outline:3px solid #86B98A; outline-offset:2px; }}
                #cg-tour-box #cg-btn-next {{ border-color:#2F6B3B; background:#2F6B3B; color:#FFFFFF !important; }}
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
st.sidebar.caption(
    f"{st.session_state['user_display_name']}\n{st.session_state['user_email']}"
)
if st.sidebar.button("Log out", key="google_oidc_logout", use_container_width=True):
    st.logout()
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

def inject_page_theme(background_image_url, dark_mode_gradient_overlay):
    background_image_css = json.dumps(background_image_url)
    st.markdown("""
    <style>
    .stApp,
    [data-testid="stAppViewContainer"] {
        color: #E2E8F0 !important;
        background-color: #1A1D20 !important;
    }
    .stApp,
    [data-testid="stAppViewContainer"] {
        background-image: __DARK_MODE_OVERLAY__, url(__BACKGROUND_IMAGE__) !important;
        background-position: center, center;
        background-size: cover, cover;
        background-attachment: fixed, fixed;
        background-repeat: no-repeat, no-repeat;
    }
    .main .block-container {
        color: #E2E8F0;
    }
    [data-testid="stMain"] h1,
    [data-testid="stMain"] h2,
    [data-testid="stMain"] h3,
    [data-testid="stMain"] h4,
    [data-testid="stMain"] h5,
    [data-testid="stMain"] h6,
    [data-testid="stMain"] p,
    [data-testid="stMain"] span,
    [data-testid="stMain"] li,
    [data-testid="stMain"] label,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"],
    [data-testid="stMain"] [data-testid="stCaptionContainer"] {
        color: #E2E8F0 !important;
        -webkit-text-fill-color: #E2E8F0 !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.85);
    }
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] *,
    [data-testid="stMain"] [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] *,
    [data-testid="stMain"] [data-testid="stChatMessage"] p,
    [data-testid="stMain"] [data-testid="stChatMessage"] span {
        color: #E2E8F0 !important;
        -webkit-text-fill-color: #E2E8F0 !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.85);
    }
    [data-testid="stMain"] [data-testid="stCaptionContainer"],
    [data-testid="stMain"] [data-testid="stCaptionContainer"] * {
        color: #94A3B8 !important;
    }

    [data-testid="stMain"] [data-testid="stVerticalBlock"] [data-testid="stContainer"],
    [data-testid="stMain"] [data-testid="stExpander"],
    [data-testid="stMain"] [data-testid="stChatMessage"] {
        color: #E2E8F0 !important;
        background-color: rgba(30, 34, 39, 0.78) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
    }

    [data-testid="stMain"] .stButton > button,
    [data-testid="stMain"] [data-testid="stFormSubmitButton"] button,
    [data-testid="stMain"] [data-testid="stLinkButton"] a,
    [data-testid="stMain"] [data-testid="stDownloadButton"] button {
        color: #FFFFFF !important;
        background: #5B8C5A !important;
        border: 1px solid #5B8C5A !important;
        border-radius: 8px !important;
        font-weight: 650 !important;
        text-shadow: none !important;
    }
    [data-testid="stMain"] .stButton > button:hover,
    [data-testid="stMain"] [data-testid="stFormSubmitButton"] button:hover,
    [data-testid="stMain"] [data-testid="stLinkButton"] a:hover,
    [data-testid="stMain"] [data-testid="stDownloadButton"] button:hover {
        color: #FFFFFF !important;
        background: #6A9B69 !important;
        border-color: #6A9B69 !important;
    }

    [data-testid="stMain"] [data-baseweb="select"] > div,
    [data-testid="stMain"] [data-baseweb="input"] > div,
    [data-testid="stMain"] [data-baseweb="textarea"] > div,
    [data-testid="stMain"] [data-testid="stDateInput"] input,
    [data-testid="stMain"] [data-testid="stTimeInput"] input,
    [data-testid="stMain"] [data-testid="stFileUploader"] {
        color: #E2E8F0 !important;
        background: #202429 !important;
        border-color: rgba(255, 255, 255, 0.14) !important;
        border-radius: 8px !important;
    }
    [data-testid="stMain"] [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
        background: rgba(15, 40, 22, 0.85) !important;
        border: 2px dashed #81C784 !important;
    }
    [data-testid="stMain"] [data-testid="stFileUploader"] button {
        color: #FFFFFF !important;
        background: #F57C00 !important;
        border: 1px solid #F57C00 !important;
        opacity: 1 !important;
        text-shadow: none !important;
    }
    [data-testid="stMain"] [data-testid="stFileUploader"] button:hover {
        color: #FFFFFF !important;
        background: #E56A00 !important;
        border-color: #E56A00 !important;
    }
    [data-testid="stMain"] [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] {
        color: #FFFFFF !important;
    }
    [data-testid="stMain"] [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        text-shadow: none !important;
    }
    [data-testid="stMain"] [data-baseweb="select"] input,
    [data-testid="stMain"] [data-baseweb="input"] input {
        color: #E2E8F0 !important;
        -webkit-text-fill-color: #E2E8F0 !important;
    }
    [data-testid="stMain"] [data-testid="stTextArea"] textarea,
    [data-testid="stMain"] textarea[data-baseweb="textarea"] {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        background-color: #202429 !important;
        caret-color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 8px !important;
        opacity: 1 !important;
    }
    [data-testid="stMain"] input::placeholder,
    [data-testid="stMain"] textarea::placeholder {
        color: #94A3B8 !important;
        -webkit-text-fill-color: #94A3B8 !important;
    }

    [data-testid="stMain"] [data-testid="stMetric"] {
        color: #E2E8F0 !important;
        background: rgba(30, 34, 39, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 12px;
    }
    [data-testid="stMain"] [data-testid="stMetricValue"] {
        color: #E2E8F0 !important;
        -webkit-text-fill-color: #E2E8F0 !important;
        font-weight: 750 !important;
        font-size: clamp(1rem, 2.4vw, 1.7rem) !important;
        line-height: 1.25 !important;
        white-space: normal !important;
        overflow-wrap: anywhere !important;
        word-break: normal !important;
        overflow: visible !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.85);
    }
    [data-testid="stMain"] [data-testid="stMetricValue"] *,
    [data-testid="stMain"] [data-testid="stMetricLabel"],
    [data-testid="stMain"] [data-testid="stMetricLabel"] * {
        max-width: 100% !important;
        height: auto !important;
        overflow: visible !important;
        white-space: normal !important;
        overflow-wrap: anywhere !important;
        word-break: normal !important;
        text-overflow: clip !important;
    }
    [data-testid="stMain"] [data-testid="stMetricLabel"],
    [data-testid="stMain"] [data-testid="stMetricLabel"] * {
        color: #E2E8F0 !important;
        -webkit-text-fill-color: #E2E8F0 !important;
        font-weight: 650 !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.85);
    }

    [data-testid="stMain"] [data-testid="stDataFrame"],
    [data-testid="stMain"] [data-testid="stTable"],
    [data-testid="stMain"] [data-testid="stDataEditor"] {
        background: rgba(30, 34, 39, 0.85) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px;
        overflow: hidden;
    }
    [data-testid="stMain"] [data-testid="stDataFrame"] *,
    [data-testid="stMain"] [data-testid="stTable"] *,
    [data-testid="stMain"] [data-testid="stDataEditor"] * {
        color: #E2E8F0;
    }
    [data-testid="stMain"] [data-testid="stPlotlyChart"],
    [data-testid="stMain"] [data-testid="stVegaLiteChart"],
    [data-testid="stMain"] [data-testid="stPyplotChart"],
    [data-testid="stMain"] [data-testid="stAltairChart"] {
        background: rgba(30, 34, 39, 0.72) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px;
        padding: 0.35rem;
    }

    [data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 0.35rem;
        border-bottom-color: rgba(255, 255, 255, 0.1);
    }
    [data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab"] {
        color: #94A3B8 !important;
    }
    [data-testid="stMain"] [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
        color: #FFFFFF !important;
        background: #5B8C5A !important;
        border-radius: 8px 8px 0 0;
    }

    [data-testid="stMain"] [data-testid="stAlert"] {
        color: #E2E8F0 !important;
        background: rgba(30, 34, 39, 0.92) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
    }
    [data-testid="stMain"] [data-testid="stAlert"] * {
        color: #E2E8F0 !important;
        text-shadow: none !important;
    }
    </style>
    """.replace("__DARK_MODE_OVERLAY__", dark_mode_gradient_overlay)
    .replace("__BACKGROUND_IMAGE__", background_image_css), unsafe_allow_html=True)


PAGE_THEMES = {
    T["nav_ai"]: (
        "https://images.unsplash.com/photo-1530836369250-ef72a3f5cda8?auto=format&fit=crop&w=2200&q=85",
        "linear-gradient(135deg, rgba(8, 18, 23, 0.82), rgba(12, 24, 27, 0.88))",
    ),
    T["nav_map"]: (
        "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?auto=format&fit=crop&w=2200&q=85",
        "linear-gradient(135deg, rgba(6, 12, 23, 0.78), rgba(10, 17, 29, 0.9))",
    ),
    T["nav_forum"]: (
        "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=2200&q=85",
        "linear-gradient(135deg, rgba(25, 18, 10, 0.78), rgba(16, 19, 18, 0.88))",
    ),
    T["nav_acc"]: (
        "https://images.unsplash.com/photo-1523348837708-15d4a09cfac2?auto=format&fit=crop&w=2200&q=85",
        "linear-gradient(135deg, rgba(10, 15, 25, 0.84), rgba(13, 18, 27, 0.9))",
    ),
}

if app_mode != T["nav_diag"]:
    background_image_url, dark_mode_gradient_overlay = PAGE_THEMES[app_mode]
    inject_page_theme(background_image_url, dark_mode_gradient_overlay)

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

def generate_cropguard_reply(prompt, messages, hub_label, zone_data, language,
                             knowledge_context=""):
    def configured_value(key):
        value = os.environ.get(key, "").strip()
        if value:
            return value
        try:
            value = st.secrets.get(key, "")
        except (FileNotFoundError, KeyError, RuntimeError):
            value = ""
        return value.strip() if isinstance(value, str) else ""

    api_key = configured_value("OPENAI_API_KEY")
    gemini_api_key = configured_value("GEMINI_API_KEY")
    if not api_key and not gemini_api_key:
        raise RuntimeError(
            "CropGuard chat is not configured. Contact the administrator."
        )

    model = configured_value("OPENAI_MODEL") or "gpt-4o-mini"
    system_instruction = f"""
You are CropGuard AI, an expert, practical, and empathetic agricultural assistant for farmers,
extension workers, and agricultural researchers worldwide. Give accurate, actionable,
science-based guidance in clear language. Explain technical terms simply and format answers
as concise steps or bullets suitable for reading on a phone.

Help with crop disease, pest, nutrient, and environmental-stress diagnosis; soil health,
rotation, irrigation, fertilizer, planting, seed choice, harvest and post-harvest handling;
and resilience to drought, heavy rain, frost, and heat. For diagnosis, explain uncertainty
and ask about crop, location, symptoms, and timing when those details matter.

Prefer integrated pest management, prevention, and practical organic or biological controls
before chemical options. Never invent pesticide products, rates, or local approvals. Before
high-risk chemical or financial advice, ask for missing details such as exact crop, location,
crop stage, and product label. If discussing a pesticide, tell the user to follow the local
registered product label, protective-equipment and re-entry instructions, and local rules;
do not recommend exceeding label rates or mixing products without label guidance.
Do not name or recommend a pesticide active ingredient unless the supplied CropGuard
knowledge-base context explicitly includes that ingredient as verified for the selected
country and crop. When it is withheld or absent, give non-chemical options and refer the
user to their national agricultural authority or extension officer.
Be transparent when uncertain, and recommend a local extension officer for urgent or
high-consequence decisions.
Identify yourself as CropGuard's AI assistant. If asked about the technology behind a
response, explain that CropGuard uses AI-based tools without naming a specific provider.

Respond in {language}. Use the user's language if their message clearly uses a different
language. Consider this current farm context when relevant: region={hub_label}; temperature
{zone_data.get("temp", "unknown")} C; humidity {zone_data.get("humidity", "unknown")}%;
regional risk={zone_data.get("risk", "not available")}. Treat these as contextual clues,
not proof of a diagnosis. Do not assume every question is about this region or these crops.

The following server-generated CropGuard knowledge-base text is reference information, not
proof of diagnosis. Preserve its uncertainty and do not add pesticide ingredients or
registration claims omitted from it:
{knowledge_context or "No current CropGuard disease-guide entry is available."}
"""

    conversation = messages[1:] if messages and messages[0].get("role") == "assistant" else messages
    api_messages = [
        {"role": "system", "content": system_instruction},
    ] + [
        {
            "role": message["role"],
            "content": message["content"],
        }
        for message in conversation[-12:]
        if message.get("role") in {"user", "assistant"} and message.get("content")
    ]
    api_messages.append({"role": "user", "content": prompt})

    def generate_gemini_reply():
        contents = [
            {
                "role": "model" if message["role"] == "assistant" else "user",
                "parts": [{"text": message["content"]}],
            }
            for message in api_messages[1:]
        ]
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{configured_value('GEMINI_CHAT_MODEL') or 'gemini-3.5-flash-lite'}:generateContent",
            headers={"x-goog-api-key": gemini_api_key},
            json={
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 900,
                },
            },
            timeout=(5, 30),
        )
        if not response.ok:
            try:
                error_data = response.json()
                detail = error_data.get("error", {}).get("message", "")
            except (ValueError, AttributeError):
                detail = ""
            message = f"AI service returned HTTP {response.status_code}."
            if detail:
                message += f" {detail}"
            raise RuntimeError(message)
        try:
            result = response.json()
        except ValueError as error:
            raise RuntimeError("AI service returned an invalid response. Please try again.") from error
        try:
            reply = result["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("AI service did not return a text answer. Please try again.") from error
        if not isinstance(reply, str) or not reply.strip():
            raise RuntimeError("AI service did not return a text answer. Please try again.")
        return reply.strip()

    if not api_key:
        return generate_gemini_reply()

    def fallback_to_gemini(openai_error):
        if not gemini_api_key:
            raise openai_error
        try:
            return generate_gemini_reply()
        except (requests.RequestException, RuntimeError) as gemini_error:
            raise RuntimeError(
                "CropGuard could not get a response from its configured AI services. "
                "Please try again later."
            ) from gemini_error

    def openai_request_with_fallback(*args, **kwargs):
        try:
            return requests.post(*args, **kwargs)
        except requests.RequestException as error:
            return fallback_to_gemini(error)

    response = openai_request_with_fallback(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": api_messages,
            "temperature": 0.4,
            "max_tokens": 900,
        },
        timeout=(5, 30),
    )
    if isinstance(response, str):
        return response

    if not response.ok:
        try:
            error_data = response.json()
            detail = error_data.get("error", {}).get("message", "")
        except (ValueError, AttributeError):
            detail = ""
        message = f"OpenAI API returned HTTP {response.status_code}."
        if detail:
            message += f" {detail}"
        return fallback_to_gemini(RuntimeError(message))

    try:
        result = response.json()
    except ValueError as error:
        raise RuntimeError("OpenAI returned an invalid response. Please try again.") from error

    if not isinstance(result, dict):
        raise RuntimeError("OpenAI returned an invalid response. Please try again.")
    choices = result.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("OpenAI did not return an answer. Please rephrase your question and try again.")
    choice = choices[0]
    message = choice.get("message") if isinstance(choice, dict) else None
    reply = message.get("content") if isinstance(message, dict) else None
    if not isinstance(reply, str) or not reply.strip():
        raise RuntimeError("OpenAI did not return a text answer. Please try again.")
    return reply.strip()


# ===========================================================================
# Epidemiological heatmap dashboard
# ===========================================================================
MAP_CELL_DEG = 0.05
MAP_PERIOD_OPTIONS = (0, 7, 14, 30, 90)
MAP_VIEWPORT_PX = (900, 500)
MAP_STYLE = getattr(getattr(pdk, "map_styles", None), "DARK", "dark")
HEATMAP_COLOR_RANGE = [
    [255, 255, 178], [254, 217, 118], [254, 178, 76],
    [253, 141, 60], [240, 59, 32], [189, 0, 38],
]
HOTSPOT_KEYS = ["hub_region", "cell_lat", "cell_lon"]
MAP_FRAME_COLUMNS = [
    "scan_id", "timestamp", "hub_region", "target_crop", "crop_family",
    "detected_disease", "disease_key", "severity", "status", "latitude", "longitude",
]
MAP_SEVERITY_BANDS = (40, 70)


def _map_text(T, key, default, **values):
    text = T.get(key, default)
    if not isinstance(text, str):
        text = default
    if values:
        try:
            return text.format(**values)
        except (KeyError, IndexError, ValueError):
            try:
                return default.format(**values)
            except (KeyError, IndexError, ValueError):
                return default
    return text


def telemetry_version():
    conn = _epi_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*), COALESCE(MAX(scan_id), 0) FROM scan_telemetry"
        ).fetchone()
    finally:
        conn.close()
    return tuple(row)


@st.cache_data(show_spinner=False, max_entries=8)
def _map_frame_cached(version, language):
    conn = _epi_conn()
    try:
        raw = pd.read_sql_query(
            """
            SELECT scan_id, timestamp, hub_region, target_crop, crop_canon AS crop_family,
                   detected_disease, disease_key, severity_percentage AS severity,
                   diagnosis_status AS status, latitude, longitude
            FROM scan_telemetry
            WHERE lower(COALESCE(detected_disease, '')) <> 'healthy'
              AND lower(COALESCE(disease_key, '')) <> 'healthy'
              AND scan_id <= ?
            """,
            conn,
            params=(version[1],),
        )
    finally:
        conn.close()
    return prepare_map_frame(raw, language)


def load_map_frame(language):
    return _map_frame_cached(telemetry_version(), language)


def prepare_map_frame(raw, language):
    df = raw.reindex(columns=MAP_FRAME_COLUMNS).copy()
    located_hubs = {
        name: hub for name, hub in GLOBAL_AGRICULTURAL_HUBS.items()
        if name != GPS_FALLBACK_HUB
    }
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    gps_valid = (
        df["latitude"].between(-90, 90)
        & df["longitude"].between(-180, 180)
    )
    df["gps"] = gps_valid
    hub_latitudes = {name: hub["lat"] for name, hub in located_hubs.items()}
    hub_longitudes = {name: hub["lon"] for name, hub in located_hubs.items()}
    df["lat"] = df["latitude"].where(gps_valid, df["hub_region"].map(hub_latitudes))
    df["lon"] = df["longitude"].where(gps_valid, df["hub_region"].map(hub_longitudes))
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    crop_source = df["crop_family"].where(df["crop_family"].notna(), df["target_crop"])
    df["crop_family"] = crop_source.map(_guide_crop_family)
    lang_index = {"English": 0, "Kiswahili": 1, "French": 2}.get(language, 0)
    df["crop"] = df["crop_family"].map(
        lambda family: disease_guide_data.CROP_FAMILIES[family][lang_index]
        if family in disease_guide_data.CROP_FAMILIES else None
    ).fillna(df["target_crop"])

    def resolve_disease_key(row):
        key = row["disease_key"]
        if isinstance(key, str) and key in disease_guide_data.DISEASES:
            return key
        return find_disease_guide_key(row["target_crop"], row["detected_disease"])

    df["disease_key"] = df.apply(resolve_disease_key, axis=1)
    df["disease"] = df["disease_key"].map(
        lambda key: disease_guide_data.DISEASES[key]["name"][lang_index]
        if key in disease_guide_data.DISEASES else None
    ).fillna(df["detected_disease"])
    df["status"] = df["status"].fillna("LEGACY").replace("", "LEGACY")
    df["severity"] = pd.to_numeric(df["severity"], errors="coerce").fillna(0.0).clip(0.0, 100.0)
    df["ts"] = pd.to_datetime(df["timestamp"], errors="coerce", format=EPI_TS_FMT)
    return df


def filter_map_frame(df, crops=(), severity_range=(0, 100), period_days=0,
                     include_possible=True, now=None):
    low, high = severity_range
    mask = df["severity"].between(low, high)
    if crops:
        mask &= df["crop"].isin(list(crops))
    if period_days:
        current_time = now if now is not None else pd.Timestamp.now()
        mask &= df["ts"] >= current_time - pd.Timedelta(days=period_days)
    if not include_possible:
        mask &= df["status"] != "POSSIBLE"
    return df[mask]


def aggregate_hotspots(df, cell_deg=MAP_CELL_DEG):
    columns = HOTSPOT_KEYS + [
        "lat", "lon", "cases", "avg_sev", "max_sev", "weight", "likely", "gps",
        "last_seen", "dominant", "dominant_cases",
    ]
    located = df.dropna(subset=["lat", "lon"])
    if located.empty:
        return pd.DataFrame(columns=columns)
    grouped_data = located.assign(
        cell_lat=(located["lat"] / cell_deg).round() * cell_deg,
        cell_lon=(located["lon"] / cell_deg).round() * cell_deg,
        is_likely=located["status"].eq("LIKELY"),
    )
    aggregate = grouped_data.groupby(HOTSPOT_KEYS, sort=False).agg(
        lat=("lat", "mean"),
        lon=("lon", "mean"),
        cases=("severity", "size"),
        avg_sev=("severity", "mean"),
        max_sev=("severity", "max"),
        sum_sev=("severity", "sum"),
        likely=("is_likely", "sum"),
        gps=("gps", "any"),
        last_seen=("ts", "max"),
    ).reset_index()
    dominant = (
        grouped_data.groupby(HOTSPOT_KEYS + ["disease"], sort=False)
        .size().rename("dominant_cases").reset_index()
        .sort_values("dominant_cases", ascending=False, kind="stable")
        .drop_duplicates(HOTSPOT_KEYS)
        .rename(columns={"disease": "dominant"})
    )
    aggregate = aggregate.merge(dominant, on=HOTSPOT_KEYS, how="left")
    aggregate["weight"] = aggregate.pop("sum_sev") / 100.0
    aggregate["cases"] = aggregate["cases"].astype(int)
    aggregate["likely"] = aggregate["likely"].astype(int)
    return aggregate.sort_values(
        ["cases", "avg_sev"], ascending=False, kind="stable"
    ).reset_index(drop=True)[columns]


def _mercator_y(lat_deg):
    return np.log(np.tan(np.pi / 4 + np.radians(np.clip(lat_deg, -85.0, 85.0)) / 2))


def compute_view_state(lats, lons, *, width_px=MAP_VIEWPORT_PX[0],
                       height_px=MAP_VIEWPORT_PX[1], padding=0.30,
                       min_zoom=1.5, max_zoom=10.0, single_point_zoom=7.0, pitch=0.0):
    latitudes = np.asarray(lats, dtype=float)
    longitudes = np.asarray(lons, dtype=float)
    valid = np.isfinite(latitudes) & np.isfinite(longitudes)
    latitudes, longitudes = latitudes[valid], longitudes[valid]
    if latitudes.size == 0:
        return pdk.ViewState(latitude=0.0, longitude=20.0, zoom=2.0, pitch=pitch, bearing=0)
    lon_min, lon_max = float(longitudes.min()), float(longitudes.max())
    y_min, y_max = float(_mercator_y(latitudes.min())), float(_mercator_y(latitudes.max()))
    lon_span, y_span = lon_max - lon_min, y_max - y_min
    if lon_span < 1e-6 and y_span < 1e-9:
        zoom = single_point_zoom
    else:
        usable_width = width_px * (1 - padding)
        usable_height = height_px * (1 - padding)
        zoom_lon = math.log2(usable_width * 360.0 / (256.0 * lon_span)) if lon_span > 1e-6 else max_zoom
        zoom_lat = math.log2(usable_height * 2 * math.pi / (256.0 * y_span)) if y_span > 1e-9 else max_zoom
        zoom = min(zoom_lon, zoom_lat)
    centre_lat = math.degrees(2 * math.atan(math.exp((y_min + y_max) / 2)) - math.pi / 2)
    return pdk.ViewState(
        latitude=centre_lat,
        longitude=(lon_min + lon_max) / 2,
        zoom=float(np.clip(zoom, min_zoom, max_zoom)),
        pitch=pitch,
        bearing=0,
    )


def map_span_km(lats, lons):
    latitudes = np.asarray(lats, dtype=float)
    longitudes = np.asarray(lons, dtype=float)
    if latitudes.size == 0:
        return 50.0
    return max(50.0, haversine_km(
        float(latitudes.min()), float(longitudes.min()),
        float(latitudes.max()), float(longitudes.max()),
    ))


def _outbreak_color(severity):
    low, high = MAP_SEVERITY_BANDS
    if severity > high:
        return [211, 47, 47, 220]
    if severity > low:
        return [245, 124, 0, 220]
    return [56, 142, 60, 220]


def _rgb_css(rgb):
    return f"rgb({rgb[0]},{rgb[1]},{rgb[2]})"


def map_tooltip(T):
    return {
        "html": (
            "<div style='font-family: \"Source Sans Pro\", sans-serif; font-size: 13px; line-height: 1.5;'>"
            "<div style='font-weight: 800; font-size: 14px; color: #76FF03;'>{region}</div>"
            f"{html_escape(_map_text(T, 'tt_cases', 'Cases'))}: <b>{{cases}}</b><br>"
            f"{html_escape(_map_text(T, 'tt_dominant', 'Dominant'))}: <b>{{dominant}}</b><br>"
            f"{html_escape(_map_text(T, 'tt_avg_sev', 'Avg severity'))}: <b>{{avg_sev_txt}}%</b><br>"
            f"{html_escape(_map_text(T, 'tt_last', 'Last report'))}: {{last_seen_txt}}"
            "</div>"
        ),
        "style": {
            "backgroundColor": "rgba(10, 37, 16, 0.96)",
            "color": "#FFFFFF",
            "border": "1px solid #76FF03",
            "borderRadius": "8px",
            "padding": "8px 12px",
            "boxShadow": "0 6px 18px rgba(0,0,0,0.6)",
        },
    }


def hotspot_layer_data(agg, T, base_radius_m):
    field_tag = f" · {_map_text(T, 'tt_field_cluster', 'field cluster')}"
    data = pd.DataFrame({
        "lon": agg["lon"].astype(float),
        "lat": agg["lat"].astype(float),
        "cases": agg["cases"].astype(int),
        "avg_sev": agg["avg_sev"].astype(float).round(1),
        "weight": agg["weight"].astype(float),
        "region": [
            html_escape(str(hub) + (field_tag if has_gps else ""))
            for hub, has_gps in zip(agg["hub_region"], agg["gps"])
        ],
        "dominant": agg["dominant"].fillna("—").astype(str).map(html_escape),
        "avg_sev_txt": agg["avg_sev"].astype(float).map("{:.1f}".format),
        "last_seen_txt": agg["last_seen"].map(
            lambda timestamp: timestamp.strftime("%Y-%m-%d") if pd.notna(timestamp) else "—"
        ),
    })
    data["color"] = data["avg_sev"].map(_outbreak_color)
    max_cases = max(int(data["cases"].max()), 1)
    data["radius_m"] = base_radius_m * (0.6 + 0.9 * np.sqrt(data["cases"] / max_cases))
    return data


def build_map_layers(data, *, show_heat, show_overlay, overlay_style,
                     base_radius_m, span_km):
    layers = []
    if show_heat:
        layers.append(pdk.Layer(
            "HeatmapLayer",
            data=data[["lon", "lat", "weight"]],
            id="outbreak-density",
            get_position=["lon", "lat"],
            get_weight="weight",
            aggregation="SUM",
            radius_pixels=70,
            intensity=1.0,
            threshold=0.03,
            opacity=0.85,
            color_range=HEATMAP_COLOR_RANGE,
        ))
    if show_overlay:
        common = dict(data=data, get_position=["lon", "lat"], pickable=True, auto_highlight=True)
        if overlay_style == "columns":
            layers.append(pdk.Layer(
                "ColumnLayer",
                id="severity-columns",
                get_elevation="avg_sev",
                elevation_scale=span_km * 1000 * 0.35 / 100.0,
                radius=base_radius_m,
                get_fill_color="color",
                extruded=True,
                coverage=1.0,
                **common,
            ))
        else:
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                id="case-circles",
                get_radius="radius_m",
                get_fill_color="color",
                radius_min_pixels=5,
                radius_max_pixels=70,
                stroked=True,
                get_line_color=[255, 255, 255],
                line_width_min_pixels=1,
                opacity=0.85,
                **common,
            ))
    return layers


def render_map_legend(T, *, show_heat, show_overlay, overlay_style):
    low, high = MAP_SEVERITY_BANDS
    parts = []
    if show_heat:
        gradient = ", ".join(_rgb_css(color) for color in HEATMAP_COLOR_RANGE)
        parts.append(
            "<div class='cg-legend-block'>"
            f"<div class='cg-legend-title'>{html_escape(_map_text(T, 'legend_heat', 'Heatmap'))}</div>"
            f"<div class='cg-gradient' style='background: linear-gradient(90deg, {gradient});'></div>"
            f"<div class='cg-gradient-labels'><span>{html_escape(_map_text(T, 'legend_low', 'Low'))}</span>"
            f"<span>{html_escape(_map_text(T, 'legend_high', 'High'))}</span></div></div>"
        )
    if show_overlay:
        chips = "".join(
            "<span class='cg-chip'><span class='cg-dot' "
            f"style='background:{_rgb_css(_outbreak_color(severity))};'></span>"
            f"<span class='cg-chip-text'>{html_escape(_map_text(T, key, key, lo=low, hi=high))}</span></span>"
            for key, severity in (("sev_1", 0), ("sev_2", (low + high) / 2), ("sev_3", 100))
        )
        note_key = "legend_columns" if overlay_style == "columns" else "legend_points"
        parts.append(
            "<div class='cg-legend-block'>"
            f"<div class='cg-legend-title'>{html_escape(_map_text(T, 'sev_key_title', 'Severity Key'))}</div>"
            f"<div class='cg-chips'>{chips}</div>"
            f"<div class='cg-legend-note'>{html_escape(_map_text(T, note_key, ''))}</div></div>"
        )
    if not parts:
        return
    st.markdown("""
    <style>
    .cg-legend { display: flex; flex-wrap: wrap; gap: 18px 32px; width: 100%; min-width: 0; box-sizing: border-box;
                 background: #12301A; border: 1px solid #76FF03; border-radius: 12px; padding: 14px 20px;
                 margin: 8px 0 14px 0; box-shadow: 0 6px 20px rgba(0,0,0,0.6); }
    .cg-legend * { color: #FFFFFF !important; text-shadow: none !important; }
    .cg-legend-block { flex: 1 1 260px; min-width: 0; }
    .cg-legend-title { font-weight: 800; font-size: 0.95rem; margin-bottom: 6px; overflow-wrap: anywhere; }
    .cg-gradient { height: 12px; border-radius: 6px; }
    .cg-gradient-labels { display: flex; justify-content: space-between; font-size: 0.8rem; opacity: 0.85; margin-top: 2px; }
    .cg-chips { display: flex; flex-wrap: wrap; gap: 6px 14px; min-width: 0; font-size: 0.88rem; font-weight: 600; }
    .cg-chip { display: inline-flex; align-items: flex-start; gap: 6px; min-width: 0; max-width: 100%; }
    .cg-chip-text { min-width: 0; white-space: normal; overflow-wrap: anywhere; word-break: normal; }
    .cg-dot { flex: 0 0 12px; width: 12px; height: 12px; border-radius: 50%; display: inline-block; border: 1px solid #FFFFFF; }
    .cg-legend-note { font-size: 0.8rem; font-style: italic; margin-top: 6px; color: #C5E1A5 !important; overflow-wrap: anywhere; }
    </style>
    """ + f"<div class='cg-legend'>{''.join(parts)}</div>", unsafe_allow_html=True)


def view_map(ctx: types.SimpleNamespace) -> None:
    T, language = ctx.T, ctx.language
    st.title(_map_text(T, "map_title", "Epidemiological Heatmap"))
    subtitle = _map_text(T, "map_subtitle", "")
    st.markdown(
        f"<p style='font-size: 1.2rem; font-weight: 500;'>{html_escape(subtitle)}</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)
    frame = load_map_frame(language)
    if frame.empty:
        with st.container(border=True):
            st.markdown(f"### {_map_text(T, 'map_cluster_header', 'Outbreak Clusters')}")
            st.info(_map_text(T, "no_map_data", "No map data yet."))
        return

    @st.fragment
    def outbreak_map():
        with st.container(border=True):
            st.markdown(f"### {_map_text(T, 'map_cluster_header', 'Outbreak Clusters')}")
            filter_col, severity_col, layers_col = st.columns([2.2, 2.2, 1.6], gap="medium")
            with filter_col:
                crops = st.multiselect(
                    _map_text(T, "filter_crop", "Filter Crop"),
                    sorted(frame["crop"].dropna().unique().tolist()),
                    placeholder=_map_text(T, "all_crops_opt", "All Crops"),
                    key=f"map_crops_{language}",
                )
                period = st.selectbox(
                    _map_text(T, "map_period", "Period"),
                    MAP_PERIOD_OPTIONS,
                    key="map_period",
                    format_func=lambda days: (
                        _map_text(T, "period_all", "All time") if days == 0
                        else _map_text(T, "period_days", "Last {n} days", n=days)
                    ),
                )
            with severity_col:
                severity_range = st.slider(
                    _map_text(T, "map_severity_range", "Severity range (%)"),
                    0, 100, (0, 100), step=5, key="map_severity",
                )
                include_possible = st.toggle(
                    _map_text(T, "map_include_possible", "Include possible"),
                    value=True,
                    key="map_possible",
                )
            with layers_col:
                show_heat = st.toggle(
                    _map_text(T, "map_layer_heat", "Density heatmap"),
                    value=True,
                    key="map_heat",
                )
                show_overlay = st.toggle(
                    _map_text(T, "map_layer_overlay", "Inspection overlay"),
                    value=True,
                    key="map_overlay",
                )
                overlay_style = st.radio(
                    _map_text(T, "map_layer_overlay", "Overlay"),
                    ("columns", "points"),
                    horizontal=True,
                    key="map_overlay_style",
                    label_visibility="collapsed",
                    disabled=not show_overlay,
                    format_func=lambda style: _map_text(
                        T,
                        "map_overlay_columns" if style == "columns" else "map_overlay_points",
                        "3D columns" if style == "columns" else "Circles",
                    ),
                )
            filtered = filter_map_frame(
                frame, crops, severity_range, period, include_possible
            )
            located = filtered.dropna(subset=["lat", "lon"])
            unlocated = len(filtered) - len(located)
            if located.empty:
                st.warning(_map_text(T, "no_crop_match", "No telemetry matches filter."))
                if unlocated:
                    st.caption(_map_text(T, "map_unlocated", "{n} scans have no mapped location.", n=unlocated))
                return

            aggregate = aggregate_hotspots(located)
            metric_1, metric_2, metric_3, metric_4 = st.columns(4)
            metric_1.metric(_map_text(T, "kpi_cases", "Cases"), f"{len(located):,}")
            metric_2.metric(_map_text(T, "kpi_hotspots", "Hotspots"), f"{len(aggregate):,}")
            metric_3.metric(
                _map_text(T, "kpi_avg_sev", "Avg severity"),
                f"{located['severity'].mean():.1f}%",
            )
            metric_4.metric(
                _map_text(T, "kpi_dominant", "Dominant problem"),
                str(located["disease"].mode().iloc[0]),
            )
            render_map_legend(
                T, show_heat=show_heat, show_overlay=show_overlay, overlay_style=overlay_style
            )
            span_km = map_span_km(aggregate["lat"], aggregate["lon"])
            base_radius_m = float(np.clip(span_km * 1000 * 0.012, 1200, 35000))
            layer_data = hotspot_layer_data(aggregate, T, base_radius_m)
            columns_3d = show_overlay and overlay_style == "columns"
            view_state = compute_view_state(
                aggregate["lat"], aggregate["lon"],
                pitch=45.0 if columns_3d else 0.0,
                single_point_zoom=9.0 if bool(aggregate["gps"].all()) else 7.0,
            )
            layers = build_map_layers(
                layer_data,
                show_heat=show_heat,
                show_overlay=show_overlay,
                overlay_style=overlay_style,
                base_radius_m=base_radius_m,
                span_km=span_km,
            )
            st.pydeck_chart(
                pdk.Deck(
                    layers=layers,
                    initial_view_state=view_state,
                    map_provider="carto",
                    map_style=MAP_STYLE,
                    tooltip=map_tooltip(T) if show_overlay else False,
                ),
                use_container_width=True,
            )
            if not show_overlay:
                st.caption(_map_text(T, "map_hover_hint", ""))
            if unlocated:
                st.caption(_map_text(
                    T, "map_unlocated", "{n} scans have no mapped location.", n=unlocated
                ))

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"### {_map_text(T, 'map_hotspot_table', 'Hotspot summary')}")
        table = pd.DataFrame({
            _map_text(T, "col_hub", "Hub"): [
                str(hub) + (f" · {_map_text(T, 'tt_field_cluster', 'field cluster')}" if has_gps else "")
                for hub, has_gps in zip(aggregate["hub_region"], aggregate["gps"])
            ],
            _map_text(T, "col_cases", "Cases"): aggregate["cases"],
            _map_text(T, "col_likely", "Likely"): aggregate["likely"],
            _map_text(T, "col_avg_sev", "Avg sev (%)"): aggregate["avg_sev"].round(1),
            _map_text(T, "col_max_sev", "Max sev (%)"): aggregate["max_sev"].round(1),
            _map_text(T, "col_dominant", "Dominant"): aggregate["dominant"],
            _map_text(T, "col_last", "Last report"): aggregate["last_seen"].dt.strftime("%Y-%m-%d"),
        })
        st.dataframe(table, hide_index=True, use_container_width=True)
        raw_title = _map_text(T, "map_raw_scans", "Raw scans ({n})", n=len(filtered))
        with st.expander(raw_title):
            raw = filtered.sort_values("ts", ascending=False).head(500)
            st.dataframe(pd.DataFrame({
                _map_text(T, "col_time", "Time"): raw["timestamp"],
                _map_text(T, "col_hub", "Hub"): raw["hub_region"],
                _map_text(T, "col_crop", "Crop"): raw["crop"],
                _map_text(T, "col_disease", "Disease"): raw["disease"],
                _map_text(T, "col_sev_pct", "Sev (%)"): raw["severity"].round(1),
                _map_text(T, "col_status", "Status"): raw["status"],
            }), hide_index=True, use_container_width=True)

    outbreak_map()


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
            st.success(f"{T['auth_success']} {st.session_state['user_display_name']}!")
            st.write(f"**{T['email_lbl']}** `{st.session_state['user_email']}`")
            st.write(
                f"**{T['user_id_lbl']}** "
                f"`F{st.session_state['logged_in_user_id']:05d}`"
            )

    with col_acc2:
        with st.container(border=True):
            st.markdown(f"### {T['history_header']} ({st.session_state.get('user_display_name', 'Farmer')})")
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
    ctx = types.SimpleNamespace(T=T, language=language)
    view_map(ctx)

elif app_mode == T["nav_ai"]:
    st.title(T["ai_title"])
    st.markdown(f"<p style='font-size: 1.2rem; font-weight: 500;'>{T['ai_subtitle']} ({selected_hub_label})</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(f"### {T['chat_header']}")
        st.info(T["chat_info"].format(hub=selected_hub_label, lang=language))
        disease_advisory = current_disease_advisory(language, selected_hub_label)
        render_current_disease_advisory(language, selected_hub_label)
        prior_chat_guide = st.session_state.get("last_chat_guide")
        if prior_chat_guide and (
            not disease_advisory
            or prior_chat_guide[0] != st.session_state.get("last_disease_guide")
        ):
            render_chat_disease_advisory(build_disease_advisory(
                prior_chat_guide[0],
                prior_chat_guide[1],
                language,
                prior_chat_guide[2],
                selected_hub_label,
            ))

        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "assistant", "content": T["chat_welcome"].format(
                    user=st.session_state.get('user_display_name', 'Farmer'),
                    hub=selected_hub_label
                )}
            ]
        elif (
            st.session_state.messages
            and st.session_state.messages[0].get("role") == "assistant"
            and "Dr. Morara" in st.session_state.messages[0].get("content", "")
        ):
            st.session_state.messages[0]["content"] = (
                st.session_state.messages[0]["content"].replace("Dr. Morara", "Farmer")
            )

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input(T["chat_input_ph"]):
            with st.chat_message("user"):
                st.markdown(prompt)

            prompt_advisory = disease_advisory_for_prompt(
                prompt, language, selected_hub_label
            ) or disease_advisory
            if prompt_advisory:
                st.session_state["last_chat_guide"] = (
                    prompt_advisory["guide_key"],
                    prompt_advisory["crop_name"],
                    prompt_advisory["severity_stage"],
                )
            else:
                st.session_state["last_chat_guide"] = None

            try:
                with st.spinner("CropGuard is preparing practical advice..."):
                    bot_reply = generate_cropguard_reply(
                        prompt,
                        st.session_state.messages,
                        selected_hub_label,
                        active_zone_data,
                        language,
                        format_disease_advisory_context(prompt_advisory),
                    )
            except (requests.RequestException, RuntimeError) as error:
                print(f"CropGuard chat request failed: {error}")
                st.error("Could not get a CropGuard answer. Please try again later.")
            else:
                st.session_state.messages.extend([
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": bot_reply},
                ])
                with st.chat_message("assistant"):
                    st.markdown(bot_reply)
                    render_chat_disease_advisory(prompt_advisory)

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
            author = st.text_input(T["author_label"], value=st.session_state.get('user_display_name', 'Farmer'))
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
        st.session_state.setdefault("analysis_done", False)
        st.session_state.setdefault("selected_crop", None)
        st.session_state.setdefault("last_prediction", "")
        st.session_state.setdefault("last_confidence", 0.0)
        st.session_state.setdefault("last_confidence_margin", None)
        st.session_state.setdefault("last_severity_stage", "")
        st.session_state.setdefault("last_severity_pct", 0.0)
        st.session_state.setdefault("last_diagnosis_notice", None)
        st.session_state.setdefault("last_diagnosis_available", False)
        st.session_state.setdefault("last_disease_guide", None)
        st.session_state.setdefault("last_consensus_report", None)
        st.session_state.setdefault("last_log_outcome", None)
        st.session_state.setdefault("last_analysis_error", None)
        st.session_state.setdefault("last_language", language)
        st.session_state.setdefault("last_diagnostic_hub", selected_hub_label)
        st.session_state.setdefault("last_gemini_advisory", None)
        st.session_state.setdefault("last_gemini_advisory_error", None)
        st.session_state.setdefault("last_gemini_gap_assessment", None)
        st.session_state.setdefault("last_gemini_gap_error", None)

        def clear_diagnostic_results():
            st.session_state.update({
                "analysis_done": False,
                "last_prediction": "",
                "last_confidence": 0.0,
                "last_confidence_margin": None,
                "last_severity_stage": "",
                "last_severity_pct": 0.0,
                "last_diagnosis_notice": None,
                "last_diagnosis_available": False,
                "last_disease_guide": None,
                "last_consensus_report": None,
                "last_log_outcome": None,
                "last_analysis_error": None,
                "last_gemini_advisory": None,
                "last_gemini_advisory_error": None,
                "last_gemini_gap_assessment": None,
                "last_gemini_gap_error": None,
            })

        if (
            st.session_state["last_language"] != language
            or st.session_state["last_diagnostic_hub"] != selected_hub_label
        ):
            clear_diagnostic_results()
            st.session_state["last_language"] = language
            st.session_state["last_diagnostic_hub"] = selected_hub_label

        uploaded_file = None
        image = None
        upload_bytes = None
        assessment = None
        image_quality = {"blocked": True}
        sample_source_type = "🌱 Verified Farm Field Sample (Log to B2G Surveillance)"
        analyze_triggered = False

        if not st.session_state.get("analysis_done", False):
            crop_list = active_zone_data["crops"]
            crop_widget_key = "diagnostic_crop_selector"
            if st.session_state.get(crop_widget_key) not in crop_list:
                st.session_state[crop_widget_key] = (
                    st.session_state["selected_crop"]
                    if st.session_state["selected_crop"] in crop_list
                    else crop_list[0]
                )

            crop_col, upload_col = st.columns(2, gap="large")
            with crop_col:
                with st.container(border=True):
                    st.markdown("<div id='tour-target-crop'></div>", unsafe_allow_html=True)
                    st.markdown(f"### {T['crop_select_header']}")
                    selected_crop = st.selectbox(
                        T["crop_select_prompt"],
                        crop_list,
                        key=crop_widget_key,
                        label_visibility="collapsed",
                    )
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("<div id='tour-target-upload'></div>", unsafe_allow_html=True)
                    st.markdown(f"### {T['upload_header']} {T['upload_label_text']}")
                    uploaded_file = st.file_uploader(
                        T["upload_label_text"],
                        type=["jpg", "jpeg", "png"],
                        key="file_upload",
                        help=T["leaf_upload_help"],
                    )

            st.session_state["selected_crop"] = selected_crop
            if uploaded_file is not None:
                upload_bytes = uploaded_file.getvalue()
                upload_digest = hashlib.sha256(upload_bytes).hexdigest()
                if st.session_state.get("_last_upload_digest") != upload_digest:
                    st.session_state["_last_upload_digest"] = upload_digest
                    clear_diagnostic_results()

            with upload_col:
                with st.container(border=True):
                    st.markdown(f"### {T['quality_integrity_header']}")
                    if uploaded_file is None:
                        st.caption(T["leaf_upload_help"])
                    else:
                        try:
                            image = ImageOps.exif_transpose(Image.open(io.BytesIO(upload_bytes)))
                            image_quality = assess_image_quality(image)
                            st.image(image, caption=f"Field Sample Preview ({selected_crop.split(' ')[0]})", width=300)
                            render_image_quality_feedback(image_quality, T)

                            sample_source_type = st.radio(
                                "Select Sample Origin (Telemetry Integrity Check):",
                                [
                                    "🌱 Verified Farm Field Sample (Log to B2G Surveillance)",
                                    "🔬 Reference / Internet Sample (Test Only - Do Not Log)",
                                ],
                                index=0,
                                key="diagnostic_sample_source",
                                help="Prevents reference or internet photos from skewing regional disease outbreak statistics.",
                            )
                            assessment = di.assess_upload(upload_bytes)
                            if "Verified Farm Field Sample" in sample_source_type:
                                di.render_assessment(st, T, assessment, attested=True)
                        except (OSError, ValueError) as error:
                            st.error(T["image_open_error"].format(error=error))

                    st.markdown("<br>", unsafe_allow_html=True)
                    analyze_triggered = st.button(
                        T["analyze_btn"],
                        type="primary",
                        use_container_width=True,
                        disabled=(
                            uploaded_file is None
                            or image is None
                            or image_quality["blocked"]
                        ),
                    )
        else:
            st.markdown("<div id='tour-target-results'></div>", unsafe_allow_html=True)
            with st.container(border=True):
                consensus_data = st.session_state.get("last_consensus_report") or {}
                vision_data = consensus_data.get("vision") or {}
                chosen_crop = (
                    vision_data.get("detected_crop")
                    if not vision_data.get("error")
                    and vision_data.get("confidence_score", 0) > 0
                    else None
                ) or st.session_state.get("selected_crop") or "Unknown crop"
                raw_label = st.session_state.get("last_prediction") or T["unsupported_crop_msg"]
                confidence = float(st.session_state.get("last_confidence") or 0.0)
                severity_stage = st.session_state.get("last_severity_stage") or "Not available"
                severity_pct = float(st.session_state.get("last_severity_pct") or 0.0)
                diagnosis_available = st.session_state.get("last_diagnosis_available", False)
                is_healthy_prediction = (
                    st.session_state.get("last_disease_guide") == "healthy"
                    or consensus_data.get("health_status") == "healthy"
                )
                gap_assessment = st.session_state.get("last_gemini_gap_assessment")
                gap_error = st.session_state.get("last_gemini_gap_error")
                if gap_assessment and not diagnosis_available:
                    raw_label = f"{chosen_crop}: AI estimate — {gap_assessment['assessment']}"
                confidence_display = (
                    f"{confidence:.1f}%" if diagnosis_available
                    else f"{gap_assessment['confidence']:.0%}" if gap_assessment
                    else "N/A"
                )
                severity_display = (
                    f"{severity_pct:.1f}%"
                    if diagnosis_available and severity_stage != "Not available"
                    else (
                        f"{gap_assessment['visual_discoloration_percent']:.1f}%"
                        if gap_assessment
                        and gap_assessment["visual_discoloration_percent"] is not None
                        else gap_assessment["severity_description"]
                        if gap_assessment and gap_assessment["severity_description"]
                        else "Not estimable" if gap_assessment
                        else "N/A"
                    )
                )
                displayed_stage = (
                    severity_stage if severity_stage != "Not available"
                    else (
                        gap_assessment["severity_description"] or "Not estimable"
                        if gap_assessment else severity_stage
                    )
                )

            with st.container(border=True, key="cg-farmer-summary"):
                guide_key = st.session_state.get("last_disease_guide")
                management_advisory = st.session_state.get("last_gemini_advisory")
                if management_advisory:
                    render_missing_kb_advisory(
                        management_advisory,
                        language,
                        region_resources=active_zone_data.get("resources", []),
                        hub_label=selected_hub_label,
                        crop_name=chosen_crop,
                        guide_key=guide_key,
                        severity_stage=severity_stage,
                    )
                else:
                    st.subheader(raw_label)
                    st.write(f"**{T['crop_context_lbl']}** {chosen_crop}")
                    if st.session_state.get("last_diagnosis_notice"):
                        st.warning(st.session_state["last_diagnosis_notice"])
                    st.caption(T["diagnosis_disclaimer"])
                    st.markdown(f"### {T['treatment_header']}")
                    if st.session_state.get("last_gemini_advisory_error"):
                        st.warning(
                            "Additional crop-management guidance could not be generated. "
                            "Please try again."
                        )
                    if is_healthy_prediction and diagnosis_available and guide_key:
                        st.markdown(f"**{T['prog_status_lbl']}** `{displayed_stage}`")
                        if severity_stage.startswith("Stage 3"):
                            st.error(T["stage3_alert"])
                        elif severity_stage.startswith("Stage 2"):
                            st.warning(T["stage2_alert"])
                        elif severity_stage.startswith("Stage 1"):
                            st.success(T["stage1_alert"])

                        render_disease_guide(
                            guide_key,
                            chosen_crop,
                            language,
                            severity_stage,
                            selected_hub_label,
                        )
                    elif diagnosis_available and guide_key:
                        render_disease_guide(
                            guide_key,
                            chosen_crop,
                            language,
                            severity_stage,
                            selected_hub_label,
                        )
                    else:
                        st.info(T.get(
                            "disease_guide_unavailable",
                            "No exact crop-compatible knowledge-base match was found for this model class.",
                        ))

            with st.container(border=True):
                st.markdown(f"### {T['hub_support_header']} ({selected_hub_label})")
                st.info(T["hub_support_info"])
                audio_col, resources_col = st.columns(2, gap="large")
                with audio_col:
                    if gap_assessment:
                        if language == "Kiswahili":
                            audio_text = (
                                f"Makadirio ya ziada ambayo hayajathibitishwa kwa "
                                f"{chosen_crop}: {gap_assessment['assessment']}. "
                                "Thibitisha kwa afisa wa ugani wa kilimo wa eneo lako."
                            )
                        elif language == "French":
                            audio_text = (
                                f"Estimation complémentaire non confirmée pour "
                                f"{chosen_crop} : {gap_assessment['assessment']}. "
                                "Faites-la confirmer par un conseiller agricole local."
                            )
                        else:
                            audio_text = (
                                f"Unconfirmed AI follow-up estimate for {chosen_crop}: "
                                f"{gap_assessment['assessment']}. Ask a local agricultural "
                                "extension officer to confirm it."
                            )
                    elif not diagnosis_available:
                        if language == "Kiswahili":
                            audio_text = "Hakuna utambuzi wa kuaminika unaopatikana kwa picha hii."
                        elif language == "French":
                            audio_text = "Aucun diagnostic fiable n’est disponible pour cette image."
                        else:
                            audio_text = "No reliable diagnosis is available for this image."
                    elif language == "Kiswahili":
                        audio_text = (
                            f"Matokeo ya uchunguzi wa {chosen_crop}: {raw_label}. "
                            "Fuata hatua za usimamizi na uwasiliane na afisa wa ugani "
                            "ikiwa dalili zitaendelea."
                        )
                    elif language == "French":
                        audio_text = (
                            f"Résultat du dépistage pour {chosen_crop}: {raw_label}. "
                            "Suivez les mesures de gestion et contactez un conseiller "
                            "agricole si les symptômes persistent."
                        )
                    else:
                        audio_text = (
                            f"Screening result for {chosen_crop}: {raw_label}. Follow the "
                            "management steps and contact an extension officer if symptoms persist."
                        )
                    render_tts_audio_controls(audio_text, tts_lang)
                with resources_col:
                    render_hub_resource_directory(
                        active_zone_data.get("resources", []),
                        selected_hub_label,
                        st.session_state.get("gps_status"),
                        language,
                    )

            advanced_labels = {
                "English": "🔬 View Advanced Technical & Model Breakdown",
                "Kiswahili": "🔬 Tazama Uchambuzi wa Kina wa Kiufundi na Miundo",
                "French": "🔬 Voir l’analyse technique et les modèles",
            }
            with st.expander(
                advanced_labels.get(
                    language,
                    advanced_labels["English"],
                ),
                expanded=False,
            ):
                st.success(T["analysis_complete_msg"])
                di.render_log_outcome(st, T, st.session_state.get("last_log_outcome"))
                if st.session_state.get("last_analysis_error"):
                    st.error(st.session_state["last_analysis_error"])

                st.subheader(raw_label)
                st.write(f"**{T['crop_context_lbl']}** {chosen_crop}")
                metric_col1, metric_col2 = st.columns(2, gap="medium")
                metric_col1.metric(T["ai_conf_lbl"], confidence_display)
                metric_col2.metric(T["inf_sev_lbl"], severity_display)
                if gap_assessment:
                    render_uncertain_assessment(gap_assessment, language)
                elif gap_error:
                    st.warning(
                        "An additional assessment could not be completed. Please try again."
                    )
                confidence_margin = st.session_state.get("last_confidence_margin")
                if confidence_margin is not None:
                    st.caption(
                        f"{T['ai_margin_lbl']}: {float(confidence_margin):.1f}. "
                        f"{T['quality_confidence_caution']}"
                    )

                render_consensus_report(
                    st.session_state.get("last_consensus_report"),
                    language,
                    _consensus_configuration(),
                )
                render_advisory_technical_analysis(
                    st.session_state.get("last_gemini_advisory"),
                    language,
                )

            if st.button(
                T["scan_another_btn"],
                use_container_width=True,
                key="scan_another_leaf",
            ):
                clear_diagnostic_results()
                st.session_state["selected_crop"] = None
                st.session_state.pop("diagnostic_crop_selector", None)
                st.session_state.pop("diagnostic_sample_source", None)
                st.session_state.pop("file_upload", None)
                st.session_state.pop("_last_upload_digest", None)
                st.rerun()

        is_active = uploaded_file is not None or st.session_state.get("analysis_done", False)
        play_state = "paused" if is_active else "running"

        st.markdown("""
        <style>
        section.main > div, [data-testid="stSidebar"] > div, .block-container {
            opacity: 1 !important;
            transition: none !important;
        }
        [data-testid="stSkeleton"] {
            display: none !important;
        }

        .bg-container {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            z-index: -999;
            background-color: #1E4620;
        }
        
        .bg-slide {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background-size: cover; background-position: center; background-repeat: no-repeat;
            opacity: 0; animation-timing-function: ease-in-out; animation-iteration-count: infinite;
            animation-duration: 40s; animation-play-state: {play_state}; will-change: transform, opacity;
        }
        
        .slide-1 { background-image: linear-gradient(rgba(0, 30, 15, 0.7), rgba(0, 15, 5, 0.9)), url("https://images.unsplash.com/photo-1500937386664-56d1dfef3854?auto=format&fit=crop&w=2070&q=80"); animation-name: fadeSlide1; }
        .slide-2 { background-image: linear-gradient(rgba(0, 30, 15, 0.7), rgba(0, 15, 5, 0.9)), url("https://images.unsplash.com/photo-1625246333195-78d9c38ad449?auto=format&fit=crop&w=2070&q=80"); animation-name: fadeSlide2; }
        .slide-3 { background-image: linear-gradient(rgba(0, 30, 15, 0.7), rgba(0, 15, 5, 0.9)), url("https://images.unsplash.com/photo-1550989460-0adf9ea622e2?auto=format&fit=crop&w=2070&q=80"); animation-name: fadeSlide3; }
        .slide-4 { background-image: linear-gradient(rgba(0, 30, 15, 0.7), rgba(0, 15, 5, 0.9)), url("https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=2070&q=80"); animation-name: fadeSlide4; }
        .slide-5 { background-image: linear-gradient(rgba(0, 30, 15, 0.7), rgba(0, 15, 5, 0.9)), url("https://images.unsplash.com/photo-1592982537447-7440770cbfc9?auto=format&fit=crop&w=2070&q=80"); animation-name: fadeSlide5; }

        @keyframes fadeSlide1 { 0% { opacity: 1; transform: scale(1); } 16% { opacity: 1; transform: scale(1.03); } 20% { opacity: 0; transform: scale(1.04); } 96% { opacity: 0; transform: scale(1); } 100% { opacity: 1; transform: scale(1); } }
        @keyframes fadeSlide2 { 0% { opacity: 0; transform: scale(1); } 16% { opacity: 0; transform: scale(1.04); } 20% { opacity: 1; transform: scale(1.04); } 36% { opacity: 1; transform: scale(1.01); } 40% { opacity: 0; transform: scale(1); } 100% { opacity: 0; transform: scale(1); } }
        @keyframes fadeSlide3 { 0% { opacity: 0; transform: scale(1); } 36% { opacity: 0; transform: scale(1); } 40% { opacity: 1; transform: scale(1); } 56% { opacity: 1; transform: scale(1.03); } 60% { opacity: 0; transform: scale(1.04); } 100% { opacity: 0; transform: scale(1); } }
        @keyframes fadeSlide4 { 0% { opacity: 0; transform: scale(1); } 56% { opacity: 0; transform: scale(1.04); } 60% { opacity: 1; transform: scale(1.04); } 76% { opacity: 1; transform: scale(1.01); } 80% { opacity: 0; transform: scale(1); } 100% { opacity: 0; transform: scale(1); } }
        @keyframes fadeSlide5 { 0% { opacity: 0; transform: scale(1); } 76% { opacity: 0; transform: scale(1); } 80% { opacity: 1; transform: scale(1); } 96% { opacity: 1; transform: scale(1.03); } 100% { opacity: 0; transform: scale(1.04); } }

        .stApp { background: transparent !important; }
        .main .block-container { background-color: transparent; padding: 2rem 3rem; }
        section[data-testid="stSidebar"] { background: linear-gradient(180deg, rgba(232, 245, 233, 0.9) 0%, rgba(200, 230, 201, 0.9) 100%); }

        .st-key-cg-farmer-summary {
            background: rgba(3, 20, 12, 0.98) !important;
            border: 1px solid rgba(165, 214, 167, 0.72) !important;
            border-radius: 16px !important;
            padding: 1.5rem !important;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.62) !important;
        }
        .st-key-cg-farmer-summary * {
            color: #FFFFFF !important;
            text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.95) !important;
        }
        
        h1, h2, h3, h4, h5, h6, p, span, li, label, div[data-testid="stMarkdownContainer"] {
            color: #FFFFFF !important;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.9) !important;
        }
        
        [data-testid="stVerticalBlock"] [data-testid="stContainer"] {
            background-color: rgba(4, 25, 12, 0.95) !important;
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 14px;
            padding: 1.5rem;
            box-shadow: 0 10px 35px 0 rgba(0, 0, 0, 0.5);
        }
        
        .stButton>button {
            background: linear-gradient(135deg, #00897B 0%, #2E7D32 100%);
            color: white; border-radius: 8px; border: none; padding: 0.7rem 2rem;
            font-weight: bold; letter-spacing: 0.5px;
            transition: all 0.2s ease;
        }
        .stButton>button:hover {
            background: linear-gradient(135deg, #00695C 0%, #1B5E20 100%);
            transform: translateY(-2px);
        }
        [data-testid="stMetricValue"] {
            color: #A5D6A7 !important; font-weight: 700;
            text-shadow: 1px 1px 3px rgba(0,0,0,0.95);
        }
        
        [data-testid="stFileUploader"] {
            background-color: rgba(15, 40, 22, 0.85); padding: 1rem;
            border-radius: 12px; border: 2px dashed #81C784;
        }
        
        [data-testid="stFileUploader"] button {
            background-color: #F57C00 !important;
            color: white !important;
            border: none !important;
        }
        </style>
        <div class="bg-container">
            <div class="bg-slide slide-1"></div>
            <div class="bg-slide slide-2"></div>
            <div class="bg-slide slide-3"></div>
            <div class="bg-slide slide-4"></div>
            <div class="bg-slide slide-5"></div>
        </div>
        """.replace("{play_state}", play_state), unsafe_allow_html=True)

        if analyze_triggered and uploaded_file is not None and image is not None and assessment is not None:
            st.session_state['selected_crop'] = selected_crop
            st.session_state["last_gemini_advisory"] = None
            st.session_state["last_gemini_advisory_error"] = None
            st.session_state["last_gemini_gap_assessment"] = None
            st.session_state["last_gemini_gap_error"] = None
            st.session_state["last_analysis_error"] = None

            def infer_local_vision():
                class_indices = supported_class_indices(selected_crop)
                if not class_indices:
                    return {
                        "available": False,
                        "detected_crop": selected_crop,
                        "primary_diagnosis": "unsupported crop",
                        "metadata": {
                            "diagnosis_available": False,
                            "predicted_label": T["unsupported_crop_msg"],
                            "confidence_val": 0.0,
                            "confidence_margin_val": 0.0,
                            "severity_stage": "Not available",
                            "severity_pct": 0.0,
                            "diagnosis_notice": T["unsupported_crop_msg"],
                            "disease_guide_key": None,
                            "epidemiological_label": None,
                        },
                    }
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
                if np.all((prediction_scores >= 0) & (prediction_scores <= 1)) and np.isclose(np.sum(prediction_scores), 1.0, atol=1e-3):
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
                epidemiological_label = None
                diagnosis_guide_key = None
                diagnosis_available = True
                if (
                    confidence_val < MODEL_SCREENING_MIN_SCORE_PCT
                    or confidence_margin_val < MODEL_SCREENING_MIN_MARGIN_PCT
                ):
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

                return {
                    "available": True,
                    "detected_crop": crop_label,
                    "primary_diagnosis": "healthy" if is_healthy_prediction else disease_label,
                    "confidence_score": confidence_val / 100.0,
                    "confidence_margin": confidence_margin_val / 100.0,
                    "health_status": "healthy" if is_healthy_prediction else "diseased",
                    "metadata": {
                        "diagnosis_available": diagnosis_available,
                        "predicted_label": predicted_label,
                        "confidence_val": confidence_val,
                        "confidence_margin_val": confidence_margin_val,
                        "severity_stage": stage,
                        "severity_pct": pct,
                        "diagnosis_notice": diagnosis_notice,
                        "disease_guide_key": diagnosis_guide_key,
                        "epidemiological_label": epidemiological_label,
                    },
                }

            consensus_config = _consensus_configuration()
            try:
                with st.status("Starting diagnostic agents...", expanded=True) as consensus_status:
                    consensus_status.markdown(
                        '<span class="cg-diagnostic-status-marker" aria-hidden="true"></span>',
                        unsafe_allow_html=True,
                    )

                    def update_consensus_status(stage_name, _message):
                        stage_labels = {
                            "starting": "Starting crop screening...",
                            "vision": "Assessing the crop image...",
                            "local": "Running a local image cross-check...",
                            "reasoning": "Checking crop and symptom information...",
                            "arbitration": "Preparing the screening summary...",
                        }
                        consensus_status.update(
                            label=stage_labels.get(
                                stage_name,
                                "Processing crop screening...",
                            ),
                            state="running",
                            expanded=True,
                        )

                    report = cropguard_consensus.run_consensus(
                        image_bytes=upload_bytes,
                        mime_type=uploaded_file.type or "image/jpeg",
                        selected_crop=selected_crop,
                        region=selected_hub_label,
                        language=language,
                        local_vision=infer_local_vision,
                        config=consensus_config,
                        progress=update_consensus_status,
                    )
                    consensus_status.update(
                        label="Diagnostic screening consensus complete.",
                        state="complete",
                        expanded=False,
                    )
                st.session_state["last_consensus_report"] = report.to_dict()
                local_metadata = report.local_vision.metadata
                vision = report.vision
                diagnosis = vision.primary_diagnosis.strip()
                normalized_diagnosis = diagnosis.casefold()
                is_gemini_healthy = (
                    vision.health_status == "healthy"
                    or normalized_diagnosis in {"healthy", "no disease", "none"}
                )
                has_gemini_diagnosis = (
                    is_gemini_healthy
                    or (
                        vision.health_status in {"diseased", "pest damage"}
                        and normalized_diagnosis not in {"", "uncertain", "unknown", "not sure"}
                    )
                )
                if vision.error is None and vision.confidence_score > 0:
                    local_metadata = dict(local_metadata)
                    diagnosis_crop = vision.detected_crop.strip() or selected_crop
                    diagnosis_guide_key = (
                        "healthy" if is_gemini_healthy
                        else find_disease_guide_key(diagnosis_crop, diagnosis)
                        if has_gemini_diagnosis else None
                    )
                    epidemiological_label = (
                        disease_guide_data.DISEASES[diagnosis_guide_key]["epi"]
                        if diagnosis_guide_key and diagnosis_guide_key != "healthy"
                        else diagnosis if has_gemini_diagnosis and not is_gemini_healthy
                        else None
                    )
                    if is_gemini_healthy:
                        severity_stage = "No disease class identified"
                        severity_pct = 0.0
                        diagnosis_notice = T["healthy_class_msg"]
                    elif has_gemini_diagnosis:
                        severity_stage, severity_pct = analyze_leaf_severity(image)
                        diagnosis_notice = (
                            T["low_confidence_msg"]
                            if vision.confidence_score * 100 < MODEL_SCREENING_MIN_SCORE_PCT
                            else None
                        )
                    else:
                        severity_stage, severity_pct = "Not available", 0.0
                        diagnosis_notice = T["low_confidence_msg"]
                    local_metadata.update({
                        "diagnosis_available": (
                            has_gemini_diagnosis
                            and (
                                is_gemini_healthy
                                or vision.confidence_score * 100
                                >= MODEL_SCREENING_MIN_SCORE_PCT
                            )
                        ),
                        "predicted_label": (
                            f"Healthy {diagnosis_crop}" if is_gemini_healthy
                            else f"{diagnosis_crop}: {diagnosis}"
                        ),
                        "diagnosed_crop": diagnosis_crop,
                        "confidence_val": vision.confidence_score * 100,
                        "confidence_margin_val": None,
                        "severity_stage": severity_stage,
                        "severity_pct": severity_pct,
                        "diagnosis_notice": diagnosis_notice,
                        "disease_guide_key": diagnosis_guide_key,
                        "epidemiological_label": epidemiological_label,
                        "health_status": vision.health_status,
                    })
            except Exception as error:
                print(f"Consensus screening failed: {error}")
                st.session_state["last_analysis_error"] = (
                    "Image screening encountered an issue; attempting local screening only."
                )
                try:
                    local_output = infer_local_vision()
                    local_metadata = local_output.get("metadata", {})
                except Exception as local_error:
                    print(f"Local ONNX screening failed: {local_error}")
                    st.session_state["last_analysis_error"] += (
                        "\nLocal screening also failed. Please try another image."
                    )
                    local_metadata = {}

            diagnosis_available = bool(local_metadata.get("diagnosis_available", False))
            predicted_label = local_metadata.get("predicted_label", T["unsupported_crop_msg"])
            confidence_val = float(local_metadata.get("confidence_val", 0.0))
            raw_confidence_margin = local_metadata.get("confidence_margin_val", 0.0)
            confidence_margin_val = (
                float(raw_confidence_margin) if raw_confidence_margin is not None else None
            )
            stage = local_metadata.get("severity_stage", "Not available")
            pct = float(local_metadata.get("severity_pct", 0.0))
            diagnosis_notice = local_metadata.get("diagnosis_notice", T["unsupported_crop_msg"])
            diagnosis_guide_key = local_metadata.get("disease_guide_key")
            epidemiological_label = local_metadata.get("epidemiological_label")
            diagnosed_crop = local_metadata.get("diagnosed_crop") or selected_crop
            is_healthy_prediction = (
                local_metadata.get("health_status") == "healthy"
                or (
                    diagnosis_available
                    and diagnosis_guide_key == "healthy"
                )
            )

            if not diagnosis_available or stage == "Not available":
                try:
                    gap_assessor = getattr(
                        cropguard_consensus,
                        "generate_uncertain_diagnostic",
                        None,
                    )
                    if not callable(gap_assessor):
                        importlib.reload(cropguard_consensus)
                        gap_assessor = getattr(
                            cropguard_consensus,
                            "generate_uncertain_diagnostic",
                            None,
                        )
                    if not callable(gap_assessor):
                        raise cropguard_consensus.ProviderError(
                            "Additional assessment is not available. Restart Streamlit "
                            "to load the updated consensus module."
                        )
                    with st.spinner("Completing an additional assessment of the uncertain result..."):
                        st.session_state["last_gemini_gap_assessment"] = gap_assessor(
                            image_bytes=upload_bytes,
                            mime_type=uploaded_file.type or "image/jpeg",
                            crop=diagnosed_crop,
                            region=selected_hub_label,
                            language=language,
                            config=consensus_config,
                        )
                except cropguard_consensus.ProviderError as error:
                    st.session_state["last_gemini_gap_error"] = str(error)

            st.session_state['last_prediction'] = predicted_label
            st.session_state['last_confidence'] = confidence_val
            st.session_state['last_confidence_margin'] = confidence_margin_val
            st.session_state['last_severity_stage'] = stage
            st.session_state['last_severity_pct'] = pct
            st.session_state['last_diagnosis_notice'] = diagnosis_notice
            st.session_state['last_diagnosis_available'] = diagnosis_available
            st.session_state['last_disease_guide'] = diagnosis_guide_key
            consensus_data = st.session_state.get("last_consensus_report") or {}
            vision_data = consensus_data.get("vision") or {}
            if not is_healthy_prediction:
                advisory_diagnosis = (
                    vision_data.get("primary_diagnosis")
                    if not vision_data.get("error")
                    and vision_data.get("confidence_score", 0) > 0
                    and vision_data.get("primary_diagnosis", "").casefold()
                    not in {"", "uncertain", "unknown", "not sure"}
                    else st.session_state.get("last_gemini_gap_assessment", {}).get(
                        "assessment"
                    ) or consensus_data.get("primary_diagnosis", predicted_label)
                )
                advisory_symptoms = (
                    vision_data.get("visual_symptoms")
                    or st.session_state.get("last_gemini_gap_assessment", {}).get("observations")
                    or []
                )
                try:
                    advisory_generator = getattr(
                        cropguard_consensus,
                        "generate_management_advisory",
                        None,
                    )
                    if not callable(advisory_generator):
                        importlib.reload(cropguard_consensus)
                        advisory_generator = getattr(
                            cropguard_consensus,
                            "generate_management_advisory",
                            None,
                        )
                    if not callable(advisory_generator):
                        raise cropguard_consensus.ProviderError(
                            "Crop-management guidance is not available. Restart Streamlit "
                            "to load the updated consensus module."
                        )
                    with st.spinner("Preparing cautious crop-management guidance..."):
                        st.session_state["last_gemini_advisory"] = (
                            advisory_generator(
                                crop=diagnosed_crop,
                                diagnosis=advisory_diagnosis,
                                symptoms=advisory_symptoms,
                                region=selected_hub_label,
                                language=language,
                                config=consensus_config,
                                local_conditions={
                                    "temperature_c": active_zone_data.get("temp"),
                                    "relative_humidity_percent": active_zone_data.get("humidity"),
                                    "regional_risk_note": active_zone_data.get("risk"),
                                },
                            )
                        )
                except cropguard_consensus.ProviderError as error:
                    st.session_state["last_gemini_advisory_error"] = str(error)

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
                        target_crop=diagnosed_crop,
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
            st.session_state["last_language"] = language
            st.session_state["last_diagnostic_hub"] = selected_hub_label
            st.session_state["analysis_done"] = True
            st.rerun()

    diagnostic_workflow()

# --- FOOTER ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f"<div style='text-align: center; color: #FFFFFF; text-shadow: 1px 1px 3px rgba(0,0,0,0.9); font-weight: 500;'>"
    f"{T['footer_text']} ({selected_hub_label})"
    f"</div>", 
    unsafe_allow_html=True
)

st.markdown("""
<style>
[data-testid="stButton"] button:not([kind="primary"]),
[data-testid="stFormSubmitButton"] button:not([kind="primary"]),
[data-testid="stDownloadButton"] button:not([kind="primary"]),
[data-testid="stPopover"] button:not([kind="primary"]),
[data-testid="stLinkButton"] a {
    background: #F3F4F6 !important;
    color: #111827 !important;
    text-shadow: none !important;
}
[data-testid="stButton"] button:not([kind="primary"]) *,
[data-testid="stFormSubmitButton"] button:not([kind="primary"]) *,
[data-testid="stDownloadButton"] button:not([kind="primary"]) *,
[data-testid="stPopover"] button:not([kind="primary"]) *,
[data-testid="stLinkButton"] a * {
    color: #111827 !important;
    text-shadow: none !important;
}
[data-testid="stAlert"],
[data-testid="stProgress"] {
    background: #F3F4F6 !important;
    color: #111827 !important;
    border: 1px solid #D1D5DB !important;
    border-radius: 8px;
}
[data-testid="stAlert"] *,
[data-testid="stProgress"] * {
    color: #111827 !important;
    text-shadow: none !important;
}
[data-testid="stExpander"]:has(.cg-diagnostic-status-marker),
[data-testid="stExpander"]:has(.cg-diagnostic-status-marker) * {
    color: #111827 !important;
    text-shadow: none !important;
}
[data-testid="stAlert"] p,
[data-testid="stAlert"] span,
[data-testid="stAlert"] label,
[data-testid="stAlert"] li,
[data-testid="stAlert"] strong,
[data-testid="stAlert"] [data-testid="stMarkdownContainer"],
[data-testid="stProgress"] p,
[data-testid="stProgress"] span,
[data-testid="stProgress"] label {
    color: #111827 !important;
    text-shadow: none !important;
}
</style>
""", unsafe_allow_html=True)

if app_mode != T["nav_diag"]:
    st.markdown("""
    <style>
    [data-testid="stMain"] [data-testid="stMetric"] {
        background: rgba(12, 16, 20, 0.96) !important;
        border: 1px solid rgba(226, 232, 240, 0.22) !important;
        border-radius: 12px !important;
        padding: 14px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.28) !important;
    }
    [data-testid="stMain"] [data-testid="stMetricLabel"],
    [data-testid="stMain"] [data-testid="stMetricLabel"] *,
    [data-testid="stMain"] [data-testid="stMetricValue"],
    [data-testid="stMain"] [data-testid="stMetricValue"] * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        opacity: 1 !important;
        text-shadow: 0 1px 4px rgba(0, 0, 0, 0.95) !important;
    }
    [data-testid="stMain"] [data-testid="stMetricLabel"] {
        font-weight: 700 !important;
    }
    [data-testid="stMain"] [data-testid="stMetricValue"] {
        font-weight: 800 !important;
    }
    [data-testid="stMain"] [data-testid="stChatMessage"] {
        color: #FFFFFF !important;
        background: rgba(12, 16, 20, 0.96) !important;
        border: 1px solid rgba(226, 232, 240, 0.22) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.28) !important;
    }
    [data-testid="stMain"] [data-testid="stChatMessage"] *,
    [data-testid="stMain"] [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] *,
    [data-testid="stMain"] [data-testid="stChatMessage"] p {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        opacity: 1 !important;
        text-shadow: 0 1px 4px rgba(0, 0, 0, 0.95) !important;
    }
    </style>
    """, unsafe_allow_html=True)

if app_mode == T["nav_ai"]:
    st.markdown("""
    <style>
    [data-testid="stMain"] [data-testid="stChatInput"] textarea,
    [data-testid="stMain"] [data-testid="stChatInputTextArea"] {
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        background-color: #FFFFFF !important;
        caret-color: #111827 !important;
        opacity: 1 !important;
        text-shadow: none !important;
    }
    [data-testid="stMain"] [data-testid="stChatInput"] textarea::placeholder,
    [data-testid="stMain"] [data-testid="stChatInputTextArea"]::placeholder {
        color: #4B5563 !important;
        -webkit-text-fill-color: #4B5563 !important;
        opacity: 1 !important;
    }
    </style>
    """, unsafe_allow_html=True)
