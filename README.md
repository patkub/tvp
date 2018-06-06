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
  
  for item in episodes:
    episode_ids = item[1]["episode_ids"]
    
    for episode in episode_ids:
      info.download(episode["asset_id"], episode["title"])
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
