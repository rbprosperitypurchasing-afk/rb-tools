import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image

from ai_studio import engine as eng
from ai_studio import storage


class TestEngineHelpers(unittest.TestCase):
    def test_build_prompt_applies_style_and_keeps_braces(self):
        prompt, negative = eng.build_prompt("a {gold} cup", "产品棚拍")
        self.assertTrue(prompt.startswith("a {gold} cup, product photography"))
        self.assertIn("lowres", negative)
        self.assertIn("people", negative)

    def test_english_prompt_not_translated(self):
        self.assertEqual(eng.translate("a red apple"), "a red apple")

    def test_resolve_seed(self):
        self.assertEqual(eng.resolve_seed(42), 42)
        self.assertGreaterEqual(eng.resolve_seed(-1), 0)

    def test_fit_crop_and_video_size(self):
        tall = Image.new("RGB", (600, 900))
        self.assertEqual(eng.video_size(tall), (576, 1024))
        self.assertEqual(eng.fit_crop(tall, 576, 1024).size, (576, 1024))
        self.assertEqual(eng.video_size(Image.new("RGB", (900, 600))), (1024, 576))


class TestMockGeneration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["AI_STUDIO_OUTPUT"] = self.tmp.name
        self.engine = eng.Engine(mock=True)

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("AI_STUDIO_OUTPUT", None)

    def test_text_to_image_seeds_and_sizes(self):
        results = self.engine.text_to_image("cat", "写实摄影", "9:16 手机竖屏", 3, 100)
        self.assertEqual([m["seed"] for _, m in results], [100, 101, 102])
        self.assertEqual(results[0][0].size, (768, 1344))

    def test_reference_meta(self):
        ref = Image.new("RGB", (300, 300))
        (_, meta), = self.engine.reference_to_image(ref, "person", 0.7, "beach", "电影感", "1:1 方形", 1, 5)
        self.assertEqual(meta["reference_kind"], "person")
        self.assertEqual(meta["reference_strength"], 0.7)

    def test_save_and_list_library(self):
        (img, meta), = self.engine.text_to_image("dog", "动漫", "1:1 方形", 1, 1)
        storage.save_image(img, meta, "image")
        frames, vmeta = self.engine.image_to_video(img, 127, 14, 3)
        self.assertEqual(len(frames), 14)
        self.assertEqual(frames[0].size, (1024, 576))
        video_path = storage.save_video(frames, vmeta["fps"], vmeta)
        self.assertGreater(Path(video_path).stat().st_size, 0)

        items = storage.list_items()
        self.assertEqual({i["kind"] for i in items}, {"image", "video"})
        for item in items:
            self.assertIn("种子", storage.describe(item))

    def test_library_skips_orphan_metadata(self):
        Path(self.tmp.name, "broken.json").write_text("{not json", encoding="utf-8")
        Path(self.tmp.name, "orphan.json").write_text('{"file": "missing.png"}', encoding="utf-8")
        self.assertEqual(storage.list_items(), [])


if __name__ == "__main__":
    unittest.main()
