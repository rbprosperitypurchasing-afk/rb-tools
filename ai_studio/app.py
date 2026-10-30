"""RB AI 创作室 —— 网页界面。

启动：
  python -m ai_studio.app                     # 本机 http://127.0.0.1:7860
  python -m ai_studio.app --share --password 1234   # 生成公开链接给团队用（Colab 用这个）
  python -m ai_studio.app --mock              # 没有显卡时调试界面，只出占位图
"""

import argparse
import os

import gradio as gr

from . import storage
from .engine import RATIOS, STYLES, Engine

engine = Engine()

GPU = {"concurrency_id": "gpu", "concurrency_limit": 1}  # 所有生成任务排队，共用一张显卡
KINDS = {"人物（保持脸部）": "person", "物品（保持外观）": "object"}


# ---------- 生成 ----------

def _gallery(paths, metas):
    return [(p, f"种子 {m['seed']}") for p, m in zip(paths, metas)]


def _image_info(meta):
    return f"实际使用的英文描述：`{meta['prompt_en']}`\n\n起始种子：{meta['seed']}（想微调同一张图，就填回这个种子再改描述）"


def run_text_to_image(prompt, style, ratio, count, seed, progress=gr.Progress()):
    if not prompt.strip():
        raise gr.Error("请先输入画面描述。")
    progress(0, desc="生成中（第一次要下载、加载模型，约需几分钟）…")
    results = engine.text_to_image(prompt, style, ratio, count, seed)
    metas = [m for _, m in results]
    paths = [storage.save_image(img, m, "image") for img, m in results]
    return _gallery(paths, metas), paths, _image_info(metas[0])


def run_reference(reference, kind, strength, prompt, style, ratio, count, seed, progress=gr.Progress()):
    if reference is None:
        raise gr.Error("请先上传参考图。")
    if not prompt.strip():
        raise gr.Error("请描述新的场景，例如：站在海边，穿白色衬衫。")
    progress(0, desc="生成中…")
    results = engine.reference_to_image(reference, KINDS[kind], strength, prompt, style, ratio, count, seed)
    metas = [m for _, m in results]
    paths = [storage.save_image(img, m, "reference") for img, m in results]
    return _gallery(paths, metas), paths, _image_info(metas[0])


def run_video(image, motion, frames, seed, progress=gr.Progress()):
    if image is None:
        raise gr.Error("请先上传或选择一张图片。")
    progress(0, desc="生成视频中（约 3-6 分钟，请耐心等待）…")
    frames_out, meta = engine.image_to_video(image, motion, frames, seed)
    path = storage.save_video(frames_out, meta["fps"], meta)
    return path, f"种子：{meta['seed']}　尺寸：{meta['width']}x{meta['height']}　时长约 {len(frames_out) / meta['fps']:.1f} 秒"


# ---------- 作品库 ----------

def load_library():
    records = storage.list_items()
    gallery = [(r["path"], r.get("prompt") or ("视频" if r.get("kind") == "video" else "")) for r in records]
    summary = f"共 {len(records)} 个作品，保存在 `{storage.output_dir()}`" if records else "还没有作品，先去生成一张吧。"
    return gallery, records, summary, "", None


def on_library_select(records, evt: gr.SelectData):
    record = records[evt.index]
    return storage.describe(record), record["path"]


def on_gallery_select(paths, evt: gr.SelectData):
    return paths[evt.index]


def send_to(tab_id):
    def handler(path):
        if not path:
            gr.Warning("请先点选一张图片。")
            return gr.update(), gr.update()
        if path.endswith(".mp4"):
            gr.Warning("这是视频，请选择图片。")
            return gr.update(), gr.update()
        return path, gr.Tabs(selected=tab_id)
    return handler


def send_row():
    with gr.Row():
        to_ref = gr.Button("➡ 用作参考图（保持人物/物品）", size="sm")
        to_video = gr.Button("➡ 用这张生成视频", size="sm")
    return to_ref, to_video


# ---------- 界面 ----------

def image_options():
    with gr.Row():
        style = gr.Dropdown(list(STYLES), value="写实摄影", label="风格")
        ratio = gr.Dropdown(list(RATIOS), value="1:1 方形", label="比例")
    with gr.Row():
        count = gr.Slider(1, 4, value=2, step=1, label="生成张数")
        seed = gr.Number(value=-1, precision=0, label="种子（-1 = 随机）")
    return style, ratio, count, seed


def build_ui():
    with gr.Blocks(title="RB AI 创作室") as demo:
        gr.Markdown("# RB AI 创作室\n文字生图 → 保持人物/物品 → 图片生成视频。描述可以直接写中文，会自动翻译。")

        with gr.Tabs() as tabs:
            with gr.Tab("① 文字生图", id="text"):
                with gr.Row():
                    with gr.Column(scale=2):
                        t_prompt = gr.Textbox(label="画面描述", lines=4,
                                              placeholder="例如：一位穿红色旗袍的年轻女子，站在古晋河边，傍晚，微笑")
                        t_style, t_ratio, t_count, t_seed = image_options()
                        t_btn = gr.Button("生成图片", variant="primary")
                    with gr.Column(scale=3):
                        t_out = gr.Gallery(label="结果（点选一张可继续使用）", columns=2, height=520)
                        t_send = send_row()
                        t_info = gr.Markdown()
                        t_paths, t_selected = gr.State([]), gr.State(None)

            with gr.Tab("② 人物/物品一致", id="ref"):
                gr.Markdown("上传一张人物或物品的图，生成**同一个人/同一件东西**在新场景里的图片。")
                with gr.Row():
                    with gr.Column(scale=2):
                        r_image = gr.Image(label="参考图", type="pil", height=300)
                        r_kind = gr.Radio(list(KINDS), value=list(KINDS)[0], label="参考类型")
                        r_strength = gr.Slider(0.3, 1.0, value=0.6, step=0.05,
                                               label="相似度（越高越像参考图，但越不听描述）")
                        r_prompt = gr.Textbox(label="新场景描述", lines=3,
                                              placeholder="例如：在咖啡馆看书，暖色灯光")
                        r_style, r_ratio, r_count, r_seed = image_options()
                        r_btn = gr.Button("生成图片", variant="primary")
                    with gr.Column(scale=3):
                        r_out = gr.Gallery(label="结果", columns=2, height=520)
                        r_send = send_row()
                        r_info = gr.Markdown()
                        r_paths, r_selected = gr.State([]), gr.State(None)

            with gr.Tab("③ 图片生成视频", id="video"):
                gr.Markdown("把一张图片变成约 2-4 秒的动态视频。画面主体清晰、背景简单，效果最好。")
                with gr.Row():
                    with gr.Column(scale=2):
                        v_image = gr.Image(label="起始图片", type="pil", height=300)
                        v_motion = gr.Slider(1, 255, value=127, step=1, label="动作幅度（越大动得越多，太大容易变形）")
                        v_frames = gr.Radio([14, 25], value=25, label="帧数（25 帧更长，但更慢）")
                        v_seed = gr.Number(value=-1, precision=0, label="种子（-1 = 随机）")
                        v_btn = gr.Button("生成视频", variant="primary")
                    with gr.Column(scale=3):
                        v_out = gr.Video(label="结果", height=420)
                        v_info = gr.Markdown()

            with gr.Tab("④ 作品库", id="library") as lib_tab:
                with gr.Row():
                    lib_refresh = gr.Button("刷新", size="sm")
                    lib_summary = gr.Markdown()
                lib_gallery = gr.Gallery(label="全部作品（点选查看详情）", columns=5, height=520)
                lib_send = send_row()
                lib_detail = gr.Markdown()
                lib_records, lib_selected = gr.State([]), gr.State(None)

        # 每个结果区都可以把图片送去“参考图”或“生成视频”
        for gallery, paths, selected in ((t_out, t_paths, t_selected), (r_out, r_paths, r_selected)):
            gallery.select(on_gallery_select, paths, selected)
        lib_gallery.select(on_library_select, lib_records, [lib_detail, lib_selected])

        for (to_ref, to_video), selected in ((t_send, t_selected), (r_send, r_selected), (lib_send, lib_selected)):
            to_ref.click(send_to("ref"), selected, [r_image, tabs])
            to_video.click(send_to("video"), selected, [v_image, tabs])

        t_btn.click(run_text_to_image, [t_prompt, t_style, t_ratio, t_count, t_seed], [t_out, t_paths, t_info], **GPU)
        r_btn.click(run_reference, [r_image, r_kind, r_strength, r_prompt, r_style, r_ratio, r_count, r_seed],
                    [r_out, r_paths, r_info], **GPU)
        v_btn.click(run_video, [v_image, v_motion, v_frames, v_seed], [v_out, v_info], **GPU)

        library_outputs = [lib_gallery, lib_records, lib_summary, lib_detail, lib_selected]
        lib_tab.select(load_library, None, library_outputs)
        lib_refresh.click(load_library, None, library_outputs)
    return demo


def main():
    parser = argparse.ArgumentParser(description="RB AI 创作室")
    parser.add_argument("--share", action="store_true", help="生成公开链接（Colab 必须加）")
    parser.add_argument("--password", default=os.environ.get("AI_STUDIO_PASSWORD"), help="登录密码，用户名固定为 rb")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--mock", action="store_true", help="不加载模型，只出占位图（调试界面用）")
    args = parser.parse_args()

    engine.mock = args.mock
    auth = ("rb", args.password) if args.password else None
    build_ui().queue().launch(share=args.share, auth=auth, server_name="0.0.0.0", server_port=args.port,
                              allowed_paths=[str(storage.output_dir().resolve())], theme=gr.themes.Soft())


if __name__ == "__main__":
    main()
