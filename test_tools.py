"""Quick test — call key tools directly via adapters."""
import sys, os
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(".env")

results = {}

# 1. Crypto - 김치프리미엄
try:
    from mcp_servers.adapters.ccxt_adapter import CCXTAdapter
    r = CCXTAdapter().calculate_kimchi_premium("BTC")
    results["crypto_kimchi"] = "OK" if r.get("success") else f"FAIL: {r.get('message','')[:50]}"
except Exception as e:
    results["crypto_kimchi"] = f"ERR: {str(e)[:50]}"

# 2. DeFi - Fear&Greed
try:
    from mcp_servers.adapters.defi_adapter import FearGreedAdapter
    r = FearGreedAdapter().get_current()
    results["feargreed"] = f"OK val={r.get('value')}" if r.get("success") else f"FAIL: {r.get('message','')[:50]}"
except Exception as e:
    results["feargreed"] = f"ERR: {str(e)[:50]}"

# 3. DefiLlama
try:
    from mcp_servers.adapters.defi_adapter import DefiLlamaAdapter
    r = DefiLlamaAdapter().get_chains()
    results["defillama"] = f"OK chains={r.get('count')}" if r.get("success") else f"FAIL"
except Exception as e:
    results["defillama"] = f"ERR: {str(e)[:50]}"

# 4. Etherscan
try:
    from mcp_servers.adapters.etherscan_adapter import EtherscanAdapter
    r = EtherscanAdapter().get_gas_price()
    results["etherscan"] = f"OK gas={r.get('propose_gwei')}" if r.get("success") else f"FAIL: {r.get('message','')[:50]}"
except Exception as e:
    results["etherscan"] = f"ERR: {str(e)[:50]}"

# 5. Naver News
try:
    from mcp_servers.adapters.naver_adapter import NaverAdapter
    r = NaverAdapter().search_news("비트코인", display=3)
    results["naver_news"] = f"OK articles={r.get('count')}" if r.get("success") else f"FAIL: {r.get('message','')[:50]}"
except Exception as e:
    results["naver_news"] = f"ERR: {str(e)[:50]}"

# 6. Polymarket
try:
    from mcp_servers.adapters.polymarket_adapter import PolymarketAdapter
    r = PolymarketAdapter().get_markets(limit=3)
    results["polymarket"] = f"OK markets={r.get('count')}" if r.get("success") else f"FAIL: {r.get('message','')[:50]}"
except Exception as e:
    results["polymarket"] = f"ERR: {str(e)[:50]}"

# 7. GDELT
try:
    from mcp_servers.adapters.gdelt_academic_adapter import GDELTAdapter
    r = GDELTAdapter().search_articles("South Korea economy", max_records=3)
    results["gdelt"] = f"OK articles={r.get('count')}" if r.get("success") else f"FAIL: {r.get('message','')[:50]}"
except Exception as e:
    results["gdelt"] = f"ERR: {str(e)[:50]}"

# 8. arXiv
try:
    from mcp_servers.adapters.gdelt_academic_adapter import AcademicAdapter
    r = AcademicAdapter().search_arxiv("AI agent economy", max_results=3)
    results["arxiv"] = f"OK papers={r.get('count')}" if r.get("success") else f"FAIL: {r.get('message','')[:50]}"
except Exception as e:
    results["arxiv"] = f"ERR: {str(e)[:50]}"

# 9. Finnhub
try:
    from mcp_servers.adapters.phase2_adapters import FinnhubAdapter
    r = FinnhubAdapter().get_quote("AAPL")
    results["finnhub"] = f"OK AAPL=${r.get('current')}" if r.get("success") else f"FAIL: {r.get('message','')[:50]}"
except Exception as e:
    results["finnhub"] = f"ERR: {str(e)[:50]}"

# 10. Maritime BDI
try:
    from mcp_servers.adapters.phase3_adapters import MaritimeAdapter
    r = MaritimeAdapter().get_bdi_proxy()
    results["maritime_bdi"] = f"OK count={r.get('count')}" if r.get("success") else f"FAIL: {r.get('message','')[:50]}"
except Exception as e:
    results["maritime_bdi"] = f"ERR: {str(e)[:50]}"

# 11. Energy (EIA)
try:
    from mcp_servers.adapters.phase3_adapters import EnergyAdapter
    r = EnergyAdapter().get_crude_oil_price(5)
    results["eia_oil"] = f"OK count={r.get('count')}" if r.get("success") else f"FAIL: {r.get('message','')[:50]}"
except Exception as e:
    results["eia_oil"] = f"ERR: {str(e)[:50]}"

# 12. Weather
try:
    from mcp_servers.adapters.phase3_adapters import WeatherAdapter
    r = WeatherAdapter().get_forecast(37.5665, 126.978, 3)
    results["weather"] = "OK" if r.get("success") else f"FAIL"
except Exception as e:
    results["weather"] = f"ERR: {str(e)[:50]}"

print("\n========= TOOL TEST RESULTS =========")
ok = 0
fail = 0
for name, status in results.items():
    icon = "✓" if status.startswith("OK") else "✗"
    if status.startswith("OK"):
        ok += 1
    else:
        fail += 1
    print(f"  {icon} {name}: {status}")
print(f"\n  TOTAL: {ok} OK / {fail} FAIL / {ok+fail} tested")
