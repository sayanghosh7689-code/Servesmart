"""
chatbot.py — a small rule-based "Help Chat" assistant for students.

No external API or key is used: questions are matched against a fixed
FAQ knowledge base by keyword overlap, and the best-scoring answer is
returned. Good enough for "how do I..." style app-usage questions;
not a general-purpose AI assistant.
"""

import streamlit as st

# Each entry: keywords to match on (lowercase, can be phrases), the
# canonical question (shown as a quick-suggestion chip for the first
# few entries), and the answer shown to the student.
FAQS = [
    {
        "keywords": ["raise", "submit", "create", "new ticket", "file a ticket", "how do i report", "report an issue"],
        "question": "How do I raise a new ticket?",
        "answer": (
            "Go to the **New Ticket** tab, fill in a title, a description "
            "(at least 20 characters), pick a category, location, and "
            "priority (P1–P4), then click **Submit ticket**. It appears "
            "immediately under **My Tickets** with status *Open*."
        ),
    },
    {
        "keywords": ["priority", "p1", "p2", "p3", "p4", "urgent", "importance"],
        "question": "What do the priorities mean?",
        "answer": (
            "Priorities range from **P1** (most urgent — e.g. safety hazards) "
            "down to **P4** (least urgent — e.g. minor cosmetic issues). "
            "Pick the level that best reflects how urgently it needs attention; "
            "tickets are shown to technicians with P1s sorted first."
        ),
    },
    {
        "keywords": ["status", "track", "check my ticket", "where is my ticket", "progress"],
        "question": "How do I check my ticket status?",
        "answer": (
            "Open the **My Tickets** tab — each ticket shows its current status "
            "(Open, Assigned, In Progress, Resolved, or Closed). Click a ticket "
            "to expand it and see its full status history under **Details & history**."
        ),
    },
    {
        "keywords": ["forgot", "reset password", "password", "can't log in", "cant log in", "locked out"],
        "question": "I forgot my password",
        "answer": (
            "ServeSmart doesn't have self-service password reset yet — please "
            "contact an admin to have your password reset. If you're using a "
            "seeded demo account, the shared demo password is shown on the "
            "login screen."
        ),
    },
    {
        "keywords": ["description", "20 characters", "minimum length", "how long should"],
        "answer": (
            "Descriptions need to be at least 20 characters long — this keeps "
            "reports detailed enough for a technician to act on. The New Ticket "
            "form shows a live character counter so you know when you've hit "
            "the minimum."
        ),
    },
    {
        "keywords": ["category", "categories", "what categories", "type of issue"],
        "answer": (
            "Available categories are: Electrical, Plumbing, HVAC, Furniture, "
            "IT, Cleaning, and Other. Pick whichever best matches your issue — "
            "if nothing fits, use Other."
        ),
    },
    {
        "keywords": ["cancel", "delete", "edit", "change my ticket", "withdraw"],
        "answer": (
            "There's currently no way to edit, cancel, or delete a ticket "
            "yourself once it's submitted. If you made a mistake or the issue "
            "is resolved, let an admin or technician know via the ticket's "
            "status history / description, or contact an admin directly."
        ),
    },
    {
        "keywords": ["assign", "technician", "who is working", "who fixes", "fix my", "will fix"],
        "answer": (
            "Admins assign each ticket to a technician. Once assigned, the "
            "technician's name appears on the ticket, and the status moves "
            "from *Open* to *Assigned*, then *In Progress*, *Resolved*, and "
            "finally *Closed* as they work on it."
        ),
    },
    {
        "keywords": ["pdf", "download", "export", "history"],
        "answer": (
            "Head to the **Activity** tab — there's a **Download my task "
            "history (PDF)** button that generates a report covering all of "
            "your tickets and their full activity logs."
        ),
    },
    {
        "keywords": ["search", "filter", "find a ticket"],
        "answer": (
            "In **My Tickets**, use the **Search by title** or **Search by "
            "location** boxes at the top to narrow the list down."
        ),
    },
    {
        "keywords": ["log out", "logout", "sign out"],
        "answer": "Click **Log out** at the bottom of the sidebar on the left.",
    },
    {
        "keywords": ["closed", "resolved", "what does closed mean", "what does resolved mean", "statuses mean"],
        "answer": (
            "Tickets move through **Open → Assigned → In Progress → Resolved → "
            "Closed**, in that order — no skipping steps. *Resolved* means "
            "the technician finished the fix; *Closed* means it's fully "
            "wrapped up."
        ),
    },
    {
        "keywords": ["hello", "hi", "hey", "help", "what can you do"],
        "answer": (
            "I can help with things like: raising a ticket, understanding "
            "priorities and categories, checking ticket status, downloading "
            "your history as a PDF, and general how-to questions about "
            "ServeSmart. What would you like to know?"
        ),
    },
]

FALLBACK_ANSWER = (
    "I'm not sure about that one — I can only help with ServeSmart's own "
    "features right now (raising tickets, priorities, categories, statuses, "
    "search, PDF history, and account basics). Try rephrasing, or contact "
    "an admin for anything else."
)

QUICK_QUESTIONS = [
    "How do I raise a new ticket?",
    "What do the priorities mean?",
    "How do I check my ticket status?",
    "I forgot my password",
]


def get_answer(text):
    """Keyword-overlap scoring against the FAQ list. Returns the
    best-matching answer, or a fallback if nothing scores above zero."""
    text = (text or "").lower()
    best_score, best_answer = 0, None
    for faq in FAQS:
        score = sum(1 for kw in faq["keywords"] if kw in text)
        if score > best_score:
            best_score, best_answer = score, faq["answer"]
    return best_answer or FALLBACK_ANSWER


def _handle_user_message(text):
    st.session_state.chat_history.append({"role": "user", "content": text})
    st.session_state.chat_history.append({"role": "assistant", "content": get_answer(text)})


def render_chat(user):
    """Renders the Help Chat tab: quick-question chips, chat history,
    and a chat input box. Rule-based only — no external API/key needed."""
    st.subheader("💬 Help Chat")
    st.caption(
        "Ask about raising tickets, priorities, statuses, or anything else "
        "in ServeSmart. This is a simple built-in helper, not an AI service."
    )

    if "chat_history" not in st.session_state:
        first_name = user["name"].split()[0] if user.get("name") else "there"
        st.session_state.chat_history = [
            {
                "role": "assistant",
                "content": (
                    f"Hi {first_name}! Ask me about raising a ticket, "
                    f"priorities, statuses, or anything else in ServeSmart."
                ),
            }
        ]

    if len(st.session_state.chat_history) <= 1:
        st.write("**Quick questions:**")
        cols = st.columns(2)
        for i, q in enumerate(QUICK_QUESTIONS):
            if cols[i % 2].button(q, key=f"chat_quick_{i}", use_container_width=True):
                _handle_user_message(q)
                st.rerun()

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_msg = st.chat_input("Type your question...")
    if user_msg:
        _handle_user_message(user_msg)
        st.rerun()

    if len(st.session_state.chat_history) > 1:
        if st.button("Clear chat"):
            st.session_state.chat_history = []
            st.rerun()
