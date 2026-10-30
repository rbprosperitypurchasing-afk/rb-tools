"""生成引擎：负责加载开源模型，提供 文字生图 / 参考图生图 / 图片生成视频。

显卡显存有限（Colab 免费 T4 约 15GB），所以同一时间只把一个大模型放在显卡上：
生图时释放视频模型，生成视频时释放生图模型。切换时会重新加载，需要等一会。

mock=True 时不加载任何模型，只画占位图，用于在没有显卡的电脑上调试界面。
"""

import gc
import random
import re

from PIL import Image, ImageDraw

SDXL_MODEL = "stabilityai/stable-diffusion-xl-base-1.0"
SDXL_VAE = "madebyollin/sdxl-vae-fp16-fix"  # 修正 SDXL 在 fp16 下出黑图的问题
IP_ADAPTER_REPO = "h94/IP-Adapter"
IP_ADAPTER_WEIGHTS = {
    "person": "ip-adapter-plus-face_sdxl_vit-h.safetensors",  # 保持人物脸部
    "object": "ip-adapter-plus_sdxl_vit-h.safetensors",  # 保持物品外观
}
SVD_MODEL = "stabilityai/stable-video-diffusion-img2vid-xt"

STYLES = {
    "无（按描述）": ("{p}", ""),
    "写实摄影": ("{p}, photorealistic, professional photography, 85mm lens, natural lighting, highly detailed", "cartoon, anime, painting"),
    "产品棚拍": ("{p}, product photography, studio lighting, clean background, commercial, sharp focus, high detail", "people, clutter"),
    "电影感": ("{p}, cinematic still, dramatic lighting, film grain, shallow depth of field, color graded", ""),
    "动漫": ("{p}, anime style, vibrant colors, clean line art, detailed illustration", "photo, realistic"),
    "3D 卡通": ("{p}, 3d render, pixar style, cute, soft lighting, octane render", "photo, realistic"),
    "国风水墨": ("{p}, traditional chinese ink painting, watercolor, elegant, minimal", "photo, 3d"),
}
NEGATIVE = "lowres, blurry, bad anatomy, bad hands, extra fingers, deformed, watermark, text, logo, jpeg artifacts"

RATIOS = {
    "1:1 方形": (1024, 1024),
    "3:4 竖图": (896, 1152),
    "4:3 横图": (1152, 896),
    "9:16 手机竖屏": (768, 1344),
    "16:9 横屏": (1344, 768),
}

_CJK = re.compile(r"[㐀-鿿]")


def translate(prompt):
    """SDXL 只懂英文，含中文的描述自动翻译（免费 Google 翻译，失败就用原文）。"""
    if not _CJK.search(prompt):
        return prompt
    try:
        from deep_translator import GoogleTranslator

        return GoogleTranslator(source="auto", target="en").translate(prompt) or prompt
    except Exception:
        return prompt


def build_prompt(prompt, style):
    template, extra_negative = STYLES.get(style, STYLES["无（按描述）"])
    english = translate(prompt.strip())
    negative = ", ".join(n for n in (NEGATIVE, extra_negative) if n)
    return template.replace("{p}", english), negative


def resolve_seed(seed):
    seed = int(seed) if seed is not None else -1
    return random.randint(0, 2**31 - 1) if seed < 0 else seed


def fit_crop(image, width, height):
    """按比例缩放后居中裁剪成指定尺寸。"""
    image = image.convert("RGB")
    scale = max(width / image.width, height / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def video_size(image):
    """SVD 训练尺寸是 1024x576，竖图就用 576x1024。"""
    return (576, 1024) if image.height > image.width else (1024, 576)


class Engine:
    def __init__(self, mock=False):
        self.mock = mock
        self.image_pipe = None
        self.video_pipe = None
        self.adapter = None  # 当前加载的 IP-Adapter："person" / "object" / None

    # ---------- 模型管理 ----------

    def _free_gpu(self):
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def _get_image_pipe(self):
        if self.video_pipe is not None:
            self.video_pipe = None
            self._free_gpu()
        if self.image_pipe is None:
            import torch
            from diffusers import AutoencoderKL, DPMSolverMultistepScheduler, StableDiffusionXLPipeline

            vae = AutoencoderKL.from_pretrained(SDXL_VAE, torch_dtype=torch.float16)
            pipe = StableDiffusionXLPipeline.from_pretrained(
                SDXL_MODEL, vae=vae, torch_dtype=torch.float16, variant="fp16", use_safetensors=True
            )
            pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, use_karras_sigmas=True)
            self.image_pipe = pipe.to("cuda")
            self.adapter = None
        return self.image_pipe

    def _set_adapter(self, pipe, kind):
        if self.adapter == kind:
            return
        if self.adapter is not None:
            pipe.unload_ip_adapter()
            self.adapter = None
        if kind is not None:
            pipe.load_ip_adapter(
                IP_ADAPTER_REPO,
                subfolder="sdxl_models",
                weight_name=IP_ADAPTER_WEIGHTS[kind],
                image_encoder_folder="models/image_encoder",  # vit-h 版本用的图像编码器
            )
            pipe.to("cuda")
            self.adapter = kind

    def _get_video_pipe(self):
        if self.image_pipe is not None:
            self.image_pipe = None
            self.adapter = None
            self._free_gpu()
        if self.video_pipe is None:
            import torch
            from diffusers import StableVideoDiffusionPipeline

            pipe = StableVideoDiffusionPipeline.from_pretrained(SVD_MODEL, torch_dtype=torch.float16, variant="fp16")
            pipe.enable_model_cpu_offload()
            self.video_pipe = pipe
        return self.video_pipe

    # ---------- 生成 ----------

    def text_to_image(self, prompt, style, ratio, count, seed, steps=25, guidance=6.0):
        return self._generate_images(prompt, style, ratio, count, seed, steps, guidance, reference=None)

    def reference_to_image(self, reference, kind, strength, prompt, style, ratio, count, seed, steps=25, guidance=6.0):
        return self._generate_images(prompt, style, ratio, count, seed, steps, guidance,
                                     reference=(reference, kind, strength))

    def _generate_images(self, prompt, style, ratio, count, seed, steps, guidance, reference):
        """返回 [(PIL 图片, 参数 dict)]，每张图一个种子（起始种子 + 序号），方便复现。"""
        width, height = RATIOS[ratio]
        full_prompt, negative = build_prompt(prompt, style)
        base_seed = resolve_seed(seed)
        meta = {"prompt": prompt, "prompt_en": full_prompt, "style": style, "ratio": ratio,
                "width": width, "height": height, "steps": steps, "guidance": guidance}
        if reference:
            meta.update(reference_kind=reference[1], reference_strength=reference[2])

        results = []
        for i in range(int(count)):
            item_seed = base_seed + i
            if self.mock:
                image = _placeholder(width, height, f"{prompt}\nseed {item_seed}", item_seed)
            else:
                image = self._run_sdxl(full_prompt, negative, width, height, item_seed, steps, guidance, reference)
            results.append((image, {**meta, "seed": item_seed}))
        return results

    def _run_sdxl(self, prompt, negative, width, height, seed, steps, guidance, reference):
        import torch

        pipe = self._get_image_pipe()
        kwargs = {}
        if reference:
            ref_image, kind, strength = reference
            self._set_adapter(pipe, kind)
            pipe.set_ip_adapter_scale(float(strength))
            kwargs["ip_adapter_image"] = ref_image.convert("RGB")
        else:
            self._set_adapter(pipe, None)
        generator = torch.Generator("cuda").manual_seed(seed)
        return pipe(prompt=prompt, negative_prompt=negative, width=width, height=height,
                    num_inference_steps=int(steps), guidance_scale=float(guidance),
                    generator=generator, **kwargs).images[0]

    def image_to_video(self, image, motion, frames, seed, fps=7):
        """返回 (帧列表, 参数 dict)。motion 是动作幅度 1-255，越大动得越多。"""
        width, height = video_size(image)
        image = fit_crop(image, width, height)
        seed = resolve_seed(seed)
        meta = {"motion": int(motion), "frames": int(frames), "fps": fps, "seed": seed,
                "width": width, "height": height}
        if self.mock:
            return _placeholder_frames(image, int(frames)), meta

        import torch

        pipe = self._get_video_pipe()
        generator = torch.Generator("cpu").manual_seed(seed)
        result = pipe(image, width=width, height=height, num_frames=int(frames), motion_bucket_id=int(motion),
                      noise_aug_strength=0.02, decode_chunk_size=4, generator=generator)
        return result.frames[0], meta


# ---------- mock 模式的占位图 ----------

def _placeholder(width, height, text, seed):
    rng = random.Random(seed)
    top = tuple(rng.randint(40, 200) for _ in range(3))
    bottom = tuple(rng.randint(40, 200) for _ in range(3))
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        t = y / max(1, height - 1)
        draw.line([(0, y), (width, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    draw.multiline_text((40, 40), f"[MOCK]\n{text}", fill="white")
    return image


def _placeholder_frames(image, count):
    frames = []
    for i in range(count):
        frame = image.copy()
        draw = ImageDraw.Draw(frame)
        x = int((frame.width - 80) * i / max(1, count - 1))
        draw.rectangle([x, frame.height - 100, x + 80, frame.height - 20], fill="white")
        frames.append(frame)
    return frames
