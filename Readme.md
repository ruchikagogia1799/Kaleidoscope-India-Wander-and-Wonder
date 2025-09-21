# Kaleidoscope India — *Wander & Wonder* 🌏✨

A Streamlit app to explore India’s iconic sights with quick facts, ⭐ ratings, entrance fees, and a **local dish to try** nearby. Filter by region/state/city, view rich cards & details, play a short quiz with instant feedback, and send suggestions via the built-in Feedback page.

**Live app:** https://finalprojecttravelindia-zaduhq35p5izncxxcpiact.streamlit.app

---

## Features

- **Explore browser**
  - Filters: Region → State(s) → City/Cities → *Type of attraction* (moved below City) + keyword search
  - Beautiful cards with cover photo, location, ⭐ Google rating, 📣 number of reviews, 💵 entrance fee
  - Local dish suggestion with Veg/Non-Veg tags, dish image, type & course
  - Detail view with extra info (nearest airport, best time, DSLR allowed)
- **Images that “just work”**
  - Reads images from local folders or URLs; safe loader auto-downscales huge files and skips corrupt ones
  - Supported by default: `.jpg .jpeg .png .webp .gif` (AVIF optional)
- **Mini-quiz (8 Qs)**
  - Instant score + per-question ✅/❌ feedback
  - Results saved to `quiz_results.csv` and visible on **Results** page
  - Share block with QR code (auto-generated)
- **Feedback page**
  - Mailto form opens a pre-filled email to your address
  - Instagram link for updates
- **Polish**
  - Half-page hero GIF/image on Home
  - USD equivalence toggle for fees
  - Robust CSV parsing (tolerant reader)

---

## Quickstart

### 1) Requirements
- Python 3.10+ (3.11/3.12 fine)
- Pip

### 2) Setup
```bash
git clone <your-repo-url>
cd Final_Project_Kaleidoscope_India

# (optional) create a virtualenv
python -m venv .venv
# Windows
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# install deps
pip install -r requirements.txt
# If you don't have a requirements.txt yet:
pip install streamlit pandas numpy pillow qrcode
# (optional, for AVIF)
pip install pillow-avif-plugin
