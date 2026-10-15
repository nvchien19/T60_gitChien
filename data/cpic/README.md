# CPIC recommendation snapshot

`recommendation_view_2026-10-15.json` was downloaded on 2026-10-15 from the
[official CPIC API](https://api.cpicpgx.org/v1/recommendation_view?limit=2500).
It contains 2,115 unmodified recommendation records. The importer only loads
recommendations whose drug name has one unambiguous match in the application's
drug table. CPIC guideline names and URLs remain attached to imported rows.
