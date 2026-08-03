"""Backfill uploaded task dates, derive project starts, and confirm July leave.

Revision ID: 20260803_0012
Revises: 20260803_0011
Create Date: 2026-08-03
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "20260803_0012"
down_revision = "20260803_0011"
branch_labels = None
depends_on = None

_GAB_LEAVE_DATES = (
    date(2026, 7, 1),
    date(2026, 7, 2),
    date(2026, 7, 3),
    date(2026, 7, 6),
)
_CARLO_INCORRECT_LEAVE_DATE = date(2026, 7, 27)
_TASK_START_DATES = (
    (225, date(2026, 8, 3)),
    (226, date(2025, 4, 15)),
    (227, date(2025, 4, 28)),
    (228, date(2025, 5, 23)),
    (229, date(2025, 5, 14)),
    (230, date(2025, 6, 2)),
    (231, date(2025, 6, 5)),
    (232, date(2025, 6, 9)),
    (233, date(2025, 6, 16)),
    (234, date(2025, 6, 20)),
    (235, date(2025, 7, 3)),
    (236, date(2025, 7, 15)),
    (237, date(2025, 7, 22)),
    (238, date(2025, 7, 21)),
    (239, date(2025, 7, 22)),
    (240, date(2025, 7, 29)),
    (241, date(2025, 7, 30)),
    (242, date(2025, 8, 13)),
    (243, date(2025, 8, 19)),
    (244, date(2025, 8, 21)),
    (245, date(2025, 8, 28)),
    (246, date(2025, 9, 2)),
    (247, date(2025, 9, 5)),
    (248, date(2025, 9, 16)),
    (249, date(2025, 9, 19)),
    (250, date(2025, 10, 1)),
    (251, date(2025, 10, 8)),
    (252, date(2025, 10, 28)),
    (253, date(2025, 11, 4)),
    (254, date(2025, 11, 26)),
    (255, date(2025, 11, 18)),
    (256, date(2025, 11, 28)),
    (257, date(2025, 12, 2)),
    (258, date(2025, 12, 8)),
    (259, date(2025, 12, 18)),
    (260, date(2026, 1, 7)),
    (261, date(2026, 1, 14)),
    (262, date(2026, 1, 19)),
    (263, date(2026, 1, 21)),
    (264, date(2026, 2, 1)),
    (265, date(2026, 2, 11)),
    (266, date(2026, 2, 6)),
    (267, date(2026, 2, 12)),
    (268, date(2026, 2, 23)),
    (269, date(2026, 2, 23)),
    (270, date(2026, 3, 9)),
    (271, date(2026, 3, 10)),
    (272, date(2026, 3, 17)),
    (273, date(2026, 4, 7)),
    (274, date(2026, 4, 23)),
    (276, date(2026, 4, 23)),
    (277, date(2025, 6, 23)),
    (278, date(2025, 7, 4)),
    (279, date(2025, 7, 9)),
    (280, date(2025, 7, 18)),
    (281, date(2025, 7, 28)),
    (282, date(2025, 8, 14)),
    (283, date(2025, 8, 15)),
    (284, date(2025, 8, 22)),
    (285, date(2025, 9, 8)),
    (286, date(2025, 9, 15)),
    (287, date(2025, 9, 19)),
    (288, date(2025, 10, 3)),
    (289, date(2025, 10, 1)),
    (290, date(2025, 10, 7)),
    (291, date(2025, 10, 15)),
    (292, date(2025, 10, 31)),
    (293, date(2025, 11, 10)),
    (294, date(2025, 11, 27)),
    (295, date(2025, 12, 1)),
    (296, date(2025, 12, 17)),
    (297, date(2026, 1, 22)),
    (298, date(2026, 2, 6)),
    (299, date(2026, 2, 23)),
    (300, date(2026, 2, 26)),
    (301, date(2026, 3, 9)),
    (302, date(2026, 3, 11)),
    (303, date(2026, 4, 1)),
    (304, date(2026, 4, 9)),
    (305, date(2026, 4, 20)),
    (306, date(2026, 5, 13)),
    (307, date(2026, 5, 21)),
    (308, date(2026, 6, 3)),
    (309, date(2025, 7, 15)),
    (310, date(2025, 7, 30)),
    (311, date(2025, 8, 11)),
    (312, date(2025, 8, 21)),
    (313, date(2025, 8, 28)),
    (314, date(2025, 8, 28)),
    (315, date(2025, 9, 5)),
    (316, date(2025, 9, 9)),
    (317, date(2025, 10, 1)),
    (318, date(2025, 9, 22)),
    (319, date(2025, 10, 8)),
    (320, date(2025, 10, 31)),
    (321, date(2025, 11, 11)),
    (322, date(2025, 12, 8)),
    (323, date(2025, 12, 12)),
    (324, date(2025, 12, 16)),
    (325, date(2026, 1, 8)),
    (326, date(2026, 1, 20)),
    (327, date(2026, 2, 3)),
    (328, date(2026, 2, 26)),
    (329, date(2026, 3, 4)),
    (330, date(2026, 3, 27)),
    (331, date(2026, 4, 1)),
    (332, date(2026, 4, 13)),
    (333, date(2026, 4, 23)),
    (334, date(2026, 5, 8)),
    (335, date(2026, 5, 25)),
    (336, date(2026, 5, 28)),
    (337, date(2026, 6, 3)),
    (338, date(2026, 6, 17)),
    (339, date(2025, 7, 15)),
    (340, date(2025, 8, 21)),
    (341, date(2025, 8, 28)),
    (342, date(2025, 9, 5)),
    (343, date(2025, 9, 15)),
    (344, date(2025, 9, 17)),
    (345, date(2025, 10, 8)),
    (346, date(2025, 10, 22)),
    (347, date(2025, 10, 23)),
    (348, date(2025, 11, 5)),
    (349, date(2025, 11, 13)),
    (350, date(2025, 12, 8)),
    (351, date(2025, 12, 12)),
    (352, date(2025, 12, 18)),
    (353, date(2026, 1, 1)),
    (354, date(2025, 12, 24)),
    (355, date(2026, 1, 15)),
    (356, date(2026, 1, 29)),
    (357, date(2026, 2, 3)),
    (358, date(2026, 2, 3)),
    (359, date(2026, 2, 23)),
    (360, date(2026, 3, 2)),
    (361, date(2026, 5, 1)),
    (362, date(2026, 4, 13)),
    (363, date(2026, 4, 13)),
    (364, date(2026, 5, 19)),
    (365, date(2026, 6, 8)),
    (366, date(2026, 6, 11)),
    (367, date(2025, 11, 24)),
    (368, date(2025, 12, 16)),
    (369, date(2025, 12, 29)),
    (370, date(2026, 1, 21)),
    (371, date(2026, 2, 5)),
    (372, date(2026, 2, 9)),
    (373, date(2026, 2, 25)),
    (374, date(2026, 3, 4)),
    (375, date(2026, 3, 23)),
    (376, date(2026, 3, 13)),
    (377, date(2026, 4, 7)),
    (378, date(2026, 4, 14)),
    (379, date(2026, 4, 14)),
    (380, date(2026, 4, 27)),
    (381, date(2026, 5, 8)),
    (382, date(2026, 5, 14)),
    (383, date(2026, 5, 25)),
    (384, date(2026, 5, 28)),
    (385, date(2026, 6, 8)),
    (386, date(2026, 6, 15)),
    (387, date(2026, 7, 8)),
    (388, date(2026, 3, 30)),
    (389, date(2026, 4, 22)),
    (390, date(2026, 5, 12)),
    (391, date(2026, 6, 24)),
    (392, date(2026, 6, 30)),
    (393, date(2025, 6, 24)),
    (394, date(2025, 7, 3)),
    (395, date(2025, 7, 9)),
    (396, date(2025, 7, 18)),
    (397, date(2025, 7, 28)),
    (398, date(2025, 8, 15)),
    (399, date(2025, 9, 1)),
    (400, date(2025, 9, 22)),
    (401, date(2025, 9, 24)),
    (402, date(2025, 10, 17)),
    (403, date(2025, 10, 28)),
    (404, date(2025, 11, 7)),
    (405, date(2025, 11, 25)),
    (406, date(2025, 11, 28)),
    (407, date(2025, 12, 11)),
    (408, date(2025, 12, 29)),
    (409, date(2026, 1, 9)),
    (410, date(2026, 1, 28)),
    (411, date(2026, 2, 26)),
    (412, date(2026, 2, 26)),
    (413, date(2026, 2, 26)),
    (414, date(2025, 12, 29)),
    (415, date(2025, 12, 29)),
    (416, date(2025, 12, 29)),
    (417, date(2025, 12, 29)),
    (418, date(2025, 12, 29)),
    (419, date(2026, 6, 24)),
    (420, date(2026, 6, 30)),
    (421, date(2026, 6, 11)),
    (422, date(2026, 7, 13)),
    (423, date(2026, 7, 13)),
    (424, date(2026, 7, 7)),
    (425, date(2026, 7, 7)),
    (426, date(2026, 7, 7)),
    (427, date(2026, 7, 10)),
    (428, date(2026, 7, 13)),
    (429, date(2026, 7, 13)),
    (430, date(2026, 7, 14)),
    (431, date(2026, 7, 15)),
    (432, date(2026, 7, 15)),
    (433, date(2026, 7, 17)),
    (434, date(2026, 7, 17)),
    (435, date(2026, 7, 16)),
    (436, date(2026, 7, 20)),
    (437, date(2026, 7, 20)),
    (438, date(2026, 7, 21)),
    (439, date(2026, 7, 21)),
    (440, date(2026, 7, 23)),
    (441, date(2026, 7, 24)),
    (442, date(2026, 7, 24)),
    (443, date(2026, 7, 27)),
    (444, date(2026, 7, 28)),
    (445, date(2026, 7, 28)),
    (446, date(2026, 7, 28)),
    (447, date(2026, 7, 30)),
    (448, date(2026, 7, 30)),
    (450, date(2026, 8, 2)),
    (452, date(2026, 8, 3))
)
_IMPORT_NOTE = "Confirmed July 2026 leave imported by Release 21.09."


def _person_id(bind, full_name: str):
    return bind.execute(
        sa.text(
            "SELECT id FROM freelancers "
            "WHERE lower(trim(full_name)) = :full_name "
            "ORDER BY id LIMIT 1"
        ),
        {"full_name": full_name.casefold()},
    ).scalar()


def _admin_id(bind):
    admin_id = bind.execute(
        sa.text(
            "SELECT id FROM hr_admin_accounts "
            "WHERE is_active = :active "
            "ORDER BY CASE WHEN upper(role) = 'ADMIN' THEN 0 ELSE 1 END, id "
            "LIMIT 1"
        ),
        {"active": True},
    ).scalar()
    if admin_id is not None:
        return admin_id
    return bind.execute(
        sa.text("SELECT id FROM hr_admin_accounts ORDER BY id LIMIT 1")
    ).scalar()


def _invalidate_non_finalized_dtr(bind, freelancer_id: int) -> None:
    dtr_ids = [
        int(row[0])
        for row in bind.execute(
            sa.text(
                "SELECT id FROM monthly_dtr "
                "WHERE freelancer_id = :freelancer_id "
                "AND month_key = '2026-07' "
                "AND status <> 'FINALIZED'"
            ),
            {"freelancer_id": freelancer_id},
        ).all()
    ]
    for dtr_id in dtr_ids:
        for table_name in (
            "payroll_month_summary",
            "dtr_daily_lines",
            "dtr_task_lines",
            "dtr_comp_lines",
            "dtr_leave_lines",
        ):
            bind.execute(
                sa.text(f"DELETE FROM {table_name} WHERE monthly_dtr_id = :dtr_id"),
                {"dtr_id": dtr_id},
            )
        bind.execute(
            sa.text("DELETE FROM monthly_dtr WHERE id = :dtr_id"),
            {"dtr_id": dtr_id},
        )


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)

    # Apply every valid Start Date supplied in the All Tasks workbook, but only
    # when the portal task is still missing its Start Date.
    bind.execute(
        sa.text(
            "UPDATE portal_tasks "
            "SET start_date = :start_date, updated_at = :updated_at "
            "WHERE id = :task_id AND start_date IS NULL"
        ),
        [
            {"task_id": task_id, "start_date": start_date, "updated_at": now}
            for task_id, start_date in _TASK_START_DATES
        ],
    )

    # Projects without a Start Date inherit the earliest dated task in the same
    # project. Existing project dates are never overwritten.
    bind.execute(
        sa.text(
            "UPDATE portal_projects "
            "SET start_date = ("
            "  SELECT MIN(portal_tasks.start_date) "
            "  FROM portal_tasks "
            "  WHERE portal_tasks.project_id = portal_projects.id "
            "    AND portal_tasks.start_date IS NOT NULL"
            "), updated_at = :updated_at "
            "WHERE start_date IS NULL "
            "AND EXISTS ("
            "  SELECT 1 FROM portal_tasks "
            "  WHERE portal_tasks.project_id = portal_projects.id "
            "    AND portal_tasks.start_date IS NOT NULL"
            ")"
        ),
        {"updated_at": now},
    )

    gab_id = _person_id(bind, "gabrielle gameng")
    carlo_id = _person_id(bind, "carlo ninoy nilo")
    admin_id = _admin_id(bind)

    # Carlo has no leave on July 27.
    if carlo_id is not None:
        bind.execute(
            sa.text(
                "DELETE FROM leave_records "
                "WHERE freelancer_id = :freelancer_id AND leave_date = :leave_date"
            ),
            {"freelancer_id": carlo_id, "leave_date": _CARLO_INCORRECT_LEAVE_DATE},
        )
        bind.execute(
            sa.text(
                "DELETE FROM leave_requests "
                "WHERE freelancer_id = :freelancer_id AND leave_date = :leave_date"
            ),
            {"freelancer_id": carlo_id, "leave_date": _CARLO_INCORRECT_LEAVE_DATE},
        )
        _invalidate_non_finalized_dtr(bind, carlo_id)

    # Gab's confirmed approved leave dates.
    if gab_id is not None and admin_id is not None:
        for leave_date in _GAB_LEAVE_DATES:
            exists = bind.execute(
                sa.text(
                    "SELECT id FROM leave_records "
                    "WHERE freelancer_id = :freelancer_id AND leave_date = :leave_date"
                ),
                {"freelancer_id": gab_id, "leave_date": leave_date},
            ).scalar()
            if exists is None:
                bind.execute(
                    sa.text(
                        "INSERT INTO leave_records ("
                        "freelancer_id, leave_date, leave_type, is_paid, status, "
                        "duration_minutes, comp_leave_minutes_used, source_request_id, notes, "
                        "approved_by_admin_id, created_at, updated_at"
                        ") VALUES ("
                        ":freelancer_id, :leave_date, :leave_type, :is_paid, :status, "
                        ":duration_minutes, :comp_leave_minutes_used, NULL, :notes, "
                        ":approved_by_admin_id, :created_at, :updated_at"
                        ")"
                    ),
                    {
                        "freelancer_id": gab_id,
                        "leave_date": leave_date,
                        "leave_type": "APPROVED_LEAVE",
                        "is_paid": False,
                        "status": "APPROVED",
                        "duration_minutes": 480,
                        "comp_leave_minutes_used": 0,
                        "notes": _IMPORT_NOTE,
                        "approved_by_admin_id": admin_id,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
        _invalidate_non_finalized_dtr(bind, gab_id)

    bind.execute(
        sa.text(
            "INSERT INTO audit_log (actor_type, actor_id, action, target_type, details, ip_address, created_at) "
            "VALUES ('SYSTEM', NULL, 'RELEASE_DATA_MIGRATION', 'JULY_2026_AND_START_DATES', "
            ":details, NULL, :created_at)"
        ),
        {
            "details": (
                "Release 21.09 confirmed Gabrielle Gameng leave on July 1-3 and 6, "
                "removed Carlo Ninoy Nilo July 27 leave when present, backfilled missing "
                "task Start Dates from the supplied workbook, and derived missing project "
                "Start Dates from their earliest dated task."
            ),
            "created_at": now,
        },
    )


def downgrade() -> None:
    # Data corrections are intentionally not reversed. A downgrade must not
    # erase legitimate Start Dates or restore an incorrect leave record.
    pass
