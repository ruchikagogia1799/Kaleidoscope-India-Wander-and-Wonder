# 🌏 Kaleidoscope India — Explore Page (Final Optimized + Polished UI)
import os, re, io, hashlib, requests
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------
st.set_page_config(page_title="🌏 Explore India • Kaleidoscope", layout="wide")

CSV_PATH = "combined_with_links2.csv"
USD_RATE = 0.012
CACHE_DIR = "img_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ---------------------------------------------------------------
# STYLE
# ---------------------------------------------------------------
st.markdown("""
<style>
:root{ --rounded:16px; }
.main .block-container{ padding-top:.8rem; padding-bottom:1.2rem; }

.card{
  border:1px solid #e6e6e6;border-radius:var(--rounded);background:#fff;
  box-shadow:0 3px 10px rgba(0,0,0,.05);overflow:hidden;margin-bottom:1.4rem;
  transition:transform .15s ease,box-shadow .15s ease;
}
.card:hover{transform:translateY(-4px);box-shadow:0 6px 18px rgba(0,0,0,.08);}
.card-body{padding:14px 16px;text-align:center;}
.card img{border-bottom:1px solid #eee;object-fit:cover;height:230px;width:100%;}

h4{margin:.3rem 0;color:#222;font-weight:600;}
.kv{color:#444;font-size:.9rem;margin-bottom:.3rem;}

.detail{border:1px solid #eee;background:#fff;border-radius:20px;
        padding:24px;box-shadow:0 6px 20px rgba(0,0,0,.08);}

button[kind="primary"], div[data-testid="stButton"] button {
  border-radius:10px !important;
  margin-top:6px !important;
  margin-bottom:8px !important;
  font-weight:500;
  transition:all .15s ease;
}
div[data-testid="stButton"] button:hover {
  box-shadow:0 0 8px rgba(0,123,255,.4);
  transform:translateY(-2px);
}
img[loading="lazy"] { transition:opacity .2s ease; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# IMAGE HELPERS
# ---------------------------------------------------------------
ID_RE = re.compile(r"(?:/d/|id=)([a-zA-Z0-9_-]+)")

def extract_file_id(url: str) -> str:
    if not isinstance(url, str) or "drive.google.com" not in url:
        return ""
    m = ID_RE.search(url)
    return m.group(1) if m else ""

def candidate_urls(file_id: str, size: int):
    return [
        f"https://drive.google.com/uc?export=view&id={file_id}",
        f"https://drive.google.com/thumbnail?id={file_id}&sz=w{size}",
    ]

@st.cache_resource
def get_http() -> requests.Session:
    s = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
    s.mount("https://", adapter)
    s.headers.update({"User-Agent": "Kaleidoscope/1.0"})
    return s

def cache_key(url: str, target_w: int, fmt: str) -> str:
    h = hashlib.sha1(f"{url}|{target_w}|{fmt}".encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{h}.{fmt.lower()}")

def fetch_and_process(url: str, target_w: int, fmt="WEBP", quality=75) -> bytes | None:
    """Fetch from Drive, resize, compress, cache to disk."""
    if not url: return None
    file_id = extract_file_id(url)
    if not file_id: return None

    ck = cache_key(url, target_w, fmt)
    if os.path.exists(ck):
        try:
            with open(ck, "rb") as f: return f.read()
        except Exception: pass

    sess = get_http()
    for u in candidate_urls(file_id, size=max(480, target_w)):
        try:
            r = sess.get(u, timeout=10)
            if r.status_code == 200 and "image" in r.headers.get("Content-Type",""):
                try:
                    img = Image.open(io.BytesIO(r.content)).convert("RGB")
                    img.thumbnail((target_w, target_w*0.75))
                    out = io.BytesIO()
                    img.save(out, format=fmt.upper(), quality=quality, method=6)
                    data = out.getvalue()
                except Exception:
                    data = r.content
                try:
                    with open(ck, "wb") as f: f.write(data)
                except Exception: pass
                return data
        except Exception:
            continue
    return None

@st.cache_data(show_spinner=False)
def get_image_bytes(url: str, target_w: int, fmt="WEBP", quality=75) -> bytes | None:
    return fetch_and_process(url, target_w=target_w, fmt=fmt, quality=quality)

def show_image(url: str, caption=None, target_w=400):
    """Render Drive image with lazy loading for speed."""
    placeholder = "https://upload.wikimedia.org/wikipedia/commons/6/65/No-Image-Placeholder.svg"
    file_id = extract_file_id(url)
    if not file_id:
        st.image(placeholder, width='stretch', caption=caption)
        return

    thumb_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w{target_w}"
    alt = caption or "Attraction image"
    st.markdown(
        f"<img src='{thumb_url}' loading='lazy' alt='{alt}' "
        f"style='width:100%;border-radius:12px;margin-bottom:8px;'>",
        unsafe_allow_html=True
    )

# ---------------------------------------------------------------
# LOAD & FILTER
# ---------------------------------------------------------------
@st.cache_data
def load_data():
    if not os.path.exists(CSV_PATH):
        st.error(f"CSV not found: {CSV_PATH}")
        st.stop()
    df = pd.read_csv(CSV_PATH).fillna("")
    df["_id"] = (df["Main Tourist Attraction"] + "|" + df["City"] + "|" + df["State"]).str.lower()
    return df

@st.cache_data
def filter_data(df, region, states, cities, q, only_dish):
    data = df.copy()
    if region != "All": data = data[data["Region"] == region]
    if states: data = data[data["State"].isin(states)]
    if cities: data = data[data["City"].isin(cities)]
    if q.strip(): data = data[data["Main Tourist Attraction"].str.contains(q, case=False)]
    if only_dish: data = data[data["Dish Name"].str.len() > 0]
    return data.reset_index(drop=True)

DF = load_data()

# ---------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------
st.session_state.setdefault("filters_submitted", False)
st.session_state.setdefault("region", "All")
st.session_state.setdefault("sel_states", [])
st.session_state.setdefault("sel_cities", [])
st.session_state.setdefault("selected_id", None)
st.session_state.setdefault("page_number", 1)

# ---------------------------------------------------------------
# FILTER PANEL
# ---------------------------------------------------------------
st.title("🌏 Explore India – Sights & Street Food")

with st.container():
    left, mid = st.columns([1, 2])
    with left: st.image("india.jpg", width='stretch')
    with mid:
        region_opts = ["All"] + sorted(DF["Region"].dropna().unique())
        region = st.radio("Region", region_opts, index=region_opts.index(st.session_state.region))
        df_r = DF if region == "All" else DF[DF["Region"] == region]
        state_opts = sorted(df_r["State"].dropna().unique())
        sel_states = st.multiselect("State(s)", state_opts, default=st.session_state.sel_states)
        df_s = df_r if not sel_states else df_r[df_r["State"].isin(sel_states)]
        city_opts = sorted(df_s["City"].dropna().unique())
        sel_cities = st.multiselect("City/Cities", city_opts, default=st.session_state.sel_cities)
        q = st.text_input("Keyword search", value="")
        only_dish = st.checkbox("Only show attractions with dish suggestion", value=False)
        if st.button("Show attractions", type="primary", width='stretch'):
            st.session_state.update({
                "filters_submitted": True,
                "region": region,
                "sel_states": sel_states,
                "sel_cities": sel_cities,
                "page_number": 1,
                "selected_id": None,
            })
            st.rerun()

# ---------------------------------------------------------------
# RESULTS
# ---------------------------------------------------------------
if not st.session_state.filters_submitted:
    st.info("Pick filters above and press **Show attractions**.")
else:
    with st.spinner("Loading images..."):
        df_show = filter_data(DF, region, sel_states, sel_cities, q, only_dish)

    if len(df_show) == 0:
        st.warning("No results found.")
    else:
        # DETAIL VIEW
        if st.session_state.selected_id:
            row = df_show[df_show["_id"] == st.session_state.selected_id].iloc[0]
            st.markdown("<div class='detail'>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1: show_image(row.get("Attraction_Link",""), row.get("Main Tourist Attraction",""), target_w=1024)
            with c2: show_image(row.get("Dish_Link",""), f"Dish: {row.get('Dish Name','')}", target_w=720)
            st.markdown(f"## {row['Main Tourist Attraction']}")
            st.caption(f"{row['City']} • {row['State']} • {row.get('Region','')}")
            fee_inr = float(row.get('Entrance Fee (INR)', 0) or 0)
            st.write(f"⭐ {row.get('Google Review Rating','—')} | 💵 ₹{fee_inr:.0f} (~${fee_inr*USD_RATE:.2f})")
            st.write(f"**Type:** {row.get('Type of Attractions','—')} | **🌅Best Time:** {row.get('Best Time to visit','—')}")
            st.write(f"**✈️Nearest Airport:** {row.get('Nearest Airport','—')} | **DSLR Allowed:** {row.get('DSLR Allowed','—')}")
            if row.get("Dish Name"):
                st.markdown("### 🍛 Local Dish")
                st.write(f"**{row['Dish Name']} ({row.get('Veg or Non Veg','')})** — {row.get('Type of Dish','')} • {row.get('Course','')}")
            if st.button("← Back to results", width='stretch'):
                st.session_state.selected_id = None
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # GRID VIEW
        else:
            PER_PAGE = 9
            total_pages = int(np.ceil(len(df_show) / PER_PAGE))
            start, end = (st.session_state.page_number - 1) * PER_PAGE, st.session_state.page_number * PER_PAGE
            df_page = df_show.iloc[start:end]

            # Prefetch thumbnails
            urls = list(df_page["Attraction_Link"].fillna("").values)
            with ThreadPoolExecutor(max_workers=8) as ex:
                futures = [ex.submit(get_image_bytes, u, 560, "WEBP", 70) for u in urls]
                for _ in as_completed(futures): pass

            cols = st.columns(3)
            for i, row in df_page.iterrows():
                with cols[i % 3]:
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    show_image(row.get("Attraction_Link",""), target_w=680)
                    st.markdown(f"<div class='card-body'><h4>{row['Main Tourist Attraction']}</h4>", unsafe_allow_html=True)
                    st.markdown(f"<div class='kv'>📍 {row['City']}, {row['State']}</div>", unsafe_allow_html=True)
                    fee_inr = float(row.get('Entrance Fee (INR)', 0) or 0)
                    st.markdown(f"<div class='kv'>⭐ {row.get('Google Review Rating','—')} • 💵 ₹{int(fee_inr):,} (~${fee_inr*USD_RATE:.2f})</div>", unsafe_allow_html=True)
                    if row.get("Dish_Link"):
                        show_image(row.get("Dish_Link",""), row.get("Dish Name",""), target_w=520)
                    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                    if st.button("🔍 View details", key=f"view_{i}", width='stretch'):
                        st.session_state.selected_id = row["_id"]
                        st.rerun()
                    st.markdown("</div></div>", unsafe_allow_html=True)

            # Pagination
            st.markdown("<br>", unsafe_allow_html=True)
            page_cols = st.columns(min(total_pages, 10))
            for i in range(1, total_pages + 1):
                if i <= 10:
                    with page_cols[(i - 1) % 10]:
                        if st.button(str(i), key=f"page_{i}", type=("primary" if i == st.session_state.page_number else "secondary")):
                            st.session_state.page_number = i
                            st.rerun()
