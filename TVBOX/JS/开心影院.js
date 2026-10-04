/*
 * @File   : 开心影院.js
 * @Author : opencode
 * @Date   : 2026-07-08
 * @Desc   : 开心影院 (kxyy1.cc) TVBox T4(JS) 源 —— 自包含，无外部依赖
 *
 * 站点特征（实测 2026-07）：
 *  - 服务端渲染的 MacCMS v10 自定义模板（Tabler UI），HTML 解析。无 CF/盾。
 *  - 首页/列表卡片：<a href="/voddetail/{id}.html" class="d-block cover">
 *        <img data-src="封面"><span class="badge">角标</span></a>
 *        <div class="card-body"><h3 class="card-title">名称</h3><p class="text-muted">日期</p></div>
 *  - 分类列表：/vodshow/{tid}-{area}-{by}-{class}-----{page}---{year}.html （12段）
 *        实测段位：idx0=tid idx1=地区 idx2=排序 idx3=类型 idx8=分页 idx11=年份
 *  - 详情：/voddetail/{id}.html
 *        线路：nav-tabs 里 a[href="#tabs-home-{sid}"] 的文本（去 svg/badge）
 *        剧集：#tabs-home-{sid} 下 a[href^="/vodplay/"]
 *        元信息：<p><strong>xx：</strong>值</p>；简介取 og:description
 *  - 播放：/vodplay/{id}-{sid}-{eid}.html
 *        页面里 var player_data={...,"url":"明文m3u8","encrypt":0}
 *        主流线路(dyttm3u8 等)为明文直链，直接 parse:0 播放。
 *  - 搜索：/vodsearch/{词}-------------.html
 *        搜索结果卡片结构不同于列表页：
 *          <a class="col-3 col-md-1" href="/voddetail/{id}.html"><img src="封面"></a>
 *          <a class="...search-movie-title" href="/voddetail/{id}.html" title="名称">...</a>
 *          <p><strong>类型/主演/简介：</strong>值</p>
 *        JSON 采集口(api.php/provide/vod)已 closed。
 *
 *  ── 搜索验证码攻破（实测已打通）──────────────────────────────
 *  首页搜索有图形验证码防护，但机制是「按 session 验证一次即长期放行」：
 *    1) 验证码图： GET /index.php/verify/index.html   （4位字母数字，绑定 PHPSESSID）
 *    2) 提交验证： POST /index.php/ajax/verify_check?type=search&verify={code}
 *                 成功返回 {"code":1,"msg":"ok"}
 *    3) 通过后验证态存在 PHPSESSID cookie 里，同一 session 内所有 /vodsearch 直接放行。
 *  纯 JS 引擎无法识图 OCR，故本源采用「Cookie 复用」方案：
 *    - 通过 init 的 ext 传入已验证过的 Cookie（形如 "PHPSESSID=xxxx"），
 *      或站点配置 ext 字段填 {"host":"...","cookie":"PHPSESSID=xxxx"}。
 *    - 运行期 req 若拿到 Set-Cookie 会自动保存复用（引擎支持时）。
 *    - 命中验证码且无可用 Cookie 时，搜索返回空并提示注入 Cookie。
 *  → 用带 OCR 的环境（浏览器/打码）过一次码，把 PHPSESSID 填进 ext 即可长期搜索。
 *
 *  ── 如何获取 PHPSESSID（配置搜索用）────────────────────────
 *  【方法1｜电脑浏览器 F12】(最简单)
 *    1. Chrome/Edge 打开 https://www.kxyy1.cc/vodsearch/斗罗-------------.html
 *    2. 弹出"安全验证"，肉眼识别 4 位验证码填入，点"提交验证"
 *    3. 通过后按 F12 → Application → Cookies → https://www.kxyy1.cc
 *       复制 PHPSESSID 那一行的 Value（如 1a0u7ifd4gv0if4447oedv216o）
 *  【方法2｜F12 控制台一键】(过码后)
 *    在 www.kxyy1.cc 页面 Console 执行：
 *       document.cookie.match(/PHPSESSID=[^;]+/)[0]
 *    直接打印出 "PHPSESSID=xxxx"，整段复制。
 *  【方法3｜手机/模拟器抓包】
 *    HttpCanary / Reqable / Fiddler 抓访问搜索页(过码后)的请求，
 *    在请求头 Cookie: 里找 PHPSESSID=xxxx。
 *  【填入配置】把值填进站点 ext：
 *       "ext": "{\"host\":\"https://www.kxyy1.cc\",\"cookie\":\"PHPSESSID=你的值\"}"
 *  【注意】PHPSESSID 有有效期(约数小时~1天/服务器重启失效)，
 *          过期后搜索又被拦截，需重新过码更新；分类/详情/播放不需要 Cookie。
 *
 *  ── 验证码手动过码接口（自动化脚本可参考）──────────────────
 *    取图 : GET  /index.php/verify/index.html?r={时间戳}   (每次取图会刷新答案)
 *    提交 : POST /index.php/ajax/verify_check?type=search&verify={4位码}
 *           需带同一 PHPSESSID；成功返回 {"code":1,"msg":"ok"}
 *    通过后该 PHPSESSID 即可直接请求 /vodsearch/... 不再拦截。
 */

var HOST = "https://www.kxyy1.cc";
var UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";
var COOKIE = "";          // 已验证的 Cookie（PHPSESSID=...），可经 init(ext) 注入或运行期抓取
var CK_STORE = "kxyy_ck"; // local 持久化 key

var CLASSES = [
    { type_id: "1", type_name: "电影" },
    { type_id: "2", type_name: "电视剧" },
    { type_id: "3", type_name: "综艺" },
    { type_id: "4", type_name: "动漫" },
    { type_id: "26", type_name: "短剧" }
];

// 筛选项（各分类共用）
var FILTERS = (function () {
    var area = ["", "中国大陆", "中国香港", "中国台湾", "美国", "韩国", "日本", "泰国", "印度", "英国", "法国", "德国", "意大利"];
    var cls = ["", "剧情", "喜剧", "动作", "爱情", "科幻", "动画", "悬疑", "惊悚", "恐怖", "犯罪", "冒险", "奇幻", "古装", "历史", "家庭", "战争", "武侠", "青春", "都市", "网剧"];
    var years = ["", "2026", "2025", "2024", "2023", "2022", "2021", "2020", "2019", "2018", "2017", "2016", "2015", "2014", "2013", "2012", "2011", "2010"];
    var by = [
        { n: "更新", v: "time" },
        { n: "热门", v: "hits" },
        { n: "评分", v: "score" }
    ];
    function opt(arr) {
        return arr.map(function (x) { return { n: x === "" ? "全部" : x, v: x }; });
    }
    var base = [
        { key: "area", name: "地区", value: opt(area) },
        { key: "by", name: "排序", value: by },
        { key: "class", name: "类型", value: opt(cls) },
        { key: "year", name: "年份", value: opt(years) }
    ];
    var obj = {};
    CLASSES.forEach(function (c) { obj[c.type_id] = base; });
    return obj;
})();

/* ---------------- 通用工具 ---------------- */

function toStr(v) { return v === undefined || v === null ? "" : String(v); }
function encode(s) { return encodeURIComponent(toStr(s)); }

function fixUrl(u) {
    u = toStr(u).trim();
    if (!u) return "";
    if (u.indexOf("//") === 0) return "https:" + u;
    if (u.charAt(0) === "/") return HOST + u;
    return u;
}

// 封面图 wework.qpic.cn（企业微信图床）——实测不防盗链，直接用原图 URL 即可。
// 注意：不要加 @Referer= 之类后缀，部分 TVBox 分支不识别会导致封面加载失败/不显示。
function fixPic(u) {
    u = toStr(u).trim();
    if (!u) return "";
    if (u.indexOf("//") === 0) u = "https:" + u;
    else if (u.charAt(0) === "/") u = HOST + u;
    return u;
}

function textClean(s) {
    return toStr(s)
        .replace(/<[^>]+>/g, "")
        .replace(/&nbsp;/g, " ")
        .replace(/&amp;/g, "&")
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/&#\d+;/g, "")
        .replace(/\s+/g, " ")
        .trim();
}

function log(msg) {
    try { console.log("[KXYY] " + msg); } catch (e) {}
}

/* ---------------- Cookie 持久化 ---------------- */

function loadCookie() {
    if (COOKIE) return COOKIE;
    try {
        if (typeof local !== "undefined" && local.get) {
            var c = local.get(CK_STORE, "cookie");
            if (c) { COOKIE = c; return c; }
        }
    } catch (e) {}
    return COOKIE;
}

function saveCookie(c) {
    if (!c) return;
    COOKIE = c;
    try {
        if (typeof local !== "undefined" && local.set) local.set(CK_STORE, "cookie", c);
    } catch (e) {}
}

// 从响应对象里提取 Set-Cookie 的 PHPSESSID 并合并保存（引擎支持时）
function grabCookie(res) {
    try {
        if (!res || typeof res === "string") return;
        var h = res.headers || res.header || {};
        var sc = h["Set-Cookie"] || h["set-cookie"] || res.cookies || "";
        if (sc instanceof Array) sc = sc.join("; ");
        sc = toStr(sc);
        var m = /PHPSESSID=[^;,\s]+/.exec(sc);
        if (m) {
            var cur = loadCookie();
            if (cur.indexOf(m[0]) < 0) saveCookie(m[0]);
        }
    } catch (e) {}
}

/* ---------------- 请求 ---------------- */

function req2(url) {
    var headers = {
        "User-Agent": UA,
        "Referer": HOST + "/",
        "Accept": "text/html,application/xhtml+xml"
    };
    var ck = loadCookie();
    if (ck) headers["Cookie"] = ck;
    try {
        var res = req(url, { method: "GET", headers: headers, timeout: 10000 });
        grabCookie(res);
        if (typeof res === "string") return res;
        return toStr(res && (res.content || res.body || res.data));
    } catch (e) {
        log("req error " + url + " : " + e);
        return "";
    }
}

// 提交搜索验证码（有 OCR 结果时用）：成功返回 true
function verifyCheck(code) {
    var url = HOST + "/index.php/ajax/verify_check?type=search&verify=" + encode(code);
    var headers = {
        "User-Agent": UA,
        "Referer": HOST + "/",
        "X-Requested-With": "XMLHttpRequest"
    };
    var ck = loadCookie();
    if (ck) headers["Cookie"] = ck;
    try {
        var res = req(url, { method: "POST", headers: headers, data: "", timeout: 10000 });
        grabCookie(res);
        var body = (typeof res === "string") ? res : toStr(res && (res.content || res.body || res.data));
        return /"code"\s*:\s*1/.test(body);
    } catch (e) {
        log("verify error " + e);
        return false;
    }
}

/* ---------------- 解析 ---------------- */

// 解析卡片列表（首页/分类通用，兼容两种卡片结构）
// 结构A(首页): <a title=".." href="/voddetail/{id}.html" class="d-block cover"><img data-src>..</a>...<h3 card-title>名</h3>
// 结构B(分类): <a target=_blank href="/voddetail/{id}.html" class="..cover2"><img src>..</a>...<h3 ..card-title>名</h3>
function parseList(html) {
    var list = [];
    var seen = {};
    if (!html) return list;

    // 以 voddetail 链接为锚，向后捕获同卡片内的 <a>..</a> 段 与 card-title
    var re = /href="\/voddetail\/(\d+)\.html"[^>]*>([\s\S]*?)<\/a>\s*<div[^>]*card-body[^>]*>([\s\S]*?)<\/div>/g;
    var m;
    while ((m = re.exec(html)) !== null) {
        var id = m[1];
        if (seen[id]) continue;

        var inner = m[2];   // <img><span badge>
        var bodyHtml = m[3];

        // 名称：card-title
        var name = "";
        var nmt = /card-title[^>]*>([\s\S]*?)<\/h3>/.exec(bodyHtml) || /<h3[^>]*>([\s\S]*?)<\/h3>/.exec(bodyHtml);
        if (nmt) name = textClean(nmt[1]);
        if (!name) {
            var tt = /title="([^"]+)"/.exec(m[0]);
            if (tt) name = textClean(tt[1]);
        }
        if (!name) continue;
        seen[id] = true;

        // 封面：data-src 优先，其次 src
        var pic = "";
        var pm = /data-src="([^"]+)"/.exec(inner) || /\ssrc="([^"]+)"/.exec(inner);
        if (pm) pic = pm[1];

        // 角标备注
        var remark = "";
        var bm = /class="[^"]*badge[^"]*"[^>]*>([\s\S]*?)<\/span>/.exec(inner);
        if (bm) remark = textClean(bm[1]);

        list.push({
            vod_id: id,
            vod_name: name,
            vod_pic: fixPic(pic),
            vod_remarks: remark
        });
    }
    return list;
}

// 搜索结果专用解析（结构不同于列表页）
// <a class="col-3 col-md-1" href="/voddetail/{id}.html"><img src="封面"></a>
// <a class="...search-movie-title" href="/voddetail/{id}.html" title="名称">2019电视剧《..》已完结</a>
// <p><strong>类型/主演/简介：</strong>值</p>
function parseSearch(html) {
    var list = [];
    var seen = {};
    if (!html) return list;

    var re = /class="[^"]*search-movie-title[^"]*"[^>]*href="\/voddetail\/(\d+)\.html"[^>]*title="([^"]*)"[^>]*>([\s\S]*?)<\/a>([\s\S]*?)(?=class="[^"]*search-movie-title|<\/div>\s*<\/div>\s*<\/div>\s*<\/div>|$)/g;
    var m;
    while ((m = re.exec(html)) !== null) {
        var id = m[1];
        if (seen[id]) continue;
        seen[id] = true;

        var name = textClean(m[2]) || textClean(m[3]);
        if (!name) continue;
        var tail = m[4] || "";

        // 封面：找该 id 对应的封面 <img>（封面 a 在标题 a 之前）
        var pic = "";
        var picRe = new RegExp('href="\\/voddetail\\/' + id + '\\.html"[^>]*>\\s*<img[^>]+src="([^"]+)"');
        var pm = picRe.exec(html);
        if (pm) pic = pm[1];

        // 备注：标题尾部状态（"已完结"）优先，否则取类型
        var remark = "";
        var sm = /》\s*([^<]{1,12})$/.exec(textClean(m[3]));
        if (sm) remark = sm[1].trim();
        if (!remark) {
            var cm = /<strong>\s*类型\s*[：:]?\s*<\/strong>([\s\S]*?)<\/p>/.exec(tail);
            if (cm) remark = textClean(cm[1]);
        }

        list.push({
            vod_id: id,
            vod_name: name,
            vod_pic: fixPic(pic),
            vod_remarks: remark
        });
    }
    return list;
}

// 详情页按 <strong>标签：</strong>值</p> 提取字段
function detailField(html, label) {
    var re = new RegExp("<strong>\\s*" + label + "\\s*[：:]?\\s*<\\/strong>([\\s\\S]*?)<\\/p>", "i");
    var m = re.exec(html);
    return m ? textClean(m[1]) : "";
}

/* ---------------- 接口实现 ---------------- */

function init(ext) {
    var cfg = ext;
    if (typeof ext === "string") {
        var s = ext.trim();
        if (/^https?:\/\//.test(s)) {
            HOST = s.replace(/\/+$/, "");
        } else if (/^\s*\{/.test(s)) {
            try { cfg = JSON.parse(s); } catch (e) { cfg = null; }
        } else if (/PHPSESSID=/.test(s)) {
            saveCookie((/PHPSESSID=[^;,\s]+/.exec(s) || [])[0] || s);
        }
    }
    if (cfg && typeof cfg === "object") {
        if (cfg.host) HOST = toStr(cfg.host).replace(/\/+$/, "");
        if (cfg.cookie) saveCookie((/PHPSESSID=[^;,\s]+/.exec(toStr(cfg.cookie)) || [toStr(cfg.cookie)])[0]);
    }
    loadCookie();
    log("init host=" + HOST + " ck=" + (COOKIE ? "yes" : "no"));
}

function home(filter) {
    return JSON.stringify({ class: CLASSES, filters: FILTERS });
}

function homeVod() {
    var html = req2(HOST + "/");
    var list = parseList(html).slice(0, 40);
    return JSON.stringify({ list: list });
}

function category(tid, pg, filter, extend) {
    tid = toStr(tid || "1");
    pg = parseInt(pg || 1);
    if (!pg || pg < 1) pg = 1;

    extend = extend || {};
    // 12 段：idx0=tid idx1=area idx2=by idx3=class idx8=page idx11=year
    var segs = [tid, "", "", "", "", "", "", "", "", "", "", ""];
    if (extend.area) segs[1] = encode(extend.area);
    if (extend.by) segs[2] = extend.by;
    if (extend["class"]) segs[3] = encode(extend["class"]);
    segs[8] = String(pg);
    if (extend.year) segs[11] = extend.year;

    var url = HOST + "/vodshow/" + segs.join("-") + ".html";
    var html = req2(url);
    var list = parseList(html);

    // 该站每页约 24 部；满页视为有下一页
    var pagecount = list.length >= 24 ? pg + 1 : pg;

    log("category tid=" + tid + " pg=" + pg + " count=" + list.length);
    return JSON.stringify({
        page: pg,
        pagecount: pagecount,
        limit: 24,
        total: pagecount * 24,
        list: list
    });
}

function detail(id) {
    var vid = toStr(id).replace(/[^\d]/g, "");
    var url = HOST + "/voddetail/" + vid + ".html";
    var html = req2(url);
    if (!html) return JSON.stringify({ list: [] });

    // 名称：优先 <h1>（最干净，去尾部年份括号）；再 og:title 书名号；最后 title
    var name = "";
    var hm = /<h1[^>]*>([\s\S]*?)<\/h1>/.exec(html);
    if (hm) name = textClean(hm[1]).replace(/\s*[\(（]\d{4}[\)）]\s*$/, "").trim();
    if (!name) {
        var om = /<meta[^>]+property="og:title"[^>]+content="([^"]+)"/.exec(html);
        if (om) {
            var bm = /《([^》]+)》/.exec(om[1]);
            name = bm ? textClean(bm[1]) : textClean(om[1]).replace(/(在线观看|免费|高清|完整版|-\s*开心影院).*$/, "").trim();
        }
    }
    if (!name) {
        var tm = /<title>\s*《?([^《》<]+?)》?(?:高清|在线观看|_|\s*-\s*\d{4}|\s*-\s*开心)/.exec(html);
        if (tm) name = textClean(tm[1]);
    }

    // 封面
    var pic = "";
    var cm = /class="[^"]*cover-lg-max-25[^"]*"[\s\S]*?<img[^>]+src="([^"]+)"/.exec(html);
    if (!cm) cm = /<meta[^>]+property="og:image"[^>]+content="([^"]+)"/.exec(html);
    if (cm) pic = cm[1];

    // 简介：og:description
    var desc = "";
    var dm = /<meta[^>]+property="og:description"[^>]+content="([^"]*)"/.exec(html);
    if (dm) desc = textClean(dm[1]);

    var director = detailField(html, "导演");
    var actor = detailField(html, "主演");
    var area = detailField(html, "制片国家/地区") || detailField(html, "地区") || detailField(html, "国家");
    area = area.replace(/[\[\]]/g, "").trim();
    var firstShow = detailField(html, "首播") || detailField(html, "上映") || detailField(html, "年份");
    var year = "";
    var ym = /(\d{4})/.exec(firstShow);
    if (ym) year = ym[1];
    if (!year) { var yh = /[\(（](\d{4})[\)）]/.exec(name); if (yh) year = yh[1]; }
    var cls = detailField(html, "类型") || detailField(html, "分类");
    var score = detailField(html, "评分") || detailField(html, "豆瓣评分");

    var vod = {
        vod_id: vid,
        vod_name: name,
        vod_pic: fixPic(pic),
        vod_year: year,
        vod_area: area,
        vod_actor: actor,
        vod_director: director,
        vod_remarks: score,
        vod_content: desc || cls
    };

    // 线路名：nav-tabs 里 a[href="#tabs-home-{sid}"]，文本去 svg/badge
    var navBlock = html;
    var tcStart = html.indexOf("tab-content");
    var navEnd = tcStart > 0 ? tcStart : html.length;
    var navStart = html.indexOf("nav-tabs");
    if (navStart >= 0) navBlock = html.slice(navStart, navEnd);

    var sids = [];
    var names = [];
    var navRe = /href="#tabs-home-(\d+)"[^>]*>([\s\S]*?)<\/a>/g;
    var nvm;
    while ((nvm = navRe.exec(navBlock)) !== null) {
        var sid = nvm[1];
        var raw = nvm[2].replace(/<svg[\s\S]*?<\/svg>/gi, "");
        // 去掉集数徽标 <span class="badge">12</span>
        raw = raw.replace(/<span[^>]*badge[^>]*>[\s\S]*?<\/span>/gi, "");
        var fn = textClean(raw) || ("线路" + sid);
        sids.push(sid);
        names.push(fn);
    }

    // 每条线路剧集：#tabs-home-{sid} 内的 a[href^="/vodplay/"]
    var playFrom = [];
    var playUrl = [];
    for (var i = 0; i < sids.length; i++) {
        var sid2 = sids[i];
        var paneRe = new RegExp('id="tabs-home-' + sid2 + '"([\\s\\S]*?)(?:<div class="tab-pane|<\\/div>\\s*<\\/div>\\s*<\\/div>)');
        var pm2 = paneRe.exec(html);
        var pane = pm2 ? pm2[1] : "";
        var eps = [];
        var epRe = /<a[^>]+href="(\/vodplay\/[^"]+\.html)"[^>]*>([\s\S]*?)<\/a>/g;
        var em;
        while ((em = epRe.exec(pane)) !== null) {
            var epName = textClean(em[2]) || (eps.length + 1);
            eps.push(epName + "$" + fixUrl(em[1]));
        }
        if (eps.length) {
            playFrom.push(names[i]);
            playUrl.push(eps.join("#"));
        }
    }

    if (playFrom.length) {
        vod.vod_play_from = playFrom.join("$$$");
        vod.vod_play_url = playUrl.join("$$$");
    } else {
        vod.vod_play_from = "提示";
        vod.vod_play_url = "暂无播放源$";
    }

    log("detail id=" + vid + " lines=" + playFrom.length);
    return JSON.stringify({ list: [vod] });
}

function play(flag, id, flags) {
    var pageUrl = fixUrl(id);
    var html = req2(pageUrl);
    var header = { "User-Agent": UA, "Referer": HOST + "/" };

    var url = "";
    var enc = 0;

    // var player_data={...}
    var pm = /var\s+player_data\s*=\s*(\{[\s\S]*?\})\s*<\/script>/.exec(html);
    if (!pm) pm = /player_data\s*=\s*(\{[\s\S]*?\})/.exec(html);
    if (pm) {
        var jsonStr = pm[1];
        var um = /"url"\s*:\s*"([^"]*)"/.exec(jsonStr);
        if (um) url = um[1];
        var em2 = /"encrypt"\s*:\s*(\d+)/.exec(jsonStr);
        if (em2) enc = parseInt(em2[1]);
    }
    if (!url) {
        var m2 = /"url"\s*:\s*"([^"]+\.(?:m3u8|mp4)[^"]*)"/i.exec(html);
        if (m2) url = m2[1];
    }

    url = url.replace(/\\\//g, "/").replace(/\\u002F/gi, "/").trim();
    if (url && enc == 2) { try { url = decodeURIComponent(url); } catch (e) {} }
    if (url && enc == 1) { try { url = unescape(url); } catch (e) {} }

    // 明文 m3u8/mp4 直链 -> 直接播放
    if (url && /^https?:\/\//.test(url) && /\.(m3u8|mp4|flv|ts|mkv)/i.test(url)) {
        log("play direct " + url);
        return JSON.stringify({ parse: 0, url: url, header: header });
    }

    // 非直链（前端加密线路）-> 交给播放器嗅探播放页
    log("play sniff " + pageUrl);
    return JSON.stringify({ parse: 1, jx: 0, url: pageUrl, header: header });
}

function search(wd, quick, pg) {
    pg = parseInt(pg || 1);
    if (!pg || pg < 1) pg = 1;
    if (pg > 1) return JSON.stringify({ list: [], page: pg, pagecount: pg });

    var url = HOST + "/vodsearch/" + encode(wd) + "-------------.html";
    var html = req2(url);

    // 命中图形验证码防护
    if (/安全验证|请输入验证码|verify\/index/.test(html)) {
        // 若引擎在此前请求中拿到了新 PHPSESSID，重试一次（Cookie 复用生效场景）
        var ck = loadCookie();
        if (ck) {
            html = req2(url);
        }
        if (/安全验证|请输入验证码|verify\/index/.test(html)) {
            log("search blocked by captcha (需注入已验证的 PHPSESSID Cookie)");
            return JSON.stringify({
                list: [{
                    vod_id: "",
                    vod_name: "搜索需验证码：请在源 ext 注入已验证 PHPSESSID",
                    vod_pic: "",
                    vod_remarks: "验证拦截"
                }],
                page: 1, pagecount: 1, limit: 0, total: 0
            });
        }
    }

    var list = parseSearch(html);
    if (!list.length) list = parseList(html);   // 结构兜底
    return JSON.stringify({
        list: list, page: 1, pagecount: 1,
        limit: list.length, total: list.length
    });
}

/* ---------------- 导出 ---------------- */

__JS_SPIDER__ = {
    init: init,
    home: home,
    homeVod: homeVod,
    category: category,
    detail: detail,
    play: play,
    search: search
};
