import os
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

    def test_subsetzer_env_alias_takes_precedence(self):
        environ = {
            "SUBSETZER_LLM_MODEL": "alias-model",
            "HOMEDOC_LLM_MODEL": "legacy-model",
        }
        with mock.patch.dict(os.environ, environ, clear=True):
            parser = cli._build_parser()
            args = parser.parse_args(["--in", "input.srt", "--out", "out"])
            self.assertEqual(args.model, "alias-model")

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

    def test_server_default_depends_on_provider(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            args = cli._build_parser().parse_args(["--in", "x.srt", "--out", "o"])
            self.assertIsNone(args.server)

    def test_server_env_overrides_provider_default(self):
        with mock.patch.dict(os.environ, {"SUBSETZER_LLM_SERVER": "http://custom:9999"}, clear=True):
            args = cli._build_parser().parse_args(["--in", "x.srt", "--out", "o", "--provider", "llamacpp"])
            self.assertIsNone(args.server)

    def test_server_resolved_from_provider_in_main(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            infile = tmp_path / "input.srt"
            infile.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n")
            outdir = tmp_path / "out"
            with mock.patch.dict(os.environ, {}, clear=True), \
                 mock.patch("subsetzer.cli.translate_range") as tr_mock:
                cli.main(["--in", str(infile), "--out", str(outdir),
                          "--no-llm", "--flat", "--provider", "llamacpp"])
                call_kwargs = tr_mock.call_args[1]
                self.assertEqual(call_kwargs["server"], "http://127.0.0.1:8080")

    def test_server_cli_overrides_all(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            infile = tmp_path / "input.srt"
            infile.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n")
            outdir = tmp_path / "out"
            with mock.patch.dict(os.environ, {}, clear=True), \
                 mock.patch("subsetzer.cli.translate_range") as tr_mock:
                cli.main(["--in", str(infile), "--out", str(outdir),
                          "--no-llm", "--flat", "--provider", "llamacpp",
                          "--server", "http://myserver:1234"])
                call_kwargs = tr_mock.call_args[1]
                self.assertEqual(call_kwargs["server"], "http://myserver:1234")
