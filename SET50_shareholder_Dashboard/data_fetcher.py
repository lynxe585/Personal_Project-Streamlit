import asyncio
import pandas as pd
import streamlit as st
from settfex.services.set import get_stock_list, get_shareholder_data, get_board_of_directors, get_highlight_data

SET50_SYMBOLS = [
    'ADVANC', 'AOT', 'AWC', 'BANPU', 'BBL', 'BDMS', 'BEM', 'BH', 'BJC', 'BTS',
    'CBG', 'CCET', 'CENTEL', 'COM7', 'CPALL', 'CPF', 'CPN', 'CRC', 'DELTA', 'EGCO',
    'GPSC', 'GULF', 'HMPRO', 'IVL', 'KBANK', 'KKP', 'KTB', 'KTC', 'LH', 'MINT',
    'MTC', 'OR', 'OSP', 'PTT', 'PTTEP', 'PTTGC', 'RATCH', 'SAWAD', 'SCB', 'SCC',
    'SCGP', 'TCAP', 'TIDLOR', 'TISCO', 'TLI', 'TOP', 'TRUE', 'TTB', 'TU', 'WHA'
]

@st.cache_data(ttl=3600)
def get_company_metadata():
    """Fetch company sectors and basic info."""
    stock_list = asyncio.run(get_stock_list())
    metadata = {}
    for stock in stock_list.security_symbols:
        if stock.symbol in SET50_SYMBOLS:
            metadata[stock.symbol] = {
                'name_en': stock.name_en,
                'name_th': stock.name_th,
                'sector': stock.sector,
                'industry': stock.industry
            }

    # Fill missing with unknown in case of API mismatches
    for sym in SET50_SYMBOLS:
        if sym not in metadata:
            metadata[sym] = {'name_en': sym, 'name_th': sym, 'sector': 'Unknown', 'industry': 'Unknown'}

    return metadata


@st.cache_data(ttl=3600)
def get_network_data(mode="Combined (3 Shareholders + 2 Directors)", lang="en"):
    """
    Fetches the relationship data based on the mode and language.

    Parameters
    ----------
    mode : str
        - "Major Shareholders (Top 5)"
        - "Board of Directors (Top 5)"
        - "Combined (3 Shareholders + 2 Directors)"
    lang : str
        "en" for English, "th" for Thai
    """
    async def fetch_all():
        sh_tasks = [get_shareholder_data(sym, lang=lang) for sym in SET50_SYMBOLS]
        dir_tasks = [get_board_of_directors(sym, lang=lang) for sym in SET50_SYMBOLS]

        all_tasks = sh_tasks + dir_tasks
        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        sh_results = results[:len(SET50_SYMBOLS)]
        dir_results = results[len(SET50_SYMBOLS):]

        edges = []
        nodes_info = {}  # stakeholder_name -> type ("Shareholder" | "Director")

        for i, sym in enumerate(SET50_SYMBOLS):
            sh_res = sh_results[i]
            dir_res = dir_results[i]

            sh_list = []
            if not isinstance(sh_res, Exception) and hasattr(sh_res, 'major_shareholders'):
                sh_list = sh_res.major_shareholders

            dir_list = []
            if not isinstance(dir_res, Exception) and isinstance(dir_res, list):
                dir_list = dir_res

            selected_edges = []
            if mode == "Major Shareholders (Top 5)":
                for sh in sh_list[:5]:
                    selected_edges.append((sym, sh.name, "Shareholder", sh.percent_of_share))
                    nodes_info[sh.name] = "Shareholder"
            elif mode == "Board of Directors (Top 5)":
                for d in dir_list[:5]:
                    pos = d.positions[0] if d.positions else "Director"
                    selected_edges.append((sym, d.name, "Director", pos))
                    nodes_info[d.name] = "Director"
            else:  # Combined
                for sh in sh_list[:3]:
                    selected_edges.append((sym, sh.name, "Shareholder", sh.percent_of_share))
                    nodes_info[sh.name] = "Shareholder"
                for d in dir_list[:2]:
                    pos = d.positions[0] if d.positions else "Director"
                    selected_edges.append((sym, d.name, "Director", pos))
                    nodes_info[d.name] = "Director"

            edges.extend(selected_edges)

        return edges, nodes_info

    return asyncio.run(fetch_all())


@st.cache_data(ttl=3600)
def get_company_highlights(symbol, lang="en"):
    """Fetch specific stock highlight data for the detail panel."""
    try:
        data = asyncio.run(get_highlight_data(symbol, lang=lang))
        if not isinstance(data, Exception):
            if lang == "th":
                return {
                    'มูลค่าตลาด (บาท)': f"{data.market_cap:,.0f}" if data.market_cap else "N/A",
                    'P/E Ratio': data.pe_ratio,
                    'P/B Ratio': data.pb_ratio,
                    'อัตราปันผล (%)': data.dividend_yield,
                    'เปลี่ยนแปลง YTD (%)': data.ytd_percent_change
                }
            else:
                return {
                    'Market Cap (THB)': f"{data.market_cap:,.0f}" if data.market_cap else "N/A",
                    'P/E Ratio': data.pe_ratio,
                    'P/B Ratio': data.pb_ratio,
                    'Dividend Yield (%)': data.dividend_yield,
                    'YTD Change (%)': data.ytd_percent_change
                }
    except Exception:
        pass
    return None
