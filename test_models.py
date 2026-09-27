"""
tests/test_models.py — unit tests for ServeSmart's core business rules.

Run from the project root with:
    pytest
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import models as m


def test_can_transition_sequential_ok():
    assert m.can_transition("Open", "Assigned")
    assert m.can_transition("Assigned", "In Progress")
    assert m.can_transition("In Progress", "Resolved")
    assert m.can_transition("Resolved", "Closed")


def test_can_transition_rejects_skips_and_backwards():
    assert not m.can_transition("Open", "In Progress")  # skip
    assert not m.can_transition("Closed", "Open")        # backwards / wrap
    assert not m.can_transition("Assigned", "Open")      # backwards
    assert not m.can_transition("Closed", "Closed")      # no-op


def test_priority_sort_key_orders_p1_first():
    tickets = [{"priority": "P3"}, {"priority": "P1"}, {"priority": "P4"}, {"priority": "P2"}]
    ordered = sorted(tickets, key=m.priority_sort_key)
    assert [t["priority"] for t in ordered] == ["P1", "P2", "P3", "P4"]


def test_validate_new_ticket_requires_all_fields():
    errors = m.validate_new_ticket("", "", "", "", "")
    assert len(errors) >= 4


def test_validate_new_ticket_enforces_min_description_length():
    errors = m.validate_new_ticket("Title", "too short", "IT", "Room 1", "P1")
    assert any("20 characters" in e for e in errors)


def test_validate_new_ticket_rejects_bad_priority():
    errors = m.validate_new_ticket(
        "Title", "A description that is definitely long enough.", "IT", "Room 1", "P9"
    )
    assert any("P1, P2, P3, P4" in e for e in errors)


def test_validate_new_ticket_passes_with_valid_data():
    errors = m.validate_new_ticket(
        "Broken window", "The window in room 12 will not close properly.", "Other", "Room 12", "P2"
    )
    assert errors == []


def test_create_ticket_and_advance_status_end_to_end(tmp_path, monkeypatch):
    # Point at a throwaway DB so tests never touch servesmart.db.
    monkeypatch.setattr(m, "DB_PATH", tmp_path / "test.db")
    m.init_db()

    ok, errors, ticket = m.create_ticket(
        "Test ticket", "A sufficiently long description for testing purposes.",
        "IT", "Test Room", "P1", "stu1",
    )
    assert ok and not errors
    assert ticket["status"] == "Open"

    ok, _ = m.assign_ticket(ticket["id"], "tech1", "admin1", "Admin")
    assert ok
    ticket = m.get_ticket(ticket["id"])
    assert ticket["status"] == "Assigned"
    assert ticket["technicianId"] == "tech1"

    ok, _ = m.advance_status(ticket["id"], "In Progress", "tech1", "Technician")
    assert ok
    ticket = m.get_ticket(ticket["id"])
    assert ticket["status"] == "In Progress"

    # A technician who isn't assigned to the ticket cannot advance it.
    ok, msg = m.advance_status(ticket["id"], "Resolved", "tech2", "Technician")
    assert not ok
    assert "assigned to you" in msg

    # Skipping a status is rejected even for the correct technician.
    ok, msg = m.advance_status(ticket["id"], "Closed", "tech1", "Technician")
    assert not ok
    assert "Cannot move" in msg


def test_assign_ticket_requires_admin_role():
    ok, msg = m.assign_ticket("T000000", "tech1", "stu1", "Student")
    assert not ok
    assert "Only admins" in msg


def test_create_user_success_and_login(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "DB_PATH", tmp_path / "test_signup.db")
    m.init_db()

    ok, errors, user = m.create_user("stu99", "Test Student", "Student", "abcdef", "abcdef")
    assert ok and not errors
    assert user["id"] == "stu99"

    logged_in = m.verify_login("stu99", "abcdef")
    assert logged_in and logged_in["role"] == "Student"
    assert m.name_for("stu99") == "Test Student"
    assert "stu99" in m.get_users_by_role("Student")


def test_create_user_rejects_duplicate_id(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "DB_PATH", tmp_path / "test_signup.db")
    m.init_db()

    m.create_user("stu99", "First", "Student", "abcdef", "abcdef")
    ok, errors, user = m.create_user("stu99", "Second", "Student", "abcdef", "abcdef")
    assert not ok
    assert any("already taken" in e for e in errors)


def test_create_user_rejects_password_mismatch(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "DB_PATH", tmp_path / "test_signup.db")
    m.init_db()

    ok, errors, user = m.create_user("stu98", "Someone", "Student", "abcdef", "different")
    assert not ok
    assert any("do not match" in e for e in errors)


def test_create_user_rejects_short_password(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "DB_PATH", tmp_path / "test_signup.db")
    m.init_db()

    ok, errors, user = m.create_user("stu97", "Someone", "Student", "abc", "abc")
    assert not ok
    assert any("6 characters" in e for e in errors)


def test_create_user_blocks_admin_self_signup(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "DB_PATH", tmp_path / "test_signup.db")
    m.init_db()

    ok, errors, user = m.create_user("adm99", "Sneaky", "Admin", "abcdef", "abcdef")
    assert not ok
    assert any("Role must be" in e for e in errors)


def test_create_user_rejects_invalid_id_characters(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "DB_PATH", tmp_path / "test_signup.db")
    m.init_db()

    ok, errors, user = m.create_user("bad id!", "Someone", "Student", "abcdef", "abcdef")
    assert not ok
