# malexport

This is still in development, but the exporters (saving data from MAL) are done.

This uses multiple methods to extract info about my MAL (MyAnimeList) account, focused on my episode history/forum posts I've made.

I wanted to use the API whenever possible here, but the information returned by the API is so scarce, or endpoints don't really exist at all, so you can't really get a lot of info out of it. As far as I could figure out, it doesn't have a history endpoint, or any way to retrieve how many times you've rewatched a show, so this uses:

- `malexport update lists` - The `load_json` endpoint (unauthenticated) to backup my `anime`/`manga` list (by most recently updated, as thats useful in many contexts)
- Selenium (so requires your MAL Username/Password; stored locally) to:
  - `malexport update history` - Individually grab episode/chapter history data
  - `malexport update export` - Download the MAL export (the giant XML files), since those have rewatch information, and better dates
- `malexport update forum` - Uses the MAL API ([docs](https://myanimelist.net/apiconfig/references/api/v2)) to grab forum posts

The defaults here are far more on the safe side when scraping. If data fails to download you may have been flagged as a bot and may need to open MAL in your browser to solve a captcha.

For my list (which is pretty big), this takes a few days to download all of my data, and then a few minutes every few days to update it.

## Installation

Requires `python3.7+`

To install with pip, run:

    pip install git+https://github.com/seanbreckenridge/malexport.git

For your [API Info](https://myanimelist.net/apiconfig), you can use 'other' as the 'App Type', 'hobbyist' as 'Purpose of Use', and `http://localhost` as the redirect URI. This only requires a Client ID, not both a Client ID and a Secret

Since this uses selenium, that requires a `chromedriver` binary somewhere on your system. Thats typically available in package repositories, else see [here](https://gist.github.com/seanbreckenridge/709a824b8c56ea22dbf4e86a7804287d). If this isn't able to find the file, set the `MALEXPORT_CHROMEDRIVER_LOCATION` environment variable, like: `MALEXPORT_CHROMEDRIVER_LOCATION=C:\\Downloads\\chromedriver.exe malexport ...`

## Usage

### update

`malexport update all` can be run to run all the updaters or `malexport update [forum|history|lists|export]` can be run to update one of them. Each of those require you to pass a `-u malUsername`. This stores everything (except for the MAL API Client ID) on an account-by-account basis, so its possible to backup multiple accounts

For the `update lists` command, this uses `load_json`, which is what is used on modern lists as MAL. Therefore, its contents might be slightly different depending on your settings. To get the most info out of it, I'd recommend going to your [list preferences](https://myanimelist.net/editprofile.php?go=listpreferences) and enabling all of the columns so that metadata is returned

Credentials are asked for the first time they're needed, and then stored in `~/.config/malexport`. Data by default is stored in `~/.local/share/malexport`, but like lots of other things here are configurable with environment variables:

```
$ fd '.py$' -X grep 'MALEXPORT_'
malexport/common.py:REQUEST_WAIT_TIME: int = int(os.environ.get("MALEXPORT_REQUEST_WAIT_TIME", 10))
malexport/exporter/driver.py:HIDDEN_CHROMEDRIVER = bool(int(os.environ.get("MALEXPORT_CHROMEDRIVER_HIDDEN", 0)))
malexport/exporter/driver.py:CHROME_LOCATION: Optional[str] = os.environ.get("MALEXPORT_CHROMEDRIVER_LOCATION")
malexport/exporter/driver.py:TEMP_DOWNLOAD_BASE = os.environ.get("MALEXPORT_TEMPDIR", tempfile.gettempdir())
malexport/exporter/episode_history.py:TILL_SAME_LIMIT = int(os.environ.get("MALEXPORT_EPISODE_LIMIT", 15))
malexport/exporter/mal_session.py:MALEXPORT_REDIRECT_URI = os.environ.get("MALEXPORT_REDIRECT_URI", "http://localhost")
malexport/log.py:    chosen_level = level or int(os.environ.get("MALEXPORT_LOGS", DEFAULT_LEVEL))
malexport/paths.py:    default_data_dir = Path(os.environ["MALEXPORT_DIR"])
malexport/paths.py:    default_conf_dir = Path(os.environ["MALEXPORT_CFG"])
```

To show debug logs set `export MALEXPORT_LOGS=10` (uses [logging levels](https://docs.python.org/3/library/logging.html#logging-levels)).

### parse

Note: Still in development

`malexport parse xml XML_FILE` can be used to convert the information from the XML exports to JSON. Like:

```
$ malexport parse xml ./animelist.xml | jq '.entries[106]'
{
  "anime_id": 31646,
  "title": "3-gatsu no Lion",
  "media_type": "TV",
  "episodes": 22,
  "my_id": 0,
  "watched_episodes": 22,
  "start_date": "2020-07-01",
  "finish_date": "2020-08-09",
  "rated": null,
  "score": 9,
  "storage": null,
  "storage_value": 0,
  "status": "Completed",
  "comments": "",
  "times_watched": 0,
  "rewatch_value": null,
  "priority": "LOW",
  "tags": "Drama, Game, Seinen, Slice of Life, sub",
  "rewatching": false,
  "rewatching_ep": 0,
  "discuss": true,
  "sns": "default",
  "update_on_import": false
}
```
