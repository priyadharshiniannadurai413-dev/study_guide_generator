"""
backend/scripts/test_langgraph_fetch.py
---------------------------------------
Integration tests for LangGraph multi-agent routing with Fetch MCP:
- Sufficiency evaluation routing (RAG sufficient vs. Web needed)
- Direct URL prompt routing
- Subgraph and Supervisor compilation
- Fault tolerance / non-crashing guarantee
"""

import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.context_evaluator import (
    evaluate_context_sufficiency,
    route_after_evaluation,
    fetch_web_node,
    validate_web_node,
)
from app.ai.agents.studynotes.graph import build_studynotes_graph
from app.ai.agents.mcq.graph import build_mcq_graph
from app.ai.agents.curriculum.graph import build_curriculum_graph
from app.ai.agents.supervisor.graph import build_supervisor_graph


class TestLangGraphFetchIntegration(unittest.IsolatedAsyncioTestCase):

    def test_routing_decisions(self):
        # Case 1: RAG context is deep and sufficient
        state_sufficient = {
            "user_query": "Explain process scheduling algorithms",
            "retrieved_context": "Round robin scheduling assigns a fixed time quantum... " * 15,
            "enable_web": False,
        }
        is_suff, score, target, _ = evaluate_context_sufficiency(state_sufficient)
        self.assertTrue(is_suff)
        self.assertGreaterEqual(score, 0.7)
        self.assertIsNone(target)

        eval_state = {"web_sufficiency_score": score, "web_target_url": target, "enable_web": False}
        self.assertEqual(route_after_evaluation(eval_state), "generate")

        # Case 2: User explicitly requests external web references
        state_web_intent = {
            "user_query": "Search the web for the latest Python 3.12 asyncio features",
            "retrieved_context": "Some basic local text",
            "enable_web": False,
        }
        is_suff, score, target, _ = evaluate_context_sufficiency(state_web_intent)
        self.assertFalse(is_suff)
        self.assertEqual(route_after_evaluation({"web_sufficiency_score": score, "web_target_url": target}), "fetch_web")

        # Case 3: Direct URL in user query
        state_url = {
            "user_query": "Summarize this page: https://fastapi.tiangolo.com/tutorial/first-steps/",
            "retrieved_context": "",
            "enable_web": False,
        }
        is_suff, score, target, _ = evaluate_context_sufficiency(state_url)
        self.assertFalse(is_suff)
        self.assertEqual(target, "https://fastapi.tiangolo.com/tutorial/first-steps/")
        self.assertEqual(route_after_evaluation({"web_sufficiency_score": score, "web_target_url": target}), "fetch_web")

    async def test_fetch_web_node_never_crashes_on_bad_url(self):
        bad_state = {
            "web_target_url": "https://nonexistent-domain-xyz-12345.edu/nonexistent",
            "user_query": "test",
        }
        res = await fetch_web_node(bad_state)
        self.assertEqual(res.get("web_context"), "")
        self.assertEqual(res.get("web_sources"), [])
        self.assertIsNotNone(res.get("web_fetch_error"))

    def test_graphs_compile_cleanly(self):
        # Ensure all subgraphs and the main supervisor graph compile without error
        notes_graph = build_studynotes_graph()
        self.assertIsNotNone(notes_graph)

        mcq_graph = build_mcq_graph()
        self.assertIsNotNone(mcq_graph)

        curriculum_graph = build_curriculum_graph()
        self.assertIsNotNone(curriculum_graph)

        supervisor_graph = build_supervisor_graph()
        self.assertIsNotNone(supervisor_graph)


if __name__ == "__main__":
    unittest.main()
