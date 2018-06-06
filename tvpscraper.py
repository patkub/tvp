from bs4 import BeautifulSoup
import requests
import re
import urllib.request
import shutil
import os
import filetype
from mimetypes import guess_extension

class TVPScraper:
  def __init__(self, url, dest="downloads/", quality=5):
    self.url = url
    self.dest = dest
    
    # quality can be 2 to 7
    self.quality = str(quality)

    # check destination
    if not os.path.exists(self.dest):
      os.makedirs(self.dest)

  def find_player(self):
    # find player
    url_data = requests.get(self.url).text
    url_soup = BeautifulSoup(url_data, 'html.parser')
    self.player_src = url_soup.find(id="JS-TVPlayer-Wrapper").get('data-src')
    #print("Player = " + self.player_src)
    return self.player_src

  def find_episode(self):
    # find episode url
    player_data = requests.get(self.player_src).text
    player_soup = BeautifulSoup(player_data, 'html.parser')
    episode_src = player_soup.find(id="tvplayer").get('src')
    self.episode_url = "https://vod.tvp.pl" + episode_src
    #print("Episode url = " + self.episode_url)
    return self.episode_url

  def find_episode_link(self):
    # find episode link
    episode_data = requests.get(self.episode_url).text
    episode_soup = BeautifulSoup(episode_data, 'html.parser')
    episode_script = episode_soup.find_all("script")[9].text
    self.episode_link = re.findall("src:\'(.*?)\', type: \'video/mp4\'", episode_script)[0]
    
    # replace quality
    self.episode_link = self.episode_link.replace("video-5", "video-" + self.quality)
    #print("Episode link = " + self.episode_link)
    return self.episode_link

  def parse_output_name(self):
    series = re.search("\/([^/,]+)\,", self.url).group(1)
    episode = re.search("\,(.*?)\,", self.url).group(1)
    self.out_name = series + " - " + episode + " - " + self.quality
    #print("Output name = " + self.out_name)
    return self.out_name

  def get(self):
    # download
    self.find_player()
    self.find_episode()
    episode_link = self.find_episode_link()
    output_name = self.parse_output_name()

    # determine episode file type
    mimetype = urllib.request.urlopen(episode_link).info().get_content_type()
    #print("Content-Type = " + mimetype)

    # guess episode extension
    extension = guess_extension(mimetype)
    #print("Guessed extension = " + extension)

    # combine output path
    output_path = os.path.join(self.dest, output_name + extension)

    # write to file
    print("Writing " + output_path)
    # https://stackoverflow.com/questions/7243750/download-file-from-web-in-python-3
    with urllib.request.urlopen(episode_link) as response, open(output_path, 'wb') as out_file:
      shutil.copyfileobj(response, out_file)

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
