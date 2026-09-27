"""
tests/test_chatbot.py — unit tests for the Help Chat FAQ matcher.

Run from the project root with:
    pytest
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chatbot as c


def test_get_answer_matches_new_ticket_question():
    ans = c.get_answer("how do I raise a new ticket?")
    assert "New Ticket" in ans


def test_get_answer_matches_priority_question():
    ans = c.get_answer("what does P1 mean?")
    assert "urgent" in ans.lower()


def test_get_answer_matches_status_question():
    ans = c.get_answer("how can I check my ticket status")
    assert "My Tickets" in ans


def test_get_answer_matches_password_question():
    ans = c.get_answer("I forgot my password, help")
    assert "reset" in ans.lower()


def test_get_answer_falls_back_on_unknown_question():
    ans = c.get_answer("asdkjaslkdj totally unrelated gibberish")
    assert ans == c.FALLBACK_ANSWER


def test_get_answer_handles_empty_input():
    ans = c.get_answer("")
    assert ans == c.FALLBACK_ANSWER
