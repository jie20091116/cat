# -*- coding: utf-8 -*-
"""
TVBox 本地 Py/Js/HTML/XBPQ 爬虫聚合源（增强版 + 站点注入）
============================================================
在原有聚合功能基础上：
  - 增量合并：保留手工站点，仅替换自动生成的站点
  - 交互操作：扫描开关、重新扫描、清除自动站点、忽略/恢复源、撤销变更、分类开关
  - 分页支持：分类列表和搜索结果支持分页浏览
  - APP 重载：通过 WebHTV 本机管理接口自动重载并校验站点列表
  - 子文件夹后缀：根据文件所在子文件夹名称自动添加后缀标识
  - ★ 站点注入：同步写入 WebHTV 原生站点注入注册表 registry.json
"""
import os
import json
import base64
import hashlib
import shutil
import threading
import time
import urllib.parse
import urllib.request
from base.spider import Spider


def _detect_storage_root():
    candidates = []
    external = str(os.environ.get("EXTERNAL_STORAGE", "")).strip()
    if external:
        candidates.append(external)
    candidates.extend(("/sdcard", "/storage/emulated/0", os.path.expanduser("~/storage/shared")))
    seen = set()
    for candidate in candidates:
        path = os.path.abspath(os.path.expanduser(candidate))
        real = os.path.realpath(path)
        if real in seen:
            continue
        seen.add(real)
        if os.path.isdir(path):
            return real
    return os.path.abspath(external or "/sdcard")


_DETECTED_STORAGE = _detect_storage_root()


class Spider(Spider):
    # ==========================================================================
    # 📂 【配置区】
    # ==========================================================================
    PY_DIR    = "/storage/emulated/0/TV/小百合/py"
    JS_DIR    = "/storage/emulated/0/TV/小百合/js"
    HTML_DIR  = "/storage/emulated/0/TV/小百合/html"
    XBPQ_DIR  = "/storage/emulated/0/TV/小百合/XBPQ"
    JAR_DIR   = "/storage/emulated/0/TV/小百合/jar"
    SAVE_PATH = "/storage/emulated/0/TV/小百合/自动接口.json"
    LOGO_PATH = "/storage/emulated/0/TV/小百合/jar/头像.gif"

    # 增强功能配置
    SETTINGS_PATH = "/storage/emulated/0/TV/小百合/接口配置/扫描配置.json"
    BACKUP_DIR    = "/storage/emulated/0/TV/小百合/接口配置"

    # ★ 站点注入注册表路径
    REGISTRY_PATH = os.path.join(_DETECTED_STORAGE, "TV", "CustomCsp", "registry.json")
    REGISTRY_BACKUP_DIR = os.path.join(os.path.dirname(os.path.join(_DETECTED_STORAGE, "TV", "CustomCsp", "registry.json")), "backups")

    HTML_API  = "csp_Nostr"
    XBPQ_API  = "csp_XBPQ"

    # 🔒 锁定在 sites 第 0、1、2 位的配置，无论扫描结果如何始终存在
    _LOCKED_SITES = [
        {
            "key": "FishConfig",
            "name": "🍼┆设置┆中心[工具]",
            "type": 3,
            "api": "csp_FishConfig"
        },
        {
            "key": "Local",
            "name": "📁┆文件┆浏览[工具]",
            "type": 3,
            "api": "csp_Local",
            "searchable": 0,
            "changeable": 0,
            "indexs": 0,
            "style": {
                "type": "list"
            },
            "ext": "https://6800.kstore.vip/share.json"
        },
        {
            "key": "自动分类加载[工具]_py",
            "name": "自动分类加载[工具]",
            "type": 3,
            "searchable": 1,
            "quickSearch": 1,
            "filterable": 1,
            "api": "./py/工具/自动分类加载.py"
        }
    ]

    _LOCKED_KEYS = {"FishConfig", "Local", "自动分类加载[工具]_py"}

    # 增量合并前缀与分页大小
    GENERATED_KEY_PREFIX = "local_auto_"
    PAGE_SIZE = 60

    # APP 重载配置
    AUTO_RELOAD_APP     = True
    APP_PORT_START      = 9978
    APP_PORT_END        = 9998
    APP_REQUEST_TIMEOUT = 0.35

    # ★ 站点注入配置
    DEFAULT_SEARCHABLE = 1
    DEFAULT_QUICK_SEARCH = 1
    MAX_REGISTRY_BACKUPS = 1

    # 交互操作常量
    ACTION_RESCAN            = "local_source_rescan"
    ACTION_TOGGLE_SCAN       = "local_source_toggle_scan"
    ACTION_CLEAR_SITES       = "local_source_clear_sites"
    ACTION_TOGGLE_IGNORE_PFX = "local_source_toggle_ignore:"
    ACTION_TOGGLE_TYPE_PFX   = "local_source_toggle_type:"
    ACTION_RESTORE_BACKUP    = "local_source_restore_backup"
    ACTION_DELETE_BACKUPS    = "local_source_delete_backups"
    ACTION_TOGGLE_APP_RELOAD = "local_source_toggle_app_reload"

    STATUS_ID         = "__local_source_status__"
    RESCAN_ID         = "__local_source_rescan__"
    TOGGLE_SCAN_ID    = "__local_source_toggle_scan__"
    CLEAR_SITES_ID    = "__local_source_clear_sites__"
    RESTORE_BACKUP_ID = "__local_source_restore_backup__"
    DELETE_BACKUPS_ID = "__local_source_delete_backups__"
    # ==========================================================================

    def __init__(self):
        super().__init__()
        self.lock = threading.RLock()
        self.inited = False

        # 扫描开关与分类开关
        self.scan_enabled = True
        self.type_enabled = {"PY": True, "JS": True, "HTML": True, "XBPQ": True}

        # 忽略源集合（存储 identity，如 "PY|/path/to/file"）
        self.ignored_sources = set()

        # APP 重载相关
        self.auto_reload_app = self.AUTO_RELOAD_APP
        self.app_server_ports = list(range(self.APP_PORT_START, self.APP_PORT_END + 1))
        self.last_app_port = 0

        # 扫描结果缓存（扩展版）
        self.cache = {
            "categories": [],
            "file_index": {},
            "sources": [],
            "ignored": [],
            "source_index": {},
            "type_counts": {},
            "ignored_counts": {},
        }

        # 扫描状态
        self.status = {
            "scan_time": "-",
            "included": 0,
            "ignored": 0,
            "manual_sites": 0,
            "generated_sites": 0,
            "added": 0,
            "updated": 0,
            "removed": 0,
            "unchanged": 0,
            "write_state": "尚未扫描",
            "written": False,
            "app_reload_state": "-",
            # ★ 站点注入状态
            "registry_manual": 0,
            "registry_generated": 0,
            "registry_added": 0,
            "registry_removed": 0,
            "registry_state": "尚未注入",
        }

    def getName(self):
        return "本地Py/Js/HTML/XBPQ聚合源（增强版+站点注入）"

    def init(self, extend):
        with self.lock:
            if self.inited:
                return
            self._load_settings()
            self._ensure_registry_dir()
            if self.scan_enabled:
                self._scan_all()
                self._save_config_json()
                self._save_registry_json()
            self.inited = True

    # ==========================================================================
    # ⚙ 【设置持久化】
    # ==========================================================================
    def _load_settings(self):
        path = self.SETTINGS_PATH
        if not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if not isinstance(data, dict):
                return
            self.scan_enabled = bool(data.get("scan_enabled", True))
            te = data.get("type_enabled", {})
            if isinstance(te, dict):
                for t in self.type_enabled:
                    if t in te:
                        self.type_enabled[t] = bool(te[t])
            ignored = data.get("ignored_sources", [])
            if isinstance(ignored, list):
                self.ignored_sources = {str(s).strip() for s in ignored if str(s).strip()}
            self.auto_reload_app = bool(data.get("auto_reload_app", self.AUTO_RELOAD_APP))
            try:
                port = int(data.get("last_app_port", 0) or 0)
                self.last_app_port = port if self.APP_PORT_START <= port <= 65535 else 0
            except Exception:
                self.last_app_port = 0
        except Exception:
            pass

    def _save_settings(self):
        data = {
            "scan_enabled": bool(self.scan_enabled),
            "type_enabled": {t: bool(v) for t, v in self.type_enabled.items()},
            "ignored_sources": sorted(self.ignored_sources),
            "auto_reload_app": bool(self.auto_reload_app),
            "last_app_port": int(self.last_app_port or 0),
        }
        self._atomic_write_json_file(self.SETTINGS_PATH, data)

    # ==========================================================================
    # ★ 【站点注入注册表】写入 WebHTV registry.json
    # ==========================================================================
    def _ensure_registry_dir(self):
        """确保注册表所在目录存在"""
        d = os.path.dirname(self.REGISTRY_PATH)
        if d and not os.path.isdir(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception:
                pass
        d2 = self.REGISTRY_BACKUP_DIR
        if d2 and not os.path.isdir(d2):
            try:
                os.makedirs(d2, exist_ok=True)
            except Exception:
                pass

    def _load_registry(self):
        """加载现有注册表，若不存在则返回空结构"""
        path = self.REGISTRY_PATH
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                if isinstance(data, dict):
                    if "items" not in data:
                        data = self._legacy_to_items(data)
                    return data
            except Exception:
                pass
        return {"enabled": True, "insertIndex": 0, "homeKey": "", "items": []}

    def _legacy_to_items(self, data):
        """将旧格式 sites 数组转换为 items 格式"""
        items = []
        sites = data.get("sites", [])
        if isinstance(sites, list):
            for idx, site in enumerate(sites):
                if not isinstance(site, dict):
                    continue
                key = str(site.get("key", "")).strip()
                items.append({
                    "id": key or "legacy_{}".format(idx),
                    "enabled": True,
                    "kind": "webHome" if site.get("homePage") else "csp",
                    "site": site,
                })
        return {
            "enabled": bool(data.get("enabled", True)),
            "insertIndex": int(data.get("insertIndex", 0) or 0),
            "homeKey": str(data.get("homeKey", data.get("home", "")) or ""),
            "items": items,
        }

    def _registry_item_key(self, item):
        """从注册表条目中提取 key（直接取 item 的 key 字段）"""
        if not isinstance(item, dict):
            return ""
        return str(item.get("key", "")).strip()

    def _is_generated_registry_item(self, item):
        """判断是否为自动生成的注册表条目"""
        if not isinstance(item, dict):
            return False
        key = self._registry_item_key(item)
        item_id = str(item.get("id", "")).strip()
        return key.startswith(self.GENERATED_KEY_PREFIX) or item_id.startswith(self.GENERATED_KEY_PREFIX)

    def _generate_registry_items(self):
        """生成平铺格式的注册表条目，api 使用 file:// 绝对路径，HTML 使用 webHome"""
        locked_paths = set()
        for site in self._LOCKED_SITES:
            for field in ("api", "homePage", "ext"):
                val = str(site.get(field, "")).strip()
                if val.startswith("./"):
                    locked_paths.add(val)

        items = []
        for source in self.cache["sources"]:
            file_info = self.cache["file_index"].get(source["type_id"])
            if not file_info:
                continue
            f_path = file_info["path"]
            type_tag = file_info.get("type_tag", "PY")
            f_base = os.path.basename(f_path)
            if "." in f_base:
                f_base = f_base.rsplit(".", 1)[0]

            # 构建 file:// 绝对路径
            abs_path = "file://" + f_path
            sub_sfx = file_info.get("sub_sfx", "")

            # 跳过锁定路径（与自动接口.json 中的锁定站点对应的文件）
            api_for_lock = self._build_api(file_info)
            if api_for_lock in locked_paths:
                continue

            key = self.GENERATED_KEY_PREFIX + type_tag.lower() + "_" + hashlib.sha256(
                (type_tag + "|" + f_path).encode("utf-8")
            ).hexdigest()[:14]

            # ========== HTML 特殊处理：使用 webHome ==========
            if type_tag == "HTML":
                item = {
                    "quickSearch": self.DEFAULT_QUICK_SEARCH,
                    "id": key,
                    "key": key,
                    "name": f"{f_base}[网页]{sub_sfx}",
                    "kind": "webHome",          # 关键：设为 webHome
                    "webHome": True,
                    "type": 3,
                    "api": "",                  # webHome 不需要 api
                    "ext": "",
                    "jar": "",
                    "homePage": abs_path,       # 使用 homePage 指向 HTML 文件
                    "click": "",
                    "playUrl": "",
                    "hide": 0,
                    "searchable": self.DEFAULT_SEARCHABLE,
                    "changeable": 1,
                }
            else:
                # PY、JS、XBPQ 保持 csp
                item = {
                    "quickSearch": self.DEFAULT_QUICK_SEARCH,
                    "id": key,
                    "key": key,
                    "name": f"{f_base}{sub_sfx}",
                    "kind": "csp",
                    "webHome": False,
                    "type": 3,
                    "api": abs_path,
                    "ext": "",
                    "jar": "",
                    "homePage": "",
                    "click": "",
                    "playUrl": "",
                    "hide": 0,
                    "searchable": self.DEFAULT_SEARCHABLE,
                    "changeable": 1,
                }
                # XBPQ 可选特殊名称
                if type_tag == "XBPQ":
                    item["name"] = f"⁽ˣᵇᵖ⁾{f_base}{sub_sfx}"

            items.append(item)

        return items

    def _save_registry_json(self):
        """★ 核心：增量合并写入 WebHTV 站点注入注册表 registry.json"""
        new_items = self._generate_registry_items()

        registry = self._load_registry()
        old_items = registry.get("items", [])
        if not isinstance(old_items, list):
            old_items = []

        # 分离手工项和旧自动生成项
        manual_items = []
        old_auto_keys = set()
        for item in old_items:
            if not isinstance(item, dict):
                manual_items.append(item)
                continue
            if self._is_generated_registry_item(item):
                old_auto_keys.add(self._registry_item_key(item))
            else:
                manual_items.append(item)

        new_auto_keys = {self._registry_item_key(item) for item in new_items}

        self.status["registry_manual"] = len(manual_items)
        self.status["registry_generated"] = len(new_items)
        self.status["registry_added"] = len(new_auto_keys - old_auto_keys)
        self.status["registry_removed"] = len(old_auto_keys - new_auto_keys)

        # 合并：手工项 + 自动生成项
        registry["enabled"] = True
        registry.setdefault("insertIndex", 0)
        registry.setdefault("homeKey", "")
        registry["items"] = manual_items + new_items

        # 清除失效的 homeKey
        gen_keys = {self._registry_item_key(item) for item in new_items}
        home_key = str(registry.get("homeKey", "")).strip()
        if home_key.startswith(self.GENERATED_KEY_PREFIX) and home_key not in gen_keys:
            registry["homeKey"] = ""

        # 原子写入（紧凑格式）
        new_content = json.dumps(registry, ensure_ascii=False, separators=(',', ':')) + "\n"
        if os.path.isfile(self.REGISTRY_PATH):
            try:
                with open(self.REGISTRY_PATH, "r", encoding="utf-8") as fp:
                    if fp.read() == new_content:
                        self.status["registry_state"] = "注册表未变化"
                        return
            except Exception:
                pass

        # 备份
        self._create_registry_backup()

        try:
            tmp = self.REGISTRY_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fp:
                fp.write(new_content)
                fp.flush()
                os.fsync(fp.fileno())
            os.replace(tmp, self.REGISTRY_PATH)
            self.status["registry_state"] = "已写入注册表"
        except Exception as e:
            self.status["registry_state"] = "写入失败: {}".format(e)

    def _clear_registry_generated(self):
        """★ 从注册表中移除所有自动生成的条目"""
        registry = self._load_registry()
        items = registry.get("items", [])
        if not isinstance(items, list):
            return 0

        old_count = len(items)
        kept = [item for item in items if not self._is_generated_registry_item(item)]
        registry["items"] = kept

        # 清除失效的 homeKey
        gen_keys = set()
        for item in items:
            if self._is_generated_registry_item(item):
                gen_keys.add(self._registry_item_key(item))
        home_key = str(registry.get("homeKey", "")).strip()
        if home_key in gen_keys:
            registry["homeKey"] = ""

        removed = old_count - len(kept)

        self._create_registry_backup()
        try:
            tmp = self.REGISTRY_PATH + ".tmp"
            content = json.dumps(registry, ensure_ascii=False, separators=(',', ':')) + "\n"
            with open(tmp, "w", encoding="utf-8") as fp:
                fp.write(content)
                fp.flush()
                os.fsync(fp.fileno())
            os.replace(tmp, self.REGISTRY_PATH)
        except Exception:
            pass

        return removed

    def _create_registry_backup(self):
        """创建注册表备份（仅保留 1 份）"""
        if not os.path.isfile(self.REGISTRY_PATH):
            return
        try:
            os.makedirs(self.REGISTRY_BACKUP_DIR, exist_ok=True)
            bp = os.path.join(self.REGISTRY_BACKUP_DIR, "registry-latest.json")
            tmp = bp + ".tmp"
            shutil.copy2(self.REGISTRY_PATH, tmp)
            os.replace(tmp, bp)
            # 清理旧备份
            for name in os.listdir(self.REGISTRY_BACKUP_DIR):
                full = os.path.join(self.REGISTRY_BACKUP_DIR, name)
                if os.path.isfile(full) and name.startswith("registry-") and name.endswith(".json") and full != bp:
                    try:
                        os.remove(full)
                    except Exception:
                        pass
        except Exception:
            pass

    def _restore_registry_backup(self):
        """从备份恢复注册表"""
        bp = os.path.join(self.REGISTRY_BACKUP_DIR, "registry-latest.json")
        if not os.path.isfile(bp):
            return False, "暂无注册表备份"
        try:
            self._create_registry_backup()
            tmp = self.REGISTRY_PATH + ".tmp"
            shutil.copy2(bp, tmp)
            os.replace(tmp, self.REGISTRY_PATH)
            return True, "已恢复注册表备份"
        except Exception as e:
            return False, "恢复失败: {}".format(e)

    def _has_registry_backup(self):
        return os.path.isfile(os.path.join(self.REGISTRY_BACKUP_DIR, "registry-latest.json"))

    # ==========================================================================
    # 📡 【APP 重载】通过 WebHTV 本机管理接口重载配置
    # ==========================================================================
    def _reload_app_vod_config(self):
        if not self.auto_reload_app:
            return False, "App重载已关闭"

        last_error = "未发现WebHTV服务"
        ports = []
        if self.last_app_port:
            ports.append(self.last_app_port)
        ports.extend(p for p in self.app_server_ports if p not in ports)

        for port in ports:
            base = "http://127.0.0.1:{}".format(port)
            try:
                payload = self._request_json(
                    base + "/manage/configs", self.APP_REQUEST_TIMEOUT
                )
                items = payload.get("items", []) if isinstance(payload, dict) else []
                current = next(
                    (
                        item for item in items
                        if isinstance(item, dict)
                        and int(item.get("type", -1)) == 0
                        and bool(item.get("active", False))
                    ),
                    None,
                )
                if not current or not str(current.get("url", "")).strip():
                    last_error = "WebHTV未返回点播接口"
                    continue

                query = urllib.parse.urlencode(
                    {"type": 0, "url": str(current["url"]).strip()}
                )
                self._request_json(
                    base + "/manage/config/use?" + query,
                    max(1.5, self.APP_REQUEST_TIMEOUT * 4),
                )

                verified = False
                for _ in range(5):
                    try:
                        sites_payload = self._request_json(
                            base + "/manage/proxy/suggest/sites",
                            max(0.5, self.APP_REQUEST_TIMEOUT),
                        )
                        sites = sites_payload.get("sites", []) if isinstance(sites_payload, dict) else []
                        if sites:
                            verified = True
                            break
                    except Exception:
                        pass
                    time.sleep(0.12)

                self._remember_app_port(port)

                if verified:
                    return True, "重载成功"
                else:
                    return True, "已发送重载请求"

            except Exception as exc:
                last_error = str(exc)

        return False, "未连接({})".format(last_error[:20] if last_error else "无")

    def _request_json(self, url, timeout):
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "Connection": "close"},
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=timeout) as response:
            status = getattr(response, "status", response.getcode())
            raw = response.read()
        if int(status) < 200 or int(status) >= 300:
            raise ValueError("HTTP {}".format(status))
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("WebHTV返回格式无效")
        return data

    def _remember_app_port(self, port):
        if self.last_app_port == int(port):
            return
        self.last_app_port = int(port)
        try:
            self._save_settings()
        except Exception:
            pass

    # ==========================================================================
    # 💾 【备份管理】
    # ==========================================================================
    def _has_backup(self):
        return os.path.isfile(self._backup_path())

    def _backup_path(self):
        return os.path.join(self.BACKUP_DIR, "回滚备份.json")

    def _create_backup(self):
        if not os.path.isfile(self.SAVE_PATH):
            return
        try:
            os.makedirs(self.BACKUP_DIR, exist_ok=True)
            bp = self._backup_path()
            tmp = bp + ".tmp"
            shutil.copy2(self.SAVE_PATH, tmp)
            os.replace(tmp, bp)
        except Exception:
            pass

    def _restore_backup(self):
        bp = self._backup_path()
        if not os.path.isfile(bp):
            return False, "暂无可恢复的备份"
        try:
            self._create_backup()
            tmp = self.SAVE_PATH + ".tmp"
            shutil.copy2(bp, tmp)
            os.replace(tmp, self.SAVE_PATH)
            return True, "已恢复到上次备份"
        except Exception as e:
            return False, "恢复失败: {}".format(e)

    def _delete_backups(self):
        bp = self._backup_path()
        if os.path.isfile(bp):
            try:
                os.remove(bp)
                return True
            except Exception:
                pass
        return False

    # ==========================================================================
    # 🔍 【扫描核心】手动递归，不依赖 os.walk
    # ==========================================================================
    def _scan_dir(self, base_dir, ext_list):
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

            if os.path.isdir(full_path):
                sub_results = self._scan_dir(full_path, ext_list)
                results.extend(sub_results)
            elif os.path.isfile(full_path):
                lower_name = entry.lower()
                matched_ext = None
                for ext in ext_list:
                    if lower_name.endswith(ext):
                        matched_ext = ext
                        break
                if matched_ext:
                    name_no_ext = entry[: -len(matched_ext)]
                    results.append((full_path, name_no_ext, matched_ext))

        return results

    def _get_sub_sfx(self, full_path, base_dir):
        try:
            rel = os.path.relpath(full_path, base_dir)
            rel_parts = rel.split(os.sep)
            subfolder = rel_parts[0] if len(rel_parts) > 1 else ""
        except (ValueError, IndexError):
            subfolder = ""

        if not subfolder:
            return ""
        if subfolder.startswith("[") and subfolder.endswith("]"):
            return subfolder
        return f"[{subfolder}]"

    def _scan_all(self):
        sources = []
        ignored_sources = []
        self_path = os.path.abspath(__file__) if hasattr(__file__, '__file__') else ""

        scan_specs = [
            (self.PY_DIR,   [".py"],                  "PY",   0),
            (self.JS_DIR,   [".js"],                  "JS",   1),
            (self.HTML_DIR, [".html"],                "HTML", 2),
            (self.XBPQ_DIR, [".py", ".js", ".json"],  "XBPQ", 3),
        ]

        for dir_path, ext_list, type_tag, order in scan_specs:
            if not self.type_enabled.get(type_tag, True):
                continue
            files = self._scan_dir(dir_path, ext_list)
            for full_path, name, ext in files:
                if self_path and os.path.abspath(full_path) == self_path:
                    continue

                identity = type_tag + "|" + full_path
                tid = base64.b64encode(identity.encode("utf-8")).decode("utf-8")

                sub_sfx = self._get_sub_sfx(full_path, dir_path)

                if type_tag == "HTML":
                    display_name = f"{name}[网页]{sub_sfx}"
                elif type_tag == "XBPQ":
                    display_name = f"⁽ˣᵇᵖ⁾{name}{sub_sfx}"
                else:
                    display_name = f"【{type_tag}】{name}{sub_sfx}"

                source = {
                    "type_id": tid,
                    "type_name": display_name,
                    "identity": identity,
                    "_path": full_path,
                    "_ext": ext.lstrip(".") if type_tag == "XBPQ" else ext,
                    "_dir": dir_path,
                    "_type_tag": type_tag,
                    "_sk": (order, name),
                    "ignored": identity in self.ignored_sources,
                    "_sub_sfx": sub_sfx,
                }

                if source["ignored"]:
                    ignored_sources.append(source)
                else:
                    sources.append(source)

                self.cache["file_index"][tid] = {
                    "path": full_path,
                    "ext": source["_ext"],
                    "dir": dir_path,
                    "type_tag": type_tag,
                    "sub_sfx": sub_sfx,
                }

        sources.sort(key=lambda x: x["_sk"])
        ignored_sources.sort(key=lambda x: x["_sk"])

        self.cache["sources"] = sources
        self.cache["ignored"] = ignored_sources
        self.cache["source_index"] = {}
        self.cache["type_counts"] = {}
        self.cache["ignored_counts"] = {}
        for s in sources + ignored_sources:
            self.cache["source_index"][s["type_id"]] = s
            tag = s["_type_tag"]
            if s["ignored"]:
                self.cache["ignored_counts"][tag] = self.cache["ignored_counts"].get(tag, 0) + 1
            else:
                self.cache["type_counts"][tag] = self.cache["type_counts"].get(tag, 0) + 1

        self.cache["categories"] = [
            {"type_id": s["type_id"], "type_name": s["type_name"]}
            for s in sources
        ]

        self.status["included"] = len(sources)
        self.status["ignored"] = len(ignored_sources)

        all_identities = {s["identity"] for s in sources + ignored_sources}
        stale = {i for i in self.ignored_sources if i not in all_identities}
        if stale:
            self.ignored_sources -= stale
            try:
                self._save_settings()
            except Exception:
                pass

    # ==========================================================================
    # 🆕 【增量合并配置生成】
    # ==========================================================================
    def _build_api(self, file_info):
        f_path = file_info["path"]
        base_dir = file_info["dir"]
        try:
            rel = os.path.relpath(f_path, base_dir)
        except ValueError:
            rel = os.path.basename(f_path)
        dir_name = os.path.basename(base_dir)
        return "./" + dir_name + "/" + rel

    def _build_spider_value(self):
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

    def _get_locked_api_set(self):
        locked = set()
        for site in self._LOCKED_SITES:
            for field in ("api", "homePage", "ext"):
                val = str(site.get(field, "")).strip()
                if val.startswith("./"):
                    locked.add(val)
        return locked

    def _is_generated_key(self, key):
        return str(key).startswith(self.GENERATED_KEY_PREFIX)

    def _load_existing_config(self):
        if not os.path.isfile(self.SAVE_PATH):
            return None
        try:
            with open(self.SAVE_PATH, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _generate_auto_sites(self):
        locked_paths = self._get_locked_api_set()
        sites = []
        for source in self.cache["sources"]:
            file_info = self.cache["file_index"].get(source["type_id"])
            if not file_info:
                continue
            f_path = file_info["path"]
            type_tag = file_info.get("type_tag", "PY")
            f_base = os.path.basename(f_path)
            if "." in f_base:
                f_base = f_base.rsplit(".", 1)[0]

            api_path = self._build_api(file_info)
            sub_sfx = file_info.get("sub_sfx", "")

            if api_path in locked_paths:
                continue

            key = self.GENERATED_KEY_PREFIX + type_tag.lower() + "_" + hashlib.sha256(
                (type_tag + "|" + f_path).encode("utf-8")
            ).hexdigest()[:14]

            if type_tag == "HTML":
                sites.append({
                    "key": key,
                    "name": f"{f_base}[网页]{sub_sfx}",
                    "type": 3,
                    "api": self.HTML_API,
                    "homePage": api_path,
                })
            elif type_tag == "XBPQ":
                sites.append({
                    "key": key,
                    "name": f"⁽ˣᵇᵖ⁾{f_base}{sub_sfx}",
                    "type": 3,
                    "api": self.XBPQ_API,
                    "ext": api_path,
                })
            else:
                sites.append({
                    "key": key,
                    "name": f"{f_base}{sub_sfx}",
                    "type": 3,
                    "searchable": 1,
                    "quickSearch": 1,
                    "filterable": 1,
                    "api": api_path,
                })
        return sites

    def _save_config_json(self):
        new_auto_sites = self._generate_auto_sites()

        existing = self._load_existing_config()
        manual_sites = []
        old_auto_keys = set()
        if existing and isinstance(existing.get("sites"), list):
            for site in existing["sites"]:
                if not isinstance(site, dict):
                    continue
                k = site.get("key", "")
                if k in self._LOCKED_KEYS:
                    continue
                if self._is_generated_key(k):
                    old_auto_keys.add(k)
                else:
                    manual_sites.append(site)

        new_auto_keys = {s.get("key") for s in new_auto_sites}
        self.status["added"] = len(new_auto_keys - old_auto_keys)
        self.status["removed"] = len(old_auto_keys - new_auto_keys)
        self.status["unchanged"] = len(old_auto_keys & new_auto_keys)
        self.status["updated"] = 0
        self.status["manual_sites"] = len(manual_sites)
        self.status["generated_sites"] = len(new_auto_sites)

        config = {
            "logo": self.LOGO_PATH,
            "spider": self._build_spider_value(),
            "sites": list(self._LOCKED_SITES) + manual_sites + new_auto_sites,
        }

        new_content = json.dumps(config, ensure_ascii=False, indent=2)
        if existing:
            old_content = json.dumps(existing, ensure_ascii=False, indent=2)
            if new_content == old_content:
                self.status["write_state"] = "配置未变化"
                self.status["written"] = True
                self.status["scan_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                self.status["app_reload_state"] = "配置未变化"
                return

        self._create_backup()
        save_dir = os.path.dirname(self.SAVE_PATH)
        if save_dir and not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except Exception:
                pass

        try:
            tmp = self.SAVE_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fp:
                fp.write(new_content)
                fp.flush()
                os.fsync(fp.fileno())
            os.replace(tmp, self.SAVE_PATH)
            self.status["write_state"] = "已写入配置"
            self.status["written"] = True
            self.status["scan_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            self.status["write_state"] = "写入失败: {}".format(e)
            self.status["written"] = False
            self.status["app_reload_state"] = "写入失败"
            return

        ok, detail = self._reload_app_vod_config()
        self.status["app_reload_state"] = detail

    def _clear_auto_sites(self):
        existing = self._load_existing_config()
        if not existing or not isinstance(existing.get("sites"), list):
            return 0
        old_count = len(existing["sites"])
        kept = [s for s in existing["sites"]
                if isinstance(s, dict) and not self._is_generated_key(s.get("key", ""))]
        existing["sites"] = kept
        removed = old_count - len(kept)

        try:
            self._create_backup()
            content = json.dumps(existing, ensure_ascii=False, indent=2)
            tmp = self.SAVE_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fp:
                fp.write(content)
                fp.flush()
                os.fsync(fp.fileno())
            os.replace(tmp, self.SAVE_PATH)
        except Exception:
            pass
        return removed

    # ==========================================================================
    # 🔧 辅助方法
    # ==========================================================================
    def _get_file_info(self, tid):
        return self.cache["file_index"].get(tid)

    def _count_str(self):
        c = self.cache["type_counts"]
        return (
            f"共扫描到 {c.get('PY', 0)} 个PY文件, {c.get('JS', 0)} 个JS文件, "
            f"{c.get('HTML', 0)} 个HTML文件, {c.get('XBPQ', 0)} 个XBPQ文件"
        )

    def _count_jar_str(self):
        if not os.path.isdir(self.JAR_DIR):
            return "jar 目录不存在"
        count = sum(
            1 for f in os.listdir(self.JAR_DIR)
            if f.lower().endswith(".jar") and os.path.isfile(os.path.join(self.JAR_DIR, f))
        )
        return f"共扫描到 {count} 个JAR文件"

    def _page_number(self, value):
        try:
            return max(1, int(value))
        except Exception:
            return 1

    def _paged_result(self, items, page, make_vod):
        total = len(items)
        page_size = max(1, self.PAGE_SIZE)
        page_count = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(page, page_count))
        start = (page - 1) * page_size
        page_items = items[start: start + page_size]
        return {
            "page": page,
            "pagecount": page_count,
            "limit": page_size,
            "total": total,
            "list": [make_vod(item) for item in page_items],
        }

    def _source_to_vod(self, source):
        ignored = source.get("ignored", False)
        return {
            "vod_id": source["type_id"],
            "vod_name": ("⛔ " if ignored else "") + source["type_name"],
            "vod_pic": "",
            "vod_remarks": (
                f"{source['_type_tag']} · "
                + ("已忽略·点击恢复" if ignored else "点击忽略")
            ),
            "action": self.ACTION_TOGGLE_IGNORE_PFX + source["type_id"],
        }

    def _atomic_write_json_file(self, path, data):
        directory = os.path.dirname(path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)
        tmp = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
                fp.flush()
                os.fsync(fp.fileno())
            os.replace(tmp, path)
        except Exception:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass

    # ==========================================================================
    # 📺 【TVBox 标准接口】
    # ==========================================================================
    def homeContent(self, filter):
        classes = [
            {"type_id": "all", "type_name": f"全部 ({len(self.cache['sources'])})"}
        ]
        for tag in ("PY", "JS", "XBPQ", "HTML"):
            count = self.cache["type_counts"].get(tag, 0)
            if count:
                classes.append({"type_id": "type:" + tag, "type_name": f"{tag} ({count})"})
        if self.cache["ignored"]:
            classes.append({"type_id": "ignored", "type_name": f"忽略 ({len(self.cache['ignored'])})"})
        classes.append({"type_id": "scan_settings", "type_name": "扫描配置"})
        if self._has_backup():
            classes.append({"type_id": "backups", "type_name": "历史备份"})
        if self._has_registry_backup():
            classes.append({"type_id": "registry_backups", "type_name": "注册表备份"})
        return {"class": classes, "list": self._home_items()}

    def homeVod(self):
        info = self._count_str() + " | " + self._count_jar_str()
        items = self._home_items()
        items.insert(0, {
            "vod_id": "__debug__",
            "vod_name": info,
            "vod_pic": "",
            "vod_remarks": "统计",
        })
        return {"list": items}

    def _home_items(self):
        if not self.scan_enabled:
            status_name = "自动扫描已关闭"
        elif self.status["written"]:
            status_name = "站点已合并"
        else:
            status_name = "站点未合并"

        remarks = f"{self.status['included']}个源·{self.status['write_state']}"
        app_state = self.status.get("app_reload_state", "")
        if app_state and app_state != "-":
            remarks += f"·App:{app_state}"
        reg_state = self.status.get("registry_state", "")
        if reg_state and reg_state != "尚未注入":
            remarks += f"·注入:{reg_state}"

        items = [
            {
                "vod_id": self.STATUS_ID,
                "vod_name": status_name,
                "vod_pic": "",
                "vod_remarks": remarks,
            },
            {
                "vod_id": self.TOGGLE_SCAN_ID,
                "vod_name": "扫描开关：{}".format("开" if self.scan_enabled else "关"),
                "vod_pic": "",
                "vod_remarks": "点击切换",
                "action": self.ACTION_TOGGLE_SCAN,
            },
            {
                "vod_id": self.RESCAN_ID,
                "vod_name": "一键扫描加载",
                "vod_pic": "",
                "vod_remarks": "扫描·写入·注入·重载App",
                "action": self.ACTION_RESCAN,
            },
            {
                "vod_id": self.CLEAR_SITES_ID,
                "vod_name": "清除自动站点",
                "vod_pic": "",
                "vod_remarks": "保留手工项+清除注册表",
                "action": self.ACTION_CLEAR_SITES,
            },
        ]
        if self._has_backup() or self._has_registry_backup():
            items.append({
                "vod_id": self.RESTORE_BACKUP_ID,
                "vod_name": "撤销上次变更",
                "vod_pic": "",
                "vod_remarks": "恢复配置+注册表备份",
                "action": self.ACTION_RESTORE_BACKUP,
            })
            items.append({
                "vod_id": self.DELETE_BACKUPS_ID,
                "vod_name": "删除历史备份",
                "vod_pic": "",
                "vod_remarks": "删除所有备份",
                "action": self.ACTION_DELETE_BACKUPS,
            })
        return items

    def categoryContent(self, tid, pg, filter, ext):
        page = self._page_number(pg)

        if tid == "all":
            return self._paged_result(self.cache["sources"], page, self._source_to_vod)

        if str(tid).startswith("type:"):
            source_type = str(tid).split(":", 1)[1].upper()
            items = [s for s in self.cache["sources"] if s["_type_tag"] == source_type]
            return self._paged_result(items, page, self._source_to_vod)

        if tid == "ignored":
            return self._paged_result(self.cache["ignored"], page, self._source_to_vod)

        if tid == "scan_settings":
            items = self._scan_setting_items()
            return self._paged_result(items, page, lambda s: s)

        if tid == "backups":
            items = self._backup_items()
            return self._paged_result(items, page, lambda s: s)

        if tid == "registry_backups":
            items = self._registry_backup_items()
            return self._paged_result(items, page, lambda s: s)

        return self._category_content_single(tid)

    def _category_content_single(self, tid):
        file_info = self._get_file_info(tid)
        if not file_info:
            return {"list": []}
        f_path = file_info["path"]
        if not os.path.exists(f_path):
            return {"list": []}

        f_base = os.path.basename(f_path)
        if "." in f_base:
            f_base = f_base.rsplit(".", 1)[0]
        ext_name = file_info["ext"]
        type_tag = file_info.get("type_tag", "PY")
        sub_sfx = file_info.get("sub_sfx", "")

        v_id = base64.b64encode(
            (type_tag + "|" + f_path).encode("utf-8")
        ).decode("utf-8")

        if type_tag == "HTML":
            vod_name = f"{f_base}[网页]{sub_sfx}"
            vod_remarks = "[网页]"
        elif type_tag == "XBPQ":
            vod_name = f"⁽ˣᵇᵖ⁾{f_base}{sub_sfx}"
            vod_remarks = "[XBPQ]"
        else:
            vod_name = f"{f_base}{sub_sfx}"
            vod_remarks = "[" + ext_name.upper() + "]"

        return {
            "page": 1, "pagecount": 1, "limit": 1, "total": 1,
            "list": [{
                "vod_id": v_id,
                "vod_name": vod_name,
                "vod_pic": "",
                "vod_remarks": vod_remarks,
            }]
        }

    def _scan_setting_items(self):
        items = []
        type_labels = {"PY": "PY源", "JS": "JS源", "XBPQ": "XBPQ源", "HTML": "HTML源"}
        for tag in ("PY", "JS", "XBPQ", "HTML"):
            enabled = self.type_enabled.get(tag, True)
            items.append({
                "vod_id": f"setting_type_{tag.lower()}",
                "vod_name": f"{'✅' if enabled else '⬜'} {type_labels[tag]}",
                "vod_pic": "",
                "vod_remarks": "开" if enabled else "关",
                "action": self.ACTION_TOGGLE_TYPE_PFX + tag,
            })
        reload_on = self.auto_reload_app
        port_info = f"{self.APP_PORT_START}-{self.APP_PORT_END}"
        last_port = str(self.last_app_port) if self.last_app_port else ""
        remarks = ("开" if reload_on else "关") + f"·{port_info}"
        if last_port:
            remarks += f"·上次{last_port}"
        items.append({
            "vod_id": "setting_app_reload",
            "vod_name": f"{'✅' if reload_on else '⬜'} 重载App",
            "vod_pic": "",
            "vod_remarks": remarks,
            "action": self.ACTION_TOGGLE_APP_RELOAD,
        })
        return items

    def _backup_items(self):
        items = []
        bp = self._backup_path()
        if os.path.isfile(bp):
            try:
                modified = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(os.path.getmtime(bp))
                )
                items.append({
                    "vod_id": "backup_latest",
                    "vod_name": f"恢复配置 {modified}",
                    "vod_pic": "",
                    "vod_remarks": "点击恢复此备份",
                    "action": self.ACTION_RESTORE_BACKUP,
                })
            except Exception:
                pass
        items.append({
            "vod_id": "delete_backups",
            "vod_name": "删除历史备份",
            "vod_pic": "",
            "vod_remarks": "删除所有备份",
            "action": self.ACTION_DELETE_BACKUPS,
        })
        return items

    def _registry_backup_items(self):
        items = []
        bp = os.path.join(self.REGISTRY_BACKUP_DIR, "registry-latest.json")
        if os.path.isfile(bp):
            try:
                modified = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(os.path.getmtime(bp))
                )
                try:
                    with open(bp, "r", encoding="utf-8") as fp:
                        reg = json.load(fp)
                    count = len(reg.get("items", []))
                except Exception:
                    count = "?"
                items.append({
                    "vod_id": "registry_backup_latest",
                    "vod_name": f"恢复注册表 {modified}",
                    "vod_pic": "",
                    "vod_remarks": f"{count} 个条目",
                    "action": self.ACTION_RESTORE_BACKUP,
                })
            except Exception:
                pass
        return items

    def detailContent(self, array):
        try:
            v_id_raw = str(array[0]) if isinstance(array, (list, tuple)) and array else str(array or "")

            if v_id_raw in ("__debug__", self.STATUS_ID):
                return {"list": [self._status_detail()]}

            v_id_padded = v_id_raw + "=" * ((4 - len(v_id_raw) % 4) % 4)
            raw = base64.b64decode(v_id_padded).decode("utf-8", errors="ignore")

            if "|" in raw:
                type_tag, f_path = raw.split("|", 1)
            else:
                type_tag, f_path = "PY", raw

            if not os.path.exists(f_path):
                return {"list": [{"vod_name": "文件不存在", "vod_content": "路径: " + f_path}]}

            f_base = os.path.basename(f_path)
            if "." in f_base:
                f_base = f_base.rsplit(".", 1)[0]
            ext_name = f_path.rsplit(".", 1)[-1] if "." in f_path else "unknown"

            file_info = self.cache["file_index"].get(v_id_raw)
            api_path = self._build_api(file_info) if file_info else f_path
            sub_sfx = file_info.get("sub_sfx", "") if file_info else ""

            if type_tag == "HTML":
                site_info = {
                    "key": f_base, "name": f"{f_base}[网页]{sub_sfx}", "type": 3,
                    "api": self.HTML_API, "homePage": api_path,
                }
                display_name = f"{f_base}[网页]{sub_sfx}"
            elif type_tag == "XBPQ":
                site_info = {
                    "key": f_base, "name": f"⁽ˣᵇᵖ⁾{f_base}{sub_sfx}", "type": 3,
                    "api": self.XBPQ_API, "ext": api_path,
                }
                display_name = f"⁽ˣᵇᵖ⁾{f_base}{sub_sfx}"
            else:
                site_info = {
                    "key": f_base + "_" + ext_name, "name": f"{f_base}{sub_sfx}", "type": 3,
                    "searchable": 1, "quickSearch": 1, "filterable": 1, "api": api_path,
                }
                display_name = "[" + ext_name.upper() + "] " + f_base + sub_sfx

            info_text = json.dumps(site_info, ensure_ascii=False, indent=2)

            return {"list": [{
                "vod_name": display_name,
                "vod_pic": "",
                "vod_play_from": "配置信息",
                "vod_play_url": "查看配置$" + f_path,
                "vod_content": (
                    "配置文件: " + self.SAVE_PATH + "\n\n"
                    "★ 注册表: " + self.REGISTRY_PATH + "\n\n"
                    "站点类型: " + type_tag + " | 后缀: ." + ext_name + "\n\n"
                    "站点配置:\n" + info_text + "\n\n"
                    "文件路径: " + f_path
                ),
            }]}
        except Exception as e:
            return {"list": [{"vod_name": "解析错误", "vod_content": str(e)}]}

    def _status_detail(self):
        c = self.cache["type_counts"]
        ic = self.cache["ignored_counts"]
        types_info = " ".join(
            f"{t}:{c.get(t, 0)}/{ic.get(t, 0)}"
            for t in ("PY", "JS", "XBPQ", "HTML")
        )

        content = (
            "自动扫描: {scan_enabled}\n"
            "扫描时间: {scan_time}\n"
            "分类开关: {types}\n\n"
            "有效源: {included}\n"
            "忽略源: {ignored}\n\n"
            "── 自动接口.json ──\n"
            "保留手工站点: {manual}\n"
            "自动注入站点: {generated}\n"
            "变更预览: +{added} -{removed} ={unchanged}\n"
            "写入状态: {state}\n\n"
            "── 站点注入注册表 ──\n"
            "注册表路径: {registry_path}\n"
            "注册表手工项: {reg_manual}\n"
            "注册表自动项: {reg_generated}\n"
            "注册表变更: +{reg_added} -{reg_removed}\n"
            "注册表状态: {reg_state}\n\n"
            "── App 重载 ──\n"
            "App重载: {app_reload}\n"
            "App自动重载: {auto_reload_enabled}\n"
            "端口范围: {port_start}-{port_end}\n"
            "上次连接: {last_port}\n\n"
            "{py_info}\n"
            "{jar_info}\n\n"
            "配置文件: {save}\n"
            "设置文件: {settings}\n"
            "备份目录: {backup}\n"
            "注册表备份: {reg_backup}\n\n"
            "已扫描文件列表:\n"
            "{file_list}"
        ).format(
            scan_enabled="开启" if self.scan_enabled else "关闭",
            scan_time=self.status["scan_time"],
            types=types_info,
            included=self.status["included"],
            ignored=self.status["ignored"],
            manual=self.status["manual_sites"],
            generated=self.status["generated_sites"],
            added=self.status["added"],
            removed=self.status["removed"],
            unchanged=self.status["unchanged"],
            state=self.status["write_state"],
            registry_path=self.REGISTRY_PATH,
            reg_manual=self.status.get("registry_manual", 0),
            reg_generated=self.status.get("registry_generated", 0),
            reg_added=self.status.get("registry_added", 0),
            reg_removed=self.status.get("registry_removed", 0),
            reg_state=self.status.get("registry_state", "尚未注入"),
            app_reload=self.status.get("app_reload_state", "-"),
            auto_reload_enabled="开启" if self.auto_reload_app else "关闭",
            port_start=self.APP_PORT_START,
            port_end=self.APP_PORT_END,
            last_port=self.last_app_port or "无",
            py_info=self._count_str(),
            jar_info=self._count_jar_str(),
            save=self.SAVE_PATH,
            settings=self.SETTINGS_PATH,
            backup=self.BACKUP_DIR,
            reg_backup=self.REGISTRY_BACKUP_DIR,
            file_list="\n".join(
                f"  [{fin.get('type_tag', fin['ext'].upper())}] {fin['path']}"
                for fin in self.cache["file_index"].values()
            ) or "  无",
        )
        return {
            "vod_id": self.STATUS_ID,
            "vod_name": "扫描状态详情",
            "vod_pic": "",
            "vod_remarks": self.status["write_state"],
            "vod_content": content,
        }

    def searchContent(self, key, quick, pg="1"):
        page = self._page_number(pg)
        keyword = str(key or "").strip().lower()
        if not keyword:
            return {"list": []}

        items = [
            s for s in self.cache["sources"]
            if keyword in s["type_name"].lower()
            or keyword in s["_type_tag"].lower()
            or keyword in os.path.basename(s["_path"]).lower()
        ]
        return self._paged_result(items, page, self._source_to_vod)

    def playerContent(self, flag, id, vipFlags):
        url = id.split("$")[-1] if "$" in id else id
        return {"url": url, "header": {}, "parse": 0}

    # ==========================================================================
    # 🎮 【交互操作】action 方法
    # ==========================================================================
    def action(self, action):
        action = str(action)

        # ---- 忽略 / 恢复单个源 ----
        if action.startswith(self.ACTION_TOGGLE_IGNORE_PFX):
            tid = action[len(self.ACTION_TOGGLE_IGNORE_PFX):]
            source = self.cache["source_index"].get(tid)
            if not source:
                return {"code": 0, "msg": "源不存在，请重新扫描"}
            with self.lock:
                identity = source["identity"]
                now_ignored = identity not in self.ignored_sources
                if now_ignored:
                    self.ignored_sources.add(identity)
                else:
                    self.ignored_sources.discard(identity)
                try:
                    self._save_settings()
                    if self.scan_enabled:
                        self._scan_all()
                        self._save_config_json()
                        self._save_registry_json()
                    return {
                        "code": 0,
                        "msg": f"已忽略：{source['type_name']}" if now_ignored
                               else f"已恢复：{source['type_name']}",
                    }
                except Exception as exc:
                    if now_ignored:
                        self.ignored_sources.discard(identity)
                    else:
                        self.ignored_sources.add(identity)
                    return {"code": 0, "msg": "操作失败：{}".format(exc)}

        # ---- 切换分类扫描开关 ----
        if action.startswith(self.ACTION_TOGGLE_TYPE_PFX):
            tag = action[len(self.ACTION_TOGGLE_TYPE_PFX):].upper()
            if tag not in self.type_enabled:
                return {"code": 0, "msg": "未知类型：{}".format(tag)}
            with self.lock:
                self.type_enabled[tag] = not self.type_enabled[tag]
                try:
                    self._save_settings()
                    return {
                        "code": 0,
                        "msg": "{}扫描已{}，重扫后生效".format(
                            tag, "开" if self.type_enabled[tag] else "关"
                        ),
                        "list": self._scan_setting_items(),
                    }
                except Exception as exc:
                    self.type_enabled[tag] = not self.type_enabled[tag]
                    return {"code": 0, "msg": "保存失败：{}".format(exc)}

        # ---- 切换 App 自动重载开关 ----
        if action == self.ACTION_TOGGLE_APP_RELOAD:
            with self.lock:
                self.auto_reload_app = not self.auto_reload_app
                try:
                    self._save_settings()
                    return {
                        "code": 0,
                        "msg": "App自动重载已{}".format(
                            "开启" if self.auto_reload_app else "关闭"
                        ),
                        "list": self._scan_setting_items(),
                    }
                except Exception as exc:
                    self.auto_reload_app = not self.auto_reload_app
                    return {"code": 0, "msg": "保存失败：{}".format(exc)}

        # ---- 切换总扫描开关 ----
        if action == self.ACTION_TOGGLE_SCAN:
            with self.lock:
                prev = self.scan_enabled
                self.scan_enabled = not self.scan_enabled
                try:
                    self._save_settings()
                    if self.scan_enabled:
                        self._scan_all()
                        self._save_config_json()
                        self._save_registry_json()
                        msg = "扫描已开：{}个源，{}，注入:{}".format(
                            self.status["included"],
                            self.status["write_state"],
                            self.status.get("registry_state", ""),
                        )
                    else:
                        self.cache["categories"] = []
                        self.cache["sources"] = []
                        self.status["write_state"] = "自动扫描已关闭"
                        msg = "扫描已关，现有配置已保留"
                    return {"code": 0, "msg": msg}
                except Exception as exc:
                    self.scan_enabled = prev
                    return {"code": 0, "msg": "操作失败：{}".format(exc)}

        # ---- 一键扫描并加载（含站点注入 + App 重载）----
        if action == self.ACTION_RESCAN:
            with self.lock:
                if self.scan_enabled:
                    self._scan_all()
                    self._save_config_json()
                    self._save_registry_json()
                    app_state = self.status.get("app_reload_state", "")
                    reg_state = self.status.get("registry_state", "")
                    msg = "已重扫：{}个源，{}".format(
                        self.status["included"], self.status["write_state"]
                    )
                    if reg_state and reg_state != "尚未注入":
                        msg += "，注入:{}".format(reg_state)
                    if app_state and app_state != "-":
                        msg += "，App:{}".format(app_state)
                else:
                    msg = "扫描已关，请先开启"
                return {"code": 0, "msg": msg}

        # ---- 一键清除自动站点（含注册表清除 + App 重载）----
        if action == self.ACTION_CLEAR_SITES:
            with self.lock:
                removed = self._clear_auto_sites()
                reg_removed = self._clear_registry_generated()
                self.scan_enabled = False
                self._save_settings()
                self.cache = {
                    "categories": [], "file_index": {}, "sources": [], "ignored": [],
                    "source_index": {}, "type_counts": {}, "ignored_counts": {},
                }
                self.status["write_state"] = "已清除{}个自动站点".format(removed)
                self.status["registry_state"] = "已清除{}个注册表条目".format(reg_removed)

                _, detail = self._reload_app_vod_config()
                self.status["app_reload_state"] = detail

                msg = "已清除{}个自动站点+{}个注册表条目，手工项保留，扫描已关".format(removed, reg_removed)
                if detail and "未连接" not in detail:
                    msg += "，App:{}".format(detail)
                return {"code": 0, "msg": msg}

        # ---- 撤销上次变更（恢复配置备份 + 注册表备份 + App 重载）----
        if action == self.ACTION_RESTORE_BACKUP:
            with self.lock:
                ok1, msg1 = self._restore_backup()
                ok2, msg2 = self._restore_registry_backup()

                parts = []
                if ok1:
                    parts.append(msg1)
                elif msg1 != "暂无可恢复的备份":
                    parts.append(msg1)
                if ok2:
                    parts.append(msg2)
                elif msg2 != "暂无注册表备份":
                    parts.append(msg2)

                if not parts:
                    parts.append("暂无可恢复的备份")

                msg = "，".join(parts)

                if (ok1 or ok2) and self.scan_enabled:
                    self._scan_all()
                    self._save_config_json()
                    self._save_registry_json()
                    app_state = self.status.get("app_reload_state", "")
                    if app_state and app_state != "-":
                        msg += "，App:{}".format(app_state)
                elif ok1 or ok2:
                    _, detail = self._reload_app_vod_config()
                    if detail and "未连接" not in detail:
                        msg += "，App:{}".format(detail)
                return {"code": 0, "msg": msg}

        # ---- 删除历史备份 ----
        if action == self.ACTION_DELETE_BACKUPS:
            with self.lock:
                removed1 = self._delete_backups()
                # 删除注册表备份
                bp = os.path.join(self.REGISTRY_BACKUP_DIR, "registry-latest.json")
                removed2 = False
                if os.path.isfile(bp):
                    try:
                        os.remove(bp)
                        removed2 = True
                    except Exception:
                        pass

                if removed1 or removed2:
                    parts = []
                    if removed1:
                        parts.append("配置备份")
                    if removed2:
                        parts.append("注册表备份")
                    return {"code": 0, "msg": "已删除：{}".format("、".join(parts))}
                return {"code": 0, "msg": "暂无可删除的备份"}

        return {"code": 0, "msg": "未知操作：{}".format(action)}

    # ==========================================================================
    def destroy(self):
        return "destroy"