
# Swing Sniper India V2

A Streamlit dashboard for 15–20 trading-day NSE swing scanning.

## V2 features
- TOP 5 "SNIPER" dashboard
- Market regime: Risk-On / Mixed / Risk-Off
- EMA trend stack
- RSI / MACD / ADX
- 20D + 55D breakout proximity
- Volume expansion
- Tight-base / consolidation detection
- Relative strength vs Nifty
- Extended-move penalty
- Entry / stop / T1 / T2
- Capital-aware position sizing
- Account risk control
- Full ranked scanner

## Run
pip install -r requirements.txt
streamlit run app.py

## Important
The prototype uses Yahoo Finance via yfinance. It is not an exchange-certified real-time feed. For real trading, replace the data layer with a broker/exchange API and add news, results, corporate-action and liquidity filters.

## Recommended V3
- Live broker WebSocket
- Sector rotation engine
- Delivery percentage
- VWAP / volume profile
- Gap and opening-range confirmation
- Earnings/event blackout
- Backtesting with costs/slippage
- Alert engine
- Trade journal
