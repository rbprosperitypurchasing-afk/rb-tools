"""作品库：每个作品存成一个文件 + 同名 .json 记录生成参数。

保存位置由环境变量 AI_STUDIO_OUTPUT 决定（Colab 上设成 Google Drive 目录，关掉也不会丢）。
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np


def output_dir():
    path = Path(os.environ.get("AI_STUDIO_OUTPUT", "outputs"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _new_stem(kind):
    return f"{datetime.now():%Y%m%d_%H%M%S}_{kind}_{uuid.uuid4().hex[:6]}"


def _write_meta(path, kind, meta):
    record = {"kind": kind, "file": path.name, "created": datetime.now().isoformat(timespec="seconds"), **meta}
    path.with_suffix(".json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def save_image(image, meta, kind="image"):
    path = output_dir() / f"{_new_stem(kind)}.png"
    image.save(path)
    _write_meta(path, kind, meta)
    return str(path)


def save_video(frames, fps, meta):
    import imageio.v2 as imageio

    path = output_dir() / f"{_new_stem('video')}.mp4"
    # libx264 + yuv420p 才能在浏览器和手机上直接播放
    imageio.mimwrite(path, [np.asarray(f.convert("RGB")) for f in frames], fps=fps,
                     codec="libx264", quality=8, pixelformat="yuv420p", macro_block_size=8)
    _write_meta(path, "video", meta)
    return str(path)


def list_items():
    """返回所有作品（最新的在前），每项是 meta dict，带 "path"。"""
    items = []
    for meta_path in output_dir().glob("*.json"):
        try:
            record = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        file_path = meta_path.with_name(record.get("file", ""))
        if file_path.is_file():
            items.append({**record, "path": str(file_path)})
    return sorted(items, key=lambda r: r.get("created", ""), reverse=True)


def describe(record):
    """把一条记录变成给人看的说明文字。"""
    kind = {"image": "文字生图", "reference": "参考图生图", "video": "图片生成视频"}.get(record.get("kind"), "作品")
    lines = [f"**{kind}**　{record.get('created', '')}"]
    if record.get("prompt"):
        lines.append(f"- 描述：{record['prompt']}")
    if record.get("style"):
        lines.append(f"- 风格：{record['style']}　比例：{record.get('ratio', '')}")
    if record.get("reference_kind"):
        lines.append(f"- 参考类型：{'人物' if record['reference_kind'] == 'person' else '物品'}　相似度：{record.get('reference_strength')}")
    if record.get("motion") is not None:
        lines.append(f"- 动作幅度：{record['motion']}　帧数：{record.get('frames')}")
    lines.append(f"- 种子：{record.get('seed')}（填同一个种子可以重现）")
    lines.append(f"- 文件：`{record.get('file')}`")
    return "\n".join(lines)
