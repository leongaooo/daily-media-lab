"""Exercise the real TSX consumers without launching a browser or making media."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


class EditorialPanelConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        cls.install = Path(
            os.environ.get(
                "NEWS_TO_VIDEO_TEST_REMOTION_INSTALL",
                Path.home() / ".cache/news-to-video/remotion-editorial",
            )
        )
        cls.source = (
            Path(__file__).parents[1] / "assets/remotion-editorial/EditorialPanels.tsx"
        )
        if not cls.node or not (cls.install / "node_modules/esbuild").is_dir():
            raise unittest.SkipTest(
                "Node/esbuild Remotion runtime unavailable; TSX consumer checks not executed"
            )

    def render_panel(self, panel, properties):
        script = r"""
const fs = require('node:fs');
const {createRequire} = require('node:module');
const localRequire = createRequire(process.argv[1] + '/package.json');
const compiler = localRequire('esbuild');
const React = localRequire('react');
const {renderToStaticMarkup} = localRequire('react-dom/server');
const compiled = compiler.transformSync(fs.readFileSync(process.argv[2], 'utf8'), {
  loader: 'tsx', format: 'cjs', jsx: 'automatic', target: 'es2020'
}).code;
const componentModule = {exports: {}};
new Function('require', 'module', 'exports', compiled)(localRequire, componentModule, componentModule.exports);
const properties = JSON.parse(process.argv[4]);
const output = renderToStaticMarkup(React.createElement(componentModule.exports[process.argv[3]], properties));
process.stdout.write(output);
"""
        palette = {
            "primary": "#66D7ED",
            "accent": "#F2BD71",
            "muted": "#A9B9CB",
            "warning": "#F2A1A5",
        }
        return subprocess.check_output(
            [
                self.node,
                "-e",
                script,
                str(self.install),
                str(self.source),
                panel,
                json.dumps({"palette": palette, **properties}, ensure_ascii=False),
            ],
            encoding="utf-8",
        )

    def test_every_checklist_item_reaches_real_component_even_with_focus(self):
        nodes = [
            {"title": "电力侧", "detail": "核对可调负荷与回退策略"},
            {"title": "网络侧", "detail": "核对接口责任与测试口径"},
        ]
        for focus in (None, 0, 1):
            with self.subTest(focus=focus):
                html = self.render_panel(
                    "EvidenceBoard", {"nodes": nodes, "focus": focus}
                )
                for node in nodes:
                    self.assertIn(node["title"], html)
                    self.assertIn(node["detail"], html)
                self.assertEqual(html.count("data-editorial-node="), 2)

    def test_independent_standard_roles_do_not_become_before_after_claims(self):
        html = self.render_panel(
            "ComparisonPanel",
            {
                "nodes": [{"title": "总体技术要求"}, {"title": "测试方法"}],
                "labels": ["规划依据", "测试依据"],
            },
        )
        for content in ("总体技术要求", "测试方法", "规划依据", "测试依据"):
            self.assertIn(content, html)
        self.assertNotIn("变化前", html)
        self.assertNotIn("变化后", html)


if __name__ == "__main__":
    unittest.main()
