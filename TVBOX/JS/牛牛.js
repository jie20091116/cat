import { Crypto, _ } from 'assets://js/lib/cat.js';

let host = '';
let siteKey = '';
let configData = {};
const UA = 'okhttp/3.12.1';

// 模拟安卓设备头，绕过防爬
const commonHeaders = {
    'User-Agent': UA,
    'p': 'android',
    'product': 'xiaomi',
    'os': '12',
    'v': '1.4.6',
    'pkg': 'com.tupai.count'
};

// --- 工具函数：加解密引擎 ---
function md5(text) {
    return Crypto.MD5(text).toString();
}

function aes_ecb_decrypt(data, keyStr) {
    const key = Crypto.enc.Utf8.parse(keyStr.substring(0, 16).padEnd(16, '0'));
    const decrypt = Crypto.AES.decrypt(data, key, {
        mode: Crypto.mode.ECB,
        padding: Crypto.pad.Pkcs7
    });
    return decrypt.toString(Crypto.enc.Utf8);
}

function aes_cbc_decrypt(data, keyStr, ivStr) {
    const key = Crypto.enc.Utf8.parse(keyStr);
    const iv = Crypto.enc.Utf8.parse(ivStr);
    const decrypt = Crypto.AES.decrypt(data, key, {
        iv: iv,
        mode: Crypto.mode.CBC,
        padding: Crypto.pad.Pkcs7
    });
    return decrypt.toString(Crypto.enc.Utf8);
}

function des3_cbc_decrypt(data, keyStr, ivStr) {
    const key = Crypto.enc.Utf8.parse(keyStr);
    const iv = Crypto.enc.Utf8.parse(ivStr);
    const decrypt = Crypto.TripleDES.decrypt(data, key, {
        iv: iv,
        mode: Crypto.mode.CBC,
        padding: Crypto.pad.Pkcs7
    });
    return decrypt.toString(Crypto.enc.Utf8);
}

// --- 核心逻辑 ---

async function init(cfg) {
    siteKey = cfg.skey;
    try {
        let entry = cfg.ext || 'https://nnal.oss-cn-beijing.aliyuncs.com/nn.php';
        if (entry.includes('oss-cn-beijing')) {
            const resp = await req(entry, { headers: commonHeaders });
            const decoded = aes_ecb_decrypt(resp.content, '@@bull!!!video$$');
            host = decoded.split('\n')[0].trim().replace(/\/$/, '');
        } else {
            host = entry.replace(/\/$/, '');
        }
        const confPath = '/config';
        const confResp = await req(host + confPath, { headers: commonHeaders });
        configData = JSON.parse(aes_ecb_decrypt(confResp.content, confPath)).data;
    } catch (e) {}
}

async function home(filter) {
    const path = '/types';
    const resp = await req(host + path, { headers: commonHeaders });
    const data = JSON.parse(aes_ecb_decrypt(resp.content, path)).data;
    
    let classes = [];
    let filters = {};

    for (const item of data) {
        if (item.type_extend.version !== '') continue;
        classes.push({ type_id: item.type_id, type_name: item.type_name });

        const ext = item.type_extend;
        const buildF = (n, k, v) => {
            if (!v) return null;
            return { key: k, name: n, value: v.split(',').map(i => ({ n: i, v: i === '全部' ? '' : i })) };
        };
        filters[item.type_id] = _.compact([
            { key: 'order', name: '排序', value: [{ n: '最新', v: '最新' }, { n: '最热', v: '最热' }, { n: '好评', v: '好评' }] },
            buildF('剧情', 'class', ext.class),
            buildF('地区', 'area', ext.area),
            buildF('年份', 'year', ext.year)
        ]);
    }
    return JSON.stringify({ class: classes, filters: filters });
}

async function category(tid, pg, filter, extend) {
    if (pg <= 0) pg = 1;
    const path = `/list?class=${encodeURIComponent(extend.class || '')}&order=${encodeURIComponent(extend.order || '最新')}&type_id=${tid}&area=${encodeURIComponent(extend.area || '')}&year=${encodeURIComponent(extend.year || '')}&state=&wd=&page=${pg}`;
    const resp = await req(host + path, { headers: commonHeaders });
    return JSON.stringify({ list: JSON.parse(aes_ecb_decrypt(resp.content, path)).data, page: pg });
}

async function detail(id) {
    const path = `/detail?vod_id=${id}`;
    const resp = await req(host + path, { headers: commonHeaders });
    const data = JSON.parse(aes_ecb_decrypt(resp.content, path)).data;
    
    let play_from = [], play_urls = [];
    for (const src of data.sources) {
        const parserInfo = _.find(configData.parser, (p) => p.player_id === src.player_id);
        if (parserInfo) {
            play_from.push(parserInfo.player_name);
            play_urls.push(src.episodes.map(ep => `${ep.name}$${src.player_id},${ep.url}`).join('#'));
        }
    }
    return JSON.stringify({
        list: [{
            vod_id: data.vod_id, vod_name: data.vod_name, vod_pic: data.vod_pic,
            vod_remarks: data.vod_remarks, vod_content: data.vod_content,
            vod_play_from: play_from.join('$$$'), vod_play_url: play_urls.join('$$$')
        }]
    });
}

async function play(flag, id, flags) {
    const [player_id, raw_url] = id.split(',');
    let url = '';
    try {
        if (player_id === 'hema') {
            const conf = configData['src2'];
            const adResp = await req(conf.adUrl, { method: 'post', data: conf.adBody, headers: commonHeaders });
            const token = JSON.parse(des3_cbc_decrypt(adResp.content, conf.key, conf.iv)).result.user_info.token;
            const [v_id, coll] = raw_url.split('@');
            const playResp = await req(conf.detailUrl, { method: 'post', data: { vod_id: v_id, collection: coll, xz: "0" }, headers: { ...commonHeaders, token: token } });
            url = JSON.parse(des3_cbc_decrypt(playResp.content, conf.key, conf.iv)).result.vod_url;
        } else if (['xm3u8', 'xiaocao'].includes(player_id)) {
            const conf = configData[player_id === 'xm3u8' ? 'src1' : 'src7'];
            const t = Date.now().toString(), d_id = 'bull' + t.slice(-8);
            const sign = md5(conf.salt + d_id + t).toUpperCase();
            const tResp = await req(conf.tokenUrl, { method: 'post', data: 'invited_by=&is_install=1', headers: { ...commonHeaders, device_id: d_id, sign: sign, cur_time: t } });
            const token = JSON.parse(aes_cbc_decrypt(tResp.content, conf.key, conf.iv)).result.user_info.token;
            const playResp = await req(conf.detailUrl, { method: 'post', data: { vod_id: raw_url.split('@')[0], vod_token: token, cur_time: t }, headers: { ...commonHeaders, token: token, sign: sign, cur_time: t } });
            url = JSON.parse(aes_cbc_decrypt(playResp.content, conf.key, conf.iv)).result.vod_url;
        } else {
            const parser = _.find(configData.parser, (p) => p.player_id === player_id);
            if (parser) {
                const resp = await req(parser.url.replace('%s', raw_url), { headers: commonHeaders });
                url = JSON.parse(resp.content).url;
            }
        }
    } catch (e) { url = raw_url; }

    return JSON.stringify({ parse: 0, url: url || raw_url, header: { 'User-Agent': 'Mozi' } });
}

async function search(wd, quick) {
    const path = `/list?class=&order=&type_id=&area=&year=&state=&wd=${encodeURIComponent(wd)}&page=1`;
    const resp = await req(host + path, { headers: commonHeaders });
    return JSON.stringify({ list: JSON.parse(aes_ecb_decrypt(resp.content, path)).data });
}

export function __jsEvalReturn() {
    return { init, home, category, detail, play, search };
}