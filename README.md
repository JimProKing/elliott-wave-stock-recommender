# 🌸 Elliott Wave Stock Recommender

**Elliott Wave Theory-based scanner for high-volume Korean stocks with strong upward potential.**

A practical Python tool (CLI + beautiful calming web UI) that analyzes the top trading volume stocks using Elliott Wave-inspired heuristics, momentum, volume confirmation, and Fibonacci-style retracements.

> "Trade calmly." — Built with a soft, feminine, stress-relieving interface featuring cute dog & cat images to help you breathe while scanning the market.

---

## ✨ Features

- **Smart Elliott Wave Scoring**  
  Detects impulse structures, healthy corrections (Fib 38–62%), volume confirmation on impulse legs, EMA alignment, and RSI health zones. Ranks stocks by upward potential.

- **High-Liquidity Focus**  
  Automatically targets the top N stocks by trading value (거래대금) from KOSPI + KOSDAQ.

- **Powerful CLI**  
  Fast scanning with customizable parameters and CSV export + optional matplotlib charts.

- **Gorgeous Calming Web UI (Flask)**  
  - Soft pastel feminine design (lavender + blush pink)
  - Fully responsive (perfect on phone)
  - Live sortable & filterable results table
  - Beautiful score badges
  - On-demand or pre-generated Elliott charts in modal
  - **"Today's Healing"** section with cute, calming dog & cat photos + gentle encouraging messages
  - Designed to reduce trading stress

- **Zero hassle local setup** — just `python app.py`

---

## 📸 Web UI Highlights

- Feminine, cozy pastel theme (much gentler than typical trading tools)
- Cute pet images that appear while you set parameters (because trading can be mentally exhausting 💕)
- Clear, high-contrast data table with one-click sorting
- Instant chart viewing for top candidates

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/JimProKing/elliott-wave-stock-recommender.git
cd elliott-wave-stock-recommender
pip install -r requirements.txt
```

### 2. Run the Web App (Recommended)

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser.

### 3. Use the CLI

```bash
python elliott_wave_volume_scanner.py --top 80 --min-score 55 --plot
```

**Common options:**

| Option          | Default | Description                              |
|-----------------|---------|------------------------------------------|
| `--top`         | 100     | Number of highest volume stocks to scan  |
| `--min-score`   | 55      | Minimum Elliott Wave score (0–100)       |
| `--days`        | 550     | Historical data window (trading days)    |
| `--reversal`    | 0.032   | ZigZag reversal sensitivity              |
| `--plot`        | —       | Generate charts for top candidates       |
| `--output`      | csv     | Export results to CSV                    |

---

## 📊 How the Scoring Works

The tool approximates Elliott Wave principles with practical heuristics:

- Strong long-term trend (price > EMA200)
- Healthy EMA alignment (21 > 55 > 200)
- Recent swing structure showing Higher Highs / Higher Lows
- Shallow corrective retracements (ideally ~38–62% Fib zone)
- Rising volume on impulse moves
- RSI in the "room to run" zone (not extremely overbought)

Higher scores → stronger confluence for potential Wave 3 or early Wave 5 setups.

**Note:** This is a heuristic reference tool. Real wave counting is subjective.

---

## 🛡️ Disclaimer

This project is for **educational and personal research purposes only**.

- Elliott Wave Theory is interpretive.
- Past performance does not guarantee future results.
- The authors are not responsible for any financial losses.
- Always do your own research and manage risk responsibly.

---

## 🛠 Tech Stack

- **Python** + pandas, numpy, FinanceDataReader, matplotlib
- **Flask** for the beautiful web interface
- **Bootstrap 5** + custom soft pastel CSS
- Designed with mental well-being in mind (cute pets included 🐶🐱)

---

## 📁 Project Structure

```
.
├── app.py                          # Flask web server
├── elliott_wave_volume_scanner.py  # Core scanner + CLI
├── requirements.txt
├── README.md
├── templates/
│   └── index.html                  # Calming feminine web UI
└── static/
    └── css/
        └── main.css
```

---

## ❤️ Why the Soft Design?

Because trading can be stressful.  
The web interface was intentionally made gentle and feminine with calming colors and cute animal photos — so you can analyze without feeling overwhelmed.

Take a breath. You've got this. 🌸

---

## 📝 License

MIT — feel free to use and modify for personal use.

---

**Made with care for traders who need a little peace while hunting for Wave 3s.**

Enjoy responsibly! 🐾
