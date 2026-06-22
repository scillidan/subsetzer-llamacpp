import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

from subsetzer import cli


class CliTests(unittest.TestCase):
    def test_help_exits_zero(self):
        with self.assertRaises(SystemExit) as ctx:
            cli.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def _run_cli(self, extra_args=None):
        extra_args = extra_args or []
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            infile = tmp_path / "input.srt"
            infile.write_text(
                textwrap.dedent(
                    """\
                    1
                    00:00:00,000 --> 00:00:01,000
                    Hello
                    """
                )
            )
            outdir = tmp_path / "out"
            args = ["--in", str(infile), "--out", str(outdir), "--no-llm", "--flat"] + extra_args
            cli.main(args)
            outputs = list(outdir.glob("**/*"))
            return outdir, outputs

    def test_llm_raw_not_created_without_capture_flag(self):
        _, outputs = self._run_cli()
        self.assertFalse(any(p.name == "llm_raw.txt" for p in outputs))

    def test_llm_raw_created_when_capture_flag_set(self):
        _, outputs = self._run_cli(["--capture-raw"])
        self.assertTrue(any(p.name == "llm_raw.txt" for p in outputs))

    def test_server_default_is_llamacpp(self):
        with mock.patch("subsetzer.cli.translate_range") as tr_mock:
            self._run_cli()
            call_kwargs = tr_mock.call_args[1]
            self.assertEqual(call_kwargs["server"], "http://127.0.0.1:8080")

    def test_server_cli_overrides_default(self):
        with mock.patch("subsetzer.cli.translate_range") as tr_mock:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                infile = tmp_path / "input.srt"
                infile.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n")
                outdir = tmp_path / "out"
                cli.main(["--in", str(infile), "--out", str(outdir),
                          "--no-llm", "--flat", "--server", "http://myhost:9999"])
                call_kwargs = tr_mock.call_args[1]
                self.assertEqual(call_kwargs["server"], "http://myhost:9999")
