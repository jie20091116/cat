# -*- coding: utf-8 -*-
"""
TVBox 本地 PY/JS/CAT/XBPQ/LIVE 爬虫聚合源
==============================
扫描 /py/、/js/、/cat/、/live/、/XBPQ/ 目录下的文件，聚合展示。
已完善：PY/JS/CAT/XBPQ/LIVE分别显示对应封面图片
新增：JS独立分类、JS图标、搜索匹配JS源
分类名称显示数量
"""
import os
import re
import json
import base64
from base.spider import Spider


class Spider(Spider):
    # ==========================================================================
    # 📂 【配置区】
    # ==========================================================================
    PY_DIR    = "/storage/emulated/0/tvbox/py"
    JS_DIR    = "/storage/emulated/0/tvbox/js"
    CAT_DIR   = "/storage/emulated/0/tvbox/cat"
    JAR_DIR   = "/storage/emulated/0/tvbox/jar"
    LIVE_DIR  = "/storage/emulated/0/tvbox/live"
    XBPQ_DIR  = "/storage/emulated/0/tvbox/xbpq"
    SAVE_PATH = "/storage/emulated/0/tvbox/自动加载.json"
    LOGO_PATH = "./gif/logo.gif"
    # PY、JS、CAT、XBPQ、LIVE专属封面图链接，可自行替换本地路径/网络图
    PY_ICON = "file://tvbox/icon/py.png"
    JS_ICON = "file://tvbox/icon/js.png"
    CAT_ICON = "file://tvbox/icon/cat.png"
    XBPQ_ICON = "file://tvbox/icon/xbpq.png"
    LIVE_ICON = "file://tvbox/icon/live.png"

    # JS引擎API固定值
    JS_API = "./lib/drpy2.min.js"
    # XBPQ引擎API固定值
    XBPQ_API = "csp_XBPQ"

    # 🔞 【敏感词配置】文件名/站点名包含以下关键词的，生成 JSON 时自动沉底排在最后
    SENSITIVE_KEYWORDS = ["18禁", "成人", "吃瓜", "🔞", "18+"]

    # 🔒 锁定在 sites 第 0、1 位的配置
    _LOCKED_SITES = [
       {
         "key": "自动加载",
         "name": "自动加载",
         "type": 3,
         "api": "./py/自动加载.py",
         "searchable": 1,
         "quickSearch": 1,
         "filterable": 1
       }
    ]
    _LOCKED_KEYS = {"自动加载", "Local"}

    # 🚫 【排除文件】不扫描的文件名
    EXCLUDE_FILES = {"自动加载.py"}
    
    # 🚫 【自身文件标识】用于过滤分类显示
    SELF_FILE_KEY = "自动加载_py"
    
    # 🎬 【解析接口配置】自定义解析接口列表
    PARSES = [
        {
            "name": "虾米",
            "type": 1,
            "url": "https://jx.xmflv.com/?url="
        },
        {
            "name": "盘古",
            "type": 1,
            "url": "https://www.playm3u8.cn/jiexi.php?url="
        }
    ]
    # ==========================================================================

    def __init__(self):
        super().__init__()
        self.inited = False
        self.cache = {
            "categories": [], 
            "file_index": {}, 
            "sites": [],
            "py_sites": [],
            "cat_sites": [],
            "js_sites": [],
            "xbpq_sites": [],
            "live_items": [],
            "live_files": [],
        }

    def getName(self):
        return "本地PY/JS/CAT/XBPQ/LIVE聚合源"

    def init(self, extend):
        if self.inited:
            return
        self._scan_all()
        self._save_config_json()
        self.inited = True

    # ==========================================================================
    # 🧼 【名称格式化】彻底剥离任何位置多余的 .py/.js/.json，保留 🔞
    # ==========================================================================
    def _format_site_name(self, text):
        """彻底清洗文件名主干中任意位置残留的 .py / .js / .json"""
        text = text.strip()
        
        text = re.sub(r'\.(py|js|json|txt|m3u|m3u8)', '', text, flags=re.IGNORECASE).strip()

        while text:
            if text.startswith("🔞"):
                break
            m = re.match(
                r'^[\U00010000-\U0010FFFF\u2600-\u27BF\u2300-\u23FF\u2B00-\u2BFF]',
                text
            )
            if m:
                text = text[len(m.group(0)):].strip()
            else:
                break
        return f"{text}"

    # ==========================================================================
    # 📁 【硬盘文件重命名】实地重命名文件夹内的文件
    # ==========================================================================
    def _rename_file_on_disk(self, full_path, self_path=""):
        """把硬盘上的实际文件重命名为干净的名称"""
        if not os.path.isfile(full_path):
            return full_path
        
        if self_path and os.path.abspath(full_path) == self_path:
            return full_path

        dir_name, file_name = os.path.split(full_path)
        if "." in file_name:
            name_no_ext, ext = file_name.rsplit(".", 1)
            ext = "." + ext
        else:
            name_no_ext, ext = file_name, ""

        clean_base = self._format_site_name(name_no_ext)
        new_file_name = clean_base + ext
        new_path = os.path.join(dir_name, new_file_name)

        if new_path != full_path:
            try:
                if not os.path.exists(new_path):
                    os.rename(full_path, new_path)
                    return new_path
            except Exception:
                pass
        return full_path

    # ==========================================================================
    # 🔍 【扫描核心】手动递归，不依赖 os.walk
    # ==========================================================================
    def _scan_dir(self, base_dir, ext_list, self_path=""):
        """手动递归扫描目录，自动重命名文件并返回 [(full_path, file_name_no_ext, ext), ...]"""
        results = []
        if not base_dir:
            return results
        if not os.path.exists(base_dir):
            try:
                os.makedirs(base_dir, exist_ok=True)
            except Exception:
                return results
        if not os.path.isdir(base_dir):
            return results

        try:
            entries = os.listdir(base_dir)
        except Exception:
            return results

        for entry in sorted(entries):
            full_path = os.path.join(base_dir, entry)
            if entry.startswith("."):
                continue

            if entry in self.EXCLUDE_FILES:
                continue

            if os.path.isdir(full_path):
                sub_results = self._scan_dir(full_path, ext_list, self_path)
                results.extend(sub_results)
            elif os.path.isfile(full_path):
                lower_name = entry.lower()
                matched_ext = None
                for ext in ext_list:
                    if lower_name.endswith(ext):
                        matched_ext = ext
                        break
                if matched_ext:
                    full_path = self._rename_file_on_disk(full_path, self_path)
                    new_entry = os.path.basename(full_path)
                    name_no_ext = new_entry[: -len(matched_ext)]
                    results.append((full_path, name_no_ext, matched_ext))

        return results

    # ==========================================================================
    # 📺 【live 扫描】扫描 live 目录下的 .txt 和 .m3u 文件
    # ==========================================================================
    def _scan_live_dir(self):
        """扫描 live 目录，返回 live 文件列表"""
        live_files = []
        live_items = []
        if not self.LIVE_DIR:
            return live_files, live_items
        if not os.path.exists(self.LIVE_DIR):
            try:
                os.makedirs(self.LIVE_DIR, exist_ok=True)
            except Exception:
                return live_files, live_items
        if not os.path.isdir(self.LIVE_DIR):
            return live_files, live_items

        try:
            entries = sorted(os.listdir(self.LIVE_DIR))
        except Exception:
            return live_files, live_items

        for entry in entries:
            if entry.startswith("."):
                continue
            full_path = os.path.join(self.LIVE_DIR, entry)
            if not os.path.isfile(full_path):
                continue
            
            lower_name = entry.lower()
            if lower_name.endswith(".txt") or lower_name.endswith(".m3u") or lower_name.endswith(".m3u8"):
                if "." in entry:
                    name_no_ext = entry.rsplit(".", 1)[0]
                else:
                    name_no_ext = entry
                
                live_files.append({
                    "name": name_no_ext,
                    "path": full_path,
                })
                tid = base64.b64encode(
                    ("LIVE|" + full_path).encode("utf-8")
                ).decode("utf-8")
                item = {
                    "type_id": tid,
                    "type_name": name_no_ext,
                    "_path": full_path,
                    "_ext": "live",
                    "_dir": self.LIVE_DIR,
                    "_sk": (4, name_no_ext),
                }
                live_items.append(item)
                self.cache["file_index"][tid] = {
                    "path": full_path,
                    "ext": "live",
                    "dir": self.LIVE_DIR,
                }
        return live_files, live_items

    # ==========================================================================
    # 📦 【XBPQ扫描】扫描XBPQ目录json规则文件
    # ==========================================================================
    def _scan_xbpq_dir(self, self_path=""):
        xbpq_list = []
        if not self.XBPQ_DIR:
            return xbpq_list
        if not os.path.exists(self.XBPQ_DIR):
            try:
                os.makedirs(self.XBPQ_DIR, exist_ok=True)
            except Exception:
                return xbpq_list
        files = self._scan_dir(self.XBPQ_DIR, [".json"], self_path)
        for full_path, name, ext in files:
            tid = base64.b64encode(
                ("XBPQ|" + full_path).encode("utf-8")
            ).decode("utf-8")
            item = {
                "type_id": tid,
                "type_name": name,
                "_path": full_path,
                "_ext": "xbpq",
                "_dir": self.XBPQ_DIR,
                "_sk": (3, name),
            }
            xbpq_list.append(item)
            self.cache["file_index"][tid] = {
                "path": full_path,
                "ext": "xbpq",
                "dir": self.XBPQ_DIR,
            }
        return xbpq_list

    def _scan_all(self):
        """扫描 py、js、cat、xbpq 和 live 目录"""
        sites = []
        py_sites = []
        cat_sites = []
        js_sites = []
        xbpq_sites = []
        live_items = []
        self_path = os.path.abspath(__file__) if '__file__' in dir() else ""

        # ---- 扫描 .py 文件 ----
        py_files = self._scan_dir(self.PY_DIR, [".py"], self_path)
        for full_path, name, ext in py_files:
            if self_path and os.path.abspath(full_path) == self_path:
                continue
            display_name = name
            tid = base64.b64encode(
                ("PY|" + full_path).encode("utf-8")
            ).decode("utf-8")
            site_data = {
                "type_id": tid,
                "type_name": display_name,
                "_path": full_path,
                "_ext": "py",
                "_dir": self.PY_DIR,
                "_sk": (0, name),
            }
            sites.append(site_data)
            py_sites.append(site_data)
            self.cache["file_index"][tid] = {
                "path": full_path,
                "ext": "py",
                "dir": self.PY_DIR,
            }

        # ---- 扫描 .js 文件（JS目录）新增 ----
        js_files = self._scan_dir(self.JS_DIR, [".js"], self_path)
        for full_path, name, ext in js_files:
            display_name = name
            tid = base64.b64encode(
                ("JS|" + full_path).encode("utf-8")
            ).decode("utf-8")
            site_data = {
                "type_id": tid,
                "type_name": display_name,
                "_path": full_path,
                "_ext": "js",
                "_dir": self.JS_DIR,
                "_sk": (1, name),
            }
            sites.append(site_data)
            js_sites.append(site_data)
            self.cache["file_index"][tid] = {
                "path": full_path,
                "ext": "js",
                "dir": self.JS_DIR,
            }
            
        # ---- 扫描 .js 文件（cat目录） ----
        cat_files = self._scan_dir(self.CAT_DIR, [".js"], self_path)
        for full_path, name, ext in cat_files:
            display_name = name
            tid = base64.b64encode(
                ("CAT|" + full_path).encode("utf-8")
            ).decode("utf-8")
            site_data = {
                "type_id": tid,
                "type_name": display_name,
                "_path": full_path,
                "_ext": "cat",
                "_dir": self.CAT_DIR,
                "_sk": (2, name),
            }
            sites.append(site_data)
            cat_sites.append(site_data)
            self.cache["file_index"][tid] = {
                "path": full_path,
                "ext": "cat",
                "dir": self.CAT_DIR,
            }

        # ---- 扫描 XBPQ json文件 ----
        xbpq_sites = self._scan_xbpq_dir(self_path)
        sites.extend(xbpq_sites)

        # ---- 扫描 live 文件 ----
        live_files, live_items = self._scan_live_dir()
        sites.extend(live_items)

        # 统计数量
        py_count = len(py_sites)
        cat_count = len(cat_sites)
        js_count = len(js_sites)
        xbpq_count = len(xbpq_sites)
        live_count = len(live_items)
        total_count = py_count + cat_count + js_count + xbpq_count + live_count

        # ============================================================
        # 📑 【分类构建】全部 / PY / JS / CAT / XBPQ / LIVE（带数量）
        # ============================================================
        sites.sort(key=lambda x: x["_sk"])
        py_sites.sort(key=lambda x: x["_sk"])
        js_sites.sort(key=lambda x: x["_sk"])
        cat_sites.sort(key=lambda x: x["_sk"])
        xbpq_sites.sort(key=lambda x: x["_sk"])
        live_items.sort(key=lambda x: x["_sk"])

        categories = []
        
        if sites:
            categories.append({
                "type_id": "cat_all",
                "type_name": f"全部 {total_count}",
            })
        
        if py_sites:
            categories.append({
                "type_id": "cat_py",
                "type_name": f"PY {py_count}",
            })
        
        if js_sites:
            categories.append({
                "type_id": "cat_js",
                "type_name": f"JS {js_count}",
            })
            
        if cat_sites:
            categories.append({
                "type_id": "cat_cat",
                "type_name": f"CAT {cat_count}",
            })

        if xbpq_sites:
            categories.append({
                "type_id": "cat_xbpq",
                "type_name": f"XBPQ {xbpq_count}",
            })
        
        if live_items:
            categories.append({
                "type_id": "cat_live",
                "type_name": f"LIVE {live_count}",
            })

        self.cache["categories"] = categories
        self.cache["sites"] = sites
        self.cache["py_sites"] = py_sites
        self.cache["js_sites"] = js_sites
        self.cache["cat_sites"] = cat_sites
        self.cache["xbpq_sites"] = xbpq_sites
        self.cache["live_items"] = live_items
        self.cache["live_files"] = live_files

    def _build_api(self, file_info):
        """拼接 api 相对路径"""
        f_path = file_info["path"]
        base_dir = file_info["dir"]
        try:
            rel = os.path.relpath(f_path, base_dir)
        except ValueError:
            rel = os.path.basename(f_path)
        dir_name = os.path.basename(base_dir)
        return "./" + dir_name + "/" + rel

    def _build_js_ext(self, file_info):
        """构建JS文件的ext相对路径"""
        f_path = file_info["path"]
        base_dir = file_info["dir"]
        try:
            rel = os.path.relpath(f_path, base_dir)
        except ValueError:
            rel = os.path.basename(f_path)
        dir_name = os.path.basename(base_dir)
        return "./" + dir_name + "/" + rel

    # ==========================================================================
    # 🆕 【jar 扫描】扫描 jar 目录下所有 .jar 文件，拼接 spider 值
    # ==========================================================================
    def _build_spider_value(self):
        """扫描 jar 目录，返回用分号拼接的所有 jar 相对路径"""
        jar_dir = self.JAR_DIR
        if not jar_dir or not os.path.isdir(jar_dir):
            return ""

        jar_files = []
        save_dir = os.path.dirname(self.SAVE_PATH)

        try:
            entries = sorted(os.listdir(jar_dir))
        except Exception:
            return ""

        for entry in entries:
            if entry.startswith("."):
                continue
            if entry.lower().endswith(".jar") and os.path.isfile(os.path.join(jar_dir, entry)):
                abs_jar = os.path.join(jar_dir, entry)
                try:
                    rel = os.path.relpath(abs_jar, save_dir)
                except ValueError:
                    rel = "jar/" + entry
                rel = "./" + rel.replace("\\", "/")
                if not rel.startswith("./"):
                    rel = "./" + rel.lstrip("./")
                jar_files.append(rel)

        return ";".join(jar_files)

    # ==========================================================================
    # 📺 【live 相对路径】构建 live 文件的相对路径
    # ==========================================================================
    def _build_live_url(self, file_path):
        """拼接 live 文件的相对路径"""
        save_dir = os.path.dirname(self.SAVE_PATH)
        try:
            rel = os.path.relpath(file_path, save_dir)
        except ValueError:
            rel = "live/" + os.path.basename(file_path)
        rel = "./" + rel.replace("\\", "/")
        if not rel.startswith("./"):
            rel = "./" + rel.lstrip("./")
        return rel

    def _save_config_json(self):
        """保存 TVBox config.json，包含 parses、lives 配置、JS/XBPQ标准站点结构"""
        config = {
            "logo": self.LOGO_PATH,
            "spider": self._build_spider_value(),
            "sites": [],
            "lives": [],
            "parses": self.PARSES  # 👈 添加解析接口配置
        }
        
        # ---- 构建 sites ----
        sites = self.cache.get("sites", [])
        for cat in sites:
            file_info = self.cache["file_index"].get(cat["type_id"])
            if not file_info:
                continue
            f_path = file_info["path"]
            ext = file_info["ext"]
            f_base = os.path.basename(f_path)
            if "." in f_base:
                f_base = f_base.rsplit(".", 1)[0]
            
            site_display_name = self._format_site_name(f_base)

            # JS格式：使用JS_API配置的固定值
            if ext == "js":
                js_ext_path = self._build_js_ext(file_info)
                item = {
                    "key": f_base,
                    "name": site_display_name,
                    "type": 3,
                    "api": self.JS_API,
                    "searchable": 1,
                    "quickSearch": 1,
                    "filterable": 1,
                    "ext": js_ext_path
                }
            # XBPQ格式：使用XBPQ_API配置的固定值
            elif ext == "xbpq":
                rel_ext_path = self._build_api(file_info)
                item = {
                    "key": f_base,
                    "name": site_display_name,
                    "type": 3,
                    "api": self.XBPQ_API,
                    "searchable": 1,
                    "quickSearch": 1,
                    "filterable": 1,
                    "ext": rel_ext_path
                }
            elif ext == "live":
                continue
            else:
                item = {
                    "key": f_base,
                    "name": site_display_name,
                    "_raw_name": f_base,
                    "type": 3,
                    "api": self._build_api(file_info),
                    "searchable": 1,
                    "quickSearch": 1,
                    "filterable": 1,
                }
            config["sites"].append(item)

        # ============================================================
        # 🔒 【锁定逻辑与敏感词分流沉底】
        # ============================================================
        filtered = [
            s for s in config["sites"]
            if s.get("key") not in self._LOCKED_KEYS
        ]

        normal_sites = []
        sensitive_sites = []

        for site in filtered:
            raw_name = site.pop("_raw_name", "") if "_raw_name" in site else ""
            site_name = site.get("name", "")
            if any(kw in raw_name or kw in site_name for kw in self.SENSITIVE_KEYWORDS):
                sensitive_sites.append(site)
            else:
                normal_sites.append(site)

        config["sites"] = list(self._LOCKED_SITES) + normal_sites + sensitive_sites

        # ---- 构建 lives ----
        live_files = self.cache.get("live_files", [])
        for live_file in live_files:
            live_url = self._build_live_url(live_file["path"])
            config["lives"].append({
                "name": live_file["name"],
                "type": 0,
                "url": live_url
            })

        # ---- 保存文件 ----
        save_dir = os.path.dirname(self.SAVE_PATH)
        if save_dir and not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except Exception:
                pass

        json_str = self._build_json_string(config)

        try:
            with open(self.SAVE_PATH, "w", encoding="utf-8") as fp:
                fp.write(json_str)
        except Exception:
            pass

    def _build_json_string(self, config):
        """手动构建 JSON 字符串，确保格式正确，包含 parses 配置"""
        lines = []
        lines.append("{")
        lines.append('  "logo": ' + json.dumps(config["logo"], ensure_ascii=False) + ",")
        lines.append('  "spider": ' + json.dumps(config["spider"], ensure_ascii=False) + ",")
        
        # ---- sites ----
        lines.append('  "sites": [')
        sites = config["sites"]
        for i, site in enumerate(sites):
            site_json = json.dumps(site, ensure_ascii=False, indent=4)
            site_lines = site_json.split("\n")
            site_lines[0] = "    " + site_lines[0].lstrip()
            for j in range(1, len(site_lines)):
                site_lines[j] = "    " + site_lines[j]
            site_str = "\n".join(site_lines)
            if i < len(sites) - 1:
                site_str += ","
            lines.append(site_str)
        lines.append("  ],")
        
        # ---- lives ----
        lines.append('  "lives": [')
        lives = config["lives"]
        for i, live in enumerate(lives):
            live_json = json.dumps(live, ensure_ascii=False, indent=4)
            live_lines = live_json.split("\n")
            live_lines[0] = "    " + live_lines[0].lstrip()
            for j in range(1, len(live_lines)):
                live_lines[j] = "    " + live_lines[j]
            live_str = "\n".join(live_lines)
            if i < len(lives) - 1:
                live_str += ","
            lines.append(live_str)
        lines.append("  ],")
        
        # ---- parses 👈 新增 ----
        lines.append('  "parses": [')
        parses = config.get("parses", [])
        for i, parse in enumerate(parses):
            parse_json = json.dumps(parse, ensure_ascii=False, indent=4)
            parse_lines = parse_json.split("\n")
            parse_lines[0] = "    " + parse_lines[0].lstrip()
            for j in range(1, len(parse_lines)):
                parse_lines[j] = "    " + parse_lines[j]
            parse_str = "\n".join(parse_lines)
            if i < len(parses) - 1:
                parse_str += ","
            lines.append(parse_str)
        lines.append("  ]")
        
        lines.append("}")
        return "\n".join(lines) + "\n"

    # ==========================================================================
    # 🔧 辅助
    # ==========================================================================
    def _get_file_info(self, tid):
        return self.cache["file_index"].get(tid)

    def _get_sites_by_category(self, tid):
        """根据分类 ID 获取对应的站点列表（排除自身文件）"""
        if tid == "cat_all":
            sites = self.cache.get("sites", [])
        elif tid == "cat_py":
            sites = self.cache.get("py_sites", [])
        elif tid == "cat_js":
            sites = self.cache.get("js_sites", [])
            
        elif tid == "cat_cat":
            sites = self.cache.get("cat_sites", [])

        elif tid == "cat_xbpq":
            sites = self.cache.get("xbpq_sites", [])
        elif tid == "cat_live":
            sites = self.cache.get("live_items", [])
        else:
            return [s for s in self.cache.get("sites", []) if s["type_id"] == tid]
        
        self_path = os.path.abspath(__file__) if '__file__' in dir() else ""
        if self_path:
            sites = [s for s in sites if os.path.abspath(s.get("_path", "")) != self_path]
        
        return sites

    # ==========================================================================
    # 📺 【TVBox 标准接口】
    # ==========================================================================
    def homeContent(self, filter):
        result = {
            "class": self.cache["categories"],
        }
        return result

    def homeVod(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, ext):
        """分类内容，分页，PY/Cat/JS/XBPQ/LIVE分别匹配专属封面图片"""
        if str(pg) != "1":
            return {"list": []}

        cat_sites = self._get_sites_by_category(tid)
        
        if not cat_sites:
            return {"list": []}

        result = []
        for site in cat_sites:
            file_info = self.cache["file_index"].get(site["type_id"])
            if not file_info:
                continue

            f_path = file_info["path"]
            if not os.path.exists(f_path):
                continue

            f_base = os.path.basename(f_path)
            if "." in f_base:
                f_base = f_base.rsplit(".", 1)[0]
            ext_name = file_info["ext"]

            if ext_name == "py":
                tag = "PY"
                cover_img = self.PY_ICON
            elif ext_name == "js":
                tag = "JS"
                cover_img = self.JS_ICON
            elif ext_name == "cat":
                tag = "CAT"
                cover_img = self.CAT_ICON
            elif ext_name == "xbpq":
                tag = "XBPQ"
                cover_img = self.XBPQ_ICON
            else:
                tag = "LIVE"
                cover_img = self.LIVE_ICON
            v_id = base64.b64encode(
                (tag + "|" + f_path).encode("utf-8")
            ).decode("utf-8")
            result.append({
                "vod_id": v_id,
                "vod_name": self._format_site_name(f_base),
                "vod_pic": cover_img,
                "vod_remarks": tag,
            })

        return {
            "list": result,
            "page": 1,
            "pagecount": 1,
            "limit": len(result),
            "total": len(result),
        }

    def detailContent(self, array):
        try:
            v_id_raw = str(array[0])

            if v_id_raw.startswith("cat_"):
                cat_sites = self._get_sites_by_category(v_id_raw)
                
                cat_names = {
                    "cat_all": "全部站点",
                    "cat_py": "PY",
                    "cat_js": "JS",
                    "cat_cat": "CAT",
                    "cat_xbpq": "XBPQ",
                    "cat_live": "LIVE",
                }
                cat_name = cat_names.get(v_id_raw, v_id_raw)
                
                detail = f"📁 分类: {cat_name}\n"
                detail += f"📊 包含 {len(cat_sites)} 个\n\n"
                detail += "列表:\n"
                for i, site in enumerate(cat_sites, 1):
                    f_path = site.get("_path", "")
                    f_name = os.path.basename(f_path) if f_path else "未知"
                    detail += f"  {i}. [{site['_ext'].upper()}] {f_name}\n"
                
                return {"list": [{
                    "vod_name": f"📁 分类信息 - {cat_name}",
                    "vod_pic": "",
                    "vod_play_from": "信息",
                    "vod_play_url": "",
                    "vod_content": detail,
                }]}

            v_id_padded = v_id_raw + "=" * ((4 - len(v_id_raw) % 4) % 4)
            raw = base64.b64decode(v_id_padded).decode("utf-8", errors="ignore")

            if "|" in raw:
                tag, f_path = raw.split("|", 1)
            else:
                tag, f_path = "PY", raw

            if not os.path.exists(f_path):
                return {"list": [{"vod_name": "文件不存在", "vod_content": "路径: " + f_path}]}

            f_base = os.path.basename(f_path)
            if "." in f_base:
                f_base = f_base.rsplit(".", 1)[0]
            ext_name = f_path.rsplit(".", 1)[-1] if "." in f_path else "unknown"

            file_info = self.cache["file_index"].get(v_id_raw)
            api = ""
            live_url = ""
            if file_info:
                if file_info["ext"] == "live":
                    live_url = self._build_live_url(f_path)
                elif file_info["ext"] == "js":
                    api = self.JS_API
                else:
                    api = self._build_api(file_info)
            else:
                api = f_path

            site_display_name = self._format_site_name(f_base)

            if tag == "JS":
                js_ext = self._build_js_ext(file_info) if file_info else f_path
                site_info = {
                    "key": f_base,
                    "name": site_display_name,
                    "type": 3,
                    "api": self.JS_API,
                    "searchable": 1,
                    "quickSearch": 1,
                    "filterable": 1,
                    "ext": js_ext,
                }
            elif tag == "XBPQ":
                site_info = {
                    "key": f_base,
                    "name": site_display_name,
                    "type": 3,
                    "api": self.XBPQ_API,
                    "searchable": 1,
                    "quickSearch": 1,
                    "filterable": 1,
                    "ext": api,
                }
            elif tag == "LIVE":
                site_info = {
                    "name": site_display_name,
                    "type": 0,
                    "url": live_url
                }
            else:
                site_info = {
                    "key": f_base,
                    "name": site_display_name,
                    "type": 3,
                    "searchable": 1,
                    "quickSearch": 1,
                    "filterable": 1,
                    "api": api,
                }
            info_text = json.dumps(site_info, ensure_ascii=False, indent=2)

            self._save_config_json()

            play_tip = "查看直播源$" + f_path if tag == "LIVE" else "查看配置$" + f_path
            return {"list": [{
                "vod_name": tag + " " + f_base,
                "vod_pic": "",
                "vod_play_from": "配置信息",
                "vod_play_url": play_tip,
                "vod_content": (
                    "配置已自动保存到: " + self.SAVE_PATH + "\n\n"
                    "资源类型: " + tag + "\n\n"
                    "资源配置:\n" + info_text + "\n\n"
                    "文件路径: " + f_path
                ),
            }]}
        except Exception as e:
            return {"list": [{"vod_name": "解析错误", "vod_content": str(e)}]}

    def searchContent(self, key, quick):
        """搜索结果增加JS封面图匹配"""
        res = []
        self_path = os.path.abspath(__file__) if '__file__' in dir() else ""
        
        for tid, file_info in self.cache["file_index"].items():
            f_path = file_info["path"]
            ext_name = file_info["ext"]
            f_base = os.path.basename(f_path)
            if "." in f_base:
                f_base = f_base.rsplit(".", 1)[0]
            
            if self_path and os.path.abspath(f_path) == self_path:
                continue
                
            if key.lower() in f_base.lower():
                if ext_name == "py":
                    tag = "PY"
                    cover_img = self.PY_ICON
                elif ext_name == "js":
                    tag = "JS"
                    cover_img = self.JS_ICON
                elif ext_name == "cat":
                    tag = "Cat"
                    cover_img = self.CAT_ICON
                elif ext_name == "xbpq":
                    tag = "XBPQ"
                    cover_img = self.XBPQ_ICON
                else:
                    tag = "LIVE"
                    cover_img = self.LIVE_ICON
                v_id = base64.b64encode(
                    (tag + "|" + f_path).encode("utf-8")
                ).decode("utf-8")
                remark_txt = self._build_api(file_info) if ext_name not in ["live", "js"] else (self._build_live_url(f_path) if ext_name == "live" else self._build_js_ext(file_info))
                res.append({
                    "vod_id": v_id,
                    "vod_name": tag + " " + f_base,
                    "vod_pic": cover_img,
                    "vod_remarks": remark_txt,
                })
        
        return {"list": res}

    def playerContent(self, flag, id, vipFlags):
        url = id.split("$")[-1] if "$" in id else id
        return {"url": url, "header": {}, "parse": 0}

    def destroy(self):
        return "destroy"