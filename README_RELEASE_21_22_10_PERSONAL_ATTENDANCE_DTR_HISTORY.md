# BIM Portal Release 21.22.10

## Freelancer Personal Attendance & DTR History

Release 21.22.10 is a cumulative code-only release based on the approved Release 21.22.9 baseline.

### Existing behavior reviewed

Before this release, freelancers already had **Attendance History**, but the page displayed only the latest 31 `DailyAttendance` records. There was no freelancer-facing archive for previously generated Monthly Daily Time Records (DTRs).

### New self-service history

The freelancer sidebar now labels the destination **Attendance History & DTR**.

The page provides:

- Recent 31 attendance records (default)
- This Month
- Last Month
- Any specific `YYYY-MM` month
- All Time attendance records
- All-time attendance record count
- First and latest attendance record dates
- A Monthly DTR archive for the signed-in freelancer

### Personal DTR access

Every Monthly DTR currently stored for the signed-in freelancer is listed newest-first. Each archive card shows the month, DTR status, key attendance totals, rendered time, approved OT, and generation time.

The freelancer may open a read-only DTR detail page. The route enforces ownership: a freelancer cannot open another member's DTR by changing the URL manually.

Normal freelancer DTRs show:

- Present / absent / leave / late summaries
- Rendered time and approved OT
- Daily attendance ledger
- Monthly task activity summary
- Monthly overtime/leave/comp summary counts

Task-hourly members retain their special Work Order-based monthly record and do not require attendance Time In / Time Out.

### Daily Time Record vs Daily Task Reports

The personal DTR detail explicitly separates:

- **Daily Time Record (DTR)** — attendance and official time record
- **Daily Task Reports** — work/project/task activity

This keeps the terminology consistent with the administrative/Finance side of the portal.

### Privacy

Freelancer codes, legacy identifiers, database IDs, and administrator-only management controls are not displayed on the personal DTR pages.

### Database safety

This release adds no Alembic migration, table, column, constraint, backfill, or destructive data operation. It only reads existing `daily_attendance`, attendance calculation, DTR, DTR daily-line, DTR task-line, comp-credit, and leave records.

Normal audit/database behavior elsewhere in the application is unchanged.
