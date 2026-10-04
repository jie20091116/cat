import { load, Crypto } from 'assets://js/lib/cat.js';

var HOST;
const PC_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36';
const DefHeader = { 'User-Agent': PC_UA };
const KParams = {
    headers: { 'User-Agent': PC_UA },
    timeout: 5000
};

async function init(cfg) {
    try {
        let host = cfg.ext?.host?.trim() || 'https://www.agedm.io';
        HOST = host.replace(/\/$/, '');
        KParams.headers.Referer = HOST;
        const parseTimeout = parseInt(cfg.ext?.timeout?.trim(), 10);
        KParams.timeout = parseTimeout > 0 ? parseTimeout : 5000;
        KParams.resHtml = await request(HOST);
    } catch (e) {
        console.error('初始化参数失败：', e.message);
    }
}

async function home(filter) {
    try {
        const classes = [
            { type_id: 'all', type_name: '全部' },
            { type_id: 'TV', type_name: 'TV' },
            { type_id: '剧场版', type_name: '剧场版' },
            { type_id: 'OVA', type_name: 'OVA' }
        ];
        const filterConfig = [
            {
                key: "area", name: "地区",
                value: [
                    { n: "全部", v: "all" }, { n: "日本", v: "日本" },
                    { n: "中国", v: "中国" }, { n: "欧美", v: "欧美" }
                ]
            },
            {
                key: "letter", name: "首字母",
                value: [
                    { n: "全部", v: "all" },
                    { n: "A", v: "A" }, { n: "B", v: "B" }, { n: "C", v: "C" }, { n: "D", v: "D" },
                    { n: "E", v: "E" }, { n: "F", v: "F" }, { n: "H", v: "H" }, { n: "I", v: "I" },
                    { n: "J", v: "J" }, { n: "K", v: "K" }, { n: "L", v: "L" }, { n: "M", v: "M" },
                    { n: "N", v: "N" }, { n: "O", v: "O" }, { n: "P", v: "P" }, { n: "Q", v: "Q" },
                    { n: "R", v: "R" }, { n: "S", v: "S" }, { n: "T", v: "T" }, { n: "U", v: "U" },
                    { n: "V", v: "V" }, { n: "W", v: "W" }, { n: "X", v: "X" }, { n: "Y", v: "Y" },
                    { n: "Z", v: "Z" }
                ]
            },
            {
                key: "year", name: "年份",
                value: [
                    { n: "全部", v: "all" },
                    { n: "2026", v: "2026" }, { n: "2025", v: "2025" }, { n: "2024", v: "2024" },
                    { n: "2023", v: "2023" }, { n: "2022", v: "2022" }, { n: "2021", v: "2021" },
                    { n: "2020", v: "2020" }, { n: "2019", v: "2019" }, { n: "2018", v: "2018" },
                    { n: "2017", v: "2017" }, { n: "2016", v: "2016" }, { n: "2015", v: "2015" },
                    { n: "2014", v: "2014" }, { n: "2013", v: "2013" }, { n: "2012", v: "2012" },
                    { n: "2011", v: "2011" }, { n: "2010", v: "2010" }, { n: "2009", v: "2009" },
                    { n: "2008", v: "2008" }, { n: "2007", v: "2007" }, { n: "2006", v: "2006" },
                    { n: "2005", v: "2005" }, { n: "2004", v: "2004" }, { n: "2003", v: "2003" },
                    { n: "2002", v: "2002" }, { n: "2001", v: "2001" }, { n: "2000以前", v: "2000以前" }
                ]
            },
            {
                key: "quarter", name: "季度",
                value: [
                    { n: "全部", v: "all" },
                    { n: "1月", v: "1" }, { n: "4月", v: "4" },
                    { n: "7月", v: "7" }, { n: "10月", v: "10" }
                ]
            },
            {
                key: "status", name: "状态",
                value: [
                    { n: "全部", v: "all" },
                    { n: "连载", v: "连载" }, { n: "完结", v: "完结" }, { n: "未播放", v: "未播放" }
                ]
            },
            {
                key: "type", name: "类型",
                value: [
                    { n: "全部", v: "all" },
                    { n: "搞笑", v: "搞笑" },{ n: "运动", v: "运动" },{ n: "励志", v: "励志" },
                    { n: "热血", v: "热血" },{ n: "战斗", v: "战斗" },{ n: "竞技", v: "竞技" },
                    { n: "校园", v: "校园" },{ n: "青春", v: "青春" },{ n: "爱情", v: "爱情" },
                    { n: "恋爱", v: "恋爱" },{ n: "冒险", v: "冒险" },{ n: "后宫", v: "后宫" },
                    { n: "百合", v: "百合" },{ n: "治愈", v: "治愈" },{ n: "萝莉", v: "萝莉" },
                    { n: "魔法", v: "魔法" },{ n: "悬疑", v: "悬疑" },{ n: "推理", v: "推理" },
                    { n: "奇幻", v: "奇幻" },{ n: "科幻", v: "科幻" },{ n: "游戏", v: "游戏" },
                    { n: "神魔", v: "神魔" },{ n: "恐怖", v: "恐怖" },{ n: "血腥", v: "血腥" },
                    { n: "机战", v: "机战" },{ n: "战争", v: "战争" },{ n: "犯罪", v: "犯罪" },
                    { n: "历史", v: "历史" },{ n: "社会", v: "社会" },{ n: "职场", v: "职场" },
                    { n: "剧情", v: "剧情" },{ n: "伪娘", v: "伪娘" },{ n: "耽美", v: "耽美" },
                    { n: "童年", v: "童年" },{ n: "教育", v: "教育" },{ n: "亲子", v: "亲子" },
                    { n: "真人", v: "真人" },{ n: "歌舞", v: "歌舞" },{ n: "肉番", v: "肉番" },
                    { n: "美少女", v: "美少女" },{ n: "轻小说", v: "轻小说" },{ n: "吸血鬼", v: "吸血鬼" },
                    { n: "女性向", v: "女性向" },{ n: "泡面番", v: "泡面番" },{ n: "欢乐向", v: "欢乐向" }
                ]
            },
            {
                key: "source", name: "资源",
                value: [
                    { n: "全部", v: "all" },
                    { n: "BDRIP", v: "BDRIP" }, { n: "AGE-RIP", v: "AGE-RIP" }
                ]
            },
            {
                key: "sort", name: "排序",
                value: [
                    { n: "全部", v: "time" },
                    { n: "时间", v: "time" }, { n: "点击量", v: "点击量" }
                ]
            }
        ];
        const filters = { all: filterConfig, TV: filterConfig, "剧场版": filterConfig, OVA: filterConfig };
        return JSON.stringify({ class: classes, filters });
    } catch (e) {
        console.error('获取分类失败：', e.message);
        return JSON.stringify({ class: [], filters: {} });
    }
}

async function homeVod() {
    try {
        const VODS = getVodList(KParams.resHtml, true);
        return JSON.stringify({ list: VODS });
    } catch (e) {
        console.error('推荐页获取失败：', e.message);
        return JSON.stringify({ list: [] });
    }
}

async function category(tid, pg, filter, extend) {
    try {
        pg = parseInt(pg, 10) || 1;
        const year = extend?.year ? encodeURIComponent(extend.year) : 'all';
        const letter = extend?.letter ? encodeURIComponent(extend.letter) : 'all';
        const type = extend?.type ? encodeURIComponent(extend.type) : 'all';
        const source = extend?.source ? encodeURIComponent(extend.source) : 'all';
        const sort = extend?.sort ? encodeURIComponent(extend.sort) : 'time';
        const area = extend?.area ? encodeURIComponent(extend.area) : 'all';
        const quarter = extend?.quarter ? encodeURIComponent(extend.quarter) : 'all';
        const status = extend?.status ? encodeURIComponent(extend.status) : 'all';
        const cateUrl = `${HOST}/catalog/${tid}-${year}-${letter}-${type}-${source}-${sort}-${pg}-${area}-${quarter}-${status}`;
        const resHtml = await request(cateUrl);
        const VODS = getVodList(resHtml);
        return JSON.stringify({ list: VODS, page: pg, pagecount: 999, limit: 30, total: 30 * 999 });
    } catch (e) {
        console.error('类别页获取失败：', e.message);
        return JSON.stringify({ list: [], page: 1, pagecount: 0, limit: 30, total: 0 });
    }
}

async function search(wd, quick, pg) {
    try {
        pg = parseInt(pg, 10) || 1;
        const searchUrl = `${HOST}/search?query=${encodeURIComponent(wd)}&page=${pg}`;
        const resHtml = await request(searchUrl);
        const VODS = getVodList(resHtml);
        return JSON.stringify({ list: VODS, page: pg, pagecount: 10, limit: 30, total: 300 });
    } catch (e) {
        console.error('搜索页获取失败：', e.message);
        return JSON.stringify({ list: [], page: 1, pagecount: 0, limit: 30, total: 0 });
    }
}

function getVodList(khtml, hm = false) {
    try {
        if (!khtml) throw new Error('源码为空');
        const kvods = [];
        const $ = load(khtml);
        const listArr = hm ? $('.video_item').get() : $('.video_cover').get();
        for (const it of listArr) {
            const $it = $(it);
            const a = $it.find('a');
            const kname = dealStr(a.text().trim() || a.attr('title'), '名称');
            const kurl = dealStr(a.attr('href'), 'href');
            const poster = $it.find('img');
            let pic = poster.attr('data-original') || poster.attr('src');
            if (pic && pic.startsWith('/')) pic = HOST + pic;
            const kpic = dealStr(pic, '图片');
            const kremarks = dealStr($it.find('span').text(), '状态');
            kvods.push({
                vod_name: kname,
                vod_pic: kpic,
                vod_remarks: kremarks,
                vod_id: `${kurl}@${kname}@${kpic}@${kremarks}`
            });
        }
        return kvods;
    } catch (e) {
        console.error(`生成视频列表失败：`, e.message);
        return [];
    }
}

async function detail(ids) {
    try {
        const [id, kname, kpic, kremarks] = ids.split('@');
        const rawUrl = /^http/.test(id) ? id : `${HOST}${id}`;
        const detailUrl = rawUrl.replace(/https?:\/\/[^\/]+/, HOST);
        const resHtml = await request(detailUrl);
        if (!resHtml) throw new Error('源码请求失败');
        const $ = load(resHtml);
        const intros = $('.detail_imform_list').html() || '';
        const ktabs = $('.nav-item:has(button)').get().map((it, idx) => {
            const btn = $(it).find('button');
            return dealStr(`${btn.text()}(${btn.attr('data-bs-target').replace('#playlist-source-','')})`, `线-${idx+1}`);
        });
        const kurls = $('.video_detail_episode').get().map(item => {
            const arr = $(item).find('li a').get().map(it => {
                const $it = $(it);
                return dealStr($it.text(), 'noEpi') + '$' + dealStr($it.attr('href'), 'noUrl');
            });
            return arr.join('#');
        });
        const VOD = {
            vod_id: detailUrl,
            vod_name: kname,
            vod_pic: kpic,
            type_name: cutStr(intros, '剧情类型：', '</li', '类型'),
            vod_remarks: kremarks,
            vod_year: cutStr(intros, '首播时间：', '</li', '1000'),
            vod_area: cutStr(intros, '地区：', '</li', '地区'),
            vod_lang: '语言',
            vod_director: cutStr(intros, '原作：', '</li', '原作'),
            vod_actor: cutStr(intros, '主演：', '</li', '主演'),
            vod_content: cutStr(intros, 'video_detail_desc£>', '</div>', '简介'),
            vod_play_from: ktabs.join('$$$'),
            vod_play_url: kurls.join('$$$')
        };
        return JSON.stringify({ list: [VOD] });
    } catch (e) {
        console.error('详情页获取失败：', e.message);
        return JSON.stringify({ list: [] });
    }
}

function uuid() {
    const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
    const arr = [];
    arr[8] = arr[13] = arr[18] = arr[23] = "-";
    arr[14] = "4";
    for (let i = 0; i < 36; i++) {
        if (!arr[i]) {
            const r = Math.random() * 16 | 0;
            arr[i] = chars[(i === 19 ? (r & 0x3 | 0x8) : r)];
        }
    }
    return arr.join("");
}

async function play(flag, ids, flags) {
    try {
        const playUrl = /^http/.test(ids) ? ids : `${HOST}${ids}`;
        let kurl = '';
        const resHtml = await request(playUrl);
        const $ = load(resHtml);
        const iframesrc = $('#iframeForVideo').attr('src') || '';
        if (iframesrc) {
            const iframeresHtml = await request(iframesrc);
            let rawVurl = cutStr(iframeresHtml, 'Vurl = ', ';');
            let Vurl = rawVurl.replace(/^["']|["']$/g, '').trim();
            if (!/m3u8|mp4|mkv/.test(Vurl)) {
                const Ref = cutStr(iframeresHtml, 'Ref = "', '";');
                const Time = cutStr(iframeresHtml, 'Time = "', '";');
                const Version = cutStr(iframeresHtml, 'Version = "', '";');
                const idList = cutStr(iframeresHtml, 'id="', '"', 'null', true, 1, true);
                const mockHtmlMeta = { contentTypeId: idList[0], viewportId: idList[1] };
                const apiUrl = 'https://jx.wuzhoupai.com:8443/vip/Api.php';
                const jxhost = 'jx.wuzhoupai.com';
                const currentUuid = uuid();
                const reqData = { url: Vurl, wap: '0', ios: '0', host: jxhost, referer: Ref, time: Time };
                const encryptParams = hxm_encrypt(JSON.stringify(reqData)).toUpperCase();
                const signRaw = `${jxhost} | ${currentUuid} | ${Time} | ${Version} | ${encryptParams}`;
                const sign = hxm_encrypt(signRaw);
                const apiRes = await request(apiUrl, {
                    method: 'post',
                    postType: 'json',
                    headers: {
                        'x-requested-with': 'XMLHttpRequest',
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'Accept': 'application/json, text/javascript, */*; q=0.01',
                        'Video-Parse-Uuid': currentUuid,
                        'Video-Parse-Time': Time,
                        'Video-Parse-Version': Version,
                        'Video-Parse-Sign': sign
                    },
                    data: { Params: encryptParams }
                });
                const apiResjson = safeParseJSON(apiRes);
                const result = decryptData(apiResjson, mockHtmlMeta);
                kurl = result.url;
            } else {
                kurl = Vurl;
            }
        }
        return JSON.stringify({ jx: 0, parse: 0, url: kurl, header: DefHeader });
    } catch (e) {
        console.error('播放失败：', e.message);
        return JSON.stringify({ jx: 0, parse: 0, url: '', header: {} });
    }
}

// 工具函数
function dealStr(str, defaultValue = '') {
    if (str === null || typeof str === 'undefined' || String(str).trim() === '') return defaultValue;
    return String(str).replace(/(&nbsp;|\u00A0|\s)+/g, ' ').trim().replace(/\s+/g, ' ') || defaultValue;
}

function cutStr(str, prefix = '', suffix = '', defaultVal = 'cutFaile', clean = true, i = 1, all = false) {
    try {
        if (typeof str !== 'string' || !str) throw new Error('被截取对象需为非空字符串');
        const cleanStr = cs => String(cs).replace(/<[^>]*?>/g, ' ').replace(/(&nbsp;|\u00A0|\s)+/g, ' ').trim().replace(/\s+/g, ' ');
        const esc = s => String(s).replace(/[.*+?${}()|[\]\\/^]/g, '\\$&');
        const pre = esc(prefix).replace(/£/g, '[^]*?');
        const end = esc(suffix);
        const regex = new RegExp(`${pre ? pre : '^'}([^]*?)${end ? end : '$'}`, 'g');
        const matchIterator = str.matchAll(regex);
        if (all) {
            const matchArr = [...matchIterator];
            return matchArr.length ? matchArr.map(it => {
                const val = it[1] ?? defaultVal;
                return clean && val !== defaultVal ? cleanStr(val) : val;
            }) : [defaultVal];
        }
        i = parseInt(i, 10);
        if (isNaN(i) || i < 1) throw new Error('序号必须为正整数');
        let tgIdx = i - 1, matchIdx = 0;
        for (const match of matchIterator) {
            if (matchIdx++ === tgIdx) {
                const result = match[1] ?? defaultVal;
                return clean && result !== defaultVal ? cleanStr(result) : result;
            }
        }
        return defaultVal;
    } catch (e) {
        console.error(`字符串截取失败：`, e.message);
        return all ? ['cutErr'] : 'cutErr';
    }
}

function safeParseJSON(jStr) {
    try { return JSON.parse(jStr); } catch (e) { return null; }
}

async function request(reqUrl, options = {}) {
    try {
        if (typeof reqUrl !== 'string' || !reqUrl.trim()) throw new Error('reqUrl需为字符串且非空');
        if (typeof options !== 'object' || Array.isArray(options) || !options) throw new Error('options类型需为非null对象');
        options.method = options.method?.toLowerCase() || 'get';
        if (['get', 'head'].includes(options.method)) {
            delete options.data;
            delete options.postType;
        } else {
            options.data = options.data ?? '';
            options.postType = options.postType?.toLowerCase() || 'form';
        }
        let { headers, timeout, toBase64 = false, ...restOpts } = options;
        const optObj = {
            headers: (headers && typeof headers === 'object' && !Array.isArray(headers)) ? headers : KParams.headers,
            timeout: parseInt(timeout, 10) > 0 ? parseInt(timeout, 10) : KParams.timeout,
            buffer: toBase64 ? 2 : 0,
            ...restOpts
        };
        const res = await req(reqUrl, optObj);
        if (options.withHeaders) {
            const resHeaders = res.headers && typeof res.headers === 'object' && !Array.isArray(res.headers) ? res.headers : {};
            return JSON.stringify({ ...resHeaders, body: res?.content ?? '' });
        }
        return res?.content ?? '';
    } catch (e) {
        console.error(`${reqUrl}→请求失败：`, e.message);
        return options?.withHeaders ? JSON.stringify({ body: '' }) : '';
    }
}

// AES解密工具
function decryptOuterAesCbc(hexCipherText, md5String) {
    const hexWords = Crypto.enc.Hex.parse(hexCipherText);
    const base64CipherText = Crypto.enc.Base64.stringify(hexWords);
    const rawKey = md5String.substring(0, 16);
    const rawIv = md5String.substring(16, 32);
    const cryptoKey = Crypto.enc.Latin1.parse(rawKey);
    const cryptoIv = Crypto.enc.Latin1.parse(rawIv);
    const decryptedWords = Crypto.AES.decrypt(base64CipherText, cryptoKey, { iv: cryptoIv, mode: Crypto.mode.CBC, padding: Crypto.pad.Pkcs7 });
    return Crypto.enc.Utf8.stringify(decryptedWords);
}

function hxm_decrypt(encryptedUrl) {
    if (!encryptedUrl) return "";
    const secretStr = "ni po jie ni ** ";
    const cryptoKey = Crypto.enc.Utf8.parse(secretStr);
    const cryptoIv = Crypto.enc.Utf8.parse(secretStr);
    let finalCipherText = encryptedUrl;
    if (/^[0-9a-fA-F]+$/.test(encryptedUrl)) {
        const hexWords = Crypto.enc.Hex.parse(encryptedUrl);
        finalCipherText = Crypto.enc.Base64.stringify(hexWords);
    }
    const decryptedWords = Crypto.AES.decrypt(finalCipherText, cryptoKey, { iv: cryptoIv, mode: Crypto.mode.CBC, padding: Crypto.pad.Pkcs7 });
    return Crypto.enc.Utf8.stringify(decryptedWords);
}

function hxm_encrypt(encryptedUrl) {
    if (!encryptedUrl) return "";
    const secretStr = "ni po jie ni ** ";
    const cryptoKey = Crypto.enc.Utf8.parse(secretStr);
    const cryptoIv = Crypto.enc.Utf8.parse(secretStr);
    let finalCipherText = encryptedUrl;
    if (/^[0-9a-fA-F]+$/.test(encryptedUrl)) {
        const hexWords = Crypto.enc.Hex.parse(encryptedUrl);
        finalCipherText = Crypto.enc.Base64.stringify(hexWords);
    }
    const encrypted = Crypto.AES.encrypt(finalCipherText, cryptoKey, { iv: cryptoIv, mode: Crypto.mode.CBC, padding: Crypto.pad.Pkcs7 });
    return Crypto.enc.Hex.stringify(encrypted.ciphertext).toUpperCase();
}

function decryptData(responseData, htmlMeta = { contentTypeId: '', viewportId: '' }) {
    let decryptedInfo = {};
    if (responseData.Status !== 1) throw new Error("Status 不为 1，数据异常");
    if (responseData.Code === 10) {
        let metaFeature = (htmlMeta.contentTypeId + htmlMeta.viewportId).replace("viewport", "");
        const rawSaltKey = responseData.Code + metaFeature + responseData.Appkey + responseData.Version;
        const md5String = md5X(rawSaltKey);
        const decryptedStr = decryptOuterAesCbc(responseData.Data, md5String);
        decryptedInfo = JSON.parse(decryptedStr);
        if (!decryptedInfo.url.startsWith('http')) decryptedInfo.url = hxm_decrypt(decryptedInfo.url);
        decryptedInfo.url = decodeURIComponent(decryptedInfo.url);
    } else {
        const rawSaltKey = responseData.Code + responseData.Appkey + responseData.Version;
        const md5String = md5X(rawSaltKey);
        const decryptedStr = decryptOuterAesCbc(responseData.Data, md5String);
        decryptedInfo = JSON.parse(decryptedStr);
        if (!decryptedInfo.url.startsWith('http')) decryptedInfo.url = hxm_decrypt(decryptedInfo.url);
        decryptedInfo.url = decodeURIComponent(decryptedInfo.url);
    }
    return decryptedInfo;
}

export function __jsEvalReturn() {
    return { init, home, homeVod, category, search, detail, play, proxy: null };
}