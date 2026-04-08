# Nexus Finance MCP — Quick Reference

> One-page cheat sheet. For full details, see [USAGE_GUIDE.md](USAGE_GUIDE.md).

---

## Connect

```bash
# Claude Code
claude mcp add nexus-finance --transport http http://62.171.141.206/mcp

# Health check
curl http://62.171.141.206/health
```

```json
// Cursor / VS Code (.cursor/mcp.json)
{ "mcpServers": { "nexus-finance": { "url": "http://62.171.141.206/mcp" } } }
```

---

## First 3 Calls

```
gateway_status()                    → Server health, tool count, uptime
list_available_tools()              → All tool names
list_tools_by_domain("crypto")      → Filter by domain
```

---

## Parse Responses

```python
if response.get("error"):
    print(response["message"])      # Error description
else:
    data = response["data"]         # Actual payload
```

---

## Top Tools by Domain

| Domain | Tool | What it does |
|--------|------|-------------|
| **Korean Macro** | `ecos_get_macro_snapshot()` | GDP, CPI, rates — zero params |
| **Korean Equity** | `stocks_quote("005930")` | Samsung live price + ratios |
| **Disclosures** | `dart_financial_statements("005930")` | 3-year financials |
| **Multi-Year** | `dart_financial_multi_year("000660", 5)` | 5-year financials (auto-merge) ★ |
| **Equity All-in-1** | `dart_equity_analysis("005930")` | Company+financials+ratios+CF+dividend ★ |
| **US Macro** | `macro_fred("GDP")` | FRED data (any series ID) |
| **Crypto** | `crypto_ticker("binance", "BTC/USDT")` | Real-time price |
| **Quant** | `quant_correlation(series1, series2)` | Pearson/Spearman/Kendall |
| **Backtest** | `backtest_run("005930", "RSI_oversold", 3)` | Strategy backtest |
| **Charts** | `viz_line_chart(data, "date", ["price"])` | Plotly line chart |
| **Research** | `academic_search("transformer finance")` | arXiv + Scholar |
| **Alt Data** | `climate_enso_index()` | El Nino/La Nina index |

---

## 6 Input Patterns

| Pattern | Params | Example |
|---------|--------|---------|
| **snapshot** | 0 | `ecos_get_macro_snapshot()` |
| **stock_code** | 1 (code) | `dart_company_info("005930")` |
| **series** | 2-3 (dates) | `ecos_get_base_rate("2020-01", "2024-12")` |
| **search** | 1 (keyword) | `academic_search("GARCH volatility")` |
| **data_columns** | 2+ (table + cols) | `kosis_get_data(table_id, columns)` |
| **composite** | 3+ (multi-step) | `backtest_run(stock, strategy, years)` |

---

## 11 Domains

| Domain | Prefix | Servers |
|--------|--------|---------|
| Korean Macro | `ecos_`, `kosis_`, `fsc_` | 4 |
| Korean Equity | `stocks_`, `dart_` | 4 |
| Global Markets | `us_`, `global_`, `asia_`, `india_` | 6 |
| Crypto | `crypto_`, `defi_`, `onchain_` | 6 |
| Quant | `quant_`, `ts_`, `backtest_`, `factor_`, `signal_` | 8 |
| Advanced Quant | `stat_arb_`, `stochvol_`, `micro_`, `ml_`, `alpha_` | 7 |
| News & Research | `news_`, `academic_`, `rss_`, `research_` | 6 |
| Alternative Data | `energy_`, `agri_`, `maritime_`, `trade_` | 7 |
| Visualization | `viz_`, `ta_`, `val_` | 3 |
| Regulatory | `regulation_`, `patent_`, `health_` | 4 |
| Knowledge | `vault_`, `memory_`, `ontology_`, `gateway_` | 4 |

---

## Rate Limits

| Scope | Limit |
|-------|-------|
| Nginx (per IP) | 5 req/s, burst 10 |
| ECOS API | 60 req/min |
| DART API | 100 req/min |
| CoinGecko | 50 req/min |
| EDINET (lowest) | 30 req/min |

---

## Backtest Strategies

| Strategy | Logic |
|----------|-------|
| `RSI_oversold` | RSI < 30 buy, > 70 sell |
| `MACD_crossover` | MACD-signal crossover |
| `Bollinger_bounce` | Lower band touch |
| `MA_cross` | 20/50 golden cross |
| `Mean_reversion` | Mean - 2 sigma |
| `Momentum` | N-day positive return |

---

## Detailed Docs

| Need | Read |
|------|------|
| Full usage patterns & workflows | [USAGE_GUIDE.md](USAGE_GUIDE.md) |
| All 398 tools listed | [TOOL_CATALOG.md](TOOL_CATALOG.md) |
| Response format spec | [PARSING_GUIDE.md](PARSING_GUIDE.md) |
| Error codes & retry | [ERROR_REFERENCE.md](ERROR_REFERENCE.md) |
| Architecture diagrams | [DATA_FLOW.md](DATA_FLOW.md) |
| System internals | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Connection guide | [CONNECT.md](../CONNECT.md) |
