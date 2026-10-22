# Cloud Deployment Report

Platform: Azure Container Apps
Resource group: clouddeployment-rg
Commit: 34188c0
Timestamp: 2026-10-21T11:28:16Z

| Student | Frontend URL | Page | Read endpoint (via frontend proxy) | Multi-Agent (expect 403/404/405) | Result |
|---|---|---|---|---|---|
| student-1 | https://student-1-frontend-1990.mangofield-7d3790ae.australiaeast.azurecontainerapps.io | 200 | `/cards/by-id?card_id=1` 200 | 403 | PASS |
| student-2 | https://student-2-frontend-10034.mangofield-7d3790ae.australiaeast.azurecontainerapps.io | 200 | `/accounts` 200 | 404 | PASS |
| student-4 | https://student-4-frontend-21451.mangofield-7d3790ae.australiaeast.azurecontainerapps.io | 200 | `/users` 200 | 405 | PASS |
| student-5 | https://student-5-frontend-7282.mangofield-7d3790ae.australiaeast.azurecontainerapps.io | 200 | `/transactions?limit=5` 200 | 403 | PASS |

Overall: Success

AI-Mode, MCP, RAG and Multi-Agent are disabled in this deployment
(MCP_ENABLED, RAG_ENABLED, MULTI_AGENT_ENABLED = false on every backend).
