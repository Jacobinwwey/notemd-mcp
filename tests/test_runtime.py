import asyncio
import unittest
import tempfile
from pathlib import Path
import subprocess
import sys
import os
import base64
import json
import stat
from unittest.mock import AsyncMock, patch

import httpx
import notemd_core as core


class MarkdownIntegrityTests(unittest.TestCase):
    def test_valid_diagram_and_escaped_currency_are_unchanged(self):
        source = '\ufeffPrice \\$5\r\n~~~mermaid\r\nflowchart TD\r\nA((Start)) --> B["Label (x)"]\r\n~~~\r\n'
        self.assertEqual(core.refine_mermaid_blocks(source), source)
        self.assertEqual(core.cleanup_latex_delimiters(source), source)

    def test_unclosed_and_nested_examples_are_not_guessed(self):
        for source in ['```mermaid\nsequenceDiagram\nAlice->>Bob: Hi\nNote over Alice: End', '````markdown\n```mermaid\nA["Example"]\n```\n````']:
            self.assertEqual(core.refine_mermaid_blocks(source), source)

    def test_known_and_future_families_are_not_prefixed_as_flowcharts(self):
        for body in ['sequenceDiagram\nAlice->>Bob: Hi', 'classDiagram\nclass A', 'futureDiagram\nA --> B', 'erDiagram\nA ||--o{ B : has']:
            self.assertEqual(core.ensure_mermaid_code_block(body, 'graph TD'), '```mermaid\n' + body + '\n```')

    def test_outer_response_unwrap_preserves_nested_code(self):
        body = 'Text\n```mermaid\nflowchart TD\nA["x"] --> B\n```'
        self.assertEqual(core.apply_standard_post_processing('````markdown\n' + body + '\n````', True), body)
        self.assertEqual(core.apply_standard_post_processing(body, True), body)

    def test_latex_preserves_code_and_placeholder_text(self):
        source = '___TEMP_DOLLAR_ESCAPE___ \\$8 `\\(x\\)`\n~~~text\n$ x $\n~~~'
        self.assertEqual(core.cleanup_latex_delimiters(source), source)
        self.assertEqual(core.cleanup_latex_delimiters('    \\(x\\)\n'), '    \\(x\\)\n')


class AsyncRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = core.SETTINGS
        core.set_settings({'API_CALL_MAX_RETRIES': 2, 'API_CALL_INTERVAL': 0.05})

    def tearDown(self):
        core.set_settings(self.settings)

    def status_error(self, status):
        return httpx.HTTPStatusError('redacted', request=httpx.Request('POST', 'https://example.invalid'), response=httpx.Response(status))

    async def test_precancel_never_sends_in_either_mode(self):
        provider = AsyncMock(return_value='unused')
        with patch.dict(core.API_CALL_FUNCTIONS, {'test': provider}):
            for stable in (False, True):
                core.SETTINGS['ENABLE_STABLE_API_CALL'] = stable
                with self.assertRaises(asyncio.CancelledError):
                    await core.call_llm_api({'name': 'test'}, 'm', 'p', 'c', True)
        provider.assert_not_awaited()

    async def test_only_transient_failures_retry(self):
        for failure in [self.status_error(401), self.status_error(422), ValueError('configuration')]:
            provider = AsyncMock(side_effect=failure)
            with patch.dict(core.API_CALL_FUNCTIONS, {'test': provider}):
                with self.assertRaises(type(failure)):
                    await core.call_api_with_retry({'name': 'test'}, 'm', 'p', 'c', False)
            self.assertEqual(provider.await_count, 1)
        provider = AsyncMock(side_effect=[self.status_error(503), 'recovered'])
        with patch.dict(core.API_CALL_FUNCTIONS, {'test': provider}):
            self.assertEqual(await core.call_api_with_retry({'name': 'test'}, 'm', 'p', 'c', False), 'recovered')
        self.assertEqual(provider.await_count, 2)

    async def test_backoff_yields_and_task_cancellation_stops_retries(self):
        first_attempt = asyncio.Event()
        async def fail(*args):
            first_attempt.set()
            raise self.status_error(503)
        provider = AsyncMock(side_effect=fail)
        with patch.dict(core.API_CALL_FUNCTIONS, {'test': provider}):
            task = asyncio.create_task(core.call_api_with_retry({'name': 'test'}, 'm', 'p', 'c', False))
            await first_attempt.wait()
            self.assertFalse(task.done(), 'retry backoff must yield to other requests')
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(provider.await_count, 1)

    async def test_process_content_never_removes_inner_fences(self):
        core.SETTINGS.update({'ACTIVE_PROVIDER': 'test', 'DEFAULT_PROVIDERS': [{'name': 'test', 'model': 'm'}], 'REMOVE_CODE_FENCES_ON_ADD_LINKS': True, 'CUSTOM_PROMPT_ADD_LINKS': 'Keep source', 'ENABLE_DUPLICATE_DETECTION': False})
        body = 'Text\n```mermaid\nflowchart TD\nA["x"] --> B\n```'
        with patch.dict(core.API_CALL_FUNCTIONS, {'test': AsyncMock(return_value='````markdown\n' + body + '\n````')}):
            self.assertEqual(await core.process_content('Source'), body)

    async def test_research_html_parser_preserves_search_and_body_extraction(self):
        search = '<div class="result"><a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.invalid%2Farticle">Title</a><div class="result__snippet">Summary</div></div>'
        article = '<html><body><script>secret()</script><style>.x{}</style><h1>Title</h1><p>Body text</p></body></html>'
        for html, operation, expected in [
            (search, core.search_duckduckgo, [{'title': 'Title', 'url': 'https://example.invalid/article', 'content': 'Summary'}]),
            (article, core.fetch_content_from_url, 'Title Body text'),
        ]:
            client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=html, headers={'content-type': 'text/html'})))
            with patch('notemd_core.httpx.AsyncClient', return_value=client):
                self.assertEqual(await operation('https://example.invalid/article'), expected)

    async def test_batch_preserves_bytes_and_failed_replace_keeps_source(self):
        with tempfile.TemporaryDirectory(prefix='notemd-regression-') as directory:
            path = Path(directory) / 'note.md'
            original = b'\xef\xbb\xbfValue \\(x\\)\r\n```mermaid\r\nflowchart TD\r\nA["x"] --> B\r\n```\r\n'
            path.write_bytes(original)
            with patch('notemd_core.os.replace', side_effect=OSError('simulated write failure')):
                failed = await core.batch_fix_mermaid_syntax_in_folder(directory)
            self.assertEqual(failed['modified_count'], 0)
            self.assertEqual(len(failed['errors']), 1)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(directory).glob('.notemd-*')), [])
            done = await core.batch_fix_mermaid_syntax_in_folder(directory)
            self.assertEqual(done['modified_count'], 1)
            self.assertEqual(path.read_bytes(), original.replace(b'\\(x\\)', b'$x$'))
            modified = path.stat().st_mtime_ns
            self.assertEqual((await core.batch_fix_mermaid_syntax_in_folder(directory))['modified_count'], 0)
            self.assertEqual(path.stat().st_mtime_ns, modified)

    async def test_readonly_source_is_unchanged_without_staged_residue(self):
        with tempfile.TemporaryDirectory(prefix='notemd-readonly-') as directory:
            path = Path(directory) / 'note.md'
            original = b'Value \\(x\\)\r\n'
            path.write_bytes(original)
            path.chmod(stat.S_IREAD)
            try:
                failed = await core.batch_fix_mermaid_syntax_in_folder(directory)
                self.assertEqual(failed['modified_count'], 0)
                self.assertEqual(len(failed['errors']), 1)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(list(Path(directory).glob('.notemd-*')), [])
            finally:
                for entry in Path(directory).iterdir():
                    entry.chmod(stat.S_IREAD | stat.S_IWRITE)

    async def test_google_credentials_are_headers_not_logged_urls(self):
        secret = 'REGRESSION_SECRET_DO_NOT_LOG'
        def respond(request):
            self.assertNotIn(secret, str(request.url))
            self.assertEqual(request.headers['x-goog-api-key'], secret)
            return httpx.Response(200, json={'candidates': [{'content': {'parts': [{'text': 'ok'}]}}]})
        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        with patch('notemd_core.httpx.AsyncClient', return_value=client), self.assertLogs('httpx', level='INFO') as logs:
            self.assertEqual(await core.execute_google_api({'baseUrl': 'https://example.invalid', 'apiKey': secret, 'temperature': 0}, 'model', 'prompt', 'content'), 'ok')
        self.assertNotIn(secret, '\n'.join(logs.output))


class ProcessLoggingTests(unittest.TestCase):
    def test_config_secrets_never_reach_stdout_or_stderr(self):
        secret = 'REGRESSION_SECRET_DO_NOT_LOG'
        environment = dict(os.environ, NOTEMD_CONFIG=base64.b64encode(json.dumps({'DEFAULT_PROVIDERS': [{'name': 'test', 'apiKey': secret}]}).encode()).decode())
        completed = subprocess.run([sys.executable, '-c', 'import main'], cwd=Path(__file__).resolve().parents[1], env=environment, capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, '')
        self.assertNotIn(secret, completed.stderr)
        self.assertIn('DEFAULT_PROVIDERS', completed.stderr)


if __name__ == '__main__':
    unittest.main()
