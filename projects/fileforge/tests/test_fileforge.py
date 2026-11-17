import os
import subprocess
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import core
from gui import build_window, early_exit


class SupportedTargetsTests(unittest.TestCase):
    def test_text_targets(self):
        self.assertEqual(core.supported_targets("notes.txt"),
                         [".csv", ".json", ".md"])
        self.assertEqual(core.supported_targets("notes.md"), [".html"])
        self.assertEqual(core.supported_targets("page.html"), [".txt"])
        self.assertEqual(core.supported_targets("data.json"), [".csv", ".txt"])
        self.assertEqual(core.supported_targets("data.csv"), [".json", ".txt"])

    def test_media_targets(self):
        self.assertEqual(core.supported_targets("pic.PNG"),
                         sorted(core.IMAGE_EXTS - {".png"}))
        self.assertEqual(core.supported_targets("song.mp3"),
                         sorted(core.AUDIO_EXTS - {".mp3"}))

    def test_unknown_extension(self):
        self.assertEqual(core.supported_targets("archive.zip"), [])


class TextConversionTests(unittest.TestCase):
    def test_txt_to_md_wraps_paragraphs(self):
        result = core.convert_text("one line\nstill one\n\nsecond para", ".txt", ".md")
        self.assertEqual(result, "one line\nstill one\n\nsecond para\n")

    def test_md_to_html_headings_bold_and_lists(self):
        source = "# Title\n\n**bold** and <script>\n\n- first\n- second\n\n1. one\n2. two\n"
        result = core.convert_text(source, ".md", ".html")
        self.assertIn("<h1>Title</h1>", result)
        self.assertIn("<strong>bold</strong>", result)
        self.assertIn("&lt;script&gt;", result)
        self.assertIn("<ul>", result)
        self.assertIn("<li>first</li>", result)
        self.assertIn("<ol>", result)
        self.assertIn("<li>two</li>", result)

    def test_html_to_txt_strips_tags(self):
        result = core.convert_text(
            "<h1>Hello</h1><p>World &amp; friends</p>", ".html", ".txt")
        self.assertEqual(result, "Hello\nWorld & friends\n")

    def test_roundtrip_txt_json(self):
        text = "a line\nwith <chars> & stuff\n"
        self.assertEqual(
            core.convert_text(core.convert_text(text, ".txt", ".json"),
                              ".json", ".txt"),
            text)

    def test_roundtrip_txt_csv(self):
        text = "first, with comma\nsecond\n"
        self.assertEqual(
            core.convert_text(core.convert_text(text, ".txt", ".csv"),
                              ".csv", ".txt"),
            text)

    def test_roundtrip_csv_json(self):
        source = "name,age\nAda,36\nBob,41\n"
        as_json = core.convert_text(source, ".csv", ".json")
        self.assertEqual(core.convert_text(as_json, ".json", ".csv"), source)

    def test_invalid_pairs_raise_clear_errors(self):
        with self.assertRaises(core.ConversionError):
            core.convert_text("x", ".txt", ".md-unknown")
        with self.assertRaises(core.ConversionError):
            core.convert_text("x", ".txt", ".txt")
        with self.assertRaises(core.ConversionError):
            core.convert_text("# x", ".md", ".json")


class MediaCommandTests(unittest.TestCase):
    def test_image_command(self):
        command = core.build_media_command("in.png", "out.webp")
        self.assertEqual(command, [
            "ffmpeg", "-y", "-i", "in.png", "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2", "out.webp"])

    def test_audio_command(self):
        self.assertEqual(core.build_media_command("in.wav", "out.mp3"), [
            "ffmpeg", "-y", "-i", "in.wav", "-codec:a", "libmp3lame",
            "-b:a", "192k", "out.mp3"])
        self.assertEqual(core.build_media_command("in.mp3", "out.wav"), [
            "ffmpeg", "-y", "-i", "in.mp3", "-codec:a", "pcm_s16le",
            "out.wav"])

    def test_invalid_media_pairs(self):
        with self.assertRaises(core.ConversionError):
            core.build_media_command("in.png", "out.mp3")
        with self.assertRaises(core.ConversionError):
            core.build_media_command("in.png", "out.png")


class ConvertFileTests(unittest.TestCase):
    def test_text_file_roundtrip_on_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            src = os.path.join(directory, "a.txt")
            mid = os.path.join(directory, "a.json")
            dst = os.path.join(directory, "a-restored.txt")
            with open(src, "w", encoding="utf-8") as handle:
                handle.write("hello\nworld\n")
            self.assertEqual(core.convert_file(src, mid), mid)
            self.assertEqual(core.convert_file(mid, dst), dst)
            with open(dst, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "hello\nworld\n")

    def test_media_dispatch_uses_injected_runner(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0)

        core.convert_file("in.ogg", "out.m4a", runner=fake_run)
        self.assertEqual(calls[0][0], core.build_media_command("in.ogg", "out.m4a"))

    def test_invalid_pair_on_disk(self):
        with self.assertRaises(core.ConversionError):
            core.convert_file("a.md", "b.csv")


class GuiTests(unittest.TestCase):
    def test_early_args(self):
        self.assertEqual(early_exit(["--help"]),
                         ("usage: fileforge [--help | --version]", 0))
        self.assertEqual(early_exit(["--version"]), ("fileforge 0.1.0", 0))
        self.assertIsNone(early_exit([]))

    def test_offscreen_smoke(self):
        from PySide6 import QtWidgets
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        window = build_window()
        self.assertIsNotNone(window)
        self.assertEqual(window.windowTitle(), "fileforge")
        window.close()
        self.assertIs(app, QtWidgets.QApplication.instance())


if __name__ == "__main__":
    unittest.main()
