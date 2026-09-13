"""Phase-2 strategy tests — fully offline.

Scorers and API-response parsers are pure functions, so the whole suite runs
without network, API keys, or heavy third-party packages.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import factcheck, hooks, research, trends  # noqa: E402
from core.project import VideoProject  # noqa: E402


class TestHooks(unittest.TestCase):
    def test_question_and_number_score_high(self):
        score, _ = hooks.score_hook("Why do 90% of players quit in week one?")
        self.assertGreaterEqual(score, 70)

    def test_empty_scores_zero(self):
        self.assertEqual(hooks.score_hook("")[0], 0)
        self.assertEqual(hooks.score_hook("   ")[0], 0)

    def test_too_long_penalized(self):
        bloated = ("This is an extremely long and rambling video title that "
                   "promises far too many different things at once")
        tight = "Why do players quit?"
        self.assertLess(hooks.score_hook(bloated)[0], hooks.score_hook(tight)[0])

    def test_pick_best_orders_first(self):
        ranked = hooks.pick_best(["stuff", "Why I quit Roblox after 7 days?"])
        self.assertEqual(ranked[0][0], "Why I quit Roblox after 7 days?")
        self.assertGreater(ranked[0][1], ranked[1][1])


class TestFactCheck(unittest.TestCase):
    def test_flags_superlative_and_absolute(self):
        flags = factcheck.check_text(
            "This is the biggest update ever.\nIt always works.")
        kinds = [f["flag"] for f in flags]
        self.assertIn("biggest", kinds)
        self.assertIn("always", kinds)

    def test_flags_bare_numbers(self):
        flags = factcheck.check_text("It earned 2 million dollars in a week.")
        self.assertTrue(any(f["flag"] == "number" for f in flags))

    def test_clean_text_passes(self):
        self.assertEqual(
            factcheck.check_text("Roblox added a new obby this week.\nPlayers seem excited."),
            [])

    def test_summarize_empty(self):
        self.assertIn("No risky claims", factcheck.summarize([]))


class TestResearchParsers(unittest.TestCase):
    def test_parse_wiki_search(self):
        payload = {"query": {"search": [{"title": "Black hole"},
                                        {"title": "Black Hole Sun"}]}}
        self.assertEqual(research.parse_wiki_search(payload),
                         ["Black hole", "Black Hole Sun"])
        self.assertEqual(research.parse_wiki_search({}), [])

    def test_parse_wiki_summary(self):
        payload = {"title": "Black hole",
                   "extract": "A black hole is a region of spacetime.",
                   "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Black_hole"}}}
        article = research.parse_wiki_summary(payload)
        self.assertEqual(article["title"], "Black hole")
        self.assertIn("spacetime", article["summary"])
        self.assertIsNone(research.parse_wiki_summary({"type": "disambiguation"}))
        self.assertIsNone(research.parse_wiki_summary({}))

    def test_parse_ddg(self):
        payload = {"Heading": "Black hole",
                   "AbstractText": "A region of spacetime.",
                   "AbstractURL": "https://example.com"}
        ddg = research.parse_ddg(payload)
        self.assertEqual(ddg["url"], "https://example.com")
        self.assertIsNone(research.parse_ddg({"AbstractText": ""}))


class TestTrendParsers(unittest.TestCase):
    def test_parse_reddit_listing(self):
        payload = {"data": {"children": [
            {"data": {"title": "Pinned post", "stickied": True, "score": 999,
                      "num_comments": 1, "subreddit": "x", "permalink": "/r/x/1"}},
            {"data": {"title": "Real topic", "stickied": False, "score": 100,
                      "num_comments": 20, "subreddit": "Minecraft",
                      "permalink": "/r/Minecraft/2"}},
        ]}}
        topics = trends.parse_reddit_listing(payload)
        self.assertEqual(len(topics), 1)  # pinned post skipped
        self.assertEqual(topics[0]["title"], "Real topic")
        self.assertIn("reddit.com", topics[0]["url"])

    def test_parse_reddit_garbage(self):
        self.assertEqual(trends.parse_reddit_listing({}), [])
        self.assertEqual(trends.parse_reddit_listing(None), [])

    def test_every_default_niche_has_sources(self):
        from core.niches import list_niches
        for key in list_niches():
            self.assertTrue(trends.SUBREDDITS.get(key),
                            f"no trend sources for niche '{key}'")

    def test_parse_hn(self):
        payload = {"hits": [{"title": "Show HN: Thing", "url": "",
                              "points": 50, "num_comments": 5,
                              "objectID": "123"}]}
        topics = trends.parse_hn(payload)
        self.assertIn("news.ycombinator", topics[0]["url"])


class TestTicketStrategyFields(unittest.TestCase):
    def test_new_ticket_has_strategy_fields(self):
        ticket = VideoProject.new("X")
        self.assertEqual(ticket.research, {})
        self.assertEqual(ticket.ideas, [])
        self.assertEqual(ticket.titles, [])
        self.assertEqual(ticket.fact_check, {})
        self.assertEqual(ticket.plan_path, "")


if __name__ == "__main__":
    unittest.main()
