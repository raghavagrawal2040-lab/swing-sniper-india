
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="Swing Sniper India V2", page_icon="🎯", layout="wide")

# ---------- Indicators ----------
def ema(s,n): return s.ewm(span=n, adjust=False).mean()

def rsi(s,n=14):
    d=s.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    rs=up.ewm(alpha=1/n,adjust=False).mean()/dn.ewm(alpha=1/n,adjust=False).mean().replace(0,np.nan)
    return 100-100/(1+rs)

def atr(df,n=14):
    h,l,c=df.High,df.Low,df.Close
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False).mean()

def macd(s):
    m=ema(s,12)-ema(s,26); sig=ema(m,9)
    return m,sig,m-sig

def adx(df,n=14):
    h,l,c=df.High,df.Low,df.Close
    up=h.diff(); dn=-l.diff()
    pdm=pd.Series(np.where((up>dn)&(up>0),up,0),index=df.index)
    mdm=pd.Series(np.where((dn>up)&(dn>0),dn,0),index=df.index)
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    av=tr.ewm(alpha=1/n,adjust=False).mean()
    pdi=100*pdm.ewm(alpha=1/n,adjust=False).mean()/av.replace(0,np.nan)
    mdi=100*mdm.ewm(alpha=1/n,adjust=False).mean()/av.replace(0,np.nan)
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    return dx.ewm(alpha=1/n,adjust=False).mean()

def flatten(df):
    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df.dropna(how="all")

# ---------- Universe ----------
UNIVERSE = sorted(set("""
RELIANCE HDFCBANK ICICIBANK SBIN AXISBANK KOTAKBANK LT BHARTIARTL INFY TCS HCLTECH
WIPRO TECHM SUNPHARMA CIPLA LUPIN MANKINDPHARMA DRREDDY DIVISLAB TORNTPHARM MARUTI
M&M TATAMOTORS EICHERMOT HEROMOTOCO BAJAJ-AUTO TRENT TITAN KALYANKJIL INDHOTEL BEL
HAL BHEL CGPOWER POLYCAB DIXON KPITTECH PERSISTENT COFORGE LTIM TATAELXSI SIEMENS ABB
APLAPOLLO JINDALSTEL JSWSTEEL TATASTEEL HINDALCO VEDL ADANIENT ADANIPORTS WAAREEENER
SOLARINDS MAZDOCK COCHINSHIP RVNL IRFC HUDCO NBCC DLF OBEROIRLTY PRESTIGE LODHA
MAXHEALTH APOLLOHOSP FORTIS ZYDUSLIFE AUROPHARMA BIOCON ALKEM JUBLFOOD VBL DABUR
BRITANNIA PIDILITIND ASIANPAINT BERGEPAINT SRF DEEPAKFERT AARTIIND MPHASIS LTTS OFSS
CYIENT BOSCHLTD ESCORTS ASHOKLEY BHARATFORG ECLERX GLANDPHARMA GLENMARK
TORRENTPOWER CGPOWER ENGINERSIN MAHSEAMLES JINDALSAW GRAPHITE INDIA TATACHEM
COROMANDEL UPL PIIND LAURUSLABS APLLTD PPLPHARMA CROMPTON HAVELLS VOLTAS
WHIRLPOOL BLUESTARCO ASTRAL SUPREMEIND KEI KAYNES NETWEB SYRMA
""".split()))

@st.cache_data(ttl=600, show_spinner=False)
def get(sym,period="1y"):
    return flatten(yf.download(sym+".NS",period=period,interval="1d",auto_adjust=False,progress=False))

@st.cache_data(ttl=600, show_spinner=False)
def nifty():
    return flatten(yf.download("^NSEI",period="1y",interval="1d",auto_adjust=False,progress=False))

# ---------- Market regime ----------
def market_regime(n):
    if len(n)<220: return ("UNKNOWN",0,"Insufficient benchmark history")
    c=n.Close; e20=ema(c,20); e50=ema(c,50); e200=ema(c,200); r=rsi(c)
    score=0
    if c.iloc[-1]>e20.iloc[-1]: score+=1
    if c.iloc[-1]>e50.iloc[-1]: score+=1
    if c.iloc[-1]>e200.iloc[-1]: score+=1
    if e20.iloc[-1]>e50.iloc[-1]: score+=1
    if r.iloc[-1]>50: score+=1
    if score>=4: return ("RISK-ON",score,"Broad trend supports long swing setups.")
    if score<=1: return ("RISK-OFF",score,"Broad trend is weak; reduce exposure and wait for confirmation.")
    return ("MIXED",score,"Selective longs only; require stronger individual setups.")

# ---------- Scoring ----------
def scan(df,bm):
    if len(df)<220: return None
    c=df.Close; v=df.Volume
    e20,e50,e200=ema(c,20),ema(c,50),ema(c,200)
    rr=rsi(c); aa=atr(df); mm,ms,mh=macd(c); ax=adx(df)
    av=v.rolling(20).mean(); h20=c.rolling(20).max().shift(1); h55=c.rolling(55).max().shift(1)
    # consolidation: narrow recent range relative to ATR
    recent_range=(c.rolling(10).max()-c.rolling(10).min()).iloc[-1]
    atrv=aa.iloc[-1]
    contraction = recent_range/(atrv*10) if atrv else 9
    price=float(c.iloc[-1]); volx=float(v.iloc[-1]/av.iloc[-1]) if av.iloc[-1] else 0
    r=float(rr.iloc[-1]); ad=float(ax.iloc[-1])
    score=0; tags=[]

    # Trend 25
    if price>e20.iloc[-1]: score+=5; tags.append("20EMA")
    if price>e50.iloc[-1]: score+=5; tags.append("50EMA")
    if price>e200.iloc[-1]: score+=5; tags.append("200EMA")
    if e20.iloc[-1]>e50.iloc[-1]>e200.iloc[-1]: score+=7; tags.append("EMA stack")
    if e50.iloc[-1]>e50.iloc[-21]: score+=3; tags.append("50EMA rising")

    # Momentum 20
    if 52<=r<=72: score+=7; tags.append(f"RSI {r:.0f}")
    elif 48<=r<52: score+=3
    if mm.iloc[-1]>ms.iloc[-1]: score+=6; tags.append("MACD+")
    if mh.iloc[-1]>mh.iloc[-2]: score+=3; tags.append("Hist rising")
    if ad>=20: score+=4; tags.append(f"ADX {ad:.0f}")

    # Breakout / volume 35
    d20=(price/float(h20.iloc[-1])-1)*100 if h20.iloc[-1] else -99
    d55=(price/float(h55.iloc[-1])-1)*100 if h55.iloc[-1] else -99
    if -1.5<=d20<=0.5: score+=10; tags.append("Near 20D BO")
    if -2<=d55<=0.5: score+=5; tags.append("Near 55D BO")
    if volx>=2: score+=10; tags.append(f"Vol {volx:.1f}x")
    elif volx>=1.5: score+=7; tags.append(f"Vol {volx:.1f}x")
    elif volx>=1.2: score+=3
    if contraction<0.75: score+=5; tags.append("Tight base")

    # Relative strength 10
    rs=None
    common=c.index.intersection(bm.Close.index)
    if len(common)>25:
        s=(c.loc[common].iloc[-1]/c.loc[common].iloc[-21]-1)*100
        b=(bm.Close.loc[common].iloc[-1]/bm.Close.loc[common].iloc[-21]-1)*100
        rs=s-b
        if rs>4: score+=10; tags.append(f"RS +{rs:.1f}pp")
        elif rs>2: score+=6; tags.append(f"RS +{rs:.1f}pp")
        elif rs>0: score+=2

    # Risk and levels
    support=min(float(e20.iloc[-1]),float(e50.iloc[-1]),float(c.rolling(20).min().iloc[-1]))
    sl=max(0.01,min(support*0.985,price-1.5*float(aa.iloc[-1])))
    risk=price-sl
    t1=price+1.5*risk; t2=price+2.5*risk
    entry_low=min(price*0.995,float(h20.iloc[-1])*0.995)
    entry_high=max(price*1.002,float(h20.iloc[-1])*1.005)

    # Avoid overextended chase
    day5=(price/c.iloc[-6]-1)*100 if len(c)>6 else 0
    if day5>12:
        score-=8; tags.append("Extended 5D")
    score=max(0,min(100,int(score)))

    setup = "SNIPER" if score>=75 and abs(d20)<=2 and volx>=1.2 else ("WATCH" if score>=65 else "PASS")
    return dict(Score=score,Setup=setup,Price=price,RSI=r,ADX=ad,VolX=volx,RS20=rs,
                Dist20=d20,Dist55=d55,Base=contraction,EntryLow=entry_low,EntryHigh=entry_high,
                SL=sl,T1=t1,T2=t2,Tags=tags,Date=df.index[-1].date())

# ---------- UI ----------
st.title("🎯 Swing Sniper India — V2")
st.caption("Rule-based professional-style scanner • NSE • 15–20 trading-day swing horizon")

with st.sidebar:
    st.header("Portfolio")
    capital=st.number_input("Capital ₹",10000,500000,50000,5000)
    risk_pct=st.slider("Max account risk / trade",0.5,2.0,1.25,0.05)
    positions=st.slider("Max simultaneous positions",1,5,3)
    minscore=st.slider("Minimum score",55,90,65)
    run=st.button("🔄 SCAN MARKET NOW",type="primary")
    st.markdown("---")
    st.write("Universe:",len(UNIVERSE),"liquid/large & mid-cap names")
    st.write("Holding:", "15–20 trading days")

if run or "data" not in st.session_state:
    n=nifty()
    regime=market_regime(n)
    rows=[]
    bar=st.progress(0)
    for i,s in enumerate(UNIVERSE):
        try:
            d=get(s)
            if not d.empty:
                a=scan(d,n)
                if a:
                    a["Symbol"]=s; rows.append(a)
        except Exception:
            pass
        bar.progress((i+1)/len(UNIVERSE))
    bar.empty()
    st.session_state.data=pd.DataFrame(rows).sort_values(["Score","VolX"],ascending=False)
    st.session_state.regime=regime
    st.session_state.when=datetime.now()

df=st.session_state.data
reg=st.session_state.regime

# Regime banner
if reg[0]=="RISK-ON": st.success(f"🟢 MARKET REGIME: {reg[0]} — {reg[2]}")
elif reg[0]=="RISK-OFF": st.error(f"🔴 MARKET REGIME: {reg[0]} — {reg[2]}")
else: st.warning(f"🟡 MARKET REGIME: {reg[0]} — {reg[2]}")

st.caption("Last scan: "+st.session_state.when.strftime("%d %b %Y %H:%M:%S"))

sn=df[(df.Score>=minscore)&(df.Setup!="PASS")].head(5)

st.header("🔥 TOP 5 SNIPER TRADES")
if sn.empty:
    st.warning("No high-quality setups currently meet the filters. That is intentional: the scanner prefers cash over forced trades.")
else:
    for i,(_,r) in enumerate(sn.iterrows(),1):
        with st.container(border=True):
            c1,c2,c3,c4,c5,c6=st.columns([1.1,1,1.4,1.2,1.2,2.4])
            c1.metric(f"#{i} {r.Symbol}",f"₹{r.Price:,.2f}",f"{int(r.Score)}/100")
            c2.write("**Setup**"); c2.write("🎯 "+r.Setup)
            c3.write("**Entry**"); c3.write(f"₹{r.EntryLow:,.0f}–₹{r.EntryHigh:,.0f}")
            c4.write("**SL**"); c4.write(f"₹{r.SL:,.0f}")
            c5.write("**T1 / T2**"); c5.write(f"₹{r.T1:,.0f} / ₹{r.T2:,.0f}")
            c6.write("**Why**"); c6.write(" • ".join(r.Tags[:7]))

st.header("💰 ₹ Risk-controlled position sizing")
rows=[]
risk_rupees=capital*risk_pct/100
for _,r in sn.head(positions).iterrows():
    risk_per=max(r.Price-r.SL,0.01)
    q_risk=int(risk_rupees/risk_per)
    q_cap=int((capital/positions)/r.Price)
    q=max(0,min(q_risk,q_cap))
    rows.append([r.Symbol,q,round(q*r.Price),round(q*risk_per),round(q*risk_per/capital*100,2)])
if rows:
    st.dataframe(pd.DataFrame(rows,columns=["Stock","Qty","Capital ₹","Max SL loss ₹","Portfolio risk %"]),use_container_width=True,hide_index=True)

st.header("📊 Full scanner")
view=df[["Symbol","Setup","Score","Price","RSI","ADX","VolX","RS20","Dist20","Dist55","Base","EntryLow","EntryHigh","SL","T1","T2"]].copy()
st.dataframe(view.round(2),use_container_width=True,hide_index=True)

st.info("Research tool only. Public-market data may be delayed or incomplete. Verify live NSE/broker price, liquidity, news, earnings and corporate actions before placing a trade. Scores are rule-based signals, not guarantees.")
