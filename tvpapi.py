from bs4 import BeautifulSoup
import requests
import re
import string
import os
from collections import OrderedDict

class TVPApi:
  def __init__(self, url, dest="downloads/", api_listing="http://www.api.v3.tvp.pl/shared/listing.php?dump=json&count&parent_id=", api_tokenizer="http://www.tvp.pl/shared/cdn/tokenizer_v2.php?object_id="):
    # http://www.tvp.pl/shared/cdn/tokenizer.php?object_id=
    # http://www.tvp.pl/shared/cdn/tokenizer_v2.php?object_id=

    self.url = url
    self.dest = dest
    self.api_listing = api_listing
    self.api_tokenizer = api_tokenizer

    # check if destination directory exists
    if not os.path.exists(self.dest):
      os.makedirs(self.dest)

  def get_series_id(self):
    url_data = requests.get(self.url).text
    url_soup = BeautifulSoup(url_data, 'html.parser')

    series_url = url_soup.find("meta",  property="og:url")["content"]
    print("Series url = " + series_url)

    self.series_id = re.findall("\/(.*?)\/", series_url)[1]
    print("Series id = " + self.series_id)

  def get_episodes_id(self):
    endpoint_resp = requests.get(self.api_listing + self.series_id)
    endpoint_json = endpoint_resp.json()

    for item in endpoint_json["items"]:
      if item["title"] == "odcinki" or item["title"] == "serie":
        self.series_episodes_id = str(item["asset_id"])
        break

    # check if series episode id was found
    # https://stackoverflow.com/questions/843277/how-do-i-check-if-a-variable-exists
    if not hasattr(self, 'series_episodes_id'):
      raise Exception('Cannot find series episodes id.')

    print("Series episodes id = " + self.series_episodes_id)

  def get_season_ids(self):
    endpoint_resp = requests.get(self.api_listing + self.series_episodes_id)
    endpoint_json = endpoint_resp.json()

    # store season ids
    self.episodes = dict()
    for item in endpoint_json["items"]:
      season = item["title"]

      season_roman = re.search("[IVXLCDM]+", season)
      if season_roman is not None:
        # season is a roman numeral, convert roman numerals
        season = str(self.roman_to_int(season_roman.group(0)))

      # season filter only number
      season = re.search("\d+", season).group(0)

      # strip leading zeros and leading and trailing spaces
      season = season.lstrip("0").strip()

      # store season id
      self.episodes[season] = {'season_id': str(item["asset_id"])}

  def get_season_episode_ids(self):
    for season, v in self.episodes.items():
      endpoint_resp = requests.get(self.api_listing + v["season_id"])
      endpoint_json = endpoint_resp.json()
      self.episodes[season]["episodes"] = list()

      for item in endpoint_json["items"]:
        if "website_title" in item:
          title = string.capwords(item["website_title"])
          if "original_title" in item:
            episode_num = item["original_title"]
          elif "web_name" in item:
            episode_num = item["web_name"]
          else:
            raise Exception('Cannot find episode title:\n' + str(item))
        else:
          raise Exception('Cannot find episode title:\n' + str(item))

        episode_num = re.search("([^\d]*)(\d*)", episode_num).group(2)
        season_num = season.strip()

        season_roman = re.search("[IVXLCDM]+", season_num)
        if season_roman is not None:
          # season is a roman numeral, convert roman numerals
          season_num = str(self.roman_to_int(season_roman.group(0)))

        # season filter only number
        season_num = re.search("\d+", season_num).group(0)

        # title format: Series - S01E001
        title = string.capwords(title) + " - S" + season_num.zfill(2) + "E" + episode_num.zfill(3)

        # store episode id and title
        episode = {'asset_id': item["asset_id"], 'title': title, 'episode': int(episode_num)}
        self.episodes[season]["episodes"].append(episode)

      # sort episodes by episode number
      self.episodes[season]["episodes"] = sorted(self.episodes[season]["episodes"], key=lambda t: int(t['episode']))

  def get_episodes(self):
    # get api data
    self.get_series_id()
    self.get_episodes_id()
    self.get_season_ids()
    self.get_season_episode_ids()
    print()

    # sort episodes by season
    self.episodes = OrderedDict(sorted(self.episodes.items(), key=lambda t: int(t[0])))

    return self.episodes

  def get_season_episodes(self, season):
    season = str(season)
    if season not in self.episodes:
      raise Exception('Cannot find season: ' + season)

    return self.episodes[season]['episodes']

  def get_season_first_episode(self, season):
    season = str(season)
    if season not in self.episodes:
      raise Exception('Cannot find season: ' + season)

    return self.episodes[season]['episodes'][0]['episode']

  def get_season_last_episode(self, season):
    season = str(season)
    if season not in self.episodes:
      raise Exception('Cannot find season: ' + season)

    return self.episodes[season]['episodes'][-1]['episode']

  def download_season(self, season, start_episode=None):
    season_episodes = self.get_season_episodes(season)
    first_episode = self.get_season_first_episode(season)
    last_episode = self.get_season_last_episode(season)

    if start_episode is not None:
      if start_episode < first_episode or start_episode > last_episode:
        raise Exception('Start episode ' + str(start_episode) + ' is out of range ' + str(first_episode) + ' to ' +  str(last_episode))

      # start downloading from start_episode
      first_episode = season_episodes[0]['episode']
      season_episodes = season_episodes[(start_episode - first_episode):]

    for item in season_episodes:
      self.download(item['asset_id'], item['title'])

  def download_episode(self, season, episode):
    season_episodes = self.get_season_episodes(season)
    first_episode = self.get_season_first_episode(season)
    episode_info = season_episodes[(episode - first_episode)]

    if episode_info is None:
      raise Exception('Cannot find episode: ' + str(episode))

    self.download(episode_info['asset_id'], episode_info['title'])

  def download(self, episode_id, title):
    endpoint_resp = requests.get(self.api_tokenizer + str(episode_id))
    endpoint_json = endpoint_resp.json()
    formats = endpoint_json["formats"]

    # filter mp4
    formats = [item for item in formats if item['mimeType'] == 'video/mp4']

    # sort by descending bitrate
    formats = sorted(endpoint_json["formats"], key=self.extract_bitrate, reverse=True)

    # pick highest bitrate
    url = formats[0]["url"]
    output_path = self.dest + str(title) + ".mp4"

    # write to file
    self.write_file(url, output_path)

  def write_file(self, url, output_path):
    # write to file
    print("Writing " + output_path)
    r = requests.get(url, stream=True)
    with open(output_path, 'wb') as f:
        for chunk in r.iter_content(100 * 2 ** 20): # 100MB chunk size
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)

  def extract_bitrate(self, json):
    try:
        return int(json['totalBitrate'])
    except KeyError:
        return 0

  def roman_to_int(self, s):
    rom_val = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    int_val = 0
    for i in range(len(s)):
      if i > 0 and rom_val[s[i]] > rom_val[s[i - 1]]:
         int_val += rom_val[s[i]] - 2 * rom_val[s[i - 1]]
      else:
         int_val += rom_val[s[i]]
    return int_val

if __name__ == '__main__':
  info = TVPApi("http://rodzinka.vod.tvp.pl/")
  episodes = info.get_episodes()

  # download entire season 1
  info.download_season(1)

  # download season 2 episode 28
  info.download_episode(2, 28)
