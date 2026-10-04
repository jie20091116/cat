import cheerio from 'assets://js/lib/cheerio.min.js';

const appConfig = {
    siteName: "金桔影视",
    siteUrl: "https://htsdaz.com"
}
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36";

async function init(ext) {
    console.log("初始化爬虫:", appConfig.siteName);
}

const movieClass = [
    { "n": "全部", "v": "" }, { "n": "喜剧", "v": "喜剧" }, { "n": "爱情", "v": "爱情" },
    { "n": "恐怖", "v": "恐怖" }, { "n": "动作", "v": "动作" }, { "n": "科幻", "v": "科幻" },
    { "n": "剧情", "v": "剧情" }, { "n": "战争", "v": "战争" }, { "n": "警匪", "v": "警匪" },
    { "n": "犯罪", "v": "犯罪" }, { "n": "动画", "v": "动画" }, { "n": "奇幻", "v": "奇幻" },
    { "n": "武侠", "v": "武侠" }, { "n": "冒险", "v": "冒险" }, { "n": "枪战", "v": "枪战" },
    { "n": "悬疑", "v": "悬疑" }, { "n": "惊悚", "v": "惊悚" }, { "n": "经典", "v": "经典" },
    { "n": "青春", "v": "青春" }, { "n": "文艺", "v": "文艺" }, { "n": "微电影", "v": "微电影" },
    { "n": "古装", "v": "古装" }, { "n": "历史", "v": "历史" }, { "n": "运动", "v": "运动" },
    { "n": "农村", "v": "农村" }, { "n": "儿童", "v": "儿童" }, { "n": "网络电影", "v": "网络电影" }
];

const tvClass = [
    { "n": "全部", "v": "" }, { "n": "国产剧", "v": "国产剧" }, { "n": "港剧", "v": "港剧" },
    { "n": "欧美剧", "v": "欧美剧" }, { "n": "日剧", "v": "日剧" }, { "n": "台剧", "v": "台剧" },
    { "n": "泰剧", "v": "泰剧" }, { "n": "韩剧", "v": "韩剧" }, { "n": "海外剧", "v": "海外剧" },
    { "n": "Netflix自制剧", "v": "Netflix自制剧" }
];

const areaFilter = [
    { "n": "全部", "v": "" }, { "n": "大陆", "v": "大陆" }, { "n": "香港", "v": "香港" },
    { "n": "台湾", "v": "台湾" }, { "n": "美国", "v": "美国" }, { "n": "法国", "v": "法国" },
    { "n": "英国", "v": "英国" }, { "n": "日本", "v": "日本" }, { "n": "韩国", "v": "韩国" },
    { "n": "德国", "v": "德国" }, { "n": "泰国", "v": "泰国" }, { "n": "印度", "v": "印度" },
    { "n": "意大利", "v": "意大利" }, { "n": "西班牙", "v": "西班牙" }, { "n": "加拿大", "v": "加拿大" },
    { "n": "其他", "v": "其他" }
];

const langFilter = [
    { "n": "全部", "v": "" }, { "n": "国语", "v": "国语" }, { "n": "英语", "v": "英语" },
    { "n": "粤语", "v": "粤语" }, { "n": "闽南语", "v": "闽南语" }, { "n": "韩语", "v": "韩语" },
    { "n": "日语", "v": "日语" }, { "n": "法语", "v": "法语" }, { "n": "德语", "v": "德语" },
    { "n": "其它", "v": "其它" }
];

function getYearFilter() {
    let years = [{ "n": "全部", "v": "" }];
    const currentYear = new Date().getFullYear();
    for (let y = currentYear; y >= 2000; y--) {
        years.push({ "n": String(y), "v": String(y) });
    }
    return { "key": "year", "name": "年份", "value": years };
}

const myFilters = {
    "1": [
        { "key": "class", "name": "类型", "value": movieClass },
        { "key": "area", "name": "地区", "value": areaFilter },
        { "key": "lang", "name": "语言", "value": langFilter },
        getYearFilter()
    ],
    "2": [
        { "key": "class", "name": "类型", "value": tvClass },
        { "key": "area", "name": "地区", "value": areaFilter },
        { "key": "lang", "name": "语言", "value": langFilter },
        getYearFilter()
    ],
    "3": [
        { "key": "area", "name": "地区", "value": areaFilter },
        { "key": "lang", "name": "语言", "value": langFilter },
        getYearFilter()
    ],
    "4": [
        { "key": "area", "name": "地区", "value": areaFilter },
        { "key": "lang", "name": "语言", "value": langFilter },
        getYearFilter()
    ],
    "34": [
        { "key": "area", "name": "地区", "value": areaFilter },
        { "key": "lang", "name": "语言", "value": langFilter },
        getYearFilter()
    ]
};

async function home(filter) {
    return JSON.stringify({
        class: [
            { type_id: "1", type_name: "电影" },
            { type_id: "2", type_name: "电视剧" },
            { type_id: "3", type_name: "综艺" },
            { type_id: "4", type_name: "动漫" },
            { type_id: "34", type_name: "短剧" }
        ],
        filters: myFilters
    });
}

function buildCategoryUrl(tid, pg, extend) {
    let classVal = extend.class || '';
    let areaVal = extend.area || '';
    let langVal = extend.lang || '';
    let yearVal = extend.year || '';

    if (!classVal && !areaVal && !langVal && !yearVal) {
        return `${appConfig.siteUrl}/stream/${tid}_${pg}.html`;
    }
    let filter = `${classVal}-${areaVal}-${langVal}-${yearVal}------`;
    return `${appConfig.siteUrl}/stream/${tid}_${pg}/${filter}.html`;
}

async function category(tid, pg, filter, extend) {
    pg = pg || 1;
    extend = extend || {};

    let url = buildCategoryUrl(tid, pg, extend);

    try {
        const html = (await req(url)).content;
        const $ = cheerio.load(html);
        let list = [];

        $("ul.stui-vodlist.clearfix .stui-vodlist__thumb.lazyload").each(function (index, el) {
            let vod_id = $(el).attr("href");
            let vod_name = $(el).attr("title");
            let vod_pic = $(el).attr("data-original");
            let vod_remarks = $(el).find(".pic-text").text().trim();

            if (vod_id && vod_name) {
                list.push({ vod_id, vod_name, vod_pic, vod_remarks });
            }
        });

        let pagecount = 1;
        $("a:contains('尾页')").each(function () {
            let href = $(this).attr("href");
            if (href) {
                let m = href.match(/\/stream\/\d+_(\d+)/);
                if (m) {
                    let p = parseInt(m[1]);
                    if (p > pagecount) pagecount = p;
                }
            }
        });

        if (pagecount <= 1) {
            let maxPage = 1;
            $(".stui-page a, .mac_pages a").each(function () {
                let href = $(this).attr("href");
                if (href) {
                    let m = href.match(/\/stream\/\d+_(\d+)/);
                    if (m) {
                        let p = parseInt(m[1]);
                        if (p > maxPage) maxPage = p;
                    }
                }
            });
            pagecount = maxPage;
        }

        return JSON.stringify({ list, pagecount });
    } catch (e) {
        console.error("分类列表获取失败:", e.message);
        return JSON.stringify({ list: [], pagecount: 0 });
    }
}

async function search(wd, quick, page) {
    if (page >= 2) return JSON.stringify({ list: [], pagecount: 1 });
    try {
        const url = `${appConfig.siteUrl}/search/${encodeURIComponent(wd)}.html`;
        const html = (await req(url)).content;
        const $ = cheerio.load(html);
        let list = [];

        $("ul.stui-vodlist.clearfix .stui-vodlist__thumb.lazyload").each(function (i, el) {
            let vod_id = $(el).attr("href");
            let vod_name = $(el).attr("title");
            let vod_pic = $(el).attr("data-original");
            let vod_remarks = $(el).find(".pic-text").text().trim();

            if (vod_id && vod_name) {
                list.push({ vod_id, vod_name, vod_pic, vod_remarks });
            }
        });

        return JSON.stringify({ list, pagecount: 1 });
    } catch (e) {
        console.error("搜索失败:", e.message);
        return JSON.stringify({ list: [] });
    }
}

async function detail(id) {
    try {
        const html = (await req(appConfig.siteUrl + id)).content;
        const $ = cheerio.load(html);

        const vod_name = $('.stui-content__detail h1, .stui-content__detail .title').first().text().trim();
        const imgSrc = $('.stui-content__thumb img').attr("data-original") || '';
        const vod_pic = imgSrc ? (imgSrc.startsWith('http') ? imgSrc : appConfig.siteUrl + imgSrc) : '';

        let vod_actor = '';
        let vod_director = '';
        let vod_remarks = '';
        let vod_year = '';
        let vod_area = '';

        $('.stui-content__detail p.data').each((i, el) => {
            const text = $(el).text();
            if (text.includes('主演')) {
                vod_actor = $(el).find('a').map(function () { return $(this).text().trim(); }).get().join(',');
            } else if (text.includes('导演')) {
                vod_director = $(el).find('a').map(function () { return $(this).text().trim(); }).get().join(',');
            } else if (text.includes('状态')) {
                vod_remarks = text.replace(/.*状态[：:]/g, '').trim();
            } else if (text.includes('年份')) {
                vod_year = $(el).find('a').text().trim();
            } else if (text.includes('地区')) {
                vod_area = $(el).find('a').text().trim();
            }
        });

        const vod_content = $('.stui-content__detail .detail, .stui-content__detail .desc').text().trim();

        let rawLines = [];
        let rawPlaylists = [];

        $('.nav-tabs li a').each((i, el) => {
            const lineName = $(el).text().trim();
            if (lineName && lineName !== '全部') {
                rawLines.push(lineName);
            }
        });

        $('.stui-content__playlist').each((lineIndex, poolEl) => {
            const episodes = [];
            $(poolEl).find('a').each((episodeIndex, epEl) => {
                const name = $(epEl).text().trim();
                const href = $(epEl).attr('href') || '';
                if (name && href) {
                    episodes.push(`${name}$${href}`);
                }
            });
            rawPlaylists.push(episodes);
        });

        if (rawLines.length === 0 && rawPlaylists.length > 0) {
            for (let i = 0; i < rawPlaylists.length; i++) {
                rawLines.push(`线路${i + 1}`);
            }
        }

        let finalLines = [];
        let finalPlaylists = [];
        for (let i = 0; i < rawLines.length; i++) {
            if (rawPlaylists[i] && rawPlaylists[i].length > 0) {
                finalLines.push(rawLines[i]);
                finalPlaylists.push(rawPlaylists[i]);
            }
        }

        const { vod_play_from, vod_play_url } = buildVodPlayData(finalLines, finalPlaylists);

        const vod = {
            vod_id: id, vod_name, vod_pic, vod_actor, vod_director,
            vod_remarks, vod_year, vod_area, vod_content,
            vod_play_from, vod_play_url
        };

        return JSON.stringify({ list: [vod] });
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

function base64Decode(str) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
    let output = '';
    let i = 0;
    str = str.replace(/[^A-Za-z0-9\+\/\=]/g, '');
    while (i < str.length) {
        let enc1 = chars.indexOf(str.charAt(i++));
        let enc2 = chars.indexOf(str.charAt(i++));
        let enc3 = chars.indexOf(str.charAt(i++));
        let enc4 = chars.indexOf(str.charAt(i++));
        let chr1 = (enc1 << 2) | (enc2 >> 4);
        let chr2 = ((enc2 & 15) << 4) | (enc3 >> 2);
        let chr3 = ((enc3 & 3) << 6) | enc4;
        output += String.fromCharCode(chr1);
        if (enc3 !== 64) output += String.fromCharCode(chr2);
        if (enc4 !== 64) output += String.fromCharCode(chr3);
    }
    return decodeURIComponent(escape(output));
}

function extractVideoUrl(html) {
    const partsMatch = html.match(/const\s+parts\s*=\s*\[([^\]]+)\]/);
    if (partsMatch) {
        try {
            const parts = JSON.parse('[' + partsMatch[1] + ']');
            let base64Str = '';
            for (let i = 0; i < parts.length; i++) {
                base64Str += parts[i];
            }
            const decoded = base64Decode(base64Str);
            if (decoded && decoded.startsWith('http')) {
                return decoded;
            }
        } catch (e) {
            console.error("base64解码失败:", e.message);
        }
    }

    const playerMatch = html.match(/var\s+player_aaaa[\s\S]*?"url"\s*:\s*"([^"]+)"/);
    if (playerMatch) {
        return playerMatch[1].replace(/\\/g, '');
    }

    return '';
}

async function play(flag, id, flags) {
    try {
        const html = (await req(`${appConfig.siteUrl}${id}`)).content;
        const url = extractVideoUrl(html);

        if (url) {
            if (url.endsWith('.m3u8') || url.endsWith('.mp4') || (url.startsWith('http') && !url.includes('.html'))) {
                return JSON.stringify({
                    parse: 0,
                    Header: { "User-Agent": UA, "Referer": appConfig.siteUrl },
                    url: url
                });
            }
            return JSON.stringify({
                parse: 1,
                Header: { "User-Agent": UA, "Referer": appConfig.siteUrl },
                url: url
            });
        }

        const $ = cheerio.load(html);
        const iframeSrc = $('#playerIframe').attr('src') || $('iframe').attr('src');
        if (iframeSrc) {
            return JSON.stringify({
                parse: 1,
                Header: { "User-Agent": UA, "Referer": appConfig.siteUrl },
                url: iframeSrc
            });
        }

        return JSON.stringify({ parse: 0, url: "" });
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
