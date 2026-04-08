# 🚀 FTTH Expansion Intelligence Platform

## AI Swarm-Powered Infrastructure Investment Decision System

---

## ⚡ Quick Start

```powershell
# 1. Extract files to folder
# 2. Open PowerShell in folder
cd C:\ftth_demo

# 3. Create venv (optional but recommended)
python -m venv venv
.\venv\Scripts\Activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run app
streamlit run app.py
```

---

## 🤖 AI Swarm Voting System

Three AI agents with different investment strategies analyze each Gemeinde:

| Agent | Style | Focus |
|-------|-------|-------|
| 🛡️ **SENTINEL** | Conservative | Risk-averse, proven markets, low infrastructure cost |
| ⚡ **VANGUARD** | Aggressive | Growth-focused, first-mover advantage, large markets |
| ⚖️ **ORACLE** | Balanced | ROI-optimized, unit economics, payback efficiency |

### Voting Outcomes
- 🟢 **STRONG_INVEST** — Deploy immediately
- 🟡 **INVEST** — Include in Phase 1
- 🟠 **HOLD** — Monitor and reassess
- 🔴 **DELAY** — Wait for better conditions
- ⛔ **AVOID** — Do not allocate capital

---

## 📁 Project Structure

```
ftth_demo/
├── app.py              # Main Streamlit dashboard
├── db_layer.py         # SQLite database + realistic Bavaria data
├── ai_swarm.py         # 3-agent voting system
├── calculations.py     # Financial modeling (NPV, IRR, CAPEX)
├── geo_utils.py        # Geocoding utilities
├── requirements.txt    # Dependencies
└── data/
    └── ftth_demo.db    # SQLite database (auto-created)
```

---

## 🗺️ Data Coverage

**30 real Bavarian Gemeinden** with simulated FTTH metrics:
- Landkreis Landsberg am Lech (primary)
- Landkreis Augsburg
- Landkreis Weilheim-Schongau
- Landkreis Fürstenfeldbruck
- Landkreis Starnberg

---

## 💡 Demo Tips

1. **AI Swarm Tab** — Show the 3-agent voting system, explain different strategies
2. **Filter by Landkreis** — Sidebar dropdown to focus on specific regions
3. **3D View** — Impressive visual, columns = homes, color = adoption
4. **Executive Report** — One-click summary with AI recommendations

---

## 🔧 Customization

### Add More Gemeinden
Edit `BAVARIA_GEMEINDEN` list in `db_layer.py`:
```python
{"name": "Your City", "lat": 48.xxx, "lon": 10.xxx, ...}
```

### Adjust AI Thresholds
Modify scoring weights in `ai_swarm.py` for each agent class.

---

## 📊 Tech Stack

- **Frontend:** Streamlit
- **Database:** SQLite (zero config)
- **Visualization:** Plotly + PyDeck (3D)
- **AI:** Pure Python rule-based agents (no LLM needed)

---

**Built for WBS Coding School Capstone**  
*Mark-Sebastian Bistrean-Chirodea*
