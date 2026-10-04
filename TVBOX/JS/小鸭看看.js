import { Crypto, load, _ } from 'assets://js/lib/cat.js';

let siteUrl = 'https://xykk.tv';
let siteKey = '';
let siteType = 0;
let t2sDict = {};

let headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
    'Referer': 'https://xykk.tv/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-User': '?1',
    'Sec-Fetch-Dest': 'document'
};

async function request(reqUrl, postData, agentSp, get) {
    let res = await req(reqUrl, {
        method: get ? 'get' : 'post',
        headers: agentSp ? Object.assign({}, headers, agentSp) : headers,
        data: postData || {},
        postType: get ? '' : 'form',
    });
    return res.content;
}

async function init(cfg) {
    siteKey = cfg.skey;
    siteType = cfg.stype;
    if (cfg.ext) {
        if (cfg.ext.startsWith('http')) {
            siteUrl = cfg.ext;
        }
    }
    try {
        let t2sRes = await request('https://gimyai.tw/template/gimyai/js/t2s.json?v=1', null, null, true);
        if (t2sRes) t2sDict = JSON.parse(t2sRes);
    } catch (e) {}
}

function s(text) {
    if (!text) return text;
    let res = '';
    for (let i = 0; i < text.length; i++) {
        res += t2sDict[text[i]] || text[i];
    }
    return res;
}

async function home(filter) {
    let classes = [
        { type_id: 'movies', type_name: '電影' },
        { type_id: 'tv', type_name: '電視劇' },
        { type_id: 'sc', type_name: '短劇' },
        { type_id: 'dm', type_name: '動漫' },
        { type_id: 'tvshow', type_name: '綜藝' }
    ];
    let filterObj = genFilterObj();
    return JSON.stringify({
        class: classes,
        filters: filterObj
    });
}

async function homeVod() {
    let html = await request(siteUrl + '/', null, null, true);
    const $ = load(html);
    let videos = [];
    $('.card').each((i, el) => {
        let id = $(el).find('a.card__thumb').attr('href');
        let name = $(el).find('.card__title').text().trim();
        let pic = $(el).find('img').attr('src');
        if (pic && pic.startsWith('/')) pic = siteUrl + pic;
        let remark = $(el).find('.card__status').text().trim();
        if (id && name) {
            videos.push({
                vod_id: id,
                vod_name: s(name),
                vod_pic: pic,
                vod_remarks: s(remark),
            });
        }
    });
    return JSON.stringify({
        list: videos,
    });
}

async function category(tid, pg, filter, extend) {
    if (pg <= 0) pg = 1;
    let params = [tid, '', '', '', '', '', '', '', pg, '', '', ''];
    if (extend['area']) params[1] = encodeURIComponent(extend['area']);
    if (extend['by']) params[2] = extend['by'];
    if (extend['class']) params[3] = extend['class'];
    if (extend['year']) params[11] = extend['year'];
    let url = `${siteUrl}/list/${params.join('-')}.html`;
    let html = await request(url, null, null, true);
    let videos = await parseVideos(html);
    return JSON.stringify({
        page: parseInt(pg),
        list: videos,
    });
}

async function detail(id) {
    try {
        const url = id.startsWith('http') ? id : siteUrl + id;
        const html = await request(url, null, null, true);
        const $ = load(html);
        let vod_name = $('h1.detail__title').text().trim();
        let vod_pic = $('.detail__poster img').attr('src');
        if (vod_pic && vod_pic.startsWith('/')) vod_pic = siteUrl + vod_pic;
        let vod_actor = '';
        let vod_director = '';
        let vod_class = '';
        let vod_year = '';
        let vod_area = '';
        let vod_remarks = $('.detail__meta .pill').text().trim();
        let actors = [];
        $('.detail__cast-line a').each((i, el) => {
            actors.push($(el).text().trim());
        });
        vod_actor = actors.join(',');
        let metas = [];
        $('.detail__meta span:not(.dot):not(.pill), .detail__meta a').each((i, el) => {
            metas.push($(el).text().trim());
        });
        if (metas.length > 0) vod_year = metas[0];
        if (metas.length > 1) vod_area = metas[1];
        if (metas.length > 2) vod_class = metas[2];
        let vod_content = $('#syn').text().trim() || $('.block p:last-child').text().trim();
        let playFrom = [];
        let playUrls = [];
        $('.source-tabs a.source-tab').each((i, el) => {
            let fromName = $(el).text().replace(/ᴴᴰ|HD/g, '').trim();
            let sid = $(el).attr('data-route-switch');
            let block = $(`.ep-grid[data-route-sid="${sid}"]`);
            if (block.length > 0 && fromName) {
                playFrom.push(s(fromName));
                let urls = [];
                block.find('a.ep-tile').each((j, a) => {
                    let epName = $(a).text().trim();
                    let epUrl = $(a).attr('href');
                    urls.push(s(epName) + '$' + epUrl);
                });
                playUrls.push(urls.join('#'));
            }
        });
        return JSON.stringify({
            list: [{
                vod_id: id,
                vod_name: s(vod_name),
                vod_pic: vod_pic,
                vod_class: s(vod_class),
                vod_area: s(vod_area),
                vod_year: vod_year,
                vod_actor: s(vod_actor),
                vod_director: s(vod_director),
                vod_content: s(vod_content),
                vod_remarks: s(vod_remarks),
                vod_play_from: playFrom.join('$$$'),
                vod_play_url: playUrls.join('$$$'),
            }]
        });
    } catch (e) {}
    return JSON.stringify({ list: [] });
}

async function search(wd, quick, pg) {
    let url = `${siteUrl}/search/${encodeURIComponent(wd)}----------${pg || 1}---.html`;
    const html = await request(url, null, null, true);
    const $ = load(html);
    let videos = [];
    $('.result-list .result').each((i, el) => {
        let id = $(el).find('a.result__thumb').attr('href');
        let name = $(el).find('.result__title').text().trim();
        let pic = $(el).find('img').attr('src');
        if (pic && pic.startsWith('/')) pic = siteUrl + pic;
        let remark = $(el).find('.result__metaline span:last-child').text().trim();
        if (id && name) {
            videos.push({
                vod_id: id,
                vod_name: s(name),
                vod_pic: pic,
                vod_remarks: s(remark),
            });
        }
    });
    return JSON.stringify({
        list: videos,
    });
}

async function play(flag, id, flags) {
    try {
        let url = id.startsWith('http') ? id : siteUrl + id;
        const html = await request(url, null, null, true);
        let playerMatch = html.match(/var\s+player_(?:aaaa|data)\s*=\s*({.+?});/);
        if (playerMatch && playerMatch[1]) {
            let playData = JSON.parse(playerMatch[1]);
            let videoUrl = playData.url;
            if (videoUrl.indexOf('.m3u8') > -1 || videoUrl.indexOf('.mp4') > -1) {
                return JSON.stringify({
                    parse: 0,
                    url: videoUrl,
                    header: headers
                });
            }
            let parseApi = '';
            if (videoUrl.startsWith('JD-')) {
                parseApi = `https://p.xiaoyakan.com/d/parse.php?url=${encodeURIComponent(videoUrl)}&_t=${Date.now()}`;
            } else {
                parseApi = `https://p.xiaoyakan.com/v/parse.php?url=${encodeURIComponent(videoUrl)}&_t=${Date.now()}`;
            }
            let apiRes = await request(parseApi, null, {
                'Referer': siteUrl,
                'Origin': siteUrl
            }, true);
            if (apiRes) {
                let jsonRes = JSON.parse(apiRes);
                if ((jsonRes.code === 200 || jsonRes.code === 1 || jsonRes.code === 0) && (jsonRes.url || jsonRes.video || jsonRes.playurl)) {
                    let realUrl = jsonRes.url || jsonRes.video || jsonRes.playurl;
                    return JSON.stringify({
                        parse: 0,
                        url: realUrl,
                        header: {
                            'User-Agent': headers['User-Agent'],
                            'Referer': 'https://p.xiaoyakan.com/'
                        }
                    });
                }
            }
        }
    } catch (e) {}
    return JSON.stringify({
        parse: 1,
        url: id.startsWith('http') ? id : siteUrl + id,
        header: headers
    });
}

async function parseVideos(html) {
    const $ = load(html);
    let videos = [];
    $('.grid > a.poster').each((i, el) => {
        let id = $(el).attr('href');
        let name = $(el).find('.poster__title').text().trim();
        let picNode = $(el).find('.poster__thumb img');
        let pic = picNode.attr('src') || picNode.attr('data-original');
        if (pic && pic.startsWith('/')) pic = siteUrl + pic;
        let remark = $(el).find('.card__status').text().trim();
        if (id && name) {
            videos.push({
                vod_id: id,
                vod_name: s(name),
                vod_pic: pic,
                vod_remarks: s(remark),
            });
        }
    });
    return videos;
}

function genFilterObj() {
    let sortList = [
        { n: '綜合排序', v: '' },
        { n: '最新上架', v: 'time_add' },
        { n: '最近更新', v: 'time' },
        { n: '周人氣', v: 'hits_week' },
        { n: '總人氣', v: 'hits' }
    ];
    let years = [
        { n: '全部', v: '' }, { n: '2026', v: '2026' }, { n: '2025', v: '2025' }, 
        { n: '2024', v: '2024' }, { n: '2023', v: '2023' }, { n: '2022', v: '2022' }, 
        { n: '2021', v: '2021' }, { n: '2020', v: '2020' }, { n: '2019', v: '2019' }, 
        { n: '2018', v: '2018' }, { n: '2017', v: '2017' }, { n: '2016', v: '2016' }
    ];
    let movieAreas = [
        { n: '全部', v: '' }, { n: '美國', v: '美國' }, { n: '歐美', v: '歐美' }, { n: '韓國', v: '韓國' },
        { n: '中國大陸', v: '中國大陸' }, { n: '大陸', v: '大陸' }, { n: '內地', v: '內地' }, { n: '日本', v: '日本' },
        { n: '台灣', v: '台灣' }, { n: '香港', v: '香港' }, { n: '泰國', v: '泰國' }, { n: '英國', v: '英國' },
        { n: '新加坡', v: '新加坡' }, { n: '其他', v: '其他' }
    ];
    let tvAreas = [
        { n: '全部', v: '' }, { n: '中國大陸', v: '中國大陸' }, { n: '大陸', v: '大陸' }, { n: '韓國', v: '韓國' },
        { n: '日本', v: '日本' }, { n: '台灣', v: '台灣' }, { n: '香港', v: '香港' }, { n: '美國', v: '美國' },
        { n: '歐美', v: '歐美' }, { n: '泰國', v: '泰國' }, { n: '英國', v: '英國' }, { n: '法國', v: '法國' },
        { n: '新加坡', v: '新加坡' }, { n: '越南', v: '越南' }, { n: '其他', v: '其他' }
    ];
    let showAreas = [
        { n: '全部', v: '' }, { n: '韓國', v: '韓國' }, { n: '中國大陸', v: '中國大陸' }, { n: '中國', v: '中國' },
        { n: '大陸', v: '大陸' }, { n: '日本', v: '日本' }, { n: '美國', v: '美國' }, { n: '歐美', v: '歐美' },
        { n: '台灣', v: '台灣' }, { n: '臺灣', v: '臺灣' }, { n: '香港', v: '香港' }
    ];
    let dmAreas = [
        { n: '全部', v: '' }, { n: '中國大陸', v: '中國大陸' }, { n: '中國', v: '中國' }, { n: '大陸', v: '大陸' },
        { n: '日本', v: '日本' }, { n: '美國', v: '美國' }, { n: '歐美', v: '歐美' }, { n: '台灣', v: '台灣' },
        { n: '臺灣', v: '臺灣' }, { n: '香港', v: '香港' }, { n: '韓國', v: '韓國' }
    ];
    let scAreas = [
        { n: '全部', v: '' }, { n: '中國大陸', v: '中國大陸' }, { n: '臺灣', v: '臺灣' }, { n: '香港', v: '香港' },
        { n: '韓國', v: '韓國' }, { n: '日本', v: '日本' }, { n: '美國', v: '美國' }, { n: '泰國', v: '泰國' }, { n: '其他', v: '其他' }
    ];
    return {
        'movies': [
            { key: 'area', name: '地區', value: movieAreas },
            { key: 'year', name: '年份', value: years },
            { key: 'by', name: '排序', value: sortList }
        ],
        'tv': [
            { key: 'area', name: '地區', value: tvAreas },
            { key: 'year', name: '年份', value: years },
            { key: 'by', name: '排序', value: sortList }
        ],
        'sc': [
            { key: 'area', name: '地區', value: scAreas },
            { key: 'year', name: '年份', value: years },
            { key: 'by', name: '排序', value: sortList }
        ],
        'dm': [
            { key: 'area', name: '地區', value: dmAreas },
            { key: 'year', name: '年份', value: years },
            { key: 'by', name: '排序', value: sortList }
        ],
        'tvshow': [
            { key: 'area', name: '地區', value: showAreas },
            { key: 'year', name: '年份', value: years },
            { key: 'by', name: '排序', value: sortList }
        ]
    };
}

export function __jsEvalReturn() {
    return {
        init: init,
        home: home,
        homeVod: homeVod,
        category: category,
        detail: detail,
        play: play,
        search: search,
    };
}