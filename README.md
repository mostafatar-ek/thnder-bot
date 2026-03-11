# 📈 Thndr EGX Deal-Finder Bot

A Python bot that scans the **Egyptian Exchange (EGX)** for the best stock deals using technical analysis and sends you **instant Telegram alerts** when it finds a great opportunity.

Built for use with the **Thndr** trading app.

---

## 🚀 How It Works

The bot runs 24/7 on Railway (cloud), scans 20 EGX stocks every 30 minutes, and scores each stock from 0–100 based on 6 technical indicators.

When a stock scores **75+**, you get a Telegram notification on your phone.

---

## 📊 Scoring System

Each stock is analyzed using **6 signals**. Each signal votes "bullish" (buy) or not, and they are combined into a single score:

| Signal | What It Checks | Bullish When |
|---|---|---|
| **RSI** (Relative Strength Index) | Is the stock oversold or overbought? | RSI ≤ 30 → stock is cheap/oversold |
| **MA Crossover** | Short-term trend vs long-term trend | 10-day MA crosses above 50-day MA (golden cross) |
| **MACD** | Momentum direction | MACD line crosses above signal line |
| **Volume Spike** | Unusual trading activity | Volume is 1.5x+ above 20-day average |
| **Price Dip** | Drop from recent high | Price dropped 5%+ from 20-day high |
| **Bollinger Bands** | Price at extremes | Price touches lower band → oversold bounce |

---

## 🟢 When to BUY

| Score | Recommendation | Action |
|---|---|---|
| **85–100** | 🔥 STRONG BUY | Multiple signals agree. **Best opportunity** — act quickly after a quick sanity check. |
| **75–84** | ⭐ BUY | Good technical setup. **Consider buying** — do a quick 2-minute check on any company news first. |

### ✅ Buy Checklist
1. Bot sends you a **BUY alert** (score ≥ 75)
2. Open **Thndr** and check the stock's chart — does the trend look right?
3. Quick Google: any recent **news** about the company? (earnings, lawsuits, etc.)
4. Check the **overall EGX market** — is it a green or red day?
5. If everything looks good → **place your buy order on Thndr**

### 🎯 Ideal Buy Setup (highest confidence)
- Score **85+**
- RSI below 30 (oversold)
- Golden cross (short MA just crossed above long MA)
- Volume spike (lots of interest)
- Price dipped from recent high

When 3+ of these fire together, it's the strongest signal.

---

## 🔴 When to SELL

The bot focuses on **buy signals**, but here's when you should consider selling:

### Take Profit (Good Exit)
| Condition | Action |
|---|---|
| Stock is up **10–15%** from your buy price | Consider taking profit on half your position |
| Stock is up **20%+** from your buy price | Strongly consider selling — lock in gains |
| RSI goes above **70** (overbought) | The stock is getting expensive — time to sell |
| Price touches **upper Bollinger Band** | Overbought — likely to pull back |

### Stop Loss (Cut Losses)
| Condition | Action |
|---|---|
| Stock drops **5–7%** below your buy price | **Sell immediately** — cut your losses |
| Stock drops **10%** below your buy price | **Absolute maximum loss** — exit now |
| Bad company news (scandal, lost contract, etc.) | Sell regardless of price — fundamentals changed |

### General Sell Rules
- **Never hold a losing position hoping it will recover** — if it drops 7%, get out
- **Don't get greedy** — if you're up 15-20%, take at least partial profit
- **If the bot stops alerting a stock** (score drops below 50), the momentum has faded — consider exiting

---

## 📋 Score Breakdown

| Score | Label | Meaning |
|---|---|---|
| **85–100** | 🔥 STRONG BUY | Multiple bullish signals firing — rare, high-confidence opportunity |
| **75–84** | ⭐ BUY | Good setup — worth buying with a quick check |
| **50–74** | 📊 HOLD / WATCH | Some positive signs but not enough — watch and wait |
| **30–49** | ⚠️ WEAK | More bearish than bullish — stay away |
| **0–29** | 🚫 AVOID | Bearish signals dominating — do not buy |

---

## 📱 Stocks Monitored

| Ticker | Company |
|---|---|
| COMI.CA | Commercial International Bank (CIB) |
| HRHO.CA | Hermes Holding |
| TMGH.CA | Talaat Moustafa Group |
| SWDY.CA | Elsewedy Electric |
| EAST.CA | Eastern Company |
| EFIH.CA | EFG Hermes |
| ORWE.CA | Oriental Weavers |
| ABUK.CA | Abu Qir Fertilizers |
| ESRS.CA | Ezz Steel |
| PHDC.CA | Palm Hills Development |
| EKHO.CA | El Khair for Industry |
| AMOC.CA | Alexandria Mineral Oils |
| JUFO.CA | Juhayna Food Industries |
| SKPC.CA | Sidi Kerir Petrochemicals |
| ETEL.CA | Telecom Egypt |
| CLHO.CA | Cleopatra Hospital |
| FWRY.CA | Fawry for Banking Technology |
| HELI.CA | Heliopolis Housing |

---

## ⚙️ Setup

### 1. Create a Telegram Bot
1. Open Telegram → search **@BotFather** → send `/newbot`
2. Copy the **bot token**

### 2. Get Your Chat ID
1. Send a message to your new bot
2. Search **@userinfobot** → send `/start`
3. Copy your **ID number**

### 3. Deploy on Railway
1. Fork/push this repo to GitHub
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
3. Add these environment variables:

```
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_id
SCAN_INTERVAL_MINUTES=30
MIN_DEAL_SCORE=75
```

4. Deploy — bot runs 24/7 automatically

---

## 🧪 Test Locally

```bash
pip install -r requirements.txt
python bot.py              # Run one scan
python bot.py --loop       # Run continuously
python bot.py --test       # Send test Telegram notification
```

---

## ⚠️ Disclaimer

This bot provides **automated technical analysis only — not financial advice**.

- Always do your own research before buying or selling
- Past technical patterns don't guarantee future results
- Never invest money you can't afford to lose
- The bot can help you **spot opportunities faster**, but the final decision is always yours

---

## 📝 Quick Strategy Summary

```
BUY  → Bot alerts you (score ≥ 75) + your quick research looks good
HOLD → Keep if still trending up and score stays above 50
SELL → Stock up 15-20% (take profit) OR down 7% (stop loss) OR RSI > 70
```

**Golden Rule: Cut losers fast, let winners run (but not forever).**
