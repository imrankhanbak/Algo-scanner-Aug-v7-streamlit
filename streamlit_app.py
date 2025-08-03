import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.subplots as sp
from plotly.subplots import make_subplots
import aiohttp
import asyncio
import requests
from datetime import datetime, date
from bs4 import BeautifulSoup
import logging
import time
from typing import List, Dict, Any, Optional
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="PSX Algo v7 - Advanced Stock Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# PSX Symbols
PSX_SYMBOLS = [
    "MEBL", "HBL", "UBL", "BAHL", "ENGRO", "LUCK", "PSO", "FFC", "OGDC", "PPL",
    "EFERT", "SNGP", "GATM", "HUBC", "KAPCO", "SYS", "TRG", "FABL", "NBP", "MCB",
    "AVN", "SEARL", "ATRL", "PAEL", "EPCL", "DGKC", "FCCL", "KOHC", "CHCC", "MLCF",
    "PIOC", "POWER", "AGP", "THALL", "INIL", "MUREB", "FCEPL", "FATIMA", "UNITY",
    "HTL", "APL", "MDTL", "BIPL", "KEL", "JDWS", "ISL", "HINOON", "SRVI", "LOTCHEM",
    "AIRLINK", "TPL", "PRL", "HUMNL", "MFL", "PAKT", "SML", "KTML", "DCR", "PSEL",
    "RPL", "NETSOL", "PKGS", "EFUG", "EFUHL", "EFU", "POL", "ATLH", "GHNI", "AVP",
    "PGLC", "CNERGY", "GSKCH", "WYETH", "ILP", "GADT", "GSK", "TSML", "NCPL", "GATI",
    "MUGHAL", "TPLP", "UGDC", "EFOODS", "AICL", "IGIHL", "PSX", "NRL", "GLAXO",
    "GTL", "ICIBL", "MEHT", "RMPL", "JLICL", "SHEL", "DAWH"
]

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_psx_data(symbol: str, year: int, month: int) -> List[Dict]:
    """Fetch historical data from PSX API with caching"""
    url = "https://dps.psx.com.pk/historical"
    
    form_data = {
        "symbol": symbol,
        "year": str(year),
        "month": str(month)
    }
    
    try:
        response = requests.post(url, data=form_data, timeout=30)
        if response.status_code != 200:
            st.error(f"Error fetching data for {symbol}: HTTP {response.status_code}")
            return []
        
        html = response.text
        if not html or len(html) < 100:
            st.warning(f"No data returned for {symbol} - {year}/{month}")
            return []
        
        # Parse HTML table
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        
        if not table:
            st.warning(f"No table found for {symbol} - {year}/{month}")
            return []
        
        rows = table.find_all('tr')[1:]  # Skip header
        data = []
        
        for row_idx, row in enumerate(rows):
            cells = row.find_all('td')
            if len(cells) >= 6:
                try:
                    # Extract and validate data
                    date_str = cells[0].get_text().strip()
                    open_str = cells[1].get_text().strip().replace(',', '')
                    high_str = cells[2].get_text().strip().replace(',', '')
                    low_str = cells[3].get_text().strip().replace(',', '')
                    close_str = cells[4].get_text().strip().replace(',', '')
                    volume_str = cells[5].get_text().strip().replace(',', '')
                    
                    # Try to parse different date formats
                    date_obj = None
                    try:
                        # First try the new format: "Jul 31, 2025"
                        date_obj = datetime.strptime(date_str, '%b %d, %Y')
                        formatted_date = date_obj.strftime('%d-%b-%Y')
                    except ValueError:
                        try:
                            # Try the old format: "31-Jul-2025"
                            date_obj = datetime.strptime(date_str, '%d-%b-%Y')
                            formatted_date = date_str
                        except ValueError:
                            continue
                    
                    if not date_obj:
                        continue
                    
                    # Parse and validate numeric values
                    open_price = float(open_str) if open_str and open_str != '-' and open_str != '0' else None
                    high_price = float(high_str) if high_str and high_str != '-' and high_str != '0' else None
                    low_price = float(low_str) if low_str and low_str != '-' and low_str != '0' else None
                    close_price = float(close_str) if close_str and close_str != '-' and close_str != '0' else None
                    volume = int(float(volume_str)) if volume_str and volume_str != '-' and volume_str != '0' else 0
                    
                    # Skip if essential data is missing
                    if not all([open_price, high_price, low_price, close_price]):
                        continue
                    
                    # Validate price relationships
                    if not (low_price <= open_price <= high_price and low_price <= close_price <= high_price):
                        continue
                    
                    data.append({
                        "date": formatted_date,
                        "date_obj": date_obj,
                        "open": open_price,
                        "high": high_price,
                        "low": low_price,
                        "close": close_price,
                        "volume": volume
                    })
                    
                except (ValueError, IndexError, AttributeError):
                    continue
        
        # Sort data by date
        data.sort(key=lambda x: x['date_obj'])
        return data
        
    except Exception as e:
        st.error(f"Error fetching data for {symbol}: {str(e)}")
        return []

def calculate_rsi(prices, period=14):
    """Calculate RSI (Relative Strength Index)"""
    prices = pd.Series(prices)
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50).tolist()

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD"""
    prices = pd.Series(prices)
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    
    return {
        "macd": macd_line.fillna(0).tolist(),
        "signal": signal_line.fillna(0).tolist(),
        "histogram": histogram.fillna(0).tolist()
    }

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    prices = pd.Series(prices)
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    
    return {
        "upper": upper_band.fillna(0).tolist(),
        "middle": sma.fillna(0).tolist(),
        "lower": lower_band.fillna(0).tolist()
    }

def calculate_atr(high, low, close, period=14):
    """Calculate Average True Range"""
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr.fillna(0).tolist()

def calculate_stochastic(high, low, close, k_period=14, d_period=3):
    """Calculate Stochastic Oscillator"""
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=d_period).mean()
    
    return {
        "k": k_percent.fillna(50).tolist(),
        "d": d_percent.fillna(50).tolist()
    }

def calculate_adx(high, low, close, period=14):
    """Calculate Average Directional Index"""
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    
    up_move = high.diff()
    down_move = -low.diff()
    
    plus_dm = pd.Series([max(um, 0) if um > dm else 0 for um, dm in zip(up_move, down_move)])
    minus_dm = pd.Series([max(dm, 0) if dm > um else 0 for um, dm in zip(up_move, down_move)])
    
    atr_values = calculate_atr(high, low, close, period)
    atr = pd.Series(atr_values)
    
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return {
        "adx": adx.fillna(25).tolist(),
        "plus_di": plus_di.fillna(0).tolist(),
        "minus_di": minus_di.fillna(0).tolist()
    }

def analyze_symbol(symbol: str, include_previous_month: bool = True):
    """Analyze a single symbol with all technical indicators"""
    today = datetime.now()
    current_year = today.year
    current_month = today.month
    
    # Fetch current month data
    current_data = fetch_psx_data(symbol, current_year, current_month)
    
    all_data = []
    if include_previous_month:
        # Fetch previous month for more comprehensive analysis
        prev_month = current_month - 1 if current_month > 1 else 12
        prev_year = current_year if current_month > 1 else current_year - 1
        prev_data = fetch_psx_data(symbol, prev_year, prev_month)
        
        if prev_data:
            all_data.extend(prev_data)
    
    if current_data:
        all_data.extend(current_data)
    
    if len(all_data) < 10:
        st.error(f"Insufficient data for {symbol}. Found only {len(all_data)} data points.")
        return None
    
    # Remove duplicates and sort
    seen_dates = set()
    unique_data = []
    for record in all_data:
        if record['date'] not in seen_dates:
            unique_data.append(record)
            seen_dates.add(record['date'])
    
    all_data = sorted(unique_data, key=lambda x: x['date_obj'])
    
    # Extract OHLCV data
    dates = [d["date"] for d in all_data]
    opens = [d["open"] for d in all_data]
    highs = [d["high"] for d in all_data]
    lows = [d["low"] for d in all_data]
    closes = [d["close"] for d in all_data]
    volumes = [d["volume"] for d in all_data]
    
    # Calculate technical indicators
    rsi = calculate_rsi(closes)
    macd = calculate_macd(closes)
    bollinger = calculate_bollinger_bands(closes)
    atr = calculate_atr(highs, lows, closes)
    stochastic = calculate_stochastic(highs, lows, closes)
    adx = calculate_adx(highs, lows, closes)
    
    # Moving averages
    closes_series = pd.Series(closes)
    sma_20 = closes_series.rolling(window=min(20, len(closes))).mean().fillna(method='ffill').fillna(0).tolist()
    sma_50 = closes_series.rolling(window=min(50, len(closes))).mean().fillna(method='ffill').fillna(0).tolist()
    sma_200 = closes_series.rolling(window=min(200, len(closes))).mean().fillna(method='ffill').fillna(0).tolist()
    
    # Generate signals
    latest_close = closes[-1]
    latest_rsi = rsi[-1] if rsi else 50
    latest_macd_hist = macd["histogram"][-1] if macd["histogram"] else 0
    
    # Simple signal generation
    signal_score = 0
    if latest_rsi < 30:
        signal_score += 2  # Oversold - bullish
    elif latest_rsi > 70:
        signal_score -= 2  # Overbought - bearish
    
    if latest_macd_hist > 0:
        signal_score += 1  # MACD positive
    else:
        signal_score -= 1  # MACD negative
    
    if closes[-1] > sma_50[-1]:
        signal_score += 1  # Above SMA 50
    if closes[-1] > sma_200[-1]:
        signal_score += 1  # Above SMA 200
    
    # Determine signal
    if signal_score >= 3:
        overall_signal = "STRONG_BUY"
        signal_color = "🟢"
    elif signal_score >= 1:
        overall_signal = "BUY"
        signal_color = "🔵"
    elif signal_score <= -3:
        overall_signal = "STRONG_SELL"
        signal_color = "🔴"
    elif signal_score <= -1:
        overall_signal = "SELL"
        signal_color = "🟠"
    else:
        overall_signal = "HOLD"
        signal_color = "🟡"
    
    # Calculate price change
    price_change = closes[-1] - closes[-2] if len(closes) > 1 else 0
    price_change_pct = (price_change / closes[-2] * 100) if len(closes) > 1 and closes[-2] != 0 else 0
    
    return {
        "symbol": symbol,
        "data": all_data,
        "dates": dates,
        "opens": opens,
        "highs": highs,
        "lows": lows,
        "closes": closes,
        "volumes": volumes,
        "indicators": {
            "rsi": rsi,
            "macd": macd,
            "bollinger": bollinger,
            "atr": atr,
            "stochastic": stochastic,
            "adx": adx,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "sma_200": sma_200
        },
        "signal": {
            "overall_signal": overall_signal,
            "signal_color": signal_color,
            "score": signal_score
        },
        "current_price": {
            "price": latest_close,
            "high": highs[-1],
            "low": lows[-1],
            "change": price_change,
            "change_pct": price_change_pct,
            "last_updated": dates[-1]
        }
    }

def create_candlestick_chart(analysis_result):
    """Create an interactive candlestick chart with technical indicators"""
    
    # Create subplots
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(
            f'{analysis_result["symbol"]} - Price & Technical Indicators',
            'MACD',
            'RSI',
            'Volume'
        ),
        row_width=[0.2, 0.1, 0.1, 0.1]
    )
    
    dates = analysis_result["dates"]
    
    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=dates,
            open=analysis_result["opens"],
            high=analysis_result["highs"],
            low=analysis_result["lows"],
            close=analysis_result["closes"],
            name="Price",
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ),
        row=1, col=1
    )
    
    # Moving Averages
    indicators = analysis_result["indicators"]
    
    if indicators["sma_20"]:
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=indicators["sma_20"],
                mode='lines',
                name='SMA 20',
                line=dict(color='orange', width=1)
            ),
            row=1, col=1
        )
    
    if indicators["sma_50"]:
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=indicators["sma_50"],
                mode='lines',
                name='SMA 50',
                line=dict(color='blue', width=2)
            ),
            row=1, col=1
        )
    
    if indicators["sma_200"]:
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=indicators["sma_200"],
                mode='lines',
                name='SMA 200',
                line=dict(color='purple', width=2)
            ),
            row=1, col=1
        )
    
    # Bollinger Bands
    if indicators["bollinger"]:
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=indicators["bollinger"]["upper"],
                mode='lines',
                name='BB Upper',
                line=dict(color='gray', width=1, dash='dash'),
                showlegend=False
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=indicators["bollinger"]["lower"],
                mode='lines',
                name='BB Lower',
                line=dict(color='gray', width=1, dash='dash'),
                fill='tonexty',
                fillcolor='rgba(128,128,128,0.1)',
                showlegend=False
            ),
            row=1, col=1
        )
    
    # MACD
    if indicators["macd"]:
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=indicators["macd"]["macd"],
                mode='lines',
                name='MACD',
                line=dict(color='blue', width=2)
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=indicators["macd"]["signal"],
                mode='lines',
                name='Signal',
                line=dict(color='red', width=1)
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=dates,
                y=indicators["macd"]["histogram"],
                name='Histogram',
                marker_color=['green' if x >= 0 else 'red' for x in indicators["macd"]["histogram"]]
            ),
            row=2, col=1
        )
    
    # RSI
    if indicators["rsi"]:
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=indicators["rsi"],
                mode='lines',
                name='RSI',
                line=dict(color='purple', width=2)
            ),
            row=3, col=1
        )
        
        # RSI levels
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    
    # Volume
    fig.add_trace(
        go.Bar(
            x=dates,
            y=analysis_result["volumes"],
            name='Volume',
            marker_color=['green' if c >= o else 'red' for c, o in zip(analysis_result["closes"], analysis_result["opens"])]
        ),
        row=4, col=1
    )
    
    # Update layout
    fig.update_layout(
        title=f'{analysis_result["symbol"]} - Technical Analysis',
        xaxis_title="Date",
        template="plotly_dark",
        height=800,
        showlegend=True,
        xaxis_rangeslider_visible=False
    )
    
    # Update y-axes titles
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="MACD", row=2, col=1)
    fig.update_yaxes(title_text="RSI", row=3, col=1)
    fig.update_yaxes(title_text="Volume", row=4, col=1)
    
    return fig

def main():
    # App header
    st.title("📈 PSX Algo v7 - Advanced Stock Scanner")
    st.markdown("### Advanced Technical Analysis for Pakistan Stock Exchange")
    
    # Sidebar
    st.sidebar.header("🔧 Configuration")
    
    # Analysis type
    analysis_type = st.sidebar.radio(
        "Analysis Type:",
        ["Single Symbol", "Multiple Symbols Scanner"]
    )
    
    # Date range
    include_previous = st.sidebar.checkbox(
        "Include Previous Month Data",
        value=True,
        help="Combine current and previous month for better analysis"
    )
    
    if analysis_type == "Single Symbol":
        # Single symbol analysis
        st.sidebar.subheader("📊 Single Symbol Analysis")
        
        # Symbol selection
        symbol_input = st.sidebar.text_input(
            "Enter PSX Symbol:",
            value="OGDC",
            help="Enter any PSX symbol (e.g., OGDC, HBL, UBL)"
        ).upper()
        
        if st.sidebar.button("🔍 Analyze Symbol", type="primary"):
            if symbol_input:
                with st.spinner(f"Analyzing {symbol_input}..."):
                    result = analyze_symbol(symbol_input, include_previous)
                
                if result:
                    # Display results
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Current Price",
                            f"₨{result['current_price']['price']:.2f}",
                            f"{result['current_price']['change']:+.2f} ({result['current_price']['change_pct']:+.2f}%)"
                        )
                    
                    with col2:
                        st.metric(
                            "Daily High",
                            f"₨{result['current_price']['high']:.2f}"
                        )
                    
                    with col3:
                        st.metric(
                            "Daily Low",
                            f"₨{result['current_price']['low']:.2f}"
                        )
                    
                    with col4:
                        signal_info = result['signal']
                        st.metric(
                            "Signal",
                            f"{signal_info['signal_color']} {signal_info['overall_signal']}",
                            f"Score: {signal_info['score']}"
                        )
                    
                    # Technical Indicators Summary
                    st.subheader("📈 Technical Indicators Summary")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    indicators = result['indicators']
                    
                    with col1:
                        latest_rsi = indicators['rsi'][-1] if indicators['rsi'] else 0
                        rsi_status = "Overbought" if latest_rsi > 70 else "Oversold" if latest_rsi < 30 else "Neutral"
                        st.info(f"**RSI (14):** {latest_rsi:.2f}\n\n**Status:** {rsi_status}")
                    
                    with col2:
                        latest_macd = indicators['macd']['histogram'][-1] if indicators['macd']['histogram'] else 0
                        macd_status = "Bullish" if latest_macd > 0 else "Bearish"
                        st.info(f"**MACD Histogram:** {latest_macd:.4f}\n\n**Status:** {macd_status}")
                    
                    with col3:
                        latest_atr = indicators['atr'][-1] if indicators['atr'] else 0
                        st.info(f"**ATR (14):** {latest_atr:.2f}\n\n**Volatility Measure**")
                    
                    with col4:
                        latest_adx = indicators['adx']['adx'][-1] if indicators['adx']['adx'] else 0
                        adx_strength = "Strong" if latest_adx > 25 else "Weak"
                        st.info(f"**ADX (14):** {latest_adx:.2f}\n\n**Trend:** {adx_strength}")
                    
                    # Interactive Chart
                    st.subheader("📊 Interactive Price Chart")
                    
                    chart = create_candlestick_chart(result)
                    st.plotly_chart(chart, use_container_width=True)
                    
                    # Data Table
                    st.subheader("📋 Recent Price Data")
                    
                    # Create DataFrame
                    df = pd.DataFrame({
                        'Date': result['dates'][-10:],
                        'Open': [f"₨{x:.2f}" for x in result['opens'][-10:]],
                        'High': [f"₨{x:.2f}" for x in result['highs'][-10:]],
                        'Low': [f"₨{x:.2f}" for x in result['lows'][-10:]],
                        'Close': [f"₨{x:.2f}" for x in result['closes'][-10:]],
                        'Volume': [f"{x:,}" for x in result['volumes'][-10:]],
                        'RSI': [f"{x:.2f}" for x in result['indicators']['rsi'][-10:]] if result['indicators']['rsi'] else ['N/A'] * 10
                    })
                    
                    st.dataframe(df, use_container_width=True)
            else:
                st.error("Please enter a symbol to analyze")
    
    else:
        # Multiple symbols scanner
        st.sidebar.subheader("🔍 Multi-Symbol Scanner")
        
        # Select symbols
        selected_symbols = st.sidebar.multiselect(
            "Select Symbols to Scan:",
            PSX_SYMBOLS,
            default=["OGDC", "HBL", "UBL", "MEBL", "ENGRO"][:5],
            help="Select up to 10 symbols for scanning"
        )
        
        max_symbols = st.sidebar.slider("Max Symbols to Scan:", 5, 20, 10)
        
        if st.sidebar.button("🚀 Start Scanning", type="primary"):
            symbols_to_scan = selected_symbols[:max_symbols] if selected_symbols else PSX_SYMBOLS[:max_symbols]
            
            st.subheader(f"📊 Scanning {len(symbols_to_scan)} Symbols")
            
            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            results = []
            
            for i, symbol in enumerate(symbols_to_scan):
                status_text.text(f"Analyzing {symbol}... ({i+1}/{len(symbols_to_scan)})")
                progress_bar.progress((i + 1) / len(symbols_to_scan))
                
                try:
                    result = analyze_symbol(symbol, include_previous)
                    if result:
                        results.append({
                            'Symbol': symbol,
                            'Current Price': f"₨{result['current_price']['price']:.2f}",
                            'Change %': f"{result['current_price']['change_pct']:+.2f}%",
                            'High': f"₨{result['current_price']['high']:.2f}",
                            'Low': f"₨{result['current_price']['low']:.2f}",
                            'Signal': f"{result['signal']['signal_color']} {result['signal']['overall_signal']}",
                            'RSI': f"{result['indicators']['rsi'][-1]:.2f}" if result['indicators']['rsi'] else 'N/A',
                            'Score': result['signal']['score'],
                            'Volume': f"{result['volumes'][-1]:,}" if result['volumes'] else 'N/A'
                        })
                except Exception as e:
                    st.warning(f"Error analyzing {symbol}: {str(e)}")
                
                time.sleep(0.1)  # Small delay to prevent overwhelming the API
            
            status_text.text("Scanning complete!")
            progress_bar.progress(1.0)
            
            if results:
                # Display results
                st.subheader("📈 Scan Results")
                
                # Convert to DataFrame and sort by score
                df_results = pd.DataFrame(results)
                df_results = df_results.sort_values('Score', ascending=False)
                
                # Color code the dataframe
                st.dataframe(df_results, use_container_width=True)
                
                # Summary stats
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    buy_signals = sum(1 for r in results if 'BUY' in r['Signal'])
                    st.metric("Buy Signals", buy_signals)
                
                with col2:
                    sell_signals = sum(1 for r in results if 'SELL' in r['Signal'])
                    st.metric("Sell Signals", sell_signals)
                
                with col3:
                    hold_signals = sum(1 for r in results if 'HOLD' in r['Signal'])
                    st.metric("Hold Signals", hold_signals)
                
                with col4:
                    st.metric("Total Scanned", len(results))
            else:
                st.error("No results to display. Please try again.")
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("**PSX Algo v7**")
    st.sidebar.markdown("Advanced Technical Analysis")
    st.sidebar.markdown("*Real-time PSX data*")

if __name__ == "__main__":
    main()