# malexport

This uses multiple methods to save your personal data from a MAL (MyAnimeList) account, focused on [anime|manga]lists/episode history and forum posts your account has made.

I wanted to use the API whenever possible here, but the information returned by the API is so scarce, or endpoints don't really exist at all, so you can't really get a lot of info out of it. As far as I could figure out, it doesn't have a history endpoint, or any way to retrieve how many times you've rewatched a show, so this uses:

- `malexport update lists` - The `load.json` endpoint (unauthenticated) to backup my `anime`/`manga` list (by most recently updated, as thats useful in many contexts)
- `malexport update api-lists` - The MAL API endpoint (authenticated) to backup my `anime`/`manga` list. This includes a lot of metadata for each entry, and also works for private lists (assuming you go through the OAuth flow with the private account logged in your browser)
- Selenium (so requires your MAL Username/Password; stored locally) to:
  - `malexport update history` - Individually grab episode/chapter history data (i.e., [this](https://i.imgur.com/2h5ZFng.png))
  - `malexport update export` - Download the MAL export (the giant XML files), since those have rewatch information, and better dates
- `malexport update forum` - Uses the MAL API ([docs](https://myanimelist.net/apiconfig/references/api/v2)) to grab forum posts
- `malexport update friends` - Uses [Jikan](https://jikan.moe/) to update your friends

The defaults here are far more on the safe side when scraping. If data fails to download you may have been flagged as a bot and may need to open MAL in your browser to solve a captcha.

For most people, this'll take a few hours to populate the initial cache, and then, and then a few minutes every few days (would recommend doing it at least once every 3 weeks, since it uses recent history to update history entries) to update it.

## Installation

Requires `python3.7+`

To install with pip, run:

    pip install git+https://github.com/seanbreckenridge/malexport.git

For your MyAnimeList [API Info](https://myanimelist.net/apiconfig), you can use 'other' as the 'App Type', 'hobbyist' as 'Purpose of Use', and `http://localhost` as the redirect URI. This only requires a Client ID, not both a Client ID and a Secret

Since this uses selenium, that requires a `chromedriver` binary somewhere on your system. Thats typically available in package repositories, else see [here](https://gist.github.com/seanbreckenridge/709a824b8c56ea22dbf4e86a7804287d). If this isn't able to find the file, set the `MALEXPORT_CHROMEDRIVER_LOCATION` environment variable, like: `MALEXPORT_CHROMEDRIVER_LOCATION=C:\\Downloads\\chromedriver.exe malexport ...`

I left some shell functions I commonly use to query my data in `malexport.sh`, to use that set the `MAL_USERNAME` variable to your account name, and then `source malexport.sh` in your shell startup. Should work on both `bash`/`zsh`

## Usage

### update

`malexport update all` can be run to run all the updaters or `malexport update [forum|history|lists|export|friends]` can be run to update one of them. Each of those require you to pass a `-u malUsername`. This stores everything (except for the MAL API Client ID) on an account-by-account basis, so its possible to backup multiple accounts

If you want to hide the chromedriver, you can run this like `MALEXPORT_CHROMEDRIVER_HIDDEN=1 malexport update ...`

For the `update lists` command, this uses the unauthenticated `load.json` endpoint, which is what is used on modern lists as MAL. Therefore, its contents might be slightly different depending on your settings. To get the most info out of it, I'd recommend going to your [list preferences](https://myanimelist.net/editprofile.php?go=listpreferences) and enabling all of the columns so that metadata is returned. Also, this assumes the [European date format](https://myanimelist.net/editprofile.php?go=listpreferences) for lists.

Credentials are asked for the first time they're needed, and then stored in `~/.config/malexport`. Data by default is stored in `~/.local/share/malexport`, but like lots of other things here are configurable with environment variables:

```
malexport/common.py:REQUEST_WAIT_TIME: int = int(os.environ.get("MALEXPORT_REQUEST_WAIT_TIME", 10))
malexport/exporter/driver.py:HIDDEN_CHROMEDRIVER = bool(int(os.environ.get("MALEXPORT_CHROMEDRIVER_HIDDEN", 0)))
malexport/exporter/driver.py:CHROME_LOCATION: Optional[str] = os.environ.get("MALEXPORT_CHROMEDRIVER_LOCATION")
malexport/exporter/driver.py:TEMP_DOWNLOAD_BASE = os.environ.get("MALEXPORT_TEMPDIR", tempfile.gettempdir())
malexport/exporter/history.py:TILL_SAME_LIMIT = int(os.environ.get("MALEXPORT_EPISODE_LIMIT", 10))
malexport/exporter/mal_session.py:MALEXPORT_REDIRECT_URI = os.environ.get("MALEXPORT_REDIRECT_URI", "http://localhost")
malexport/log.py:    chosen_level = level or int(os.environ.get("MALEXPORT_LOGS", DEFAULT_LEVEL))
malexport/parse/common.py:CUTOFF_DATE = int(os.environ.get("MALEXPORT_CUTOFF_DATE", date.today().year + 5))
malexport/paths.py:    default_data_dir = Path(os.environ["MALEXPORT_DIR"])
malexport/paths.py:    default_conf_dir = Path(os.environ["MALEXPORT_CFG"])
```

To show debug logs set `export MALEXPORT_LOGS=10` (uses [logging levels](https://docs.python.org/3/library/logging.html#logging-levels)).

### parse

The `parse` subcommand includes corresponding commands which take the saved data, clean it up a bit into easier to manipulate representations. Those each have python functions which can be imported from `malexport.parse`, or called from the CLI to produce JSON.

The most useful is probably `combine`, which combines the `xml`, `api-lists`, `history` and `lists` data.

Otherwise, this acts on the data files (Reminder that data by default is stored in `~/.local/share/malexport`):

`$ malexport parse xml ./animelist.xml | jq '.entries[106]'`

```json
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
  "tags": "",
  "rewatching": false,
  "rewatching_ep": 0,
  "discuss": true,
  "sns": "default",
  "update_on_import": false
}
```

`parse list` converts some of the status int enumerations (status/airing status) into the corresponding string values, and parses date strings like '04-09-20' to '09-04-2020':

`malexport parse list ./animelist.json | jq '.[0]'`:

```json
{
  "status": "On Hold",
  "score": 6,
  "tags": "Slice of Life",
  "rewatching": false,
  "watched_episodes": 8,
  "title": "Shiroi Suna no Aquatope",
  "episodes": 24,
  "airing_status": "Currently Airing",
  "id": 46093,
  "studios": [
    {
      "id": 132,
      "name": "P.A. Works"
    }
  ],
  "licensors": [],
  "season": {
    "year": 2021,
    "season": "Summer"
  },
  "has_episode_video": true,
  "has_promotion_video": true,
  "has_video": true,
  "video_url": "/anime/46093/Shiroi_Suna_no_Aquatope/video",
  "url": "/anime/46093/Shiroi_Suna_no_Aquatope",
  "image_path": "https://cdn.myanimelist.net/r/96x136/images/anime/1932/114952.jpg?s=12d30d08dd16eb006e02f73d9dc14a8f",
  "is_added_to_list": false,
  "media_type": "TV",
  "rating": "PG-13",
  "start_date": "2021-07-10",
  "finish_date": null,
  "air_start_date": "2021-07-09",
  "air_end_date": null,
  "days": 53,
  "storage": "",
  "priority": "Low"
}
```

If you want exact dates, I'd recommend using the `xml` export, as theres some estimation that has to done for the `list` export since the dates aren't absolute (e.g. `04-09-20` could be `2020` or `1920`

`malexport parse forum -u malUsername` extracts posts made by your user to JSON

`malexport parse history -u malUsername | jq '.[] | select(.title == "Akira")'`

```json
{
  "mal_id": 47,
  "list_type": "anime",
  "title": "Akira",
  "entries": [
    {
      "at": "2016-02-02 21:47:00",
      "number": 1
    }
  ]
}
```

'number' in this case refers to the chapter or episode number

---

As some random examples, using this from the python, or the CLI:

_Which season do I have the most completed from?_

```python
>>> Counter([a.season for a in malexport.parse.parse_list("animelist.json", malexport.parse.ListType.ANIME) if a.score is not None and a.status == "Completed" if a.season is not None]).most_common(1)
[(Season(year=2016, season='Spring'), 73)]
```

Or, you can use [`jq`](https://github.com/stedolan/jq) to mangle it into whatever you want. Heres a mess of pipes to create a graph of your `Completed` ratings, using [`termgraph`](https://github.com/mkaz/termgraph):

```
$ malexport parse list ./animelist.json | jq '.[] | select(.status == "Completed") | .score' | grep -vx 0 | sort | uniq -c | awk '{ print $2 " " $1}' | termgraph | sort -n
1 : ▇▇▇▇▇▇▇▇▇ 158.00
2 : ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ 652.00
3 : ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ 847.00
4 : ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ 791.00
5 : ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ 562.00
6 : ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ 384.00
7 : ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇ 263.00
8 : ▇▇▇▇▇▇ 103.00
9 : ▇▇ 47.00
10: ▏ 5.00
```
