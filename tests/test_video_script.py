import csv
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import video_script as vs
from script_templates import AUDIENCES, FESTIVALS, STYLES


def make_info(**overrides):
    info = {
        "product": "金玉满堂礼篮",
        "price": "188",
        "items": ["燕窝", "鲍鱼", "红酒", "饼干", "茶叶"],
        "points": ["进口产品", "精美包装", "免费配送"],
        "festival": "cny",
        "audience": "elder",
        "style": "unboxing",
        "duration": 30,
        "offer": None,
        "contact": None,
        "area": "古晋",
    }
    info.update(overrides)
    return info


class TestHelpers(unittest.TestCase):
    def test_split_list_mixed_separators(self):
        self.assertEqual(vs.split_list("A,B，C、 D;;"), ["A", "B", "C", "D"])
        self.assertEqual(vs.split_list(None), [])

    def test_chunk_keeps_all_values(self):
        groups = vs.chunk(list("abcde"), 2)
        self.assertEqual(groups, [["a", "b", "c"], ["d", "e"]])
        self.assertEqual(vs.chunk(["a"], 4), [["a"]])

    def test_allocate_seconds_sums_to_total(self):
        for total in (15, 30, 60):
            secs = vs.allocate_seconds([2, 3, 3, 3, 2, 2, 2], total)
            self.assertEqual(sum(secs), total)
            self.assertTrue(all(s >= 1 for s in secs))


class TestGenerate(unittest.TestCase):
    def test_every_combination_fills_all_placeholders(self):
        rng = random.Random(0)
        for style in STYLES:
            for festival in FESTIVALS:
                for audience in AUDIENCES:
                    for duration in vs.DURATIONS:
                        script = vs.generate_script(make_info(
                            style=style, festival=festival, audience=audience, duration=duration), rng)
                        shots = script["shots"]
                        self.assertEqual(sum(s["seconds"] for s in shots), duration)
                        self.assertTrue(shots[-1]["time"].endswith(vs.fmt_time(duration)))
                        md = vs.to_markdown(script, 1)
                        self.assertNotIn("{", md)

    def test_all_items_appear(self):
        script = vs.generate_script(make_info(duration=15), random.Random(1))
        text = " ".join(s["visual"] + s["voice"] + s["caption"] for s in script["shots"])
        for item in make_info()["items"]:
            self.assertIn(item, text)

    def test_defaults_without_price_or_points(self):
        script = vs.generate_script(make_info(price="", points=[]), random.Random(2))
        self.assertEqual(script["context"]["price_text"], "价格私讯了解")
        self.assertEqual(script["context"]["offer"], vs.DEFAULT_OFFER)

    def test_price_prefix_not_duplicated(self):
        ctx = vs.build_context(make_info(price="RM288"))
        self.assertEqual(ctx["price_text"], "RM288")

    def test_seed_is_reproducible(self):
        a = vs.generate_script(make_info(), random.Random(42))
        b = vs.generate_script(make_info(), random.Random(42))
        self.assertEqual(a, b)


class TestCli(unittest.TestCase):
    def test_main_writes_markdown_and_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            vs.main(["--product", "测试/礼篮", "--items", "燕窝,红酒", "--versions", "2",
                     "--seed", "1", "--out", tmp])
            md = list(Path(tmp).glob("*.md"))
            csvs = list(Path(tmp).glob("*.csv"))
            self.assertEqual(len(md), 1)
            self.assertEqual(len(csvs), 1)
            self.assertIn("版本 2", md[0].read_text(encoding="utf-8"))
            with csvs[0].open(encoding="utf-8-sig") as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0][0], "版本")
            self.assertEqual({r[0] for r in rows[1:]}, {"1", "2"})


if __name__ == "__main__":
    unittest.main()
