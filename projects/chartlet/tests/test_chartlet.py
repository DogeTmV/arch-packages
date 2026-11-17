"""Tests for the chartlet CSV-to-SVG tool."""

import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "chartlet"
NS = "{http://www.w3.org/2000/svg}"


def run(*args):
    return subprocess.run([str(SCRIPT), *args], capture_output=True, text=True)


class ChartletTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def write_csv(self, text, name="data.csv"):
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def parse(self, name="out.svg"):
        return ET.parse(self.dir / name).getroot()

    def test_bar_heights_follow_values(self):
        csv_path = self.write_csv("name,value\nA,3\nB,6\nC,9\n")
        out = self.dir / "out.svg"
        result = run("bar", str(csv_path), str(out), "--x", "name", "--y", "value")
        self.assertEqual(result.returncode, 0, result.stderr)
        root = self.parse()
        bars = root.findall(f".//{NS}rect[@class='bar']")
        self.assertEqual(len(bars), 3)
        heights = [float(bar.get("height")) for bar in bars]
        self.assertAlmostEqual(heights[1] / heights[0], 2.0, places=5)
        self.assertAlmostEqual(heights[2] / heights[0], 3.0, places=5)

    def test_bar_chart_has_axes_gridlines_legend_and_title(self):
        csv_path = self.write_csv("name,value\nA,1\nB,2\n")
        result = run("bar", str(csv_path), str(self.dir / "out.svg"),
                     "--title", "Café totals", "--color", "2f9e6e")
        self.assertEqual(result.returncode, 0, result.stderr)
        root = self.parse()
        self.assertEqual(len(root.findall(f".//{NS}line[@class='axis']")), 2)
        self.assertEqual(len(root.findall(f".//{NS}line[@class='gridline']")), 5)
        self.assertIsNotNone(root.find(f".//{NS}g[@class='legend']"))
        self.assertEqual(root.find(f".//{NS}text[@class='title']").text, "Café totals")
        bars = root.findall(f".//{NS}rect[@class='bar']")
        self.assertTrue(all(bar.get("fill") == "#2f9e6e" for bar in bars))

    def test_line_chart_draws_polyline_points_and_gridlines(self):
        csv_path = self.write_csv("day,temp\nMon,10\nTue,15\nWed,12\n")
        result = run("line", str(csv_path), str(self.dir / "out.svg"), "--x", "day", "--y", "temp")
        self.assertEqual(result.returncode, 0, result.stderr)
        root = self.parse()
        polyline = root.find(f".//{NS}polyline[@class='line']")
        self.assertIsNotNone(polyline)
        self.assertEqual(len(polyline.get("points").split()), 3)
        self.assertEqual(len(root.findall(f".//{NS}circle[@class='point']")), 3)
        self.assertEqual(len(root.findall(f".//{NS}line[@class='gridline']")), 5)

    def test_pie_has_one_slice_per_row_and_keeps_utf8_labels(self):
        csv_path = self.write_csv("fruit,count\nPomme,5\nBirne,3\nМанго,2\n")
        result = run("pie", str(csv_path), str(self.dir / "out.svg"),
                     "--label", "fruit", "--value", "count", "--title", "Fruits")
        self.assertEqual(result.returncode, 0, result.stderr)
        root = self.parse()
        slices = root.findall(f".//{NS}path[@class='slice']")
        self.assertEqual(len(slices), 3)
        legend = " ".join(
            node.text or "" for node in root.findall(f".//{NS}text[@class='legend-label']")
        )
        for label in ("Pomme", "Birne", "Манго"):
            self.assertIn(label, legend)

    def test_sparkline_is_deterministic_and_contains_one_polyline(self):
        csv_path = self.write_csv("t,v\n1,4\n2,9\n3,2\n4,7\n")
        args = ("sparkline", str(csv_path), "--value", "v")
        first = self.dir / "one.svg"
        second = self.dir / "two.svg"
        self.assertEqual(run(*args, str(first)).returncode, 0)
        self.assertEqual(run(*args, str(second)).returncode, 0)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        root = ET.parse(first).getroot()
        self.assertIsNotNone(root.find(f".//{NS}polyline[@class='sparkline']"))
        self.assertFalse(root.findall(f".//{NS}line[@class='axis']"))

    def test_numeric_validation_names_row_and_column(self):
        csv_path = self.write_csv("name,value\nA,1\nB,oops\nC,3\n")
        result = run("bar", str(csv_path), str(self.dir / "out.svg"), "--x", "name", "--y", "value")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("row 3", result.stderr)
        self.assertIn("'value'", result.stderr)
        self.assertIn("number", result.stderr)
        self.assertFalse((self.dir / "out.svg").exists())

    def test_unknown_column_reports_available_columns(self):
        csv_path = self.write_csv("name,value\nA,1\n")
        result = run("bar", str(csv_path), str(self.dir / "out.svg"), "--x", "name", "--y", "missing")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not found", result.stderr)
        self.assertIn("name, value", result.stderr)

    def test_invalid_color_is_rejected(self):
        csv_path = self.write_csv("name,value\nA,1\n")
        result = run("bar", str(csv_path), str(self.dir / "out.svg"), "--x", "name", "--y", "value", "--color", "nope")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("color", result.stderr)

    def test_help_and_version_exit_zero(self):
        self.assertEqual(run("--help").returncode, 0)
        self.assertEqual(run("pie", "--help").returncode, 0)
        version = run("--version")
        self.assertEqual(version.returncode, 0)
        self.assertIn("0.1.0", version.stdout)

    def test_unknown_command_is_nonzero(self):
        result = run("frobnicate")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.strip())


if __name__ == "__main__":
    unittest.main()
