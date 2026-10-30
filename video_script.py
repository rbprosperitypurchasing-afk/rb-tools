#!/usr/bin/env python3
"""礼篮短视频脚本生成器（模板填空，无需联网 / API）。

用法：
  python3 video_script.py                 # 交互模式，逐项提问
  python3 video_script.py --product "金玉满堂礼篮" --price 188 \\
      --items "燕窝,鲍鱼,红酒,饼干" --points "进口产品,免费配送" \\
      --festival cny --audience elder --duration 30 --style unboxing --versions 2

结果会打印在终端，并保存到 output/ 目录（Markdown + CSV，CSV 可直接用 Excel 打开）。
"""

import argparse
import csv
import random
import re
import sys
from datetime import datetime
from pathlib import Path

from script_templates import AUDIENCES, COVER_TITLES, EACH_LIMITS, FESTIVALS, STYLES

DURATIONS = (15, 30, 60)
DEFAULT_OFFER = "限量供应，先订先得"
DEFAULT_CONTACT = "WhatsApp 私讯我们"
DEFAULT_AREA = "古晋"


def split_list(text):
    """把 "A,B，C、D" 拆成 ["A", "B", "C", "D"]。"""
    if not text:
        return []
    return [part.strip() for part in re.split(r"[,，、;；/\n]", text) if part.strip()]


def chunk(values, n):
    """把列表尽量平均分成 n 组（保持顺序）。"""
    n = max(1, min(n, len(values)))
    size, extra = divmod(len(values), n)
    groups, start = [], 0
    for i in range(n):
        end = start + size + (1 if i < extra else 0)
        groups.append(values[start:end])
        start = end
    return groups


def allocate_seconds(weights, total):
    """按权重把总秒数分给每个镜头，每个至少 1 秒，总和精确等于 total。"""
    if len(weights) > total:
        raise ValueError(f"{total} 秒放不下 {len(weights)} 个镜头")
    spare = total - len(weights)
    raw = [w / sum(weights) * spare for w in weights]
    secs = [1 + int(r) for r in raw]
    leftovers = sorted(range(len(raw)), key=lambda i: raw[i] - int(raw[i]), reverse=True)
    for i in leftovers[: total - sum(secs)]:
        secs[i] += 1
    return secs


def fmt_time(seconds):
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def build_context(info):
    festival = FESTIVALS[info["festival"]]
    price = str(info.get("price") or "").strip()
    if price and not price.upper().startswith("RM"):
        price = f"RM{price}"
    return {
        "product": info["product"],
        "price_text": price or "价格私讯了解",
        "items_text": "、".join(info["items"]) or info["product"],
        "festival": festival["name"],
        "greeting": festival["greeting"],
        "mood": festival["mood"],
        "props": festival["props"],
        "audience": AUDIENCES[info["audience"]],
        "offer": info.get("offer") or DEFAULT_OFFER,
        "contact": info.get("contact") or DEFAULT_CONTACT,
        "area": info.get("area") or DEFAULT_AREA,
    }


def fill(template, ctx):
    return template.format_map(ctx)


def plan_shots(style_key, duration, items, points):
    """展开模板：省略可选镜头、按内容物/卖点拆分镜头。返回 [(模板, 额外占位符)]。"""
    values = {"items": items, "points": points}
    planned = []
    for shot in STYLES[style_key]["shots"]:
        if shot.get("optional") and duration <= 15:
            continue
        each = shot.get("each")
        if not each:
            planned.append((shot, {}))
            continue
        source = values[each]
        if not source:
            continue
        name = "item" if each == "items" else "point"
        joiner = "、" if each == "items" else "，"
        for group in chunk(source, EACH_LIMITS[each][duration]):
            planned.append((shot, {name: joiner.join(group)}))
    return planned


def generate_script(info, rng):
    ctx = build_context(info)
    duration = info["duration"]
    planned = plan_shots(info["style"], duration, info["items"], info["points"])
    secs = allocate_seconds([shot["weight"] for shot, _ in planned], duration)

    shots, start = [], 0
    for idx, ((shot, extra), sec) in enumerate(zip(planned, secs), 1):
        local = {**ctx, **extra}
        shots.append({
            "no": idx,
            "time": f"{fmt_time(start)}-{fmt_time(start + sec)}",
            "seconds": sec,
            "visual": fill(rng.choice(shot["visual"]), local),
            "voice": fill(rng.choice(shot["voice"]), local),
            "caption": fill(rng.choice(shot["caption"]), local),
            "note": fill(shot.get("note", ""), local),
        })
        start += sec

    festival = FESTIVALS[info["festival"]]
    return {
        "info": info,
        "context": ctx,
        "style_name": STYLES[info["style"]]["name"],
        "covers": [fill(t, ctx) for t in rng.sample(COVER_TITLES, 3)],
        "shots": shots,
        "bgm": festival["bgm"],
        "hashtags": festival["hashtags"],
    }


def _cell(text):
    return str(text).replace("|", "｜").replace("\n", " ")


def to_markdown(script, version):
    ctx, info = script["context"], script["info"]
    lines = [
        f"# 短视频脚本｜{ctx['product']}（版本 {version}）",
        "",
        f"- 风格：{script['style_name']}　时长：{info['duration']} 秒　节日：{ctx['festival']}　对象：{ctx['audience']}",
        f"- 价格：{ctx['price_text']}　优惠：{ctx['offer']}　联系：{ctx['contact']}　配送：{ctx['area']}",
        f"- 内容物：{ctx['items_text']}",
        "",
        "## 封面标题（三选一）",
        *[f"{i}. {t}" for i, t in enumerate(script["covers"], 1)],
        "",
        "## 分镜脚本",
        "| # | 时间 | 画面 | 口播 | 字幕 | 拍摄提示 |",
        "|---|---|---|---|---|---|",
    ]
    for s in script["shots"]:
        lines.append("| " + " | ".join(_cell(v) for v in (
            s["no"], f"{s['time']}（{s['seconds']}s）", s["visual"], s["voice"], s["caption"], s["note"],
        )) + " |")
    lines += [
        "",
        "## BGM 建议",
        *[f"- {b}" for b in script["bgm"]],
        "",
        "## Hashtag",
        " ".join(script["hashtags"]),
        "",
    ]
    return "\n".join(lines)


def save(scripts, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    product = scripts[0]["context"]["product"]
    safe = re.sub(r'[\\/:*?"<>|\s]+', "_", product).strip("_") or "script"
    stem = f"{safe}_{datetime.now():%Y%m%d_%H%M%S}"

    md_path = out_dir / f"{stem}.md"
    md_path.write_text("\n\n---\n\n".join(to_markdown(s, i) for i, s in enumerate(scripts, 1)), encoding="utf-8")

    csv_path = out_dir / f"{stem}.csv"
    # utf-8-sig 让 Excel 正确显示中文
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["版本", "镜头", "时间", "秒数", "画面", "口播", "字幕", "拍摄提示"])
        for i, s in enumerate(scripts, 1):
            for shot in s["shots"]:
                writer.writerow([i, shot["no"], shot["time"], shot["seconds"],
                                 shot["visual"], shot["voice"], shot["caption"], shot["note"]])
    return md_path, csv_path


# ---------- 交互输入 ----------

def ask(prompt, default=None, required=False):
    suffix = f"（默认：{default}）" if default else ""
    while True:
        value = input(f"{prompt}{suffix}：").strip()
        if value:
            return value
        if default is not None or not required:
            return default
        print("  这一项必须填写。")


def ask_choice(prompt, options, default):
    """options: {key: 显示名}。可以输入编号或 key。"""
    keys = list(options)
    print(prompt)
    for i, key in enumerate(keys, 1):
        print(f"  {i}. {options[key]}{'  ← 默认' if key == default else ''}")
    while True:
        value = input("请选择编号：").strip()
        if not value:
            return default
        if value.isdigit() and 1 <= int(value) <= len(keys):
            return keys[int(value) - 1]
        if value in options:
            return value
        print("  输入无效，请重新选择。")


def interactive(args):
    print("=== RB 礼篮短视频脚本生成器 ===（直接按 Enter 使用默认值）\n")
    args.product = args.product or ask("产品/礼篮名称", required=True)
    args.price = args.price or ask("价格（RM，可留空）")
    args.items = args.items or ask("内容物（用逗号分隔）", required=True)
    args.points = args.points or ask("卖点（用逗号分隔，建议 2-3 个，可留空）")
    if args.festival is None:
        args.festival = ask_choice("节日/场合：", {k: v["name"] for k, v in FESTIVALS.items()}, "cny")
    if args.audience is None:
        args.audience = ask_choice("送礼对象：", AUDIENCES, "elder")
    if args.style is None:
        args.style = ask_choice("视频风格：", {k: f"{v['name']} — {v['desc']}" for k, v in STYLES.items()}, "unboxing")
    if args.duration is None:
        args.duration = int(ask_choice("视频时长：", {str(d): f"{d} 秒" for d in DURATIONS}, "30"))
    args.offer = args.offer or ask("优惠信息", default=DEFAULT_OFFER)
    args.contact = args.contact or ask("联系方式", default=DEFAULT_CONTACT)
    print()


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="礼篮短视频脚本生成器（模板填空）")
    p.add_argument("--product", help="产品/礼篮名称；不填则进入交互模式")
    p.add_argument("--price", help="价格，如 188")
    p.add_argument("--items", help="内容物，逗号分隔")
    p.add_argument("--points", help="卖点，逗号分隔")
    p.add_argument("--festival", choices=FESTIVALS, help="节日：" + " / ".join(f"{k}={v['name']}" for k, v in FESTIVALS.items()))
    p.add_argument("--audience", choices=AUDIENCES, help="对象：" + " / ".join(f"{k}={v}" for k, v in AUDIENCES.items()))
    p.add_argument("--style", choices=STYLES, help="风格：" + " / ".join(f"{k}={v['name']}" for k, v in STYLES.items()))
    p.add_argument("--duration", type=int, choices=DURATIONS, help="时长（秒）")
    p.add_argument("--offer", help="优惠信息")
    p.add_argument("--contact", help="联系方式")
    p.add_argument("--area", default=DEFAULT_AREA, help="配送地区（默认：古晋）")
    p.add_argument("--versions", type=int, default=1, help="生成几个不同版本（默认 1）")
    p.add_argument("--seed", type=int, help="随机种子，填同一个数字会得到同样的结果")
    p.add_argument("--out", default="output", help="保存目录（默认 output/）")
    p.add_argument("--no-save", action="store_true", help="只打印，不保存文件")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not args.product:
        if not sys.stdin.isatty():
            sys.exit("错误：非交互环境请用 --product 等参数提供信息。")
        interactive(args)

    info = {
        "product": args.product,
        "price": args.price,
        "items": split_list(args.items),
        "points": split_list(args.points),
        "festival": args.festival or "cny",
        "audience": args.audience or "elder",
        "style": args.style or "unboxing",
        "duration": args.duration or 30,
        "offer": args.offer,
        "contact": args.contact,
        "area": args.area,
    }
    if not info["items"]:
        sys.exit("错误：请至少填写一个内容物（--items）。")

    rng = random.Random(args.seed)
    scripts = [generate_script(info, rng) for _ in range(max(1, args.versions))]
    for i, s in enumerate(scripts, 1):
        print(to_markdown(s, i))

    if not args.no_save:
        md_path, csv_path = save(scripts, args.out)
        print(f"已保存：{md_path}\n已保存：{csv_path}")


if __name__ == "__main__":
    main()
