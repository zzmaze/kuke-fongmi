import re, json, base64
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    def __init__(self):
        super().__init__()
        self.site = "https://www.8886m.com"
        self.name = "酷客影院"
        self.header = {
            "User-Agent": self.net.getUserAgent(),
            "Referer": self.site,
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self._extend = {}
        self._home = None
        self.cats = [(1, "电影"), (2, "电视剧"), (3, "动漫"), (4, "综艺"), (67, "伦理")]
        self.areas = ["大陆", "中国大陆", "香港", "台湾", "日本", "韩国", "美国", "英国", "泰国", "德国", "法国", "印度", "俄罗斯", "西班牙", "意大利", "加拿大", "澳大利亚", "新加坡", "中国香港", "欧美"]
        self.years = [str(y) for y in range(2026, 1999, -1)]

    def getDependence(self):
        return []

    def manualVideoCheck(self):
        return False

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return u.endswith((".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".avi")) or "m3u8" in u

    def destroy(self):
        # FongMi manages its shared network client lifecycle.
        pass

    def action(self, action):
        return {}

    def _response_value(self, response, key, default=None):
        if isinstance(response, dict):
            return response.get(key, default)
        return getattr(response, key, default)

    def _request(self, url, method="GET", data=None, referer=None, binary=False):
        headers = dict(self.header)
        if referer:
            headers["Referer"] = referer
        options = {
            "method": method,
            "headers": headers,
            "timeout": 12000,
            "callTimeout": 15000,
        }
        if binary:
            options["buffer"] = 3
        if method == "POST":
            options["data"] = data or {}
            options["postType"] = "form"
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        try:
            response = self.net.req(url, options)
            code = self._response_value(response, "code", 200)
            error = self._response_value(response, "error", None)
            if error or (code is not None and int(code) >= 400):
                return None
            content = self._response_value(response, "content", "")
            return content
        except Exception:
            return None

    def _get(self, url, referer=None):
        content = self._request(url, "GET", referer=referer)
        if content is None:
            return ""
        if isinstance(content, bytes):
            return content.decode("utf-8", "ignore")
        return str(content)

    def _post(self, url, data):
        content = self._request(url, "POST", data=data)
        if content is None:
            return ""
        if isinstance(content, bytes):
            return content.decode("utf-8", "ignore")
        return str(content)

    def _u(self, u):
        if not u:
            return u
        u = u.strip()
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("http"):
            return u
        if u.startswith("/"):
            m = re.match(r"(https?://[^/]+)", self.site)
            return (m.group(1) if m else self.site) + u
        return self.site.rstrip("/") + "/" + u.lstrip("/")

    def _clean(self, s):
        if not s:
            return ""
        s = re.sub(r"<[^>]+>", "", s)
        import html as _h
        return _h.unescape(s).strip()

    def _items(self, html):
        out, seen = [], set()
        for bm in re.finditer(r"<li[^>]*>([\s\S]{0,3000}?)</li>", html):
            block = bm.group(1)
            hm = re.search(r'href="(/edu-\d+\.html)"', block)
            if not hm:
                continue
            vid = self._u(hm.group(1))
            if vid in seen:
                continue
            im = re.search(r'data-original="([^"]+)"', block)
            if not im:
                im = re.search(r"background:\s*url\(([^)]+)\)", block)
            if not im:
                continue
            nm = re.search(r'<h[34][^>]*>\s*<a[^>]*>([^<]{1,60})</a>', block)
            if nm:
                title = self._clean(nm.group(1))
            else:
                tm = re.search(r'title="([^"]+)"', block)
                title = self._clean(tm.group(1)) if tm else ""
            if not title:
                continue
            seen.add(vid)
            rm = re.search(r'<span class="pic-text[^"]*">([^<]{1,30})</span>', block)
            item = {"vod_id": vid, "vod_name": title,
                    "vod_pic": self._u(im.group(1)) if im else "",
                    "vod_remarks": rm.group(1).strip() if rm else ""}
            tm = re.search(r"类型：</span>\s*<a[^>]+href=\"/list/(\d+)\.html\"", block)
            if tm:
                item["_tid"] = int(tm.group(1))
            ym = re.search(r"年份：</span>\s*<a[^>]+href=\"/year\.php\?searchword=(\d+)\"", block)
            if ym:
                item["_year"] = ym.group(1)
            am = re.search(r"地区：</span>\s*<a[^>]+href=\"/area\.php\?searchword=([^\"]+)\"", block)
            if am:
                import urllib.parse
                item["_area"] = urllib.parse.unquote(am.group(1))
            out.append(item)
        for am in re.finditer(r'<a[^>]+href="(/edu-\d+\.html)"[^>]*>', html):
            tag = am.group(0)
            if "stui-vodlist__thumb" not in tag:
                continue
            vid = self._u(am.group(1))
            if vid in seen:
                continue
            im = re.search(r'data-original="([^"]+)"', tag)
            if not im:
                im = re.search(r"background:\s*url\(([^)]+)\)", tag)
            if not im:
                continue
            tm = re.search(r'title="([^"]+)"', tag)
            title = self._clean(tm.group(1)) if tm else ""
            if not title:
                continue
            seen.add(vid)
            seg = html[am.end():am.end() + 300]
            rm = re.search(r'<span class="pic-text[^"]*">([^<]{1,30})</span>', seg)
            remarks = rm.group(1).strip() if rm else ""
            if remarks == title:
                remarks = ""
            out.append({"vod_id": vid, "vod_name": title,
                        "vod_pic": self._u(im.group(1)),
                        "vod_remarks": remarks})
        return out

    def _pagecount(self, html, tid):
        m = re.search(r'href="/list/%d_(\d+)\.html"[^>]*>尾页' % tid, html)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass
        nums = [int(n) for n in re.findall(r'href="/list/%d_(\d+)\.html"' % tid, html)]
        if nums:
            return max(nums)
        return 1

    def _home_html(self):
        if self._home is None:
            self._home = self._get(self.site)
        return self._home or ""

    def init(self, extend=""):
        self._extend = {}
        if isinstance(extend, dict):
            self._extend = extend
        elif isinstance(extend, str) and extend.strip():
            try:
                e = json.loads(extend)
                if isinstance(e, dict):
                    self._extend = e
            except Exception:
                pass

    def homeContent(self, filter=None):
        cats = [{"type_id": str(c), "type_name": n} for c, n in self.cats]
        filters = {}
        for c, n in self.cats:
            filters[str(c)] = [
                {"key": "area", "name": "地区", "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in self.areas]},
                {"key": "year", "name": "年份", "value": [{"n": "全部", "v": ""}] + [{"n": y, "v": y} for y in self.years]},
            ]
        vod_list = self._items(self._home_html())
        return {"class": cats, "filters": filters, "list": vod_list}

    def homeVideoContent(self):
        return {"list": self._items(self._home_html())}

    def _media_list(self, tid, area, year):
        import urllib.parse
        if area:
            url = self.site + "/area.php?searchword=" + urllib.parse.quote(area)
        else:
            url = self.site + "/year.php?searchword=" + urllib.parse.quote(year)
        html = self._get(url)
        if not html:
            return []
        out = []
        for it in self._items(html):
            if it.get("_tid") is not None and it["_tid"] != tid:
                continue
            if area and year and it.get("_year") is not None and it["_year"] != year:
                continue
            it.pop("_tid", None)
            it.pop("_year", None)
            it.pop("_area", None)
            out.append(it)
        return out

    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        try:
            tid = int(tid)
        except Exception:
            tid = 1
        ext = extend if isinstance(extend, dict) else {}
        area = str(ext.get("area") or "")
        year = str(ext.get("year") or "")
        if area or year:
            if pg > 1:
                return {"list": [], "page": pg, "pagecount": 1, "limit": 26, "total": 0}
            items = self._media_list(tid, area, year)
            return {"list": items, "page": 1, "pagecount": 1, "limit": 26, "total": 0}
        if pg <= 1:
            url = self.site + "/list/%d.html" % tid
        else:
            url = self.site + "/list/%d_%d.html" % (tid, pg)
        html = self._get(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 26, "total": 0}
        items = self._items(html)
        return {"list": items, "page": pg, "pagecount": self._pagecount(html, tid), "limit": 26, "total": 0}

    def detailContent(self, ids):
        if not isinstance(ids, (list, tuple)):
            ids = [ids]
        result = []
        for video_id in ids:
            item = self._detail_one(video_id)
            records = item.get("list", []) if isinstance(item, dict) else []
            result.extend(records)
        return {"list": result}

    def _detail_one(self, ids):
        vid = ids
        if isinstance(ids, (list, tuple)):
            vid = ids[0] if ids else ""
        vid = str(vid or "").strip()
        if not vid:
            return {"list": []}
        url = vid if vid.startswith("http") else self._u(vid)
        html = self._get(url)
        if not html:
            return {"list": []}
        title = ""
        tm = re.search(r'<h1[^>]*>([^<]{1,80})</h1>', html)
        if tm:
            title = self._clean(tm.group(1))
        if not title:
            tm = re.search(r"<title>([^<]{1,80})</title>", html)
            if tm:
                title = self._clean(tm.group(1)).split("_")[0].split("《")[-1].replace("》", "").strip()
        im = re.search(r'<img[^>]+data-original="([^"]+)"', html)
        if not im:
            im = re.search(r'property="og:image" content="([^"]+)"', html)
        pic = self._u(im.group(1)) if im else ""
        desc = ""
        dm = re.search(r'"description"\s*:\s*"((?:[^"\\]|\\.){10,2000})"', html)
        if dm:
            desc = self._clean(dm.group(1).replace("\\/", "/"))
        if not desc:
            dm = re.search(r'<p class="desc[^"]*"[^>]*>([\s\S]{10,2000}?)</p>', html)
            if dm:
                desc = self._clean(dm.group(1))
        director = ""
        dm = re.search(r"导演：</span>([\s\S]{0,200}?)</p>", html)
        if dm:
            director = self._clean(dm.group(1))
        actor = ""
        am = re.search(r"主演：</span>([\s\S]{0,3000}?)</p>", html)
        if am:
            actor = ", ".join([self._clean(a) for a in re.findall(r"<a[^>]*>([^<]{1,20})</a>", am.group(1)) if self._clean(a)])
        year = ""
        ym = re.search(r"年份：</span><a[^>]*>([^<]{1,10})</a>", html)
        if ym:
            year = ym.group(1).strip()
        area = ""
        rm = re.search(r"地区：</span><a[^>]*>([^<]{1,10})</a>", html)
        if rm:
            area = rm.group(1).strip()
        remarks = ""
        pm = re.search(r'<span class="pic-text[^"]*">([^<]{1,30})</span>', html)
        if pm:
            remarks = pm.group(1).strip()
        sources = []
        tm = re.search(r'<ul class="nav nav-tabs[^>]*>([\s\S]{0,1500}?)</ul>', html)
        if tm:
            for a in re.finditer(r'href="#down(\d+)"[^>]*>([^<]{1,30})</a>', tm.group(1)):
                sources.append((int(a.group(1)) - 1, self._clean(a.group(2))))
        eps = {}
        seen_ep = set()
        for em in re.finditer(r'href="(/gov-(\d+)-(\d+)-(\d+)\.html)"[^>]*>([^<]{1,20})</a>', html):
            href, _vid, frm, _ep, name = em.group(1), em.group(2), int(em.group(3)), int(em.group(4)), self._clean(em.group(5))
            if name in ("立即播放", ""):
                continue
            if href in seen_ep:
                continue
            seen_ep.add(href)
            eps.setdefault(frm, []).append("%s$%s" % (name, self._u(href)))
        if not sources:
            sources = [(f, "线路%d" % (f + 1)) for f in sorted(eps)]
        play_from, play_url = [], []
        for frm, name in sources:
            if frm in eps and eps[frm]:
                play_from.append(name)
                play_url.append("#".join(eps[frm]))
        return {"list": [{"vod_id": vid, "vod_name": title, "vod_pic": pic,
                          "vod_actor": actor, "vod_director": director,
                          "vod_year": year, "vod_area": area,
                          "vod_remarks": remarks, "vod_content": desc,
                          "vod_play_from": "$$$".join(play_from),
                          "vod_play_url": "$$$".join(play_url)}]}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        data = {"searchword": str(key)}
        if pg > 1:
            data["page"] = str(pg)
        html = self._post(self.site + "/search.php", data)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 26, "total": 0}
        items = self._items(html)
        pc = 1
        m = re.search(r"共\s*(\d+)\s*页", html)
        if m:
            try:
                pc = int(m.group(1))
            except Exception:
                pass
        return {"list": items, "page": pg, "pagecount": pc, "limit": 26, "total": 0}

    def playerContent(self, flag, ids, vipFlags=None):
        url = ids
        if isinstance(ids, (list, tuple)):
            url = ids[0] if ids else ""
        url = str(url or "").strip()
        if not url:
            return {"parse": 0, "url": "", "header": dict(self.header)}
        if not url.startswith("http"):
            url = self._u(url)
        u = url.lower()
        if u.endswith((".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".avi", ".mp3", ".m4a")) or "m3u8" in u:
            return {"parse": 0, "url": url, "header": dict(self.header)}
        html = self._get(url, referer=self.site)
        if not html:
            return {"parse": 0, "url": "", "header": dict(self.header)}
        found = ""
        ref = url
        im = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if im:
            iframe = self._u(im.group(1))
            phtml = self._get(iframe, referer=url)
            if phtml:
                html = phtml
                ref = iframe
        m = re.search(r'id:\s*"([^"]+\.m3u8[^"]*)"', html)
        if m:
            found = m.group(1)
        if not found:
            m = re.search(r'(https?://[^\s"\'<>\\]+\.m3u8[^\s"\'<>\\]*)', html)
            if m:
                found = m.group(1)
        if not found:
            return {"parse": 0, "url": "", "header": dict(self.header)}
        found = found.strip().rstrip('";,')
        if found.startswith("//"):
            found = "https:" + found
        elif not found.startswith("http"):
            found = self._u(found)
        h = dict(self.header)
        h["Referer"] = ref
        return {"parse": 0, "url": found, "header": h}

    def proxy(self, params):
        url = params.get("url", "") if isinstance(params, dict) else ""
        if not url:
            return [403, "text/plain", b"", {}]
        headers = dict(self.header)
        try:
            response = self.net.req(url, {
                "headers": headers,
                "timeout": 15000,
                "callTimeout": 20000,
                "buffer": 3,
            })
            code = self._response_value(response, "code", 200)
            content_type = self._response_value(response, "contentType", "application/octet-stream")
            content = self._response_value(response, "content", b"")
            response_headers = self._response_value(response, "headers", {})
            if content is None:
                content = b""
            if isinstance(content, str):
                content = content.encode("utf-8")
            return [int(code or 200), content_type or "application/octet-stream", content, response_headers or {}]
        except Exception:
            return [403, "text/plain", b"", {}]
