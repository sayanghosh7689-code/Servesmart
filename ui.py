"""
ui.py — shared visual helpers for ServeSmart (CSS injection, colored
status/priority badges, ticket cards, and a global activity feed).

Kept separate from views.py so the look-and-feel can change without
touching page logic.
"""

import io
from datetime import datetime

import streamlit as st
import models as m

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

STATUS_COLORS = {
    "Open":        ("#fff4e5", "#b25e00"),
    "Assigned":    ("#e8f0fe", "#1a56c4"),
    "In Progress": ("#eef2ff", "#4338ca"),
    "Resolved":    ("#e7f8ec", "#137a3b"),
    "Closed":      ("#f1f3f5", "#5f6368"),
}

PRIORITY_COLORS = {
    "P1": ("#fdeaea", "#c62828"),
    "P2": ("#fff1e0", "#c76a00"),
    "P3": ("#eef7ff", "#1565c0"),
    "P4": ("#f1f3f5", "#5f6368"),
}


def inject_css():
    st.markdown(
        """
        <style>
        html, body, [class*="css"]  { font-family: "Inter", "Segoe UI", sans-serif; }

        .block-container { padding-top: 2rem; max-width: 1100px; }

        /* Badges */
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            margin-right: 6px;
            white-space: nowrap;
        }

        /* Ticket card */
        .ticket-card {
            border: 1px solid #e6e6e6;
            border-radius: 12px;
            padding: 16px 18px;
            margin-bottom: 14px;
            background: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        .ticket-title {
            font-size: 1.05rem;
            font-weight: 700;
            margin: 2px 0 8px 0;
            color: #1a1a1a;
        }
        .ticket-meta {
            font-size: 0.85rem;
            color: #6b7280;
            margin-bottom: 2px;
        }

        /* Activity feed */
        .feed-item {
            border-left: 3px solid #d0d7de;
            padding: 4px 0 4px 12px;
            margin-bottom: 6px;
            font-size: 0.88rem;
        }
        .feed-time { color: #9aa0a6; font-size: 0.78rem; }

        /* Sidebar user card */
        .user-card {
            border-radius: 10px;
            padding: 12px 14px;
            background: linear-gradient(135deg, #eef2ff, #e8f0fe);
            margin-bottom: 10px;
        }
        .user-card .name { font-weight: 700; font-size: 1rem; color: #1a1a1a; }
        .user-card .role { font-size: 0.8rem; color: #4338ca; font-weight: 600; }
        .user-card .id   { font-size: 0.78rem; color: #6b7280; }

        div.stButton > button[kind="primary"] {
            border-radius: 8px;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _chip(text, palette, key):
    bg, fg = palette.get(key, ("#eee", "#333"))
    return f'<span class="badge" style="background:{bg};color:{fg};">{text}</span>'


def status_badge(status):
    return _chip(status, STATUS_COLORS, status)


def priority_badge(priority):
    return _chip(priority, PRIORITY_COLORS, priority)


def metrics_row(tickets):
    """Small KPI strip: total / open / in-progress / resolved+closed."""
    total = len(tickets)
    open_ct = sum(1 for t in tickets if t["status"] == "Open")
    active_ct = sum(1 for t in tickets if t["status"] in ("Assigned", "In Progress"))
    done_ct = sum(1 for t in tickets if t["status"] in ("Resolved", "Closed"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total tickets", total)
    c2.metric("Open", open_ct)
    c3.metric("In progress", active_ct)
    c4.metric("Resolved / Closed", done_ct)


def ticket_card_header_html(t):
    tech_name = m.name_for(t["technicianId"]) if t["technicianId"] else "Unassigned"
    return (
        f'{status_badge(t["status"])}{priority_badge(t["priority"])}'
        f'<span class="ticket-title">{t["title"]}</span><br>'
        f'<span class="ticket-meta">{t["id"]} · {t["category"]} · {t["location"]} · '
        f'Tech: {tech_name}</span>'
    )


def render_ticket_card(t, actor_id, actor_role, allow_advance=False):
    with st.container(border=True):
        st.markdown(ticket_card_header_html(t), unsafe_allow_html=True)
        with st.expander("Details & history"):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Ticket ID:** {t['id']}")
                st.write(f"**Category:** {t['category']}")
                st.write(f"**Location:** {t['location']}")
            with c2:
                st.write(f"**Student:** {m.name_for(t['studentId'])}")
                st.write(f"**Technician:** {m.name_for(t['technicianId']) if t['technicianId'] else 'Unassigned'}")
                st.write(f"**Created:** {t['createdAt']}")
            st.write("**Description:**")
            st.write(t["description"])

            st.write("**Status history:**")
            for entry in t["activity"]:
                st.markdown(
                    f'<div class="feed-item"><span class="feed-time">{entry["at"]}</span> — '
                    f'{status_badge(entry["status"])} by {m.name_for(entry["by"])}</div>',
                    unsafe_allow_html=True,
                )

            if allow_advance:
                nxt = m.next_status(t["status"])
                if nxt:
                    if st.button(f"Advance to '{nxt}'", key=f"advance_{t['id']}", type="primary"):
                        ok, msg = m.advance_status(t["id"], nxt, actor_id, actor_role)
                        (st.success if ok else st.error)(msg)
                        st.rerun()
                else:
                    st.info("This ticket is already Closed — no further transitions.")


def global_activity_feed(limit=25):
    """Flattened, most-recent-first feed of every status/activity event
    across every ticket — the single place to see 'everything happening'."""
    tickets = m.get_all_tickets()
    events = []
    for t in tickets:
        for a in t["activity"]:
            events.append({
                "at": a["at"], "status": a["status"], "by": a["by"],
                "ticket_id": t["id"], "title": t["title"],
            })
    events.sort(key=lambda e: e["at"], reverse=True)

    if not events:
        st.info("No activity yet.")
        return

    for e in events[:limit]:
        st.markdown(
            f'<div class="feed-item">'
            f'<span class="feed-time">{e["at"]}</span> — {status_badge(e["status"])} '
            f'<b>{e["ticket_id"]}</b> · {e["title"]} (by {m.name_for(e["by"])})'
            f'</div>',
            unsafe_allow_html=True,
        )
    if len(events) > limit:
        st.caption(f"Showing {limit} of {len(events)} events.")


# --------------------------------------------------------------- PDF export --

def build_history_pdf(tickets, report_title="ServeSmart — Task History"):
    """Builds a PDF (in memory) covering every ticket passed in, plus its
    full activity log. Returns raw PDF bytes ready for st.download_button."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8.5, leading=11)
    wrap = ParagraphStyle("wrap", parent=styles["Normal"], fontSize=9, leading=12)

    story = [
        Paragraph(report_title, styles["Title"]),
        Paragraph(
            f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · {len(tickets)} ticket(s)",
            small,
        ),
        Spacer(1, 14),
    ]

    if not tickets:
        story.append(Paragraph("No tickets to report.", styles["Normal"]))
        doc.build(story)
        return buf.getvalue()

    # Summary table
    summary_data = [["Ticket ID", "Title", "Status", "Priority", "Student", "Technician"]]
    for t in sorted(tickets, key=m.priority_sort_key):
        tech = m.name_for(t["technicianId"]) if t["technicianId"] else "Unassigned"
        summary_data.append([
            t["id"], Paragraph(t["title"], wrap), t["status"], t["priority"],
            m.name_for(t["studentId"]), tech,
        ])
    summary_table = Table(
        summary_data, repeatRows=1,
        colWidths=[0.75 * inch, 1.9 * inch, 0.9 * inch, 0.6 * inch, 1.1 * inch, 1.1 * inch],
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4338ca")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f7fb")]),
    ]))
    story.append(Paragraph("Summary", styles["Heading2"]))
    story.append(summary_table)
    story.append(PageBreak())

    # One detail section per ticket, each with its full activity/status log.
    story.append(Paragraph("Full Activity Log by Ticket", styles["Heading2"]))
    story.append(Spacer(1, 8))
    for t in sorted(tickets, key=m.priority_sort_key):
        tech = m.name_for(t["technicianId"]) if t["technicianId"] else "Unassigned"
        story.append(Paragraph(f"{t['id']} — {t['title']}", styles["Heading3"]))
        story.append(Paragraph(
            f"Status: {t['status']} · Priority: {t['priority']} · Category: {t['category']} · "
            f"Location: {t['location']}<br/>Student: {m.name_for(t['studentId'])} · Technician: {tech}<br/>"
            f"Created: {t['createdAt']} · Updated: {t['updatedAt']}",
            small,
        ))
        story.append(Spacer(1, 4))

        log_data = [["Timestamp", "Status", "By"]]
        for a in t["activity"]:
            log_data.append([a["at"], a["status"], m.name_for(a["by"])])
        log_table = Table(log_data, colWidths=[1.8 * inch, 1.8 * inch, 2.0 * inch])
        log_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fe")),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ]))
        story.append(log_table)
        story.append(Spacer(1, 14))

    doc.build(story)
    return buf.getvalue()


def pdf_download_button(tickets, label, file_name, report_title="ServeSmart — Task History", key=None):
    """Renders a button that generates the PDF on click and offers it for
    download. Generation happens lazily (only when clicked) since building
    the PDF has a small cost."""
    pdf_bytes = build_history_pdf(tickets, report_title=report_title)
    st.download_button(
        label=label,
        data=pdf_bytes,
        file_name=file_name,
        mime="application/pdf",
        key=key,
        type="primary",
    )
