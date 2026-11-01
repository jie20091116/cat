/*
title: '灯泡影视', author: '小可乐/v6.1.1'
说明：可以不写ext，也可以写ext，ext支持的参数和格式参数如下
"ext": {
    "host": "xxxx", //站点网址
    "timeout": 6000,  //请求超时，单位毫秒
    "tabsSet": "网盘&磁力&线路1"  //指定线路和顺序，可模糊指定
}
*/

const MOBILE_UA = 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36';
const DefHeader = {'User-Agent': MOBILE_UA};
var HOST;
var KParams = {
    headers: {'User-Agent': MOBILE_UA},
    timeout: 5000
};

async function init(cfg) {
    try {
        HOST = (cfg.ext?.host?.trim() || 'https://www.dp88.net').replace(/\/$/, '');
        KParams.headers['Referer'] = HOST;
        let parseTimeout = parseInt(cfg.ext?.timeout?.trim(), 10);
        if (parseTimeout > 0) {KParams.timeout = parseTimeout;}
        KParams.catesSet = cfg.ext?.catesSet?.trim() || '';
        KParams.tabsSet = cfg.ext?.tabsSet?.trim() || '';
        KParams.resHtml = await request(HOST);
    } catch (e) {
        console.error('初始化参数失败：', e.message);
    }
}

async function home(filter) {
    try {
        let kclassName = '电影$3&剧集$2&动漫$4';
        let classes = kclassName.split('&').map(it => {
            let [cName, cId] = it.split('$');
            return {type_name: cName, type_id: cId};
        });
        let filters = {};
        return JSON.stringify({class: classes, filters: filters});
    } catch (e) {
        console.error('获取分类失败：', e.message);
        return JSON.stringify({class: [], filters: {}});
    }
}

async function homeVod() {
    try {
        let resHtml = KParams.resHtml;
        let VODS = getVodList(resHtml);
        return JSON.stringify({list: VODS});
    } catch (e) {
        console.error('推荐页获取失败：', e.message);
        return JSON.stringify({list: []});
    }
}

async function category(tid, pg, filter, extend) {
    try {
        pg = parseInt(pg, 10), pg = pg > 0 ? pg : 1;
        let fl = extend || {};        
        let cateUrl = `${HOST}/list/${fl.by ?? '0'}_${fl.area ?? '0'}_${fl.area ?? '0'}_${fl.class ?? '0'}_${tid}/${pg}`;
        let resHtml = await request(cateUrl);
        let VODS = getVodList(resHtml);
        let limit = VODS.length;
        let hasMore = cutStr(resHtml, 'pages">', '</div>').includes('下一页');
        let pagecount = hasMore ? pg + 1 : pg;
        return JSON.stringify({list: VODS, page: pg, pagecount: pagecount, limit: limit, total: limit*pagecount});
    } catch (e) {
        console.error('类别页获取失败：', e.message);
        return JSON.stringify({list: [], page: 1, pagecount: 0, limit: 30, total: 0});
    }
}

async function search(wd, quick, pg) {
    try {
        pg = parseInt(pg, 10), pg = pg > 0 ? pg : 1;
        let searchUrl = `${HOST}/page/${pg}/?s=${wd}`;
        let resHtml = await request(searchUrl);
        let VODS = getVodList(resHtml, true);
        return JSON.stringify({list: VODS, page: pg, pagecount: 10, limit: 30, total: 300});
    } catch (e) {
        console.error('搜索页获取失败：', e.message);
        return JSON.stringify({list: [], page: 1, pagecount: 0, limit: 30, total: 0});
    }
}

function getVodList(khtml, sch=false) {
    try {
        if (!khtml) {throw new Error('源码为空');}  
        let kvods = [];
        let prefix = sch ? 'content">' : '<li><a';
        let listArr = cutStr(khtml, prefix, '</li>', '', false, 0, true);
        for (let it of listArr) {
            let kname = sch ? cutStr(it, '<h3>', '</h3>', '名称') : cutStr(it, 'alt="', '"', '名称');
            let kpic = sch ? cutStr(it, 'src="', '"', '图片') : cutStr(it, 'data-original="', '"', '图片');
            let kremarks = sch ? cutStr(it, 'int">', '</p>', '状态') : cutStr(it, 's1">', '<', '状态');
            let kyear = sch ? '' : cutStr(it, '<p>', '/');
            let kid = cutStr(it, 'href="', '"');
            if (kid) {
                kvods.push({
                    vod_name: kname,
                    vod_pic: kpic,
                    vod_remarks: kremarks,
                    vod_year: kyear,
                    vod_id: `${kid}@${kname}@${kpic}`
                });
            }
        }
        return kvods;
    } catch (e) {
        console.error(`生成视频列表失败：`, e.message);
        return [];
    }
}

async function detail(ids) {
    try {
        let [id, kname, kpic] = ids.split('@');
        let detailUrl = !/^http/.test(id) ? `${HOST}${id}` : id;
        let resHtml = await request(detailUrl);
        if (!resHtml) {throw new Error('源码为空');}  
        let intros = cutStr(resHtml, 'content-rt">', '<section', '', false);
        let [ktabs, kurls] = [[], []];       
        let zxTwoCut = cutStr(resHtml, 'pd-tit-0">', 'pd-item"', '', false);
        let zxArr = cutStr(zxTwoCut, 'tabid£>', '</ul>', '', false, 0, true)
        if (zxArr[0]) {
            zxArr.forEach((item,idx) => {
                let siglUrl = cutStr(item, '<a', '/a>', '', false, 0, true).map(it => `${cutStr(it, '>', '<', 'noEpi')}$${cutStr(it, 'href="', '"', 'noUrl')}` ).join('#');
                kurls.push(siglUrl);
            });
            cutStr(zxTwoCut, '<option', '/option>', '', false, 0, true).forEach((it,idx) => {
                ktabs.push(cutStr(it, '>', '<', `在线${idx+1}`));
            });
        }
        let clTwoCut = cutStr(resHtml, 'pd-tit-1">', 'pd-item"', '', false);
        let clArr = cutStr(clTwoCut, 'lip">', '</ul>', '', false, 0, true);
        if (clArr[0]) {
            clArr.forEach((item,idx) => {
                let siglUrl = cutStr(item, '<a', '/a>', '', false, 0, true).map(it => `${cutStr(it, 'title="', '"', 'noEpi')}$${cutStr(it, 'href="', '"', 'noUrl')}` ).join('#');
                kurls.push(siglUrl);
            });
            cutStr(clTwoCut, '<h2', 'h2>', '', false, 0, true).forEach((it,idx) => {
                ktabs.push(`磁力${idx+1}-${cutStr(it, '>', '</', '线')}`);
            });
        }        
        let wpTwoCut = cutStr(resHtml, 'pd-tit-2">', '</section>', '', false);
        let wpArr = cutStr(wpTwoCut, 'lip">', '</ul>', '', false, 0, true);
        if (wpArr[0]) {
            wpArr.forEach((item,idx) => {
                let siglUrl = cutStr(item, '<a', '/a>', '', false, 0, true).map(it => `${cutStr(it, 'title="', '"', 'noEpi')}$${cutStr(it, 'href="', '"', 'noUrl')}` ).join('#');
                kurls.push(siglUrl);
            });
            cutStr(wpTwoCut, '<h2', 'h2>', '', false, 0, true).forEach((it,idx) => {
                ktabs.push(`网盘${idx+1}-${cutStr(it, '>', '</', '线')}`);
            });
        }
        if (KParams.tabsSet) {
            let ktus = ktabs.map((it, idx) => { return {type_name: it, type_value: kurls[idx]} });
            ktus = ctSet(ktus, KParams.tabsSet);
            ktabs = ktus.map(it => it.type_name);
            kurls = ktus.map(it => it.type_value);
        }
        let VOD = {
            vod_id: detailUrl,
            vod_name: kname,
            vod_pic: kpic,
            vod_remarks: cutStr(intros, '更新：', '</p>', '状态'),
            type_name: cutStr(intros, '类型：', '</p>', '类型'),
            vod_year: cutStr(intros, 'year">（', '）', '1000'),
            vod_area: cutStr(intros, '地区：', '</p>', '地区'),
            vod_lang: cutStr(intros, '语言：', '</p>', '语言'),
            vod_director: cutStr(intros, '导演：', '</p>', '导演'),
            vod_actor: cutStr(intros, '主演：', '</p>', '主演'),
            vod_content: cutStr(intros, 'sq_a"£>', '<span', kname),
            vod_play_from: ktabs.join('$$$'),
            vod_play_url: kurls.join('$$$')
        };
        return JSON.stringify({list: [VOD]});
    } catch (e) {
        console.error('详情页获取失败：', e.message);
        return JSON.stringify({list: []});
    }
}

async function play(flag, ids, flags) {
    try {
        let kp = 0, kurl = '';
        if (/磁力/.test(flag)) {
            kurl = ids;
        } else if (/网盘/.test(flag)) {
            kurl = `push://${ids}`;
        } else {
            let resHtml = await request(ids);
            kurl = cutStr(resHtml, '<iframe£url=', '"') || cutStr(resHtml, '<iframe£src="', '"');
            if (!/^http/.test(kurl)) {
                kurl = ids;
                kp = 1;
            }
        }
        return JSON.stringify({jx: 0, parse: kp, url: kurl, header: DefHeader});
    } catch (e) {
        console.error('播放失败：', e.message);
        return JSON.stringify({jx: 0, parse: 0, url: '', header: {}});
    }
}

function ctSet(kArr, setStr) {
    try {
        if (!Array.isArray(kArr) || kArr.length === 0 || typeof setStr !== 'string' || !setStr) { throw new Error('第一参数需为非空数组，第二参数需为非空字符串'); }
        const set_arr = [...kArr];
        const arrNames = setStr.split('&');
        const filtered_arr = arrNames.flatMap(item => set_arr.filter(it => it.type_name.includes(item)) ).filter((flt, idx, self) => self.findIndex(fdi => fdi === flt) === idx);
        return filtered_arr.length? filtered_arr : [set_arr[0]];
    } catch (e) {
        console.error('ctSet 执行异常：', e.message);
        return kArr;
    }
}

function cutStr(str, prefix = '', suffix = '', defVal = '', clean = true, i = 0, all = false) {
    try {
        if (typeof str !== 'string') {throw new Error('被截取对象必须为字符串');}
        const cleanStr = cs => String(cs).replace(/<[^>]*?>/g, ' ').replace(/(&nbsp;|[\u0020\u00A0\u3000\s])+/g, ' ').trim().replace(/\s+/g, ' ');
        const esc = s => String(s).replace(/[.*+?${}()|[\]\\/^]/g, '\\$&');
        let pre = esc(prefix).replace(/£/g, '[^]*?'), end = esc(suffix);
        const regex = new RegExp(`${pre || '^'}([^]*?)${end || '$'}`, 'g');
        const matchIter = str.matchAll(regex);
        if (all) {
            let matchArr = [...matchIter];
            if (!matchArr.length) {return [defVal];}
            return matchArr.map(ela => ela[1] !== undefined ? (clean ? cleanStr(ela[1]) : ela[1]) : defVal);
        }
        const idx = parseInt(i, 10);
        if (isNaN(idx)) {throw new Error('序号必须为整数');}
        let tgResult, matchIdx = 0;
        if (idx >= 0) {
            for (let elt of matchIter) {
                if (matchIdx++ === idx) {
                    tgResult = elt[1];
                    break;
                }
            }
        } else {
            let absI = Math.abs(idx), ringBuf = new Array(absI), ringPtr = 0, ringCnt = 0;
            for (let elt of matchIter) {
                ringBuf[ringPtr] = elt[1];
                ringPtr = (ringPtr + 1) % absI;
                ringCnt = Math.min(ringCnt + 1, absI);
                matchIdx++;
            }
            tgResult = (matchIdx >= absI && ringCnt > 0) ? ringBuf[ringPtr % ringCnt] : undefined;
        }
        return tgResult !== undefined ? (clean ? (cleanStr(tgResult) || defVal) : tgResult) : defVal;
    } catch (e) {
        console.error(`字符串截取错误：`, e.message);
        return all ? ['cutErr'] : 'cutErr';
    }
}

async function request(reqUrl, options = {}) {
    try {
        if (typeof reqUrl !== 'string' || !reqUrl.trim()) { throw new Error('reqUrl需为字符串且非空'); }
        if (typeof options !== 'object' || Array.isArray(options) || options === null) { throw new Error('options类型需为非null对象'); }
        options.method = options.method?.toUpperCase() || 'GET';
        if (['GET', 'HEAD'].includes(options.method)) {
            delete options.body;
            delete options.data;
            delete options.postType;
        }
        let {headers, timeout, ...restOpts} = options;
        const optObj = {
            headers: (typeof headers === 'object' && !Array.isArray(headers) && headers) ? headers : KParams.headers,
            timeout: parseInt(timeout, 10) > 0 ? parseInt(timeout, 10) : KParams.timeout,
            ...restOpts
        };
        const res = await req(reqUrl, optObj);
        if (options.withHeaders) {
            const resHeaders = typeof res.headers === 'object' && !Array.isArray(res.headers) && res.headers ? res.headers : {};
            const resWithHeaders = { ...resHeaders, body: res?.content ?? '' };
            return JSON.stringify(resWithHeaders);
        }
        return res?.content ?? '';
    } catch (e) {
        console.error(`${reqUrl}→请求失败：`, e.message);
        return options?.withHeaders ? JSON.stringify({ body: '' }) : '';
    }
}

export function __jsEvalReturn() {
    return {
        init,
        home,
        homeVod,
        category,
        search,
        detail,
        play,
        proxy: null
    };
}