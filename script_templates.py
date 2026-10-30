"""短视频脚本模板库。

想改文案、加新风格或新节日，直接改这个文件即可，不需要动 video_script.py。

模板里可用的占位符：
  {product}      产品/礼篮名称
  {price_text}   价格文字（如 "RM188"，没填价格时为 "价格私讯了解"）
  {items_text}   全部内容物，用 "、" 连接
  {item}         当前镜头负责展示的内容物（逐个展示的镜头才有）
  {point}        当前镜头负责讲的卖点（逐个讲卖点的镜头才有）
  {festival}     节日名称，如 "新年"
  {greeting}     节日祝福语
  {audience}     送礼对象，如 "长辈"
  {offer}        优惠/促销信息
  {contact}      联系方式
  {area}         配送地区

每种文字（visual/voice/caption）都可以写多个版本，程序会随机挑一个，
这样同一个产品可以一次生成好几版不重复的脚本。
"""

FESTIVALS = {
    "cny": {
        "name": "新年",
        "greeting": "新年快乐，恭喜发财",
        "mood": "红金色调、喜气洋洋",
        "props": "春联、红包、橘子、灯笼",
        "bgm": ["《恭喜恭喜》轻快改编版", "《财神到》电子混音版", "抖音/TikTok 热门新年 BGM"],
        "hashtags": ["#新年礼篮", "#CNYHamper", "#古晋礼篮", "#KuchingHamper", "#新年送礼", "#恭喜发财"],
    },
    "midautumn": {
        "name": "中秋",
        "greeting": "中秋快乐，花好月圆",
        "mood": "暖黄灯光、温馨团圆",
        "props": "灯笼、月饼、茶具",
        "bgm": ["《但愿人长久》纯音乐", "古筝轻音乐", "温柔钢琴曲"],
        "hashtags": ["#中秋礼篮", "#MooncakeHamper", "#古晋礼篮", "#KuchingHamper", "#中秋送礼"],
    },
    "christmas": {
        "name": "圣诞",
        "greeting": "Merry Christmas，圣诞快乐",
        "mood": "红绿配色、暖光、圣诞树",
        "props": "圣诞树、彩灯、礼物盒、松果",
        "bgm": ["《Jingle Bells》轻快版", "《All I Want for Christmas Is You》", "圣诞爵士钢琴"],
        "hashtags": ["#ChristmasHamper", "#圣诞礼篮", "#KuchingHamper", "#古晋礼篮", "#圣诞送礼"],
    },
    "raya": {
        "name": "开斋节",
        "greeting": "Selamat Hari Raya，Maaf Zahir dan Batin",
        "mood": "绿金配色、ketupat 装饰",
        "props": "ketupat、pelita 油灯、绿色布艺",
        "bgm": ["Raya 经典歌曲轻音乐版", "马来传统乐器纯音乐"],
        "hashtags": ["#HariRayaHamper", "#RayaHamper", "#KuchingHamper", "#开斋节礼篮"],
    },
    "corporate": {
        "name": "企业送礼",
        "greeting": "感谢一路支持，合作愉快",
        "mood": "简洁高级、深色背景、商务感",
        "props": "办公桌、名片、贺卡",
        "bgm": ["商务轻快钢琴", "高级感 Lo-fi 纯音乐"],
        "hashtags": ["#CorporateGift", "#企业礼篮", "#KuchingHamper", "#古晋礼篮", "#客户送礼"],
    },
    "general": {
        "name": "送礼",
        "greeting": "心意满满，送礼不烦恼",
        "mood": "明亮自然光、干净背景",
        "props": "鲜花、贺卡、丝带",
        "bgm": ["轻快尤克里里", "热门 Vlog 背景音乐"],
        "hashtags": ["#礼篮", "#Hamper", "#KuchingHamper", "#古晋礼篮", "#送礼推荐"],
    },
}

AUDIENCES = {
    "elder": "长辈",
    "client": "客户",
    "staff": "员工",
    "friend": "朋友",
    "family": "家人",
}

# 每个镜头的字段：
#   key       镜头用途（只用于识别）
#   weight    时长权重，越大占的秒数越多
#   optional  True 表示 15 秒版本会省略这个镜头
#   each      "items" / "points"：按内容物 / 卖点拆成多个镜头
#   visual / voice / caption  候选文案列表
#   note      拍摄提示
STYLES = {
    "unboxing": {
        "name": "开箱展示",
        "desc": "直接展示礼篮全景和内容物，适合新品上架、产品介绍",
        "shots": [
            {
                "key": "hook",
                "weight": 2,
                "visual": [
                    "礼篮从画面外推入，镜头快速推近，丝带随风飘动",
                    "双手掀开礼篮包装纸，露出满满一篮，镜头俯拍",
                ],
                "voice": [
                    "{price_text}能买到这么豪华的{festival}礼篮？",
                    "今年{festival}送{audience}，就送这一篮！",
                    "开箱一个让{audience}收到就笑的{festival}礼篮！",
                ],
                "caption": ["{price_text}｜{product}", "{festival}送礼首选｜{product}"],
                "note": "前 3 秒决定完播率，动作要快，画面要满",
            },
            {
                "key": "overview",
                "weight": 3,
                "visual": [
                    "礼篮 360° 旋转展示（转盘或手持环绕），背景布置{props}",
                    "礼篮放在桌面正中，镜头由远拉近，{mood}",
                ],
                "voice": [
                    "这款是我们的{product}，满满一篮都是心意。",
                    "先来看看整体，{product}包装是不是很有{festival}的气氛？",
                ],
                "caption": ["{product}", "整体包装展示"],
                "note": "{mood}；保持画面稳定，可用稳定器",
            },
            {
                "key": "items",
                "each": "items",
                "weight": 3,
                "visual": [
                    "逐一拿起{item}特写，手部入镜",
                    "微距镜头扫过{item}，突出质感与品牌标签",
                ],
                "voice": [
                    "里面有{item}。",
                    "看看这个，{item}，送{audience}超有面子。",
                ],
                "caption": ["{item}"],
                "note": "每样产品停留 1-2 秒，标签朝向镜头",
            },
            {
                "key": "points",
                "each": "points",
                "weight": 2,
                "optional": True,
                "visual": ["卖点文字大字弹出，配合礼篮局部特写", "手指点出礼篮细节，画面配合文字标注"],
                "voice": ["最重要的是，{point}！", "而且{point}。"],
                "caption": ["✔ {point}"],
                "note": "卖点文字用大号粗体，颜色与节日主色一致",
            },
            {
                "key": "offer",
                "weight": 2,
                "visual": ["礼篮正面定格，价格标签/优惠贴纸弹出", "店员手拿礼篮对镜头微笑"],
                "voice": ["现在只要{price_text}，{offer}！", "{offer}，{price_text}就能带回家。"],
                "caption": ["{price_text}｜{offer}"],
                "note": "价格要大、要清楚，停留至少 2 秒",
            },
            {
                "key": "cta",
                "weight": 2,
                "visual": ["画面出现联系方式和店铺 Logo", "店员挥手 + 联系方式字幕"],
                "voice": ["{area}可配送，{contact}，{greeting}！", "想订的赶快{contact}，{area}送货上门！"],
                "caption": ["📲 {contact}｜{area}配送"],
                "note": "结尾画面保留 Logo，方便用户截图",
            },
        ],
    },
    "story": {
        "name": "送礼剧情",
        "desc": "用送礼场景讲故事，情感带入，适合节日前预热",
        "shots": [
            {
                "key": "hook",
                "weight": 2,
                "visual": [
                    "主角对着手机发愁，旁边字幕：“{festival}送{audience}什么好？”",
                    "主角提着礼篮站在门口，按门铃",
                ],
                "voice": [
                    "每年{festival}最头痛的就是：送{audience}什么？",
                    "今年{festival}，我终于找到送{audience}不会出错的礼物了。",
                ],
                "caption": ["{festival}送{audience}送什么？"],
                "note": "演员表情要夸张一点，制造代入感",
            },
            {
                "key": "scene",
                "weight": 3,
                "visual": [
                    "主角把礼篮交给{audience}，{audience}惊喜接过",
                    "{audience}打开门看见礼篮，脸上露出笑容",
                ],
                "voice": ["送上这篮{product}，", "{audience}一看到{product}就笑了。"],
                "caption": ["送礼那一刻", "收到礼物的反应"],
                "note": "{mood}；布景加{props}增加节日感",
            },
            {
                "key": "reaction",
                "weight": 2,
                "optional": True,
                "visual": ["{audience}翻看礼篮里的东西，频频点头", "两人一起拆开礼篮，开心聊天"],
                "voice": ["“哇，这么丰富，你太有心了！”", "“这个我最喜欢了！”"],
                "caption": ["“你太有心了！”"],
                "note": "这句台词可以由演员说，口播改为现场收音",
            },
            {
                "key": "items",
                "each": "items",
                "weight": 3,
                "visual": ["切换到产品特写：{item}", "俯拍礼篮，镜头扫过{item}"],
                "voice": ["里面有{item}，", "{item}，每一样都很实用。"],
                "caption": ["{item}"],
                "note": "剧情镜头与产品特写交替，节奏要快",
            },
            {
                "key": "points",
                "each": "points",
                "weight": 2,
                "optional": True,
                "visual": ["礼篮特写 + 卖点文字", "主角面对镜头竖起大拇指"],
                "voice": ["{point}，送礼很有面子。", "关键是{point}。"],
                "caption": ["✔ {point}"],
                "note": "",
            },
            {
                "key": "cta",
                "weight": 3,
                "visual": ["主角拿起礼篮面对镜头，旁边出现价格与联系方式", "礼篮定格 + 价格 + 联系方式"],
                "voice": [
                    "{product}只要{price_text}，{offer}。{contact}，{greeting}！",
                    "想送{audience}一份心意？{product}{price_text}，{contact}，{area}可配送！",
                ],
                "caption": ["{price_text}｜{offer}｜📲 {contact}"],
                "note": "结尾画面保留 Logo 与联系方式",
            },
        ],
    },
    "pain": {
        "name": "痛点解决",
        "desc": "先讲送礼烦恼，再给出解决方案，适合转化下单",
        "shots": [
            {
                "key": "hook",
                "weight": 2,
                "visual": [
                    "主角在超市货架前来回走，拿起又放下，一脸烦恼",
                    "画面快速切换：排队、塞车、包装失败的混乱画面",
                ],
                "voice": [
                    "送礼又要挑、又要包、又要送，烦不烦？",
                    "还在为{festival}送{audience}的礼物到处跑？",
                ],
                "caption": ["送礼好麻烦？😩"],
                "note": "痛点画面可用黑白滤镜，与后面彩色画面形成对比",
            },
            {
                "key": "pain",
                "weight": 2,
                "optional": True,
                "visual": ["字幕逐条弹出：不知道送什么 / 没时间包装 / 怕送得寒酸"],
                "voice": ["不知道送什么、没时间包装、又怕送得寒酸。"],
                "caption": ["❌ 不知道送什么  ❌ 没时间  ❌ 怕寒酸"],
                "note": "",
            },
            {
                "key": "solution",
                "weight": 3,
                "visual": ["画面变彩色，{product}隆重登场，镜头推近", "响指一打，礼篮出现在桌上"],
                "voice": ["交给我们就好！这款{product}帮你一次搞定。", "一篮{product}，全部帮你搞定！"],
                "caption": ["✅ 一篮搞定｜{product}"],
                "note": "转场要有音效（叮/响指），制造反差",
            },
            {
                "key": "items",
                "each": "items",
                "weight": 3,
                "visual": ["快速切换展示：{item}", "礼篮俯拍，逐一圈出{item}"],
                "voice": ["{item}，全部配好了。", "有{item}。"],
                "caption": ["{item}"],
                "note": "快节奏剪辑，每个镜头 1 秒左右",
            },
            {
                "key": "points",
                "each": "points",
                "weight": 2,
                "visual": ["卖点文字配合打勾动画", "礼篮细节特写 + 卖点标注"],
                "voice": ["✔ {point}。", "还有，{point}。"],
                "caption": ["✅ {point}"],
                "note": "",
            },
            {
                "key": "cta",
                "weight": 3,
                "visual": ["礼篮正面定格，价格与联系方式弹出", "店员把礼篮装车/交给快递，画面出现联系方式"],
                "voice": ["{price_text}，{offer}，{area}直接配送。{contact}！", "现在{contact}，{offer}，省时又有面子！"],
                "caption": ["{price_text}｜{offer}｜📲 {contact}"],
                "note": "结尾强调“省事”，加送货画面更有说服力",
            },
        ],
    },
}

# 封面标题模板
COVER_TITLES = [
    "{price_text}的{festival}礼篮长这样！",
    "{festival}送{audience}，这篮不会错",
    "{area}人都在订的{festival}礼篮",
    "开箱｜{product}",
    "送礼不再烦恼｜{product}",
]

# "each" 镜头在不同时长下最多拆成几个镜头
EACH_LIMITS = {
    "items": {15: 1, 30: 2, 60: 4},
    "points": {15: 1, 30: 2, 60: 3},
}
