/* Platform identities and honest connection states; no inferred third-party metrics. */
(function(root){
  const platforms=[
    {id:'闲鱼',group:'商品交易',purpose:'二手商品、闲置需求与服务供给',hint:'优先记录同城、成色、规格一致的人工观察；在售数量不等于成交量。',url:'https://www.goofish.com/'},
    {id:'小红书',group:'内容需求',purpose:'种草话题、使用场景与消费需求',hint:'可导入有权限的聚光报表或人工观察。笔记数量与互动不能直接换算为搜索量或销量。',url:'https://ad-market.xiaohongshu.com/'},
    {id:'拼多多',group:'商品交易',purpose:'大众商品、价格带与店铺关键词',hint:'优先使用本店后台报表或已授权接口；本店访客不能代表平台全量需求。',url:'https://open.yangkeduo.com/application/home'},
    {id:'淘宝/天猫',group:'商品交易',purpose:'商品细分、品牌与价格带对比',hint:'建议使用获准的商家报表与淘宝开放平台能力；淘宝与天猫的范围应在统计范围字段注明。',url:'https://open.taobao.com/'},
    {id:'京东',group:'商品交易',purpose:'数码家电、品牌商品与价格观察',hint:'可导入有权限的店铺报表或公开人工观察。需保留SKU规格、店铺和日期。',url:'https://open.jd.com/'},
    {id:'抖音',group:'内容需求',purpose:'短视频话题、带货场景与商品内容',hint:'使用获准的账号或电商报表。播放量、互动和商品成交是不同指标，不可互相替代。',url:'https://open.douyin.com/'},
    {id:'1688',group:'货源采购',purpose:'货源、批发供给与采购成本对比',hint:'供应数量、报价和起订量主要反映供给；报价应结合规格、阶梯价、运费与售后复核。',url:'https://www.1688.com/'},
    {id:'知乎',group:'软件线索',purpose:'需求痛点、选型问题与软件服务场景',hint:'从有权使用的问答观察中记录问题与来源。讨论热度不等于实际付费意愿。',url:'https://www.zhihu.com/'},
    {id:'哔哩哔哩',group:'软件线索',purpose:'教程需求、工具使用与数码内容',hint:'可记录人工观察或授权创作者报表；内容数、播放和互动不等于购买或软件付费。',url:'https://www.bilibili.com/'},
    {id:'GitHub',group:'自动公开来源',purpose:'开源软件项目的真实Star关注',hint:'已接入6个公开项目，按北京时间每天11:23采集；历史从接入日积累。',url:'https://github.com/',metric:'github_stars'},
    {id:'维基百科',group:'自动公开来源',purpose:'商品与软件主题的百科阅读关注',hint:'已接入16个中文条目，按北京时间每天11:23更新；数据按UTC自然日统计。',url:'https://zh.wikipedia.org/',metric:'wiki_pageviews'},
    {id:'其他',group:'其他来源',purpose:'暂未归类的授权数据和手工观察',hint:'请填写具体来源名称与统计范围，避免把不同站点的数据混为同一系列。',url:null}
  ];
  const aliases={'咸鱼':'闲鱼','淘宝':'淘宝/天猫','天猫':'淘宝/天猫','淘宝天猫':'淘宝/天猫','淘宝/天猫':'淘宝/天猫','B站':'哔哩哔哩','b站':'哔哩哔哩','bilibili':'哔哩哔哩','github':'GitHub','Wikipedia':'维基百科'};
  const normalize=p=>aliases[p]||p;
  const filter=(rows,platform)=>platform==='all'?rows:rows.filter(r=>normalize(r.platform)===normalize(platform));
  const select=(platform,mode)=>{const p=platforms.find(p=>p.id===platform);return p?.metric?{mode:'public',metric:p.metric}:{mode:mode==='public'?'real':mode,metric:null};};
  const api={platforms,normalize,filter,select};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.RadarPlatforms=api;
})(typeof globalThis!=='undefined'?globalThis:this);
