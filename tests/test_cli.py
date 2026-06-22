import tempfile
import unittest
from pathlib import Path
from unittest import mock

from subsetzer import cli


class CliTests(unittest.TestCase):
    def test_help_exits_zero(self):
        with self.assertRaises(SystemExit) as ctx:
            cli.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_llm_raw_not_created_without_capture_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            infile = tmp_path / "input.srt"
            infile.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n")
            out_path = tmp_path / "out.srt"
            cli.main(["--input", str(infile), "--output", str(out_path), "--model", "dummy", "--target", "German", "--no-llm", "--force"])
            self.assertTrue(out_path.exists())
            raw_path = out_path.with_name(out_path.stem + "_raw.txt")
            self.assertFalse(raw_path.exists())

    def test_llm_raw_created_when_capture_flag_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            infile = tmp_path / "input.srt"
            infile.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n")
            out_path = tmp_path / "out.srt"
            cli.main(["--input", str(infile), "--output", str(out_path), "--model", "dummy", "--target", "German", "--no-llm", "--force", "--capture-raw"])
            self.assertTrue(out_path.exists())
            raw_path = out_path.with_name(out_path.stem + "_raw.txt")
            self.assertTrue(raw_path.exists())

    def test_api_url_cli_overrides_default(self):
        with mock.patch("subsetzer.cli.translate_range") as tr_mock:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                infile = tmp_path / "input.srt"
                infile.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n")
                outp = tmp_path / "out.srt"
                cli.main(["--input", str(infile), "--output", str(outp),
                          "--model", "dummy", "--target", "German", "--no-llm", "--force", "--host", "http://myhost:9999"])
                call_kwargs = tr_mock.call_args[1]
                self.assertEqual(call_kwargs["api_url"], "http://myhost:9999")

    def test_output_defaults_to_input_dir_with_iso_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            infile = tmp_path / "movie.srt"
            infile.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n")
            cli.main(["--input", str(infile), "--target", "Chinese", "--model", "dummy", "--no-llm", "--force"])
            default_out = tmp_path / "movie.auto2zh-cn.srt"
            self.assertTrue(default_out.exists(), f"Expected {default_out} to exist")

    def test_format_srt_is_default(self):
        parser = cli._build_parser()
        args = parser.parse_args(["--input", "x.srt", "--model", "t", "--target", "de"])
        self.assertEqual(args.format, "srt")

    def test_host_arg_dest_is_api_url(self):
        parser = cli._build_parser()
        args = parser.parse_args(["--input", "x.srt", "--model", "t", "--target", "de", "--host", "http://other:9999"])
        self.assertEqual(args.api_url, "http://other:9999")
