"""
scripts/parse_holdings.py
─────────────────────────
Parses the user's Excel holdings statement into a structured JSON file:
data/user_holdings.json
Maps each stock to its NSE ticker for live price tracking.
"""

import os
import json
import pandas as pd

EXCEL_PATH = r"C:\Users\saksh\OneDrive\Documents\Stocks_Holdings_Statement_9376328401_2026-10-01.xlsx"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "user_holdings.json")

# Map broker names to live NSE tickers
TICKER_MAP = {
    "AXIS BANK LIMITED": "AXISBANK.NS",
    "BHARAT ELECTRONICS LTD": "BEL.NS",
    "BHARTI AIRTEL LIMITED": "BHARTIARTL.NS",
    "BSE LIMITED": "BSE.NS",
    "COAL INDIA LTD": "COALINDIA.NS",
    "DRONE DESTINATION LIMITED": "DRONEDESTN.NS",
    "ETERNAL LIMITED": "ETERNAL.NS",
    "GROWWAMC - GROWWDEFNC": "GROWWDEFNC.NS",
    "GROWWAMC - GROWWGOLD": "GROWWGOLD.NS",
    "GROWWAMC - GROWWSLVR": "GROWWSLVR.NS",
    "GTL INFRA.LTD": "GTLINFRA.NS",
    "HDFC BANK LTD": "HDFCBANK.NS",
    "HDFCAMC - HDFCSILVER": "HDFCSILVER.NS",
    "INDIAN RAILWAY FIN CORP L": "IRFC.NS",
    "MAZAGON DOCK SHIPBUIL LTD": "MAZDOCK.NS",
    "NIP IND ETF GOLD BEES": "GOLDBEES.NS",
    "NIP IND ETF PSU BANK BEES": "PSUBNKBEES.NS",
    "NIPPONAMC - NETFSILVER": "SILVERBEES.NS",
    "NTPC LTD": "NTPC.NS",
    "QUADRANT TELEVENTURES LIMITED": "QUADRANT.NS",
    "STATE BANK OF INDIA": "SBIN.NS",
    "TATAAML-TATSILV": "TATSILV.NS",
    "VEDANTA IRON AND STEEL L": "VEDL.NS",       # Demerged proxy
    "VEDANTA LIMITED": "VEDL.NS",
    "VEDANTA OIL AND GAS LTD": "VEDL.NS",       # Demerged proxy
    "VEDANTA POWER LIMITED": "VEDL.NS",         # Demerged proxy
    "YES BANK LIMITED": "YESBANK.NS",
    "ZEE MEDIA CORPORATION LTD": "ZEEMEDIA.NS",
}


def parse():
    df = pd.read_excel(EXCEL_PATH, header=None)
    
    client_name = "Saksham Aggarwal"
    ucc = "9376328401"
    as_of = "2026-10-01"
    
    invested_val = 608295.98
    closing_val = 572973.44
    unrealised_pnl = -35322.54

    holdings = []
    
    # Rows 11 to 38 are holdings
    for i in range(11, len(df)):
        row = df.iloc[i].tolist()
        name = str(row[0]).strip()
        if not name or name == "nan":
            continue
            
        isin = str(row[1]).strip()
        qty = float(row[2])
        avg_price = float(row[3])
        buy_val = float(row[4])
        close_price = float(row[5])
        close_val = float(row[6])
        pnl = float(row[7])
        pnl_pct = (pnl / buy_val * 100) if buy_val else 0.0

        ticker = TICKER_MAP.get(name, f"{name[:6]}.NS")

        holdings.append({
            "name": name,
            "ticker": ticker,
            "isin": isin,
            "quantity": int(qty) if qty.is_integer() else qty,
            "avg_buy_price": round(avg_price, 2),
            "invested_value": round(buy_val, 2),
            "closing_price": round(close_price, 2),
            "closing_value": round(close_val, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
        })

    portfolio = {
        "client_name": client_name,
        "ucc": ucc,
        "as_of_date": as_of,
        "invested_value": invested_val,
        "closing_value": closing_val,
        "unrealised_pnl": unrealised_pnl,
        "unrealised_pnl_pct": round(unrealised_pnl / invested_val * 100, 2),
        "total_holdings_count": len(holdings),
        "holdings": holdings,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)

    print(f"Parsed {len(holdings)} holdings successfully -> {OUTPUT_PATH}")
    return portfolio


if __name__ == "__main__":
    parse()
