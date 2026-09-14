import unittest
from pathlib import Path


class DevelopmentDocumentTest(unittest.TestCase):
    """Ensure the personal development guide keeps the agreed project scope."""

    @classmethod
    def setUpClass(cls):
        cls.document_path = Path(__file__).resolve().parents[1] / "DEVELOPMENT.md"
        cls.content = cls.document_path.read_text(encoding="utf-8")

    def test_document_exists_and_has_architecture_sections(self):
        self.assertTrue(self.document_path.is_file())
        for heading in ("## 1. 项目要解决什么问题", "## 3. 整体架构", "## 4. 主要数据对象", "## 7. 推荐项目目录"):
            self.assertIn(heading, self.content)

    def test_document_contains_all_current_development_stages(self):
        stages = (
            "项目骨架、配置、SQLite 数据模型和基础测试",
            "研究问题输入、子问题生成、子问题编辑和确认",
            "搜索适配器、来源保存、链接去重和搜索日志",
            "证据提取、证据与子问题及观点的关联",
            "报告生成、引用合法性检查和不确定性标注",
            "结论回溯页面和端到端演示",
            "使用老师推荐的问题完成一次完整演示，并补充 README",
        )
        for stage in stages:
            self.assertIn(stage, self.content)

    def test_document_explains_traceability(self):
        self.assertIn("Claim → Evidence → Source", self.content)
        self.assertIn("证据不足", self.content)
        self.assertIn("研究过程记录", self.content)


if __name__ == "__main__":
    unittest.main()
