"""The legal pages (scripts/build_legal.py) and the version a parent agrees to (api.AGREEMENT_VERSION). Run by ./dev check."""
import datetime as dt
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_legal  # noqa: E402


def last_updated(name):
    m = re.search(r"\*Last updated: ([A-Z][a-z]+ \d{1,2}, \d{4})\*", (build_legal.SRC / f"{name}.md").read_text())
    assert m, f"{name}.md has no '*Last updated: Month D, YYYY*' line"
    return dt.datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()


class AgreementVersion(unittest.TestCase):
    def test_it_is_the_date_the_legal_documents_were_last_updated(self):
        """Changing a policy without moving the version would record that a parent agreed to words they never saw."""
        api = (ROOT / "controller" / "treeline" / "api.py").read_text()
        version = re.search(r'^AGREEMENT_VERSION = "([\d-]+)"', api, re.M).group(1)
        self.assertEqual(version, max(last_updated(n) for n in build_legal.DOCS))


class Pages(unittest.TestCase):
    def test_the_committed_pages_are_what_the_markdown_makes(self):
        for name in build_legal.DOCS:
            page = build_legal.OUT / name / "index.html"
            self.assertTrue(page.exists(), f"{page} is missing: python3 scripts/build_legal.py")
            self.assertEqual(page.read_text(), build_legal.render(name), f"{page} is stale: python3 scripts/build_legal.py")

    def test_owner_notes_never_reach_a_page(self):
        for name in build_legal.DOCS:
            html = build_legal.render(name)
            self.assertNotIn("TODO", html)
            self.assertEqual(html.count("<!--"), 1, "only the 'generated from' note")

    def test_links_between_the_documents_become_page_urls_and_anchors_exist(self):
        pages = {n: build_legal.render(n) for n in build_legal.DOCS}
        for name, html in pages.items():
            self.assertNotRegex(html, r'href="[^"]*\.md', name)
            for target, anchor in re.findall(r'href="/legal/([\w-]+)/#([\w-]+)"', html):
                self.assertIn(f'id="{anchor}"', pages[target], f"{name} links to a missing heading {target}#{anchor}")
            for anchor in re.findall(r'href="#([\w-]+)"', html):
                self.assertIn(f'id="{anchor}"', html, f"{name} links to a missing heading #{anchor}")

    def test_markup_in_the_markdown_is_escaped_not_run(self):
        self.assertEqual(build_legal.inline('<script>x</script> **b**'), "&lt;script&gt;x&lt;/script&gt; <strong>b</strong>")
        self.assertNotIn("<script", build_legal.blocks(["* <script>alert(1)</script>"]))

    def test_dash_bullets_are_a_list_and_a_wrapped_number_stays_in_its_paragraph(self):
        """Code review: '- ' bullets came out as one run-on paragraph, and a wrapped line starting '2026. ' began a list."""
        out = build_legal.blocks(["- one", "- two"])
        self.assertEqual((out.count("<ul"), out.count("<li>")), (1, 2))
        out = build_legal.blocks(["We last changed this in November", "2026. Nothing else changed."])
        self.assertEqual((out.count("<p"), out.count("<ol"), out.count("<li")), (1, 0, 0))
        self.assertIn("November 2026. Nothing", out)
        out = build_legal.blocks(["Steps:", "1. first", "2. second"])          # a list that starts at 1 may follow a line directly
        self.assertEqual((out.count("<p"), out.count("<ol"), out.count("<li>")), (1, 1, 2))
        self.assertEqual(build_legal.blocks(["---"]).count("<hr"), 1)        # a rule is not a bullet

    def test_markdown_inside_backticks_is_shown_as_written(self):
        """Code review: `**x**` and `[x](y)` inside backticks came out bold and as a link."""
        self.assertEqual(build_legal.inline("use `**/legal/**` and `[x](y)` here"),
                         "use <code>**/legal/**</code> and <code>[x](y)</code> here")
        self.assertEqual(build_legal.inline("**b** `c` *i*"), "<strong>b</strong> <code>c</code> <em>i</em>")

    def test_only_a_single_italic_line_is_a_caption(self):
        """Code review: a line starting with bold and ending in italics was shown small and grey."""
        self.assertIn('class="caption"', build_legal.blocks(["*Last updated: November 23, 2026*"]))
        safety = build_legal.blocks(["**Important:** Treeline can't call 911, *ever*"])
        self.assertIn('class="tl-measure"', safety)
        self.assertNotIn("caption", safety)

    def test_one_h1_and_the_911_statement_on_every_page(self):
        for name in build_legal.DOCS:
            html = build_legal.render(name)
            self.assertEqual(html.count("<h1"), 1, name)
            self.assertTrue("can&#x27;t call 911" in html or "cannot call 911" in html, f"{name} must say Treeline can't call 911")

    def test_the_basecamp_credit_stays(self):
        for name in build_legal.DOCS:
            self.assertIn("https://github.com/basecamp/policies", build_legal.render(name), name)


if __name__ == "__main__":
    unittest.main()
