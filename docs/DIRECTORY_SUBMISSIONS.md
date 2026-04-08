# MCP Directory Submissions Checklist

**Project:** nexus-finance-mcp
**GitHub:** https://github.com/pollmap/nexus-finance-mcp
**Description:** Finance & Research Intelligence Platform -- 396 tools, 64 servers
**Category:** Finance
**Transport:** streamable-http
**Endpoint:** http://62.171.141.206/mcp
**Date:** 2026-04-08

---

## Submission Status

| # | Directory | Status | Method | Notes |
|---|-----------|--------|--------|-------|
| 1 | mcp.so | SUBMITTED | GitHub Issue comment | Comment posted on chatmcp/mcpso#1 |
| 2 | mcpservers.org | MANUAL NEEDED | Web form | /submit page, free listing |
| 3 | glama.ai | MANUAL NEEDED | Web form | "Add Server" button, auto-indexes from GitHub |
| 4 | smithery.ai | NOT LISTED | Smithery CLI or web | Previously noted as registered but not found |
| 5 | pulsemcp.com | MANUAL NEEDED | Web form | /submit page, also auto-ingests from Official MCP Registry |
| 6 | mcpmarket.com | MANUAL NEEDED | Web form | /submit page, just needs GitHub URL |
| 7 | Official MCP Registry | NOT SUBMITTED | mcp-publisher CLI | registry.modelcontextprotocol.io |

---

## 1. mcp.so

- **URL:** https://mcp.so
- **Submit method:** Comment on GitHub issue https://github.com/chatmcp/mcpso/issues/1
- **Status:** SUBMITTED (2026-04-08)
- **Comment URL:** https://github.com/chatmcp/mcpso/issues/1#issuecomment-4203736232
- **What was posted:**
  ```
  nexus-finance-mcp -- Finance & Research Intelligence Platform
  GitHub: https://github.com/pollmap/nexus-finance-mcp
  396 tools, 64 servers, streamable-http transport
  Category: Finance
  ```
- **Next:** Wait for maintainers to add to directory

## 2. mcpservers.org

- **URL:** https://mcpservers.org/submit
- **Submit method:** Web form (manual)
- **Status:** MANUAL NEEDED
- **Required fields:**
  - Server Name: `nexus-finance-mcp`
  - Short Description: `Finance & Research Intelligence Platform -- 396 tools, 64 servers for DART, FRED, ECOS, SEC, CCXT, arXiv and more`
  - Link: `https://github.com/pollmap/nexus-finance-mcp`
  - Category: `Other` (no Finance category; closest is Other or Productivity)
  - Contact Email: (your email)
- **Options:** Free listing or $39 premium (faster review + badge + dofollow link)
- **Action:** Go to https://mcpservers.org/submit and fill the form

## 3. glama.ai

- **URL:** https://glama.ai/mcp/servers
- **Submit method:** Click "Add Server" button on the servers page
- **Status:** MANUAL NEEDED
- **Required fields:**
  - GitHub repository URL: `https://github.com/pollmap/nexus-finance-mcp`
  - (Auto-indexes metadata from repo)
- **Notes:** Glama auto-scores servers with A/B/C quality grades for security, license, and quality
- **Action:** Go to https://glama.ai/mcp/servers, click "Add Server", paste GitHub URL

## 4. smithery.ai

- **URL:** https://smithery.ai
- **Submit method:** Smithery CLI or web dashboard
- **Status:** NOT LISTED (despite earlier belief it was registered)
- **CLI search confirmed:** `smithery mcp search "nexus-finance"` returned no results
- **How to register:**
  1. Ensure `smithery.yaml` exists in repo root (or create one)
  2. Use `npx @smithery/cli mcp publish` or register via web dashboard
  3. Alternative: Submit via https://smithery.ai dashboard after login
- **Required config (smithery.yaml):**
  ```yaml
  name: nexus-finance-mcp
  description: Finance & Research Intelligence Platform
  startCommand:
    type: http
    configSchema:
      type: object
      properties:
        url:
          type: string
          default: http://62.171.141.206/mcp
  ```
- **Action:** Create smithery.yaml, push to repo, then publish via CLI or web

## 5. pulsemcp.com

- **URL:** https://pulsemcp.com/submit
- **Submit method:** Web form (manual)
- **Status:** MANUAL NEEDED (confirmed not listed via search)
- **Required fields:**
  - Type: MCP Server
  - GitHub repository URL: `https://github.com/pollmap/nexus-finance-mcp`
- **Notes:** PulseMCP also auto-ingests from the Official MCP Registry daily, so publishing to the official registry would auto-populate here too
- **Action:** Go to https://pulsemcp.com/submit, select "MCP Server", paste GitHub URL

## 6. mcpmarket.com

- **URL:** https://mcpmarket.com/submit
- **Submit method:** Web form (manual)
- **Status:** MANUAL NEEDED
- **Required fields:**
  - Tab: MCP Server
  - GitHub URL: `https://github.com/pollmap/nexus-finance-mcp`
- **Notes:** Simple form, just needs GitHub URL. Has duplicate detection. Review process before listing.
- **Action:** Go to https://mcpmarket.com/submit, paste GitHub URL, submit

## 7. Official MCP Registry (Bonus)

- **URL:** https://registry.modelcontextprotocol.io
- **Submit method:** `mcp-publisher` CLI tool
- **Status:** NOT SUBMITTED
- **Steps:**
  1. Install: `brew install mcp-publisher` or download binary
  2. Init: `mcp-publisher init` (creates server.json)
  3. Configure server.json with namespace `io.github.pollmap/nexus-finance-mcp`
  4. Auth: `mcp-publisher login github`
  5. Publish: `mcp-publisher publish`
- **Required metadata (server.json):**
  ```json
  {
    "$schema": "...",
    "name": "io.github.pollmap/nexus-finance-mcp",
    "description": "Finance & Research Intelligence Platform -- 396 tools, 64 servers",
    "version": "8.0.0",
    "remotes": [{
      "transport": "streamable-http",
      "url": "http://62.171.141.206/mcp"
    }]
  }
  ```
- **Why important:** PulseMCP auto-ingests from this registry. This is the canonical source.

---

## Priority Order

1. **Official MCP Registry** -- Canonical source, feeds PulseMCP automatically
2. **smithery.ai** -- Largest marketplace, high visibility
3. **mcpservers.org** -- Popular directory, consider $39 premium for badge
4. **glama.ai** -- Auto-indexes, just needs GitHub URL click
5. **mcpmarket.com** -- Simple submission, just GitHub URL
6. **pulsemcp.com** -- Will auto-populate from Official Registry, but manual submit is faster

---

## Additional Directories to Consider

| Directory | URL | Notes |
|-----------|-----|-------|
| mcp.directory | https://mcp.directory | Blog-style directory |
| mcpserverfinder.com | https://www.mcpserverfinder.com | Has finance category |
| aiagentslist.com | https://aiagentslist.com/mcp-servers | 593+ servers listed |
| opentools.com | https://opentools.com/registry | Click "Submit Server" |
| playbooks.com | https://playbooks.com/mcp | Auto-indexes GitHub |

---

*Last updated: 2026-04-08*
