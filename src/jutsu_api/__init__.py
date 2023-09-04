from __future__ import annotations
from typing import Self, Iterable

import requests
import re
import html
import base64
import os
from multiprocessing.pool import ThreadPool

class Utils:
  @classmethod
  def parse_anime(clazz, html:str, id:str, full:bool = False) -> Anime:
    if "<div class=\"clear berrors\">" in html:
      raise NameError("Anime with this id not found")
    pic = re.findall("background: url\('(.*?\\.jpg)'\)", html)[0]
    if full:
      na = re.findall("\\<meta itemprop=\"name\" content=\"(.*?)\"\\>", html)[0]
      orig = re.findall("\\<meta itemprop=\"alternateName\" content=\"(.*?)\"\\>", html)[0]
    else:
      na, orig = re.findall("class=\"tooltip_title_in_anime\"\\>(.*?)\\</a\\>\\<br\\>(.*?)\\</span\\>", html)[0]
    name = Name(na, id, orig)
    years = []
    ys = []
    for yy in Filter.available.years:
      y = re.findall(f"href=\"/anime/{yy.id}/\"\\>(\\d+)", html)
      if y:
        years.append(int(y[0]))
        ys.append(yy)
    genres = []
    for gg in Filter.available.genres:
      g = re.findall(f"href=\"/anime/{gg.id}/\"\\>", html)
      if g: genres.append(gg)
    types = []
    for tt in Filter.available.types:
      t = re.findall(f"href=\"/anime/{tt.id}/\"\\>", html)
      if t: types.append(tt)
    info = Filter(genres = genres, types = types, years = ys)
    if full:
      dd = re.findall("(?ms)\\<p class=\"under_video uv_rounded_bottom the_hildi\" style=\"margin-bottom: 0; margin-top: 0;\"\\>(.*?)\\</p\\>", html)
      if dd:
        d = dd[0].replace("<b>", "").replace("</b>", "").replace("<br>", "\n")
        desc = re.findall("(?ms)\\<span\\>(.*?)\\</?span", d)[0].strip()
      else:
        desc = ""

      ongoing = "<a href=\"/anime/ongoing/\"" in html
      age = int(re.findall("age_rating_(\\d+)", html)[0])

      s = html.split("<div style=\"margin-top: 40px; margin-bottom: 25px; \">")[0]
      s = s.split("<h1 class=\"header_video allanimevideo anime_padding_for_title\">")[1]
      s = re.split("(?ms)\\</div>\\s*\\<div\\>(?:\\s*\\<br\\>)?", s, 1)[1].strip()
      ss = s.split("<br>")

      seasons = []
      films = None
      for ht in ss:
        episodes = []
        e = ht.split("</h2>", 1)[1] if "</h2>" in ht else ht
        for i in re.findall(f"\\<a href=\"/({id}/.*?)\" class=\"short-btn \\w+ video the_hildi\"\\>(.*?)\\</a\\>", e):
          episodes.append(Episode(title = i[1], id = i[0]))

        if "films_title" in ht:
          ti = re.findall("\\<h2 class=\".*?the-anime-season center films_title.*?\"\\>(.*?)\\</h2\\>", ht)[0]
          films = Season(title = ti, episodes = episodes, name = None)
          pass
        else:
          if "the_invis" in ht:
            title = re.findall("\\<h2 class=\"b-b-title the-anime-season center\"( title=\".*?\")?\\>(.*?)( \\(.*?\\))?\\</h2\\>", ht)[0]
            href = re.findall(f"the_invis\"\\>\\<a href=\"/({id}/.*?)/\"", ht)[0]
            if title[0]:
              ori = title[0].split("\"")[1]
              nn = Name(id = href, name = title[1], orig = ori)
              ti = title[2][2:-1]
            else:
              nn = Name(id = href, name = None)
              ti = title[1]
            seasons.append(Season(title = ti, episodes = episodes, name = nn))
          elif "b-b-title the-anime-season center" in ht:
            title = re.findall("\\<h2 class=\"b-b-title the-anime-season center\"( title=\".*?\")?\\>(.*?)( \\(.*?\\))?\\</h2\\>", ht)[0]
            if title[0]:
              ori = title[0].split("\"")[1]
              nn = Name(id = None, name = title[1], orig = ori)
              if title[2]: ti = title[2][2:-1]
              else: ti = None
            else:
              nn = Name(id = None, name = None)
              ti = title[1]
            seasons.append(Season(title = ti, episodes = episodes, name = nn))
          else:
            seasons.append(Season(title = None, episodes = episodes, name = None))
      content = Content(seasons = seasons, films = films)

      return Anime(
        name = name,
        thumbnail = pic,
        info = info,
        years = years,
        age = age,
        description = desc,
        content = content,
        ongoing = ongoing
      )
    else:
      return Anime(
        name = name,
        thumbnail = pic,
        info = info,
        years = years
      )

  @classmethod
  def log(clazz, message:str, level:int = 0) -> None:
    if API.instance.verbosity >= level:
      print(message, file = os.sys.stderr)

class Name:
  def __init__(self, name:str|None, id:str, orig:str|None = None):
    self.name = name
    self.id = id
    self.orig = orig

  def __repr__(self) -> str:
    return f"[{self.name}]({self.id})"

class Filter:
  _cache_available = None

  @classmethod
  @property
  def available(clazz) -> Self:
    if clazz._cache_available is not None:
      return clazz._cache_available

    r = requests.get(
      "https://jut.su/anime/", headers = {
        "User-Agent": "Mozilla/5.0"
      }
    )
    i = re.findall("(?ms)\\<div class=\"anime_choose_wall\" id=\"choose_anime_cat\"\\>.*?\\<a href=\"#\"\\>ОК\\</a\\>\\</div\\>", html.unescape(r.text))[0]

    genres = []
    g = re.findall("(?ms)\\<div class=\"anime_ganres_are_here\"\\>.*?\\</div\\>\\r\\n", i)[0]
    for j in re.findall("id=\"anime_ganre_(.*?).*?href=\"/anime/(\\1)/\"\\>(.*?)\\<", g):
      genres.append(Name(j[2], j[0]))

    types = []
    g = re.findall("(?ms)\\<div class=\"anime_types_are_here\"\\>.*?\\<div class=\"anime_choose_block_years\"\\>", i)[0]
    for j in re.findall("id=\"anime_ganre_(.*?).*?/(\\1)/\"\\>(.*?)\\<", g):
      types.append(Name(j[2], j[0]))

    years = []
    for j in re.findall("id=\"anime_year_(.*?).*?/(\\1)/\"\\>(.*?)\\<", i):
      years.append(Name(j[2], j[0]))

    sorting = []
    g = re.findall("(?ms)\\<div class=\"anime_orders_are_here\"\\>.*?\\</div\\>\\r\\n", i)[0]
    for j in re.findall("href=\"/anime/(.*?)\"\\>(.*?)\\<", g):
      sorting.append(Name(j[1], j[0].strip("/")))

    clazz._cache_available = Filter(genres, types, years, sorting)
    return clazz._cache_available

  def __init__(
    self,
    genres:list[Name] = [],
    types:list[Name] = [],
    years:list[Name] = [],
    sorting:list[Name] = [],
    link:str|None = None
  ):
    if link is not None:
      ps = link.split("/")
      for p in ps:
        for g in Filter.available.genres:
          if g.id in p.split("-"):
            genres.append(g)
        else:
          for t in Filter.available.types:
            if t.id in p.split("-"):
              types.append(t)
          else:
            for y in Filter.available.years:
              if y.id in p.split("-and-"):
                years.append(y)
            else:
              for s in Filter.available.sorting:
                if s.id == p:
                  sorting.append(s)

    self.genres = [*{*genres}]
    self.types = [*{*types}]
    self.years = [*{*years}]
    self.sorting = [*{*sorting}]

  def __repr__(self) -> str:
    gt = self.genres + self.types
    g = "-".join(i.id for i in gt)
    if g: g += "/"
    y = "-and-".join(i.id for i in self.years)
    if y: y += "/"
    if len(self.sorting) > 1:
      raise ValueError("Filter with more than one sorting cannot be used as a URL")
    s = "".join(i.id for i in self.sorting)
    if s: s += "/"
    return f"{g}{y}{s}"

class API:
  instance = None

  def __init__(self, verbosity:int = 0):
    if API.instance is not None:
      raise ValueError("Only one instance of the API is possible")

    self.verbosity = verbosity
    API.instance = self

  def verbosity(self, v:int) -> None:
    self.verbosity = v

  def search(self, keyword:str = "", filter:Filter = Filter(), maxpage:int = -1) -> list[Anime]:
    t = ""
    page = 1
    while True:
      if ~maxpage:
        if page > maxpage: break
      r = requests.post(
        f"https://jut.su/anime/{filter}", headers = {
          "User-Agent": "Mozilla/5.0",
          "Content-Type": "application/x-www-form-urlencoded"
        },
        data = (f"ajax_load=yes&start_from_page={page}&show_search={keyword}&anime_of_user=").encode("utf-8")
      )
      n = html.unescape(r.text)
      if n == "empty": break
      n = re.sub("(?ms)\\<script.*\\</script\\>", "", n)
      t += n.strip()
      page += 1

    l = []
    for i in re.findall("(?ms)(\\<a href=\"/(.*?)/\"\\>.*?\\<a href=\"/\\2/\"\\>.*?\\</a\\>)", t):
      anime = Utils.parse_anime(i[0], i[1])
      l.append(anime)

    return l

  def anime(self, id:str) -> Anime:
    return Anime(id = id)

  def episode(self, id:str) -> Episode:
    return Episode(id = id)

class Anime:
  def __init__(
    self,
    name:Name|None = None,
    thumbnail:str|None = None,
    info:Filter|None = None,
    years:list[int]|None = None,
    age:int|None = None,
    description:str|None = None,
    content:Content|None = None,
    ongoing:bool|None = None,
    id:str|None = None
  ):
    if name is None and id is None:
      raise ValueError("At least one of (name:Name, id:str) must have a value")

    self._cache_name = name or Name(None, id)
    self._cache_thumbnail = thumbnail
    self._cache_info = info
    self._cache_years = years
    self._cache_age = age
    self._cache_description = description
    self._cache_content = content
    self._cache_ongoing = ongoing

    self.selector = Selector(self)

  def __repr__(self) -> str:
    return f"{self.name.name} - {self.name.orig} {self.years}:\n{self.content}"

  def download(self, quality:int|None = None, path:str = "", threads:int = 1) -> None:
    if path and path[-1] != "/": path += "/"
    n = path + self.name.name
    try: os.mkdir(n)
    except FileExistsError: pass
    n += "/"
    with open(n + "README.md", "w") as f:
      f.write(
f"""# {self.name.name}

Original name: {self.name.orig}

Description: {self.description}

Recommended age: {self.age}+

Genres: {", ".join(g.name for g in self.info.genres)}

Types: {", ".join(t.name for t in self.info.types)}

Years: {", ".join(map(str, self.years))}{" (ongoing)" if self.ongoing else ""}
"""
      )
    if threads == 1:
      for s in self.content.seasons:
        s.download(quality, path = n)
      if self.content.films is not None:
        self.content.films.download(quality, path = n)
    else:
      poolmap = []
      for s in self.content.seasons:
        s._download(quality, path = n, poolmap = poolmap)
      if self.content.films is not None:
        self.content.films.download(quality, path = n, poolmap = poolmap)
      Utils.log(f"Pool Map collection finished with final {len(poolmap)} tasks", 1)
      pool = ThreadPool(threads)
      def downloader(l:list[Episode, str]):
        e, p = l
        e.download(quality, p)
      pool.map(downloader, poolmap)

  @property
  def name(self) -> Name:
    if self._cache_name.name is None:
      self._fetch()
    return self._cache_name

  @property
  def thumbnail(self) -> str:
    if self._cache_thumbnail is None:
      self._fetch()
    return self._cache_thumbnail

  @property
  def info(self) -> Filter:
    if self._cache_info is None:
      self._fetch()
    return self._cache_info

  @property
  def years(self) -> list[int]:
    if self._cache_years is None:
      self._fetch()
    return self._cache_years

  @property
  def content(self) -> Content:
    if self._cache_content is None:
      self._fetch()
    return self._cache_content

  @property
  def age(self) -> int:
    if self._cache_age is None:
      self._fetch()
    return self._cache_age

  @property
  def ongoing(self) -> bool:
    if self._cache_ongoing is None:
      self._fetch()
    return self._cache_ongoing

  @property
  def description(self) -> str:
    if self._cache_description is None:
      self._fetch()
    return self._cache_description

  def _fetch(self) -> None:
    Utils.log("Fetching missing information for Anime", 3)
    r = requests.get(
      f"https://jut.su/{self._cache_name.id}", headers = {
        "User-Agent": "Mozilla/5.0"
      }
    )
    t = re.sub("\\<i\\>.*?\\</i\\>", "", html.unescape(r.text).split("<!-- content -->")[1])
    a = Utils.parse_anime(t, self._cache_name.id, full = True)
    self._cache_name = a.name
    self._cache_thumbnail = a._cache_thumbnail
    self._cache_info = a.info
    self._cache_years = a.years
    self._cache_content = a.content
    self._cache_age = a.age
    self._cache_description = a.description
    self._cache_ongoing = a.ongoing

class Selector:
  def __init__(
    self,
    parent:Anime
  ):
    self.parent = parent

  def select_episodes(
    self,
    quality:int|None = None,
    items:Iterable[int]|None = None
  ) -> Downloader:
    ep = []
    i = 0
    for s in self.parent.content.seasons:
      for e in s.episodes:
        if items is None or i in items:
          ep.append([e.player(quality), f"s:{i} {e.title}"])
        i += 1

    if items is not None:
      if len(ep) < len(items):
        Utils.log("Warning: Unprocessed items left in Selector", 0)

    return Downloader(items = ep)

  def select_seasons(
    self,
    quality:int|None = None,
    items:list[int]|None = None,
  ) -> Downloader:
    ep = []
    i = 0
    for s in self.parent.content.seasons:
      t = (" " + s.title) if s.title is not None else ""
      if items is None or i in items:
        for e in s.episodes:
          ep.append([e.player(quality), f"s:{i}{t}/{e.title}"])
      i += 1

    if items is not None:
      if len(ep) < len(items):
        Utils.log("Warning: Unprocessed items left in Selector", 0)

    return Downloader(items = ep)

  def select_in_seasons(
    self,
    quality:int|None = None,
    items:dict[int, Iterable[int]|None] = { }
  ) -> Downloader:
    ep = []
    for it in items:
      i = 0
      s = self.parent.content.seasons[it]
      t = (" " + s.title) if s.title is not None else ""
      for e in s.episodes:
        if items[it] is None or i in items[it]:
          ep.append([e.player(quality), f"s:{it}{t}/s:{i} {e.title}"])
        i += 1

    return Downloader(items = ep)

class Downloader:
  def __init__(self, items:list[list[Player, str]] = []):
    self.items = items

  def add(self, downloader:Downloader) -> None:
    self.items.extend(downloader.items)

  def download(self, path:str = "", threads:int = 1) -> None:
    if path and path[-1] != "/": path += "/"
    if threads == 1:
      for e, p in self.items:
        if "/" in p:
          try: os.mkdir(path + p.split("/")[0])
          except FileExistsError: pass
        e.download(local = path + p)
    else:
      pool = ThreadPool(threads)
      def downloader(l:list[Player, str]):
        e, p = l
        if "/" in p:
          try: os.mkdir(path + p.split("/")[0])
          except FileExistsError: pass
        e.download(local = path + p)
      pool.map(downloader, self.items)

class Content:
  def __init__(
    self,
    seasons:list[Season],
    films:Season|None = None
  ):
    self.seasons = seasons
    self.films = films
    l = 0
    for s in seasons:
      l += len(s.episodes)
    self.count = l

  def __repr__(self) -> str:
    return f"Seasons: {self.seasons}\nFilms: {self.films}"

class Season:
  def __init__(
    self,
    title:str|None,
    episodes:list[Episode],
    name:Name|None = None,
  ):
   self.title = title
   self.episodes = episodes
   self.name = name

  def download(
    self,
    quality:int|None = None,
    path:str = "",
    threads:int = 1
  ) -> None:

    s = self._path(path)

    if threads == 1:
      for e in self.episodes:
        e.download(quality, path = s)
    else:
      pool = ThreadPool(threads)
      def downloader(e:Episode):
        e.download(quality, path = s)
      pool.map(downloader, self.episodes)

  def _download(
    self,
    quality:int|None,
    path:str,
    poolmap:list[list[Episode, str]]
  ) -> None:
    s = self._path(path = path)

    for e in self.episodes:
      poolmap.append([e, s])

  def _path(self, path:str = "") -> str:
    if path and path[-1] != "/": path += "/"
    if self.name is not None and self.name.name is not None:
      t = self.name.name
    else:
      t = ""
    if self.title:
      n = self.title
      if t:
        n += " - "
    else:
      n = ""

    s = n + t
    if s:
      try: os.mkdir(path + s)
      except FileExistsError: pass
      s += "/"

    return path + s

  def __repr__(self) -> str:
    t = ""
    if self.title is not None:
      t = self.title
    n = ""
    if self.name is not None:
      if self.name.name is not None:
        n = self.name.name
    if n:
      t += ", "
      n += ": "
    else:
      if t:
        t += ": "
    return f"{t}{n}{self.episodes}"

class Episode:
  def __init__(
    self,
    title:str|None = None,
    name:Name|None = None,
    duration:int|None = None,
    opening:Opening|None = None,
    ending:Ending|None = None,
    players:list[Player]|None = None,
    thumbnail:str|None = None,
    preview:str|None = None,
    id:str|None = None
  ):
    if name is None and id is None:
      raise ValueError("At least one of (name:Name, id:str) must have a value")
    self._cache_title = title
    self._cache_name = name or Name(None, id)
    self._cache_duration = duration
    self._cache_opening = opening
    self._cache_ending = ending
    self._cache_players = players
    self._cache_thumbnail = thumbnail
    self._cache_preview = preview

  def __repr__(self) -> str:
    return f"{self.title}"

  def download(self, quality:int|None = None, path:str = "") -> None:
    if path and path[-1] != "/": path += "/"
    if self.name.name is not None:
      t = " - " + self.name.name
    else:
      t = ""
    n = self.title + t
    self.player(quality).download(path + n)

  @property
  def title(self) -> str:
    if self._cache_title is None:
      self._fetch()
    return self._cache_title

  @property
  def name(self) -> Name:
    if self._cache_name.name is None:
      self._fetch()
    return self._cache_name

  @property
  def duration(self) -> int:
    if self._cache_duration is None:
      self._fetch()
    return self._cache_duration

  @property
  def opening(self) -> Opening:
    if self._cache_opening is None:
      self._fetch()
    return self._cache_opening

  @property
  def ending(self) -> Ending:
    if self._cache_ending is None:
      self._fetch()
    return self._cache_ending

  @property
  def players(self) -> list[Player]:
    if self._cache_players is None:
      self._fetch()
    return self._cache_players

  def player(self, quality:int|None = None) -> Player|None:
    if quality is not None:
      for p in self.players:
        if p.quality == quality:
          return p
      return None
    else:
      q = [p.quality for p in self.players]
      return self.player(quality = max(q))

  @property
  def thumbnail(self) -> str:
    if self._cache_thumbnail is None:
      self._fetch()
    return self._cache_thumbnail

  @property
  def preview(self) -> str:
    if self._cache_preview is None:
      self._fetch()
    return self._cache_preview

  def _fetch(self) -> None:
    Utils.log("Fetching missing information for Episode", 3)
    r = requests.get(
      f"https://jut.su/{self._cache_name.id}", headers = {
        "User-Agent": "Mozilla/5.0",
      }
    )
    n = html.unescape(r.text)
    n = n.split("<!-- content -->")[1]
    n = n.split("<!--end content -->")[0]
    n = n.strip()
    if "<div class=\"clear berrors\">" in n:
      raise NameError("Episode with this id not found")

    titl = re.findall("\\<span itemprop=\"name\"\\>\\<i\\>.*?\\</i\\>(.*?)\\</span\\>", n)[0]

    if "video_plate_title" in n:
      na = re.findall("\\<h2\\>(.*?)\\</h2\\>", n)[0]
    else:
      na = None
    nn = Name(id = self._cache_name.id, name = na)

    base = re.findall("Base64.decode\\( \"(.*)\" \\)", n)[0]
    data = base64.b64decode(base).decode("utf-8")

    dur = int(re.findall("this_video_duration = (\\d+)", data)[0])

    oph = re.findall("video_music_intro = \"(.*?)\"", data)
    if oph:
      opl = oph[0]
      opi = int(re.findall("video_intro_start = (\\d+)", data)[0])
      opo = int(re.findall("video_intro_end = (\\d+)", data)[0])
      op = Opening(opi, opo, opl)
    else:
      op = None

    edh = re.findall("video_music_outro = \"(.*?)\"", data)
    if edh:
      edl = edh[0]
      edi = int(re.findall("video_outro_start = (\\d+)", data)[0])
      ed = Ending(edi, edl)
    else:
      ed = None

    thum = re.findall("preload=\"none\" poster=\"(.*?)\"", n)[0]
    prev = re.findall("previews=\"(.*?)\\|\\d+\\|\\d+\"", n)[0]

    pl = []
    for i in re.findall("\\<source src=\"(.*?)\" .*? label=\"(\\d+)p\" res=\"\\2\"", n):
      link = i[0]
      qual = int(i[1])
      pl.append(Player(qual, link))

    if self._cache_title is None:
      self._cache_title = titl
    self._cache_name = nn
    self._cache_duration = dur
    self._cache_opening = op
    self._cache_ending = ed
    self._cache_players = pl
    self._cache_thumbnail = thum
    self._cache_preview = prev

class Opening:
  def __init__(self, begin:int, end:int, link:str):
    self.begin = begin
    self.end = end
    self.link = link

class Ending:
  def __init__(self, begin:int, link:str):
    self.begin = begin
    self.link = link

class Player:
  def __init__(self, quality:int, link:str):
    self.quality = quality
    self.link = link

  def __repr__(self) -> str:
    return f"{self.link} ({self.quality}p)"

  def download(self, local:str|None = None) -> None:
    if local is None:
      local = self.link.split("?")[0].split("/")[-1]
    ending = self.link.split("?")[0].split(".")[-1]
    p = f"{local} ({self.quality}p).{ending}"
    if os.path.exists(p):
      Utils.log(f"Skipping episode, because file '{p}' exists", 1)
      return
    with requests.get(
      self.link, headers = {
        "User-Agent": "Mozilla/5.0"
      }, stream = True
    ) as r:
      Utils.log(f"Downloading episode to '{p}'...", 1)
      size = int(r.headers["Content-Length"])
      r.raise_for_status()
      with open(p, "wb") as f:
        d = 0
        for chunk in r.iter_content(chunk_size = 512 * 1024):
          f.write(chunk)
          d += len(chunk)
          if not d % 1024 * 1024 * 10:
            Utils.log(f"Progress: {100 * d // size}% with {d} bytes", 2)
