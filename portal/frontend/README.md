# Portal Frontend (Phase UI)

This is a basic dark-themed portal interface with mock login and local mock data.

## UI components included
- Mock login overlay
- Document search with table view
- Filters: property + tenant + text query
- Property dashboard cards
- Document viewer panel
- Compliance alerts panel

## How to run locally
From repository root:

```bash
python -m http.server 8080
```

Open:

`http://127.0.0.1:8080/portal/frontend/templates/base.html`

## Notes
- This phase is UI-first and uses mock data in `static/js/app.js`.
- Existing scan pipeline is untouched.
