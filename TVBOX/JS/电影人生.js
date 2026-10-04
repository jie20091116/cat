import cheerio from 'assets://js/lib/cheerio.min.js';

const appConfig = {
    siteName: "电影人生",
    siteUrl: "https://dyrs9.vip"
};
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36";

async function init(ext) {
    console.log("初始化爬虫:", appConfig.siteName);
}

const classList = [
    { type_id: "dianying", type_name: "电影" },
    { type_id: "dianshiju", type_name: "电视剧" },
    { type_id: "zongyi", type_name: "综艺" },
    { type_id: "dongman", type_name: "动漫" },
    { type_id: "duanju", type_name: "短剧" },
    { type_id: "dianying-剧情", type_name: "剧情片" },
    { type_id: "dianying-喜剧", type_name: "喜剧片" },
    { type_id: "dianying-动作", type_name: "动作片" },
    { type_id: "dianying-爱情", type_name: "爱情片" },
    { type_id: "dianying-惊悚", type_name: "惊悚片" },
    { type_id: "dianying-犯罪", type_name: "犯罪片" },
    { type_id: "dianying-恐怖", type_name: "恐怖片" },
    { type_id: "dianying-悬疑", type_name: "悬疑片" },
    { type_id: "dianying-冒险", type_name: "冒险片" },
    { type_id: "dianying-奇幻", type_name: "奇幻片" },
    { type_id: "dianying-科幻", type_name: "科幻片" },
    { type_id: "dianying-家庭", type_name: "家庭片" },
    { type_id: "dianying-历史", type_name: "历史片" },
    { type_id: "dianying-战争", type_name: "战争片" },
    { type_id: "dianying-纪录片", type_name: "纪录片" },
    { type_id: "dianying-古装", type_name: "古装片" },
    { type_id: "dianying-音乐", type_name: "音乐片" },
    { type_id: "dianying-动画", type_name: "动画片" }
];

function getAreaFilter() {
    return {
        "key": "area", "name": "地区", "value": [
            { "n": "全部", "v": "" },
            { "n": "大陆", "v": "大陆" },
            { "n": "香港", "v": "香港" },
            { "n": "台湾", "v": "台湾" },
            { "n": "美国", "v": "美国" },
            { "n": "日本", "v": "日本" },
            { "n": "韩国", "v": "韩国" },
            { "n": "英国", "v": "英国" },
            { "n": "法国", "v": "法国" },
            { "n": "德国", "v": "德国" },
            { "n": "泰国", "v": "泰国" },
            { "n": "印度", "v": "印度" },
            { "n": "其他", "v": "其他" }
        ]
    };
}

function getYearFilter() {
    let years = [{ "n": "全部", "v": "" }];
    const currentYear = new Date().getFullYear();
    for (let y = currentYear; y >= 2010; y--) {
        years.push({ "n": String(y), "v": String(y) });
    }
    return { "key": "year", "name": "年份", "value": years };
}

function getLangFilter() {
    return {
        "key": "lang", "name": "语言", "value": [
            { "n": "全部", "v": "" },
            { "n": "国语", "v": "国语" },
            { "n": "粤语", "v": "粤语" },
            { "n": "英语", "v": "英语" },
            { "n": "日语", "v": "日语" },
            { "n": "韩语", "v": "韩语" },
            { "n": "其他", "v": "其他" }
        ]
    };
}

function getTypeFilter() {
    return {
        "key": "type", "name": "类型", "value": [
            { "n": "全部", "v": "" },
            { "n": "剧情", "v": "剧情" },
            { "n": "喜剧", "v": "喜剧" },
            { "n": "动作", "v": "动作" },
            { "n": "爱情", "v": "爱情" },
            { "n": "科幻", "v": "科幻" },
            { "n": "恐怖", "v": "恐怖" },
            { "n": "悬疑", "v": "悬疑" },
            { "n": "犯罪", "v": "犯罪" },
            { "n": "动画", "v": "动画" },
            { "n": "冒险", "v": "冒险" },
            { "n": "奇幻", "v": "奇幻" },
            { "n": "战争", "v": "战争" },
            { "n": "纪录片", "v": "纪录片" }
        ]
    };
}

const commonFilters = [getAreaFilter(), getYearFilter(), getLangFilter(), getTypeFilter()];

const myFilters = {};
classList.forEach(item => {
    myFilters[item.type_id] = commonFilters;
});

async function home(filter) {
    let list = [];
    try {
        const html = (await req(appConfig.siteUrl, {
            method: "GET",
            headers: {
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        })).content;
        const $ = cheerio.load(html);
        let seen = {};

        $("a[href*='/wzzy-']").each(function () {
            let vod_id = $(this).attr("href");
            if (!vod_id || seen[vod_id]) return;
            if (!vod_id.startsWith('/wzzy-')) return;

            let vod_name = $(this).attr("title") || $(this).text().trim() || "";
            let hash = vod_id.match(/\/wzzy-\d+\/([a-f0-9]+)\.html/)?.[1] || "";
            let vod_pic = hash ? `${appConfig.siteUrl}/img/id/${hash}.jpg` : "";
            let vod_remarks = "";

            if (vod_name && vod_id) {
                seen[vod_id] = true;
                list.push({ vod_id, vod_name, vod_pic, vod_remarks });
            }
        });
    } catch (e) {
        console.error("首页推荐获取失败:", e.message);
    }

    return JSON.stringify({
        class: classList,
        filters: myFilters,
        list: list.slice(0, 30)
    });
}

function buildCategoryUrl(tid, pg, extend) {
    extend = extend || {};
    let baseType = tid.split('-')[0];
    let subType = tid.split('-')[1] || '';

    if (!subType && extend.type) {
        subType = extend.type;
    }

    let url = `/${baseType}.html`;
    let params = [];
    
    if (subType) params.push(`class=${encodeURIComponent(subType)}`);
    if (pg && pg > 1) params.push(`page=${pg}`);

    if (params.length > 0) {
        url += '?' + params.join('&');
    }

    return appConfig.siteUrl + url;
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

    $("a[href*='/wzzy-']").each(function () {
        let vod_id = $(this).attr("href");
        if (!vod_id || vodIds[vod_id]) return;
        if (!vod_id.startsWith('/wzzy-')) return;

        let vod_name = $(this).attr("title") || $(this).text().trim() || "";
        let hash = vod_id.match(/\/wzzy-\d+\/([a-f0-9]+)\.html/)?.[1] || "";
        let vod_pic = hash ? `${appConfig.siteUrl}/img/id/${hash}.jpg` : "";
        let vod_remarks = "";

        if (vod_name && vod_id) {
            vodIds[vod_id] = true;
            list.push({ vod_id, vod_name, vod_pic, vod_remarks });
        }
    });

    let pagecount = 1;
    $("a[href*='page=']").each(function () {
        let href = $(this).attr("href") || '';
        let m = href.match(/page=(\d+)/);
        if (m) {
            let p = parseInt(m[1]);
            if (p > pagecount) pagecount = p;
        }
    });

    return { list, pagecount };
}

async function category(tid, pg, filter, extend) {
    pg = pg || 1;
    extend = extend || {};

    let url = buildCategoryUrl(tid, pg, extend);

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
        let url = `${appConfig.siteUrl}/s.html?name=${encodeURIComponent(wd)}`;
        if (page > 1) url += `&page=${page}`;

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
        const html = (await req(appConfig.siteUrl + id, {
            method: "GET",
            headers: {
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": appConfig.siteUrl
            }
        })).content;
        const $ = cheerio.load(html);

        let vod_name = "";
        let vod_director = "";
        let vod_actor = "";
        let vod_year = "";
        let vod_area = "";
        let vod_class = "";
        let vod_content = "";
        let vod_pic = "";

        let hash = id.match(/\/wzzy-\d+\/([a-f0-9]+)\.html/)?.[1] || "";
        vod_pic = hash ? `${appConfig.siteUrl}/img/id/${hash}.jpg` : "";

        $('script[type="application/ld+json"]').each(function () {
            try {
                let jsonText = $(this).html();
                if (!jsonText) return;
                let data = JSON.parse(jsonText);
                if (data && data.name) vod_name = data.name;
                if (data && data.year) vod_year = String(data.year);
                if (data && data.countryOfOrigin) vod_area = data.countryOfOrigin;
                if (data && data.inLanguage) {
                    vod_class = data.inLanguage;
                }
                if (data && data.description) {
                    vod_content = data.description.replace(/<br \/>/g, "\n").replace(/　/g, "").trim();
                }
                if (data && data.director) {
                    if (data.director.name) vod_director = data.director.name;
                }
                if (data && data.actor && Array.isArray(data.actor)) {
                    let actors = data.actor.map(a => a.name).filter(Boolean);
                    vod_actor = actors.join(',');
                }
            } catch (e) {}
        });

        if (!vod_name) {
            vod_name = $("title").text().replace(/《|》/g, "").replace(/-.*$/, "").trim() || "";
        }

        if (!vod_actor) {
            let desc = $('meta[name="description"]').attr("content") || "";
            let actorMatch = desc.match(/主演包括([^。]+)/);
            if (actorMatch) {
                vod_actor = actorMatch[1].trim();
            }
        }

        if (!vod_director) {
            $("p, div, span").each(function () {
                let text = $(this).text();
                if (text.includes("导演") && !vod_director) {
                    let match = text.match(/导演[：:]\s*([^\n\r]+)/);
                    if (match) {
                        vod_director = match[1].trim().split(/[,，、\s]/)[0];
                    }
                }
            });
        }

        if (!vod_class) {
            $("a[href*='class=']").each(function () {
                let href = $(this).attr("href") || '';
                if (href.includes("class=") && !href.includes("sso")) {
                    let m = href.match(/class=([^&]+)/);
                    if (m) {
                        if (!vod_class) vod_class = decodeURIComponent(m[1]);
                    }
                }
            });
        }

        let vod_remarks = "";

        let lines = [];
        let playlists = [];

        let originEpisodes = {};

        $("#episodeContent a[href]").each(function () {
            let href = $(this).attr("href") || "";
            let name = $(this).attr("data-title") || $(this).text().trim() || "";
            let origin = $(this).attr("data-origin") || "";
            
            if (href && name && origin) {
                let pMatch = href.match(/[?&]p=(\d+)/);
                let p = pMatch ? parseInt(pMatch[1]) : 0;
                
                if (!originEpisodes[origin]) {
                    originEpisodes[origin] = [];
                }
                originEpisodes[origin].push({ name, href, p });
            }
        });

        let originOrder = [];
        $("[id$='Tab'][data-origin]").each(function () {
            let origin = $(this).attr("data-origin");
            if (origin && !originOrder.includes(origin)) {
                originOrder.push(origin);
            }
        });

        if (originOrder.length === 0) {
            originOrder = Object.keys(originEpisodes);
        }

        let templateOrigin = Object.keys(originEpisodes)[0];
        let templateEpisodes = templateOrigin ? originEpisodes[templateOrigin] : [];

        originOrder.forEach(origin => {
            let eps = originEpisodes[origin];
            
            if (!eps || eps.length === 0) {
                if (templateEpisodes.length === 0) return;
                eps = templateEpisodes.map(ep => {
                    let newHref = ep.href.replace(
                        /origin=[^&]+/,
                        'origin=' + encodeURIComponent(origin)
                    );
                    return { name: ep.name, href: newHref, p: ep.p };
                });
            }

            eps.sort((a, b) => a.p - b.p);

            let lineEpisodes = eps.map(ep => `${ep.name}$${ep.href}`);
            
            lines.push(origin);
            playlists.push(lineEpisodes);
        });

        if (lines.length === 0) {
            lines.push("默认");
            playlists.push([`暂无播放地址$${id}`]);
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

        let m3u8Match = html.match(/href="\/api\/m3u8\?origin=([^&]+)&amp;url=([^"]+)"/);
        if (!m3u8Match) {
            m3u8Match = html.match(/href="\/api\/m3u8\?origin=([^&]+)&url=([^"]+)"/);
        }
        if (m3u8Match) {
            let m3u8Origin = decodeURIComponent(m3u8Match[1]);
            let m3u8Url = m3u8Match[2];
            let playUrl = `${appConfig.siteUrl}/api/m3u8?origin=${encodeURIComponent(m3u8Origin)}&url=${m3u8Url}`;
            return JSON.stringify({
                parse: 0,
                Header: { "User-Agent": UA, "Referer": appConfig.siteUrl },
                url: playUrl
            });
        }

        let urlMatch = html.match(/"url"\s*[:=]\s*"([^"]+\.m3u8[^"]*)"/);
        if (urlMatch) {
            return JSON.stringify({
                parse: 0,
                Header: { "User-Agent": UA, "Referer": appConfig.siteUrl },
                url: urlMatch[1].replace(/\\/g, '')
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
