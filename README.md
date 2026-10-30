# rb-tools

RB Prosperity 内部小工具集。

## RB AI 创作室 `ai_studio/`

类似即梦的 AI 创作工具，全部使用**免费开源模型**，不需要付费 API：

| 功能 | 模型 |
|---|---|
| ① 文字生图（人物、物品、场景，可直接写中文） | SDXL |
| ② 人物/物品保持一致（上传参考图，生成新场景） | IP-Adapter（人物用 Face 版，物品用 Plus 版） |
| ③ 图片生成视频（约 2-4 秒） | Stable Video Diffusion XT |
| ④ 作品库（查看、下载、继续生成） | — |

### 在 Google Colab 上运行（免费显卡，推荐）

需要 NVIDIA 显卡（16GB 显存较好）。没有的话，用 Colab 免费的 T4 显卡：

1. 打开 https://colab.research.google.com → 文件 → 上传笔记本 → 选 `ai_studio/AI_Studio_Colab.ipynb`
   （如果仓库是公开的，也可以直接打开：
   `https://colab.research.google.com/github/rbprosperitypurchasing-afk/rb-tools/blob/claude/sweet-turing-mb6b3k/ai_studio/AI_Studio_Colab.ipynb`）
2. 按笔记本第一格的说明设置 Hugging Face token（免费），然后「全部运行」
3. 打开出现的 `gradio.live` 链接，用户名 `rb`，密码在笔记本里设置

### 在有 NVIDIA 显卡的电脑上运行

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
pip install -r ai_studio/requirements.txt
python -m ai_studio.app
```

### 没有显卡时调试界面

```bash
python -m ai_studio.app --mock
```

`--mock` 不加载模型，只出占位图，用来改界面。

### 已知限制

- 视频模型不能用文字控制动作，只能调「动作幅度」；人物大动作容易变形，适合镜头推移、头发衣服飘动、产品旋转等小动作。
- Colab 免费版每天有使用时长限制；每次启动要重新下载模型（约 15GB，几分钟）。
- 生图与生成视频共用一张显卡，两者切换时要重新加载模型（约 1 分钟）。

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
