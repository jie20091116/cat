var rule = {
    title: '爱奇艺',
    host: 'https://www.iqiyi.com',
    homeUrl: '',
    detailUrl: 'https://pcw-api.iqiyi.com/video/video/videoinfowithuser/fyid?agent_type=1&authcookie=&subkey=fyid&subscribe=1',
    searchUrl: 'https://search.video.iqiyi.com/o?if=html5&key=**&pageNum=fypage&pos=1&pageSize=24&site=iqiyi',
    searchable: 2,
    multi: 1,
    filterable: 1,
    filter: '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',
    url: 'https://pcw-api.iqiyi.com/search/recommend/list?channel_id=fyclass&data_type=1&page_id=fypage&ret_num=48',
    filter_url: 'is_purchase={{fl.is_purchase}}&mode={{fl.mode}}&three_category_id={{fl.three_category_id}}&market_release_date_level={{fl.year}}',
    headers: {
        'User-Agent': 'MOBILE_UA'
    },
    timeout: 5000,
    class_name: '电影&电视剧&纪录片&动漫&综艺&音乐&网络电影',
    class_url: '1&2&3&4&6&5&16',
    limit: 20,
    play_parse: true,
    lazy: $js.toString(() => {
        let d = [];
        let url1 = JSON.parse(request("" + input)).url;
        var withoutDomain = url1.replace(/^https:\/\/baidu\.con\//, '');
        var first16Chars = withoutDomain.substring(0, 16);
        var remainingString = withoutDomain.substring(16);
        var key = CryptoJS.enc.Utf8.parse(first16Chars);
        var iv = key;

        function AES_Decrypt(word) {
            var srcs = word;
            var decrypt = CryptoJS.AES.decrypt(srcs, key, {
                iv: iv,
                mode: CryptoJS.mode.CBC,
                padding: CryptoJS.pad.Pkcs7
            });
            return decrypt.toString(CryptoJS.enc.Utf8);
        };
        let url = AES_Decrypt(remainingString);
        input = {
            url: url,
            parse: 0,
            header: rule.headers
        }
        setResult(d)
    }),
    推荐: '',
    一级: 'js:let d=[];if(MY_CATE==="16"){input=input.replace("channel_id=16","channel_id=1").split("three_category_id")[0];input+="three_category_id=27401"}else if(MY_CATE==="5"){input=input.replace("data_type=1","data_type=2")}let html=request(input);let json=JSON.parse(html);if(json.code==="A00003"){fetch_params.headers["user-agent"]=PC_UA;json=JSON.parse(fetch(input,fetch_params))}json.data.list.forEach(function(data){if(data.channelId===1){desc=data.hasOwnProperty("score")?data.score+"分\\t":""}else if(data.channelId===2||data.channelId===4){if(data.latestOrder===data.videoCount){desc=(data.hasOwnProperty("score")?data.score+"分\\t":"")+data.latestOrder+"集全"}else{if(data.videoCount){desc=(data.hasOwnProperty("score")?data.score+"分\\t":"")+data.latestOrder+"/"+data.videoCount+"集"}else{desc="更新至 "+data.latestOrder+"集"}}}else if(data.channelId===6){desc=data.period+"期"}else if(data.channelId===5){desc=data.focus}else{if(data.latestOrder){desc="更新至 第"+data.latestOrder+"期"}else if(data.period){desc=data.period}else{desc=data.focus}}url=MY_CATE+"$"+data.albumId;d.push({url:url,title:data.name,desc:desc,pic_url:data.imageUrl.replace(".jpg","_390_520.jpg?caplist=jpg,webp")})});setResult(d);',
    二级: 'js:let d=[];let html=request(input);let json=JSON.parse(html).data;VOD={vod_id:"",vod_url:input,vod_name:"",type_name:"",vod_actor:"",vod_year:"",vod_director:"",vod_area:"",vod_content:"",vod_remarks:"",vod_pic:""};VOD.vod_name=json.name;try{if(json.latestOrder){VOD.vod_remarks="评分："+(json.score||"")+"\\n更新至：第"+json.latestOrder+"集(期)/共"+json.videoCount+"集(期)"}else{VOD.vod_remarks="类型: "+(json.categories[0].name||"")+"\\t"+(json.categories[1].name||"")+"\\t"+(json.categories[2].name||"")+"\\t"+"评分："+(json.score||"")+json.period}}catch(e){VOD.vod_remarks=json.subtitle}VOD.vod_area=""+(json.areas||"");let vsize="579_772";try{vsize=json.imageSize[12]}catch(e){}VOD.vod_pic=json.imageUrl.replace(".jpg","_"+vsize+".jpg?caplist=jpg,webp");VOD.type_name=json.categories.map(function(it){return it.name}).join(",");if(json.people.main_charactor){let vod_actors=[];json.people.main_charactor.forEach(function(it){vod_actors.push(it.name)});VOD.vod_actor=vod_actors.join(",")}VOD.vod_content=json.description;let playlists=[];if(json.channelId===1||json.channelId===5){playlists=[{playUrl:json.playUrl,imageUrl:json.imageUrl,shortTitle:json.shortTitle,focus:json.focus,period:json.period}]}else{if(json.channelId===6){let qs=json.period.split("-")[0];let listUrl="https://pcw-api.iqiyi.com/album/source/svlistinfo?cid=6&sourceid="+json.albumId+"&timelist="+qs;let playData=JSON.parse(request(listUrl)).data[qs];playData.forEach(function(it){playlists.push({playUrl:it.playUrl,imageUrl:it.imageUrl,shortTitle:it.shortTitle,focus:it.focus,period:it.period})})}else{let listUrl="https://pcw-api.iqiyi.com/albums/album/avlistinfo?aid="+json.albumId+"&size=200&page=1";let data=JSON.parse(request(listUrl)).data;let total=data.total;playlists=data.epsodelist;if(total>200){for(let i=2;i<total/200+1;i++){let listUrl="https://pcw-api.iqiyi.com/albums/album/avlistinfo?aid="+json.albumId+"&size=200&page="+i;let data=JSON.parse(request(listUrl)).data;playlists=playlists.concat(data.epsodelist)}}}}playlists.forEach(function(it){d.push({title:it.shortTitle||"第"+it.order+"集",desc:it.subtitle||it.focus||it.period,img:it.imageUrl.replace(".jpg","_480_270.jpg?caplist=jpg,webp"),url:it.playUrl})});VOD.vod_play_from="爱奇艺";VOD.vod_play_url=d.map(function(it){return it.title+"$"+it.url}).join("#");',
    搜索: 'json:.data.docinfos;.albumDocInfo.albumTitle;.albumDocInfo.albumVImage;.albumDocInfo.channel;.albumDocInfo.albumId;.albumDocInfo.tvFocus',
}