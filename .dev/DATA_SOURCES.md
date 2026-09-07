# Data Sources

No data source is connected yet. Milestone 3 will connect the first one (World Bank).

Planned sources and their adapter files:

| Source | Adapter file | Indicators planned | Status |
|---|---|---|---|
| World Bank | apps/api/app/data_sources/world_bank.py | GDP growth, education, debt indicators | planned |
| BIS | apps/api/app/data_sources/bis.py | Credit gaps, debt service ratios | planned |
| OECD | apps/api/app/data_sources/oecd.py | Productivity, education (PISA) | planned |
| FRED / ALFRED | apps/api/app/data_sources/fred.py | US macro series (ALFRED for vintage data) | planned |
| Eurostat | apps/api/app/data_sources/eurostat.py | EU indicators | planned |
| ECB | apps/api/app/data_sources/ecb.py | Euro area indicators | planned |
| SNB | apps/api/app/data_sources/snb.py | Swiss indicators | planned |
| UN Comtrade | apps/api/app/data_sources/comtrade.py | Trade flows | planned |

Template for each connected source (fill in when it goes to `testing`/`active`):

```
## Source name
- API base:
- Authentication:
- Endpoints used:
- Indicators retrieved:
- Countries available:
- Update frequency:
- Rate limit:
- Transformation notes:
- Last tested:
- Status: planned | testing | active | broken
```