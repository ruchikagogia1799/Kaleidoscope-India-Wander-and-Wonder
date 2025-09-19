# app.py — Kaleidoscope India: Sights • Stories • Street Food
# Run: streamlit run app.py

import os, re, pathlib, urllib.parse
from io import BytesIO
import numpy as np
import pandas as pd
import streamlit as st
from PIL import UnidentifiedImageError  # for safe image handling

# Optional: if you later want AVIF support, add pillow-avif-plugin in requirements and keep this try/except.
try:
    from pillow_avif import AvifImagePlugin  # noqa: F401
except Exception:
    pass

CSV_PATH = "combined.csv"
IMG_ROOT_ATTR  = pathlib.Path("images_verified")
IMG_ROOT_DISH  = pathlib.Path("images_verified_dishes")
# Removed ".avif" to avoid Pillow errors on platforms without AVIF plugin
IMG_EXTS = [".jpg", ".jpeg", ".png", ".webp", ".gif"]

CONTACT_EMAIL = "ruchikagogia17@gmail.com"
INSTAGRAM_HANDLE = "wanderlust.ruchika"
INSTAGRAM_URL = "https://www.instagram.com/wanderlust.ruchika?igsh=MTJlMHdqMGszc3Fv"

def find_named_image(basename: str) -> str | None:
    """Return a path to 'basename' image, trying common folders and extensions."""
    candidates = []
    for ext in IMG_EXTS:
        candidates += [
            pathlib.Path(f"{basename}{ext}"),
            pathlib.Path("images") / f"{basename}{ext}",
            pathlib.Path("assets") / f"{basename}{ext}",
        ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None

st.set_page_config(page_title="Kaleidoscope India • Wander & Wonder", page_icon="🌏", layout="wide")

# ----------------------------- Styles -----------------------------
st.markdown("""
<style>
:root{ --rounded:16px; }
.main .block-container{ padding-top:.6rem; padding-bottom:1.2rem; }
.hero{
  display:flex; gap:16px; align-items:center; border:1px solid #efeae2;
  border-radius:var(--rounded); padding:12px 14px; background:#fff;
  min-height:50vh;
}
.hero img{
  height:50vh; max-height:50vh; width:100%;
  border-radius:12px; object-fit:cover; object-position:center;
  display:block;
}
.hero .copy h1{ font-size:1.7rem; margin:.25rem 0 .35rem; }
.badge{ display:inline-block; padding:.15rem .5rem; border-radius:999px; font-size:.80rem; background:#f4f4f5; margin:.1rem }
.card{ border:1px solid #eee; border-radius:var(--rounded); background:#fff; box-shadow:0 1px 1px rgba(10,10,10,.04); height:100%; overflow:hidden }
.card-body{ padding:14px }
.card h4{ margin:.15rem 0 .25rem; font-size:1.06rem }
.kv{ color:#444; font-size:.92rem }
.small{ color:#666; font-size:.85rem }
.tag{ display:inline-block; font-size:.78rem; padding:.18rem .5rem; border-radius:8px; margin-left:.35rem}
.veg{ background:#ecfdf5; color:#065f46; border:1px solid #a7f3d0 }
.nonveg{ background:#fef2f2; color:#7f1d1d; border:1px solid #fecaca }
.detail{ border:1px solid #e9e9e9; background:#fff; border-radius:18px; padding:18px; box-shadow:0 6px 20px rgba(0,0,0,.06); }
.detail h2{ margin:.2rem 0 .4rem; }
hr.soft{ border:none; border-top:1px solid #eee; margin:.8rem 0; }
.imgcap{ color:#666; font-size:.8rem; margin-top:.25rem }
.filters{ border:1px solid #eee; border-radius:18px; padding:18px; background:#fff; box-shadow:0 4px 16px rgba(0,0,0,.05); }
.sticky{ position: sticky; top: 1rem; }
.qrow{ border:1px solid #eee; border-radius:12px; padding:.6rem .8rem; margin:.35rem 0; background:#fff; }
.qok{ background:#f0fdf4; border-color:#bbf7d0; }
.qbad{ background:#fef2f2; border-color:#fecaca; }
</style>
""", unsafe_allow_html=True)

# ------------------------- Helpers / IO ---------------------------
def clean_text(s): return re.sub(r"\s+", " ", str(s)).strip()
def keyfy(s): return clean_text(s).casefold()
def _norm(s: str) -> str: return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(s).lower())).strip("_")

def tolerant_csv_read(path: str):
    try:
        return pd.read_csv(path)
    except Exception as e:
        st.warning(f"CSV parse failed: {e}\nRetrying with tolerant parser…")
        return pd.read_csv(path, engine="python", on_bad_lines="skip")

@st.cache_data(show_spinner=False)
def load_csv(path: str):
    return tolerant_csv_read(path) if os.path.exists(path) else None

def pick_col(df, candidates):
    for c in candidates:
        if c in df.columns: return c
    return None

# Display images robustly (prevents crashes)
def safe_image(src, **kwargs) -> bool:
    """Try to display an image; on failure, show a small note and continue."""
    if not src:
        return False
    try:
        st.image(src, **kwargs)
        return True
    except (FileNotFoundError, UnidentifiedImageError, OSError, TypeError) as e:
        st.caption(f"🖼️ Image unavailable ({e.__class__.__name__}).")
        return False

# ---------- STRICT local lookup (keeps within same state/city) ----------
STOP_WORDS = {
    "temple","mandir","fort","palace","gate","park","lake","beach","museum",
    "national","state","monument","ji","sri","shri","maa","mata","baba","the"
}
def _tokset(s: str) -> set[str]:
    return {t for t in _norm(s).split("_") if t and t not in STOP_WORDS}

def _folder_variants(name: str):
    if not isinstance(name, str): return []
    raw = name
    underscored = re.sub(r"\s+", "_", raw.strip())
    stripped = re.sub(r"[^A-Za-z0-9_]", "", underscored)
    return [raw, underscored, stripped]

def _find_in_folder_strict(basefolder: pathlib.Path, state: str, city: str, stems: list[str], kind: str):
    if not basefolder.exists():
        return None

    state_dir = None
    for sname in _folder_variants(state):
        cand = basefolder / sname
        if cand.exists():
            state_dir = cand
            break
    if not state_dir:
        return None

    city_dir = None
    for cname in _folder_variants(city):
        cand = state_dir / cname
        if cand.exists():
            city_dir = cand
            break

    stem_norms = [_norm(s) for s in stems]
    stem_toksets = [_tokset(s) for s in stems]
    stem_flat_subs = [sn.replace("_","") for sn in stem_norms]

    def _exact_in(folder: pathlib.Path):
        if not folder or not folder.exists():
            return None
        for stem in stem_norms:
            for ext in IMG_EXTS:
                p = folder / f"{stem}{ext}"
                if p.exists():
                    return str(p)
        return None

    def _loose_in(folder: pathlib.Path):
        if not folder or not folder.exists():
            return None
        for p in folder.rglob("*"):
            if p.is_file() and p.suffix.lower() in IMG_EXTS:
                cand_norm = _norm(p.stem)
                cand_toks = _tokset(cand_norm)
                cand_flat = cand_norm.replace("_","")
                for toks, flat in zip(stem_toksets, stem_flat_subs):
                    if len(cand_toks & toks) >= 2 or (flat and (flat in cand_flat or cand_flat in flat)):
                        return str(p)
        return None

    for where in (city_dir, state_dir):
        hit = _exact_in(where)
        if hit: return hit
    for where in (city_dir, state_dir):
        hit = _loose_in(where)
        if hit: return hit
    return None

def resolve_image(
    csv_val: str,
    *,
    subdir: str,
    attraction: str = "",
    city: str = "",
    state: str = "",
    local_base: str = "",
    dish: str = None,
    overrides: dict | None = None,
) -> str | None:
    overrides = overrides or {}
    kind = "dish" if subdir == "dishes" else "attr"

    # 1) explicit override
    override_url = overrides.get("dish_image_override_url") if kind == "dish" else overrides.get("attraction_image_override_url")
    if isinstance(override_url, str) and override_url.strip() and override_url.strip().lower() != "nan":
        return override_url.strip()

    # 2) CSV value (URL or relative path)
    if isinstance(csv_val, str) and csv_val.strip() and csv_val.strip().lower() != "nan":
        v = csv_val.strip()
        if v.startswith(("http://", "https://")):
            return v
        roots = [
            pathlib.Path("."),
            (IMG_ROOT_DISH if kind == "dish" else IMG_ROOT_ATTR),
            pathlib.Path("images") / subdir,
            pathlib.Path("images"),
        ]
        for r in roots:
            p = (r / v) if not pathlib.Path(v).is_absolute() else pathlib.Path(v)
            if p.exists():
                return str(p)
        # If it's not a URL and we didn't find a real file, don't return a bogus path
        return None

    # 3) local search (strict)
    def _stem_candidates(attraction, city, state, dish_name=None, kind="attr"):
        base = []
        aN, cN, sN = _norm(attraction), _norm(city), _norm(state)
        base += [f"{aN}_{cN}_{sN}", f"{aN}_{cN}", aN]
        if kind == "dish":
            if dish_name:
                dN = _norm(dish_name)
                base = [f"{dN}_{cN}_{sN}", f"{dN}_{cN}", dN] + base
            base += [f"{aN}_{cN}_{sN}_dish", f"{aN}_{cN}_dish", f"{aN}_dish"]
        return base

    stems = []
    if isinstance(local_base, str) and local_base:
        stems.append(local_base)
    stems += _stem_candidates(attraction, city, state, dish_name=dish, kind=kind)

    root = IMG_ROOT_DISH if kind == "dish" else IMG_ROOT_ATTR
    hit = _find_in_folder_strict(root, state, city, stems, kind)
    if hit: return hit
    alt_root = pathlib.Path("images") / subdir
    hit = _find_in_folder_strict(alt_root, state, city, stems, kind)
    if hit: return hit
    return None

ATTRACTION_IMG_COLS = ["Attraction Image (src)","Attraction Image","Attraction Image URL","Image","Photo"]
DISH_IMG_COLS       = ["Dish Image (src)","Dish Image","Dish Image URL","Dish Photo"]

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for c in ["Region","State","City","Main Tourist Attraction","Type of Attractions",
              "Nearest Airport","Best Time (Months)","Best Time to visit","Dish Name",
              "Veg or Non Veg","Type of Dish","Course","DSLR Allowed"]:
        if c in df.columns: df[c] = df[c].map(clean_text)

    if "DSLR Allowed" in df.columns:
        x = df["DSLR Allowed"].astype(str).str.strip().str.lower()
        df["DSLR Allowed (std)"] = np.where(
            x.str.startswith("y"), "Yes",
            np.where(x.str.startswith("n"), "No", "Unknown")
        )

    for c in ["Google Review Rating","Entrance Fee (INR)","Number of Google Reviews"]:
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")

    a_col = pick_col(df, ATTRACTION_IMG_COLS)
    d_col = pick_col(df, DISH_IMG_COLS)
    if a_col and a_col != "Attraction Image (src)": df["Attraction Image (src)"] = df[a_col]
    if d_col and d_col != "Dish Image (src)": df["Dish Image (src)"] = df[d_col]

    for c in ["Main Tourist Attraction","City","State"]:
        df[f"_{c}_key"] = df[c].map(keyfy)
    df["_id"] = df["_Main Tourist Attraction_key"] + "|" + df["_City_key"] + "|" + df["_State_key"]
    df["_img_base"] = (df["Main Tourist Attraction"] + "_" + df["City"] + "_" + df["State"]).map(clean_text)
    return df

# ----------------------------- Share / QR -----------------------------
PRIVATE_HOST_RE = re.compile(
    r"^(?:http://localhost|https?://(?:127\.0\.0\.1|0\.0\.0\.0|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[0-1])\.\d+\.\d+))", re.I)
def _normalize_base_url(s: str) -> str:
    s = (s or "").strip()
    if s and not s.startswith(("http://","https://")): s = "https://" + s
    return s.rstrip("/")
def _public_default() -> str:
    val = ""
    try: val = st.secrets.get("APP_BASE", "")
    except Exception: pass
    if not val: val = os.environ.get("APP_BASE", "")
    if not val: val = "https://finalprojecttravelindia-zaduhq35p5izncxxcpiact.streamlit.app"
    return _normalize_base_url(val)
def _sanitize_base(s: str, fallback_public: str) -> str:
    s = _normalize_base_url(s)
    if (not s) or PRIVATE_HOST_RE.match(s): return fallback_public
    return s
def render_share_block():
    public_default = _public_default()
    if "app_base" not in st.session_state: st.session_state.app_base = public_default
    with st.expander("🔗 Share link / QR", expanded=True):
        st.session_state.app_base = st.text_input("Your app URL (public or LAN)",
                                                  value=st.session_state.app_base)
        if st.button("Reset to public"): st.session_state.app_base = public_default
    base   = _sanitize_base(st.session_state.app_base, public_default)
    game_url = f"{base}/?page=Play+Quiz"
    colA, colB = st.columns([1,2])
    with colA:
        try:
            import qrcode
            img = qrcode.make(game_url)
            buf = BytesIO(); img.save(buf, format="PNG")
            st.image(buf.getvalue(), caption="Scan to play", use_container_width=True)
        except Exception:
            qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=" + urllib.parse.quote(game_url)
            st.markdown(f'<img alt="QR" src="{qr_url}" style="max-width:100%;border-radius:8px;border:1px solid #eee;">', unsafe_allow_html=True)
            st.caption("Using fallback QR")
    with colB:
        st.text_input("", value=game_url, label_visibility="collapsed")
        st.link_button("Open quiz", game_url, use_container_width=True)

def format_fee_inr_usd(fee_inr, inr_per_usd: float, show_usd: bool) -> str:
    if pd.isna(fee_inr) or fee_inr <= 0: return "—"
    fee_int = int(fee_inr)
    if show_usd and inr_per_usd and inr_per_usd > 0:
        usd = fee_int / float(inr_per_usd)
        return f"{fee_int:,} INR (~${usd:,.2f})"
    return f"{fee_int:,} INR"

# ----------------------------- Cards & Detail -----------------------------
def show_card(row: pd.Series, key_suffix: str, inr_per_usd: float, show_usd: bool):
    st.markdown('<div class="card">', unsafe_allow_html=True)

    img_src = resolve_image(
        row.get("Attraction Image (src)"),
        subdir="attractions",
        attraction=row.get("Main Tourist Attraction",""),
        city=row.get("City",""),
        state=row.get("State",""),
        local_base=row.get("_img_base",""),
        overrides={
            "attraction_image_override_url": row.get("attraction_image_override_url",""),
            "dish_image_override_url": row.get("dish_image_override_url",""),
        },
    )
    if img_src:
        safe_image(img_src, use_container_width=True)

    st.markdown('<div class="card-body">', unsafe_allow_html=True)
    st.markdown(f"<h4>{row['Main Tourist Attraction']}</h4>", unsafe_allow_html=True)
    st.markdown(f"<div class='kv'><b>Location:</b> {row['City']} • {row['State']} • {row.get('Region','')}</div>", unsafe_allow_html=True)

    rat = row.get("Google Review Rating", np.nan)
    reviews_n = row.get("Number of Google Reviews", np.nan)
    fee_txt = format_fee_inr_usd(row.get("Entrance Fee (INR)", np.nan), inr_per_usd, show_usd)

    rating_txt = "—" if pd.isna(rat) else f"{float(rat):.2f}"
    reviews_txt = "" if pd.isna(reviews_n) else f" &nbsp;&nbsp; 📣 <b>Google reviews:</b> {int(reviews_n):,}"
    st.markdown(f"<div class='kv'>⭐ <b>Rating:</b> {rating_txt}{reviews_txt}  &nbsp;&nbsp; 💵 <b>Entrance Fee:</b> {fee_txt}</div>", unsafe_allow_html=True)

    dish = row.get("Dish Name","")
    if isinstance(dish,str) and dish:
        veg = row.get("Veg or Non Veg","Veg"); badge = "veg" if veg=="Veg" else "nonveg"
        extra = " • ".join([x for x in [row.get("Type of Dish",""), row.get("Course","")] if x])
        st.markdown(f"<div class='kv'><b>Try this local dish:</b> {dish} <span class='tag {badge}'>{veg}</span>{' • '+extra if extra else ''}</div>", unsafe_allow_html=True)

        dimg = resolve_image(
            row.get("Dish Image (src)"),
            subdir="dishes",
            dish=row.get("Dish Name",""),
            attraction=row.get("Main Tourist Attraction",""),
            city=row.get("City",""),
            state=row.get("State",""),
            local_base=(row.get("_img_base","") + "_dish"),
            overrides={
                "attraction_image_override_url": row.get("attraction_image_override_url",""),
                "dish_image_override_url": row.get("dish_image_override_url",""),
            },
        )
        if dimg:
            safe_image(dimg, use_container_width=True, caption=f"Dish: {dish}")

    if st.button("🔎 View details", key=f"view_{key_suffix}", use_container_width=True):
        st.session_state.selected_id = row["_id"]
        st.query_params.update({"id": row["_id"]})
        st.rerun()
    st.markdown('</div></div>', unsafe_allow_html=True)

def show_detail(row: pd.Series, inr_per_usd: float, show_usd: bool):
    st.markdown("<div class='detail'>", unsafe_allow_html=True)

    img_src = resolve_image(
        row.get("Attraction Image (src)"),
        subdir="attractions",
        attraction=row.get("Main Tourist Attraction",""),
        city=row.get("City",""),
        state=row.get("State",""),
        local_base=row.get("_img_base",""),
        overrides={
            "attraction_image_override_url": row.get("attraction_image_override_url",""),
            "dish_image_override_url": row.get("dish_image_override_url",""),
        },
    )
    if img_src:
        safe_image(img_src, use_container_width=True)

    st.markdown(f"<h2>{row['Main Tourist Attraction']}</h2>", unsafe_allow_html=True)
    st.caption(f"{row['City']} • {row['State']} • {row.get('Region','')}")

    rating = row.get("Google Review Rating", np.nan)
    st.metric("⭐ Rating", "—" if pd.isna(rating) else f"{float(rating):.2f}")
    reviews_n = row.get("Number of Google Reviews", np.nan)
    if not pd.isna(reviews_n):
        st.caption(f"📣 Google reviews: {int(reviews_n):,}")

    fee_txt = format_fee_inr_usd(row.get("Entrance Fee (INR)", np.nan), inr_per_usd, show_usd)
    st.markdown(f"**💵 Entrance Fee:** {fee_txt}")

    ap = row.get("Nearest Airport","")
    if isinstance(ap,str) and ap:
        st.markdown(f"✈️ **Nearest Airport:** {ap}")

    info = []
    typ = row.get("Type of Attractions","")
    bt  = row.get("Best Time (Months)", row.get("Best Time to visit",""))
    dslr = row.get("DSLR Allowed (std)", row.get("DSLR Allowed",""))
    if typ:  info.append(f"**Type:** {typ}")
    if bt:   info.append(f"**Best Time:** {bt}")
    if dslr: info.append(f"**DSLR Allowed:** {dslr}")
    if info: st.write(" • ".join(info))

    dish = row.get("Dish Name","")
    if isinstance(dish,str) and dish:
        veg = row.get("Veg or Non Veg","Veg"); badge = "veg" if veg=="Veg" else "nonveg"
        extras = " • ".join([x for x in [row.get("Type of Dish",""), row.get("Course","")] if x])
        st.markdown(f"**Local dish to try:** {dish}  <span class='tag {badge}'>{veg}</span>  {('• '+extras) if extras else ''}",
                    unsafe_allow_html=True)

        dimg = resolve_image(
            row.get("Dish Image (src)"),
            subdir="dishes",
            dish=row.get("Dish Name",""),
            attraction=row.get("Main Tourist Attraction",""),
            city=row.get("City",""),
            state=row.get("State",""),
            local_base=(row.get("_img_base","") + "_dish"),
            overrides={
                "attraction_image_override_url": row.get("attraction_image_override_url",""),
                "dish_image_override_url": row.get("dish_image_override_url",""),
            },
        )
        if dimg:
            safe_image(dimg, use_container_width=True, caption=f"{dish}")
    else:
        st.markdown("_No dish suggestion found._")

    if st.button("← Back to results", use_container_width=True, key="back_results"):
        st.session_state.back_to_results = True

    st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------- Results CSV -----------------------------
RESULTS_CSV = "quiz_results.csv"
def append_result(rowdict: dict):
    rowdict = {k: clean_text(v) if isinstance(v,str) else v for k,v in rowdict.items()}
    if os.path.exists(RESULTS_CSV):
        df = pd.read_csv(RESULTS_CSV)
        df = pd.concat([df, pd.DataFrame([rowdict])], ignore_index=True)
    else:
        df = pd.DataFrame([rowdict])
    df.to_csv(RESULTS_CSV, index=False)

# ----------------------------- Load data -----------------------------
DF = load_csv(CSV_PATH)
if DF is None: st.stop()
DF = normalize_df(DF)

# ----------------------------- Routing -----------------------------
page = st.query_params.get("page")
if isinstance(page, list): page = page[0]
page = page or "Home"

with st.sidebar:
    st.header("Navigate")
    pages = ["Home","Explore","Play Quiz","Results","Feedback"]
    page = st.radio("Go to", pages, index=pages.index(page) if page in pages else 0)
    st.query_params.update({"page": page})

# ----------------------------- Pages -----------------------------
if page == "Home":
    hero_file = next((f for f in ["ind.gif","hero.gif","ind.jpg","hero.jpg"] if os.path.exists(f)), None)
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    col1, col2 = st.columns([1,1])  # larger visual area
    with col1:
        if hero_file:
            safe_image(hero_file, use_container_width=True)
    with col2:
        st.markdown("### Kaleidoscope India ", unsafe_allow_html=True)
        st.markdown("#### • Wander & Wonder", unsafe_allow_html=True)
        st.write("Discover iconic landmarks and a local dish to try nearby. Start with filters on the Explore page.")
        st.markdown('<span class="badge">Photos</span> <span class="badge">Local dishes</span> <span class="badge">Quick filters</span>', unsafe_allow_html=True)
        if st.button("Start Exploring →", type="primary"):
            st.query_params.update({"page": "Explore"})
            st.session_state.filters_submitted = False
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Explore":
    # callbacks to keep pickers in sync
    def _on_region_change():
        st.session_state.sel_states = []
        st.session_state.sel_cities = []
    def _on_states_change():
        st.session_state.sel_cities = []

    # defaults in session_state
    st.session_state.setdefault("filters_submitted", False)
    st.session_state.setdefault("sel_states", [])
    st.session_state.setdefault("sel_cities", [])
    st.session_state.setdefault("region", "All")
    st.session_state.setdefault("auto_show", False)

    st.markdown("### Find your vibe")
    st.caption("Pick filters, then press **Show attractions**. (State and City update instantly by Region/State.)")

    left, mid, right = st.columns([1,2,1])

    with left:
        st.markdown('<div class="sticky">', unsafe_allow_html=True)
        india_img = find_named_image("india")
        if india_img:
            safe_image(india_img, use_container_width=True)
            st.caption("Map of India — quick orientation while you filter")
        else:
            st.info("Add a map named `india.(jpg|png|webp|gif)` in app root, /images or /assets.")
        st.markdown('</div>', unsafe_allow_html=True)

    with mid:
        st.markdown('<div class="filters">', unsafe_allow_html=True)

        # (a) Region
        regions = ["All"] + sorted(DF["Region"].dropna().unique().tolist())
        region = st.radio("Region", regions,
                          index=regions.index(st.session_state.region) if st.session_state.region in regions else 0,
                          horizontal=True, key="region", on_change=_on_region_change)

        # (b) States
        df_r = DF if region == "All" else DF[DF["Region"] == region]
        state_opts = sorted(df_r["State"].dropna().unique().tolist())
        st.session_state.sel_states = [s for s in st.session_state.sel_states if s in state_opts]
        st.multiselect("State(s)", state_opts, key="sel_states", on_change=_on_states_change,
                       placeholder="Start typing a state…")

        # (c) Cities
        df_s = df_r if not st.session_state.sel_states else df_r[df_r["State"].isin(st.session_state.sel_states)]
        city_opts = sorted(df_s["City"].dropna().unique().tolist())
        st.session_state.sel_cities = [c for c in st.session_state.sel_cities if c in city_opts]
        st.multiselect("City/Cities", city_opts, key="sel_cities", placeholder="(optional) narrow to cities")

        # (d) Type of attraction (moved below City)
        type_opts = sorted([x for x in DF.get("Type of Attractions", pd.Series()).dropna().unique().tolist()])
        selected_types = st.multiselect("Type of attraction", type_opts, placeholder="e.g., Temple, Beach, Fort")

        # (e) Keyword
        q = st.text_input("Search attractions (keyword)", "")

        # Currency options
        st.session_state.setdefault("inr_per_usd", 83.0)
        st.session_state.setdefault("show_usd", True)
        with st.expander("Currency", expanded=False):
            st.session_state.inr_per_usd = st.number_input("INR per USD", min_value=1.0, max_value=1000.0,
                                                           value=float(st.session_state.inr_per_usd), step=0.5)
            st.session_state.show_usd = st.checkbox("Show USD equivalent", value=st.session_state.show_usd)

        only_with_dish = st.checkbox("Only show entries with a dish suggestion", value=False)

        colA, colB = st.columns([1,1])
        with colA:
            if st.button("Show attractions", type="primary", use_container_width=True):
                st.session_state.filters_submitted = True
        with colB:
            st.session_state.auto_show = st.toggle("Auto show as I filter", value=st.session_state.auto_show)

        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.auto_show:
        st.session_state.filters_submitted = True

    if not st.session_state.filters_submitted and not st.session_state.auto_show:
        st.info("Pick filters above and press **Show attractions**.")
    else:
        df = DF.copy()

        # Apply filters
        if region != "All":
            df = df[df["Region"] == region]
        if st.session_state.sel_states:
            df = df[df["State"].isin(st.session_state.sel_states)]
        if st.session_state.sel_cities:
            df = df[df["City"].isin(st.session_state.sel_cities)]
        if selected_types:
            pat = "|".join([re.escape(t.casefold()) for t in selected_types])
            df = df[df["Type of Attractions"].str.casefold().str.contains(pat, na=False)]
        if q.strip():
            df = df[df["Main Tourist Attraction"].str.casefold().str.contains(q.strip().casefold())]
        if only_with_dish and "Dish Name" in df.columns:
            df = df[df["Dish Name"].notna() & (df["Dish Name"].str.len() > 0)]

        if len(df) == 0:
            st.warning("No results for these filters. Try widening your search.")
        else:
            sort_cols = ["Google Review Rating"] + (["Number of Google Reviews"] if "Number of Google Reviews" in df.columns else [])
            df_show = df.sort_values(sort_cols, ascending=False, na_position="last").reset_index(drop=True)

            raw_id = st.query_params.get("id")
            if isinstance(raw_id, list): raw_id = raw_id[0]
            if "selected_id" not in st.session_state:
                st.session_state.selected_id = raw_id
            elif raw_id and st.session_state.selected_id != raw_id:
                st.session_state.selected_id = raw_id

            if st.session_state.selected_id:
                row = df_show.loc[df_show["_id"] == st.session_state.selected_id]
                if len(row) == 0:
                    row = DF.loc[DF["_id"] == st.session_state.selected_id]
                if len(row):
                    show_detail(row.iloc[0], st.session_state.inr_per_usd, st.session_state.show_usd)

                    if st.session_state.get("back_to_results"):
                        st.session_state.back_to_results = False
                        st.session_state.selected_id = None
                        try:
                            st.query_params.update({"page": "Explore", "id": ""})
                        except Exception:
                            pass
                        st.rerun()
                else:
                    st.info("That attraction isn’t in the current filter. Clear filters or go back.")
            else:
                st.markdown("### Results")
                cols = st.columns(3)
                for i, row in df_show.head(18).iterrows():
                    with cols[i % 3]:
                        show_card(row, key_suffix=f"{i}",
                                  inr_per_usd=st.session_state.inr_per_usd,
                                  show_usd=st.session_state.show_usd)

elif page == "Play Quiz":
    render_share_block()
    st.markdown("## 🎮 India Mini-Quiz (1.5 minutes)")
    st.write("Enter your name & email, then answer **8 easy questions**. New to India? Guess! 😊")

    # Correct answers (for immediate feedback)
    ANSWERS = {
        "q1": "New Delhi",
        "q2": "Spicy",
        "q3": "Holi",
        "q4": "With Bread (like naan or roti)",
        "q5": "Himachal Pradesh",
        "q6": "Rupee",
        "q7": "Sari",
        "q8": "Agra",
    }

    with st.form("quiz"):
        name  = st.text_input("Your name *", "")
        email = st.text_input("Your email *", "")
        q1 = st.radio("What is the capital city of India?", ["Mumbai","New Delhi","Kolkata","Bengaluru"], index=None)
        q2 = st.radio("🥘👨‍🍳🌶️🥵 What word best describes Indian food?", ["Spicy","Cold","Sweet","Boring"], index=None)
        q3 = st.radio("🌈🎨 Which Indian festival is known as the Festival of Colors?", ["Diwali","Baisakhi","Holi","Onam"], index=None)
        q4 = st.radio("🍞 + 🍛 = ❓What is a popular way of eating Indian curry?", ["With Chopsticks","With Bread (like naan or roti)","With a straw","In a taco shell"], index=None)
        q5 = st.radio("🚩🌄🧗‍♂️Which region in India is famous for the Himalayas?", ["Kerala","Goa","Gujarat","Himachal Pradesh"], index=None)
        q6 = st.radio("💵💰🪙Which of these is the Indian currency?", ["Yen","Peso","Dirham","Rupee"], index=None)
        q7 = st.radio("🥻🧵🌺 What is a traditional Indian dress for women called?", ["Kimono","Hanbok","Sari","Poncho"], index=None)
        q8 = st.radio("🏰 Which city is home to the famous Taj Mahal?", ["Agra","Delhi","Jaipur","Goa"], index=None)
        submitted = st.form_submit_button("Submit")

    if submitted:
        if not name.strip() or not email.strip():
            st.error("Please fill your name and email.")
        else:
            selections = {"q1": q1, "q2": q2, "q3": q3, "q4": q4, "q5": q5, "q6": q6, "q7": q7, "q8": q8}
            correct = sum(int(selections[k] == v) for k, v in ANSWERS.items())
            append_result({"name": name, "email": email, "score": int(correct), **selections})

            st.success(f"🎉 Thanks for playing, {name}! You scored **{correct}/8**.")
            st.caption("See which ones you got right (✅) or wrong (❌).")

            qtexts = {
                "q1": "Capital city of India",
                "q2": "What word best describes Indian food?",
                "q3": "Festival of Colors",
                "q4": "Popular way to eat curry",
                "q5": "Region famous for the Himalayas",
                "q6": "Indian currency",
                "q7": "Traditional dress for women",
                "q8": "City of the Taj Mahal",
            }

            for key in ["q1","q2","q3","q4","q5","q6","q7","q8"]:
                sel = selections.get(key)
                ans = ANSWERS[key]
                ok = (sel == ans)
                icon = "✅" if ok else "❌"
                klass = "qok" if ok else "qbad"
                st.markdown(
                    f"<div class='qrow {klass}'><b>{icon} {qtexts[key]}:</b><br>"
                    f"Your answer: <i>{sel if sel is not None else '—'}</i><br>"
                    f"Correct answer: <b>{ans}</b></div>",
                    unsafe_allow_html=True
                )

            st.info("You can view the global scoreboard on the **Results** page.")

elif page == "Results":
    st.markdown("## 🏆 Quiz Results")
    if os.path.exists("quiz_results.csv"):
        df = pd.read_csv("quiz_results.csv")
        if len(df):
            st.dataframe(df.sort_values("score", ascending=False), use_container_width=True, hide_index=True)
            st.download_button("Download results CSV", df.to_csv(index=False).encode("utf-8"),
                               file_name="quiz_results.csv", mime="text/csv")
        else:
            st.info("No results yet.")
    else:
        st.info("No results yet.")

elif page == "Feedback":
    st.markdown("## 💌 Feedback & Queries")
    st.write(
        "Have a suggestion, found a bug, or want a new feature? "
        "Send me a quick message below — it will open your email app with the details pre-filled."
    )

    with st.form("feedback_form"):
        your_name  = st.text_input("Your name", "")
        your_email = st.text_input("Your email (so I can reply)", "")
        subject    = st.text_input("Subject", "Feedback for Kaleidoscope India")
        message    = st.text_area("Your message", height=160, placeholder="Type your idea, issue, or request…")
        send = st.form_submit_button("Open email draft")

    if send:
        base_subject = subject.strip() or "Feedback for Kaleidoscope India"
        intro = f"Name: {your_name}\nEmail: {your_email}\n\n" if (your_name or your_email) else ""
        body = intro + (message or "")
        mailto = (
            "mailto:"
            + urllib.parse.quote(CONTACT_EMAIL)
            + "?subject="
            + urllib.parse.quote(base_subject)
            + "&body="
            + urllib.parse.quote(body)
        )
        st.link_button("✉️ Click to send via your email app", mailto, use_container_width=True)
        st.success("If nothing opened, your browser may be blocking pop-ups. Try clicking the button again or copy the email address below.")

    st.divider()
    col1, col2 = st.columns([2,1])
    with col1:
        st.markdown(f"**Email:** [{CONTACT_EMAIL}](mailto:{CONTACT_EMAIL})")
        st.markdown(f"**Instagram:** [{INSTAGRAM_HANDLE}]({INSTAGRAM_URL}) — follow for updates, reels & new features!")
    with col2:
        st.link_button("Open Instagram", INSTAGRAM_URL, use_container_width=True)
