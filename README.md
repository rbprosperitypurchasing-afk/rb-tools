# rb-tools

RB Prosperity 内部小工具集。

## 礼篮短视频脚本生成器 `video_script.py`

输入礼篮信息，自动生成分镜脚本（画面 / 口播 / 字幕 / 拍摄提示 / 时间轴），外加封面标题、BGM 建议和 Hashtag。
纯模板填空，**不需要联网或 API Key**，只需 Python 3.8+，没有其他依赖。

### 交互模式（推荐新手）

```bash
python3 video_script.py
```

程序会逐项提问：产品名称、价格、内容物、卖点、节日、送礼对象、风格、时长、优惠、联系方式。

### 命令行模式（适合批量）

```bash
python3 video_script.py --product "金玉满堂礼篮" --price 188 --items "燕窝,鲍鱼,红酒,饼干,茶叶" --points "全进口产品,精美手工包装,古晋免费配送" --festival cny --audience elder --style story --duration 30 --offer "早鸟价 9 折" --contact "WhatsApp 012-345 6789" --versions 3
```

| 参数 | 可选值 |
|---|---|
| `--festival` | `cny` 新年 / `midautumn` 中秋 / `christmas` 圣诞 / `raya` 开斋节 / `corporate` 企业送礼 / `general` 通用 |
| `--audience` | `elder` 长辈 / `client` 客户 / `staff` 员工 / `friend` 朋友 / `family` 家人 |
| `--style` | `unboxing` 开箱展示 / `story` 送礼剧情 / `pain` 痛点解决 |
| `--duration` | `15` / `30` / `60` 秒 |
| `--versions` | 一次生成几个不同版本 |
| `--seed` | 固定随机种子，结果可重现 |
| `--no-save` | 只打印不保存 |

结果保存在 `output/`：`.md`（方便阅读/分享）和 `.csv`（用 Excel 打开，可直接给拍摄团队）。

### 修改文案模板

所有文案、节日、风格都在 `script_templates.py`，直接改文字即可；每项可写多个候选句，程序随机挑选。

### 测试

```bash
python3 -m unittest discover -s tests
```
