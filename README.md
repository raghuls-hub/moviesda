# MoviesDA KivyMD App

A KivyMD mobile app for browsing year-based movie pages, viewing details, and downloading files from a configured legal source site.

## Features

- Year selection screen
- Paginated movie grid screen
- Movie detail screen
- Redirect-aware download handler
- Configurable base URL and search query

## Setup with uv

```powershell
uv sync
```

## Run

```powershell
uv run moviesda-app
```

You can also launch the root entry point directly:

```powershell
uv run python main.py
```

## Configuration

Set these environment variables before launching the app:

- `MOVIESDA_BASE_URL`
- `MOVIESDA_SEARCH_QUERY`
- `MOVIESDA_DOWNLOAD_DIR`
- `MOVIESDA_PAGE_SIZE`

If no values are set, the app uses safe defaults and prompts for a valid source URL at runtime.

## Android packaging

The repository includes a starter `buildozer.spec` so you can package the app for Android after adjusting the package name and permissions for your target site.
