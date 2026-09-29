// ==UserScript==
// @name JK领域
// @namespace https://l8k5r4.jksolsorapid.buzz
// @version 1.0.0
// ==/UserScript==
// {"name":"JK领域","type":"js","url":"https://l8k5r4.jksolsorapid.buzz"}
import cheerio from 'assets://js/lib/cheerio.min.js';

const appConfig = {
    siteName: "JK领域",
    siteUrl: "https://l8k5r4.jksolsorapid.buzz"
};
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

async function init(ext) {
    console.log("初始化爬虫:", appConfig.siteName);
}

const classList = [
    { type_id: "424", type_name: "麻豆视频" },
    { type_id: "441", type_name: "糖心VLOG" },
    { type_id: "437", type_name: "香蕉视频" },
    { type_id: "423", type_name: "国产传媒" },
    { type_id: "23", type_name: "中文视频" },
    { type_id: "35", type_name: "国产视频" },
    { type_id: "57", type_name: "日本有码" },
    { type_id: "58", type_name: "日本无码" },
    { type_id: "601", type_name: "视频一区" },
    { type_id: "602", type_name: "视频二区" },
    { type_id: "603", type_name: "视频三区" },
    { type_id: "604", type_name: "视频四区" },
    { type_id: "605", type_name: "视频五区" },
    { type_id: "606", type_name: "视频六区" },
    { type_id: "607", type_name: "视频七区" },
    { type_id: "608", type_name: "视频八区" },
    { type_id: "609", type_name: "视频九区" },
    { type_id: "610", type_name: "视频十区" },
    { type_id: "611", type_name: "视频十一区" },
    { type_id: "612", type_name: "视频十二区" },
    { type_id: "613", type_name: "视频十三区" },
    { type_id: "614", type_name: "视频十四区" },
    { type_id: "615", type_name: "视频十五区" },
    { type_id: "616", type_name: "视频十六区" },
    { type_id: "617", type_name: "视频十七区" },
    { type_id: "618", type_name: "视频十八区" },
    { type_id: "619", type_name: "视频十九区" },
    { type_id: "620", type_name: "视频二十区" }
];

const myFilters = {};

async function home(filter) {
    let list = [];
    try {
        const html = (await req(appConfig.siteUrl + "/gogo/", {
            method: "GET",
            headers: {
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        })).content;
        const $ = cheerio.load(html);
        let seen = {};

        $("a.mo-situ-pics[href*='/vodplay/']").each(function () {
            let vod_id = $(this).attr("href");
            if (!vod_id || seen[vod_id]) return;

            let vod_name = $(this).attr("title") || "";
            let vod_pic = fixUrl($(this).attr("data-original") || $(this).find("img").attr("data-original") || $(this).find("img").attr("src") || "");
            let vod_remarks = "";

            if (vod_name && vod_id) {
                seen[vod_id] = true;
                list.push({ vod_id, vod_name, vod_pic, vod_remarks });
            }
        });

        if (list.length === 0) {
            $("li.mo-paxs-5px a[href*='/vodplay/']").each(function () {
                let vod_id = $(this).attr("href");
                if (!vod_id || seen[vod_id]) return;

                let vod_name = $(this).attr("title") || $(this).text().trim() || "";
                let vod_pic = fixUrl($(this).attr("data-original") || "");
                let vod_remarks = "";

                if (vod_name && vod_id) {
                    seen[vod_id] = true;
                    list.push({ vod_id, vod_name, vod_pic, vod_remarks });
                }
            });
        }
    } catch (e) {
        console.error("首页推荐获取失败:", e.message);
    }

    return JSON.stringify({
        class: classList,
        filters: myFilters,
        list: list.slice(0, 30)
    });
}

function buildCategoryUrl(tid, pg) {
    pg = pg || 1;
    if (pg > 1) {
        return `${appConfig.siteUrl}/vodtype/${tid}-${pg}/`;
    }
    return `${appConfig.siteUrl}/vodtype/${tid}/`;
}

function fixUrl(u) {
    if (!u) return '';
    if (u.startsWith('http')) return u;
    if (u.startsWith('//')) return 'https:' + u;
    if (u.startsWith('/')) return appConfig.siteUrl + u;
    return u;
}

function parseListHtml(html) {
    const $ = cheerio.load(html);
    let list = [];
    let vodIds = {};

    $("a.mo-situ-pics[href*='/vodplay/']").each(function () {
        let vod_id = $(this).attr("href");
        if (!vod_id || vodIds[vod_id]) return;

        let vod_name = $(this).attr("title") || "";
        let vod_pic = fixUrl($(this).attr("data-original") || "");
        let vod_remarks = $(this).find(".mo-situ-rema").text().trim() || "";

        if (!vod_name) {
            let $nameLink = $(this).siblings(".txtbox").find("a.mo-situ-name").first();
            if ($nameLink.length > 0) {
                vod_name = $nameLink.attr("title") || $nameLink.text().trim() || "";
            }
        }

        if (vod_name && vod_id) {
            vodIds[vod_id] = true;
            list.push({ vod_id, vod_name, vod_pic, vod_remarks });
        }
    });

    if (list.length === 0) {
        $("li a[href*='/vodplay/']").each(function () {
            let vod_id = $(this).attr("href");
            if (!vod_id || vodIds[vod_id]) return;

            let vod_name = $(this).attr("title") || $(this).text().trim() || "";
            let vod_pic = fixUrl($(this).attr("data-original") || "");
            let vod_remarks = "";

            if (vod_name && vod_id) {
                vodIds[vod_id] = true;
                list.push({ vod_id, vod_name, vod_pic, vod_remarks });
            }
        });
    }

    let pagecount = 1;
    $("a[href*='/vodtype/']").each(function () {
        let href = $(this).attr("href") || '';
        let m = href.match(/-(\d+)\/?$/);
        if (m) {
            let p = parseInt(m[1]);
            if (p > pagecount) pagecount = p;
        }
    });

    return { list, pagecount };
}

async function category(tid, pg, filter, extend) {
    pg = pg || 1;

    let url = buildCategoryUrl(tid, pg);

    try {
        const html = (await req(url, {
            method: "GET",
            headers: {
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": appConfig.siteUrl
            }
        })).content;
        const result = parseListHtml(html);
        return JSON.stringify(result);
    } catch (e) {
        console.error("分类列表获取失败:", e.message);
        return JSON.stringify({ list: [], pagecount: 0 });
    }
}

async function search(wd, quick, page) {
    page = page || 1;
    try {
        let url;
        if (page > 1) {
            url = `${appConfig.siteUrl}/vodsearch/${encodeURIComponent(wd)}-${page}/`;
        } else {
            url = `${appConfig.siteUrl}/vodsearch/${encodeURIComponent(wd)}/`;
        }
        const html = (await req(url, {
            method: "GET",
            headers: {
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": appConfig.siteUrl
            }
        })).content;
        const result = parseListHtml(html);
        return JSON.stringify(result);
    } catch (e) {
        console.error("搜索失败:", e.message);
        return JSON.stringify({ list: [], pagecount: 0 });
    }
}

async function detail(id) {
    try {
        let detailUrl;
        if (id.startsWith("/vodplay/")) {
            let idMatch = id.match(/\/vodplay\/(\d+)-/);
            if (idMatch) {
                detailUrl = `${appConfig.siteUrl}/voddetail/${idMatch[1]}/`;
            } else {
                detailUrl = `${appConfig.siteUrl}${id}`;
            }
        } else if (id.startsWith("/voddetail/")) {
            detailUrl = `${appConfig.siteUrl}${id}`;
        } else if (id.startsWith("http")) {
            detailUrl = id;
        } else {
            detailUrl = `${appConfig.siteUrl}/voddetail/${id}/`;
        }

        const html = (await req(detailUrl, {
            method: "GET",
            headers: {
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": appConfig.siteUrl
            }
        })).content;
        const $ = cheerio.load(html);

        let vod_name = "";
        let $title = $("h1").first();
        if ($title.length > 0) {
            vod_name = $title.text().trim();
        }
        if (!vod_name) {
            let titleText = $("title").text() || "";
            let titleMatch = titleText.match(/^(.+?)详情介绍/);
            if (titleMatch) {
                vod_name = titleMatch[1].trim();
            } else {
                vod_name = titleText.split("--")[0].trim();
            }
        }

        let vod_pic = "";
        let $pic = $("img[data-original]").first();
        if ($pic.length > 0) {
            vod_pic = fixUrl($pic.attr("data-original") || $pic.attr("src") || "");
        }

        let vod_director = "";
        let vod_actor = "";
        let vod_area = "";
        let vod_year = "";
        let vod_content = "";
        let vod_class = "";
        let vod_remarks = "";

        $("dt").each(function () {
            let label = $(this).text().trim();
            let $dd = $(this).next("dd");
            let value = $dd.text().trim();

            if (label.includes("主演")) {
                vod_actor = $dd.find("a").map(function () { return $(this).text().trim(); }).get().filter(Boolean).join(',') || value;
            } else if (label.includes("导演")) {
                vod_director = $dd.find("a").map(function () { return $(this).text().trim(); }).get().filter(Boolean).join(',') || value;
            } else if (label.includes("类型")) {
                vod_class = $dd.find("a").map(function () { return $(this).text().trim(); }).get().filter(Boolean).join(',') || value;
            } else if (label.includes("地区")) {
                vod_area = value;
            } else if (label.includes("年份")) {
                vod_year = value;
            } else if (label.includes("状态")) {
                vod_remarks = value;
            }
        });

        let $intro = $(".mo-text-mojia, .desc, .detail-content, .mo-cols-content");
        if ($intro.length > 0) {
            vod_content = $intro.first().text().replace(/剧情简介\s*[：:]/, "").trim();
        }

        let lines = [];
        let playlists = [];
        let seenEpisodes = new Set();

        $("a.mo-scre-name").each(function (panelIndex) {
            let lineName = $(this).text().trim() || "线路" + (panelIndex + 1);

            let $pane = $(".mo-cols-case .mo-cols-rows, .mo-tabr-info").eq(panelIndex);
            if (!$pane.length) {
                $pane = $(this).closest(".mo-cols-lays").find(".mo-cols-rows").first();
            }

            let episodes = [];
            let epArray = [];

            $pane.find("a[href*='/vodplay/']").each(function () {
                let name = $(this).text().trim();
                let href = $(this).attr('href') || '';
                if (name && href) {
                    let episodeKey = `${name}_${href}`;
                    if (!seenEpisodes.has(episodeKey)) {
                        seenEpisodes.add(episodeKey);
                        epArray.push({ name, href });
                    }
                }
            });

            epArray.sort((a, b) => {
                let numA = parseInt(a.name.match(/第(\d+)/)?.[1] || 0);
                let numB = parseInt(b.name.match(/第(\d+)/)?.[1] || 0);
                return numA - numB;
            });

            epArray.forEach(ep => {
                episodes.push(`${ep.name}$${ep.href}`);
            });

            if (episodes.length > 0) {
                lines.push(lineName);
                playlists.push(episodes);
            }
        });

        if (lines.length === 0) {
            let episodes = [];
            let epArray = [];

            $("a[href*='/vodplay/']").each(function () {
                let name = $(this).text().trim();
                let href = $(this).attr('href') || '';
                if (name && href && name !== "立即播放") {
                    let episodeKey = `${name}_${href}`;
                    if (!seenEpisodes.has(episodeKey)) {
                        seenEpisodes.add(episodeKey);
                        epArray.push({ name, href });
                    }
                }
            });

            epArray.sort((a, b) => {
                let numA = parseInt(a.name.match(/第(\d+)/)?.[1] || 0);
                let numB = parseInt(b.name.match(/第(\d+)/)?.[1] || 0);
                return numA - numB;
            });

            epArray.forEach(ep => {
                episodes.push(`${ep.name}$${ep.href}`);
            });

            if (episodes.length > 0) {
                lines.push("默认");
                playlists.push(episodes);
            }
        }

        if (lines.length === 0) {
            let vodIdMatch = detailUrl.match(/\/voddetail\/(\d+)/);
            let playId = vodIdMatch ? `${vodIdMatch[1]}-1-1` : "1-1-1";
            lines.push("默认");
            playlists.push([`第1集$/vodplay/${playId}/`]);
        }

        const { vod_play_from, vod_play_url } = buildVodPlayData(lines, playlists);

        return JSON.stringify({
            list: [{
                vod_id: id,
                vod_name,
                vod_pic,
                vod_actor,
                vod_director,
                vod_remarks,
                vod_year,
                vod_area,
                vod_content,
                vod_class,
                vod_play_from,
                vod_play_url
            }]
        });
    } catch (error) {
        console.error(`解析详情页异常 [ID: ${id}]:`, error);
        return JSON.stringify({ list: [] });
    }
}

function buildVodPlayData(lines, playlists) {
    const processedPlaylists = playlists.map(eps => eps.join('#'));
    return {
        vod_play_from: lines.filter(Boolean).join('$$$'),
        vod_play_url: processedPlaylists.join('$$$')
    };
}

async function play(flag, id, flags) {
    try {
        if (id.startsWith("http")) {
            return JSON.stringify({
                parse: 0,
                Header: { "User-Agent": UA, "Referer": appConfig.siteUrl },
                url: id
            });
        }

        const html = (await req(`${appConfig.siteUrl}${id}`, {
            method: "GET",
            headers: {
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": appConfig.siteUrl
            }
        })).content;

        let playerMatch = html.match(/var player_data\s*=\s*(\{.+?\})\s*<\/script>/);
        if (playerMatch) {
            try {
                let playerData = JSON.parse(playerMatch[1]);
                if (playerData.url) {
                    let playUrl = playerData.url.replace(/\\\//g, '/');
                    return JSON.stringify({
                        parse: 0,
                        Header: { "User-Agent": UA, "Referer": appConfig.siteUrl },
                        url: playUrl
                    });
                }
            } catch (e) {
                console.error("解析player_data失败:", e.message);
            }
        }

        playerMatch = html.match(/var player_aaaa\s*=\s*(\{.+?\})\s*;?\s*<\/script>/);
        if (playerMatch) {
            try {
                let playerData = JSON.parse(playerMatch[1]);
                if (playerData.url) {
                    let playUrl = playerData.url.replace(/\\\//g, '/');
                    return JSON.stringify({
                        parse: 0,
                        Header: { "User-Agent": UA, "Referer": appConfig.siteUrl },
                        url: playUrl
                    });
                }
            } catch (e) {
                console.error("解析player_aaaa失败:", e.message);
            }
        }

        let urlMatch = html.match(/"url"\s*[:=]\s*"([^"]*\.m3u8[^"]*)"/);
        if (urlMatch) {
            return JSON.stringify({
                parse: 0,
                Header: { "User-Agent": UA, "Referer": appConfig.siteUrl },
                url: urlMatch[1].replace(/\\\//g, '/')
            });
        }

        let m3u8Match = html.match(/(https?:\\?\/\\?\/[^\"]+\.m3u8[^\"]*)/);
        if (m3u8Match) {
            return JSON.stringify({
                parse: 0,
                Header: { "User-Agent": UA, "Referer": appConfig.siteUrl },
                url: m3u8Match[1].replace(/\\\//g, '/')
            });
        }

        const $ = cheerio.load(html);
        let iframeSrc = $("iframe").attr("src");
        if (iframeSrc) {
            return JSON.stringify({
                parse: 1,
                Header: { "User-Agent": UA, "Referer": appConfig.siteUrl },
                url: fixUrl(iframeSrc)
            });
        }

        return JSON.stringify({
            parse: 1,
            Header: { "User-Agent": UA, "Referer": appConfig.siteUrl },
            url: appConfig.siteUrl + id
        });
    } catch (e) {
        console.error("播放失败:", e);
        return JSON.stringify({ parse: 0, url: "" });
    }
}

export default {
    init,
    home,
    category,
    detail,
    search,
    play
};
