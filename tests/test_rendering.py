"""Mock PNG checks exercise deterministic output and complete episode previews."""

import io
import unittest

from PIL import Image, ImageChops

from backend.rendering import compose_preview, render_cut


class RenderingTests(unittest.TestCase):
    def setUp(self):
        self.unit = {
            "unit_id": "synthetic-cut-1", "order": 1,
            "action": "가상 주인공이 창가에서 하루를 준비한다.",
            "dialogue": [{"text": "오늘은 어떤 하루가 될까?"}],
            "character_id": "synthetic-character",
            "composition": "가상 인물의 전신", "continuity": "같은 청록색 상의",
        }

    def open_png(self, blob):
        self.assertTrue(blob.startswith(b"\x89PNG\r\n\x1a\n"))
        image = Image.open(io.BytesIO(blob))
        image.load()
        self.assertEqual(image.format, "PNG")
        return image

    def test_rough_and_candidates_are_readable_and_labeled(self):
        rough = self.open_png(render_cut(self.unit, rough=True))
        candidate = self.open_png(render_cut(self.unit))
        self.assertEqual(rough.size, (480, 400))
        self.assertEqual(candidate.size, (640, 640))
        for image in (rough, candidate):
            self.assertEqual(image.info["synthetic"], "true")
            self.assertEqual(image.info["unit_id"], self.unit["unit_id"])
            self.assertEqual(image.info["action"], self.unit["action"])
            # The actual top label area contains ink as well as paper.
            label = image.crop((image.width - 205, 35, image.width - 38, 64))
            self.assertGreater(len(label.getcolors(maxcolors=100_000)), 3)

    def test_candidates_differ_but_identity_and_determinism_are_preserved(self):
        first = render_cut(self.unit, variant=0)
        self.assertEqual(first, render_cut(self.unit, variant=0))
        a, b = self.open_png(first), self.open_png(render_cut(self.unit, variant=1))
        self.assertEqual(a.info["character_id"], b.info["character_id"])
        self.assertIsNotNone(ImageChops.difference(a, b).getbbox())
        self.assertEqual(a.info["dialogue"], "오늘은 어떤 하루가 될까?")

    def test_preview_includes_every_cut_in_supplied_order(self):
        cuts = [render_cut({**self.unit, "unit_id": f"cut-{i}", "order": i}) for i in range(1, 6)]
        preview = self.open_png(compose_preview(cuts))
        self.assertEqual(preview.info["cut_count"], "5")
        self.assertEqual(preview.info["unit_ids"].splitlines(), [f"cut-{i}" for i in range(1, 6)])
        self.assertEqual(preview.size, (940, 1482))
        # Five cells are populated, including the last row of an odd-cut episode.
        for index in range(5):
            x, y = 20 + (index % 2) * 460, 102 + (index // 2) * 460
            cell = preview.crop((x, y, x + 440, y + 440))
            self.assertGreater(len(cell.getcolors(maxcolors=300_000)), 10)

    def test_single_panel_and_long_multiline_korean_caption(self):
        action = ("가상 예시 문장입니다. " * 40) + "\n두 번째 줄"
        blob = render_cut({**self.unit, "action": action})
        image = self.open_png(blob)
        self.assertEqual(image.info["action"], action)
        single = self.open_png(compose_preview([blob]))
        self.assertEqual(single.info["cut_count"], "1")
        self.assertEqual(single.size, (480, 562))

    def test_invalid_preview_is_rejected(self):
        with self.assertRaises(ValueError):
            compose_preview([])
        with self.assertRaises(ValueError):
            compose_preview([b"not an image"])


if __name__ == "__main__":
    unittest.main()
