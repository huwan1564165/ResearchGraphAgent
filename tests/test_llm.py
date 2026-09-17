import json
import unittest
from unittest.mock import patch

from agent.decomposition import LLMQuestionDecomposer
from models.project import ResearchProject
from tools.llm import OpenAIClient, parse_json_object


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.prompt = None

    def generate(self, prompt, *, system=None):
        self.prompt = prompt
        return self.response


class LLMTest(unittest.TestCase):
    def test_decomposer_parses_structured_questions(self):
        client = FakeLLM(json.dumps(["问题一", "问题二", "问题三"], ensure_ascii=False))
        questions = LLMQuestionDecomposer(client).suggest_questions(
            ResearchProject(7, "标题", "研究问题", subject="学生")
        )
        self.assertEqual([item.text for item in questions], ["问题一", "问题二", "问题三"])
        self.assertEqual([item.position for item in questions], [1, 2, 3])
        self.assertIn("JSON 字符串数组", client.prompt)

    def test_parser_accepts_markdown_fenced_json(self):
        self.assertEqual(parse_json_object("```json\n[1, 2]\n```"), [1, 2])

    @patch("tools.llm.urlopen")
    def test_openai_client_uses_configured_endpoint_and_model(self, urlopen):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self):
                return b'{"choices":[{"message":{"content":"hello"}}]}'
        urlopen.return_value = Response()
        self.assertEqual(OpenAIClient("secret", model="custom", base_url="https://gateway/v1").generate("hi"), "hello")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://gateway/v1/chat/completions")
        self.assertIn('"model": "custom"', request.data.decode())
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")


if __name__ == "__main__":
    unittest.main()
