from bs4 import BeautifulSoup
import requests
import re
import string
import os

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
      self.episodes[item["title"]] = {'season_id': str(item["asset_id"])}

  def get_season_episode_ids(self):
    for season, v in self.episodes.items():
      endpoint_resp = requests.get(self.api_listing + v["season_id"])
      endpoint_json = endpoint_resp.json()
      self.episodes[season]["episode_ids"] = list()

      for item in endpoint_json["items"]:
        # title format: Series - S01E001
        if "website_title" in item:
          title = string.capwords(item["website_title"])
          if "original_title" in item:
            episode_num = item["original_title"]
          elif "web_name" in item:
            episode_num = item["web_name"]
        else:
          print(item)
          raise Exception('Cannot find episode title.')

        episode_num = re.search("([^\d]*)(\d*)", episode_num).group(2)
        season_num = season.strip()

        season_roman = re.search("[IVXLCDM]+", season_num)
        if season_roman is not None:
          # season is a roman numeral, convert roman numerals
          season_num = str(self.roman_to_int(season_roman.group(0)))

        # season filter only number
        season_num = re.search("\d+", season_num).group(0)

        # store episode id and title
        title = string.capwords(title) + " - S" + season_num.zfill(2) + "E" + episode_num.zfill(3)
        episode = {'asset_id': item["asset_id"], 'title': title}
        self.episodes[season]["episode_ids"].append(episode)

  def get_episodes(self):
    # get api data
    self.get_series_id()
    self.get_episodes_id()
    self.get_season_ids()
    self.get_season_episode_ids()

    # sort
    return sorted(self.episodes.items())

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

  for item in episodes:
    episode_ids = item[1]["episode_ids"]

    for episode in episode_ids:
      info.download(episode["asset_id"], episode["title"])
