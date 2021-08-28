# malexport

Man. Given MALs reputation I was expecting this to be complicated, but this is far more...

I wanted to use the API whenever possible here, but the information returned by the API is so scarce, or endpoints don't really exist at all, so you can't really get a lot of info out of it. As far as I could figure out, it doesn't have a history endpoint, or any way to retrieve how many times you've rewatched a show, so this uses:

- The `load_json` endpoint (unauthenticated) to backup my `anime`/`manga` list (by most recently updated, as thats useful in many contexts)
- Selenium to:
  - Individually grab episode/chapter history data
  - Download the MAL export (the giant XML files), since those have rewatch information, and better dates
- The MAL API ([docs](https://myanimelist.net/apiconfig/references/api/v2#operation/anime_get)) to grab forum posts
- [Jikan](https://jikan.moe/) in some cases where the API doesn't provide the relevant data

I attempted to make this as minimal as possible -- saving timestamps to optimize forum posts, using the [Jikan /history](https://jikan.moe/) endpoint to find episode data to update, but the defaults here are far more on the safe side when scraping. If data fails to download you may have been flagged as a bot and may need to open MAL in your browser to solve a captcha.

For my list (which is pretty big), this takes a few days to download all of my data, and then a few minutes every few days to update it.

## Installation

Requires `python3.7+`

To install with pip, run:

    pip install malexport

---

## Usage

```
TODO: Fill this out

Usage: ...
```

For your [API Info](https://myanimelist.net/apiconfig), you can use 'other' as the 'App Type' and 'hobbyist' as 'Purpose of Use'. This only requires a Client ID, not both a Client ID and a Secret
