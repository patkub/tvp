# tvp

> Download episodes from vod.tvp.pl

## TVPapi

Download full series from vod.tvp.pl using public api

### Example:
```python
from tvpapi import *

if __name__ == '__main__':
  info = TVPApi("http://rodzinka.vod.tvp.pl/")
  episodes = info.get_episodes()

  # download entire season 1
  info.download_season(1)

  # download season 5 starting from episode 65
  info.download_season(5, 65)

  # download season 2 episode 28
  info.download_episode(2, 28)
```

## TVPScraper

Web scraper that downloads episodes from vod.tvp.pl

### Usage:
```sh
python3 tvpscraper.py
```

### Example:
```python
from tvpscraper import *

if __name__ == '__main__':
  # list of urls to download
  urls = [
    {"url": "https://vod.tvp.pl/video/rodzinkapl,odc1,3994796", "quality": 5},
    {"url": "https://vod.tvp.pl/video/rodzinkapl,odc-221,34842411", "quality": 5},
  ]

  for u in urls:
    # download each url
    print("Downloading: " + u['url'] + " Quality: " + str(u['quality']))
    TVPScraper(url=u['url'], quality=u['quality']).get()

  print("Done!")
```
