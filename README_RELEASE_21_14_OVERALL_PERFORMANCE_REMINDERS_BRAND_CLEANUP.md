# BIM Portal Release 21.14

## Purpose

Release 21.14 is a cumulative update built on Release 21.13. It introduces an Overall Performance report, changes the portal to a text-only BIM Portal / Freelancers identity, and makes unread freelancer reminders prominent immediately after login.

## Overall Performance report

The Performance page now opens with **Overall Performance** before Quality Score, Total Tasks, and Delivery Speed.

The displayed formula is:

`Overall Performance = 40% Speed + 60% Quality`

- Speed uses the member's early-or-on-time delivery rate from completed tasks that have both a deadline and completion date.
- Quality uses the established Quality Score calculation already used by the portal.
- An Overall Performance result is shown only when the member has both measurable Speed data and rated Quality data.
- Members without both components remain visible with an unavailable Overall result instead of receiving an invented score.

The new report includes:

- Overall leader
- Team average
- Members measured
- Top-three Overall Performance cards
- Sortable member ranking table
- Speed, Quality, measured-task, and rated-task details
- Management recommendation

## Text-only portal identity

Visible company logo images and company-name branding are removed from:

- Sidebar
- Top bar
- Public header
- Administration login
- Freelancer login
- Initial setup
- Password-change pages
- Footer

The visible identity now uses only:

- **BIM Portal**
- **Freelancers**

Generated Excel and DTR workbook titles and download filenames also use BIM Portal wording.

## Prominent freelancer reminders

When a freelancer signs in and has unread reminders, the portal immediately opens the Reminders page.

The page now displays:

- A large unread-reminder alert
- A direct Review Now action
- Larger reminder cards
- Stronger unread highlighting
- Larger message text and action buttons

The normal Attendance landing page remains unchanged when there are no unread reminders. A first-login password change still takes priority; after the password is changed, unread reminders are shown before the freelancer continues.

## Preserved Release 21.13 behavior

- Members with active Work Orders remain visible in Team Availability.
- Working members stay visible in the Assigned section with blue Working Now styling.
- Overdue members remain under the red Overdue section.
- Freelancer Today's Attendance uses consistent rounded cards and controls.
- Work Order Daily Task Reports remain required.
- All active Work Orders remain visible simultaneously.
- July attendance and historical Start Date backfills remain unchanged.

## Database impact

- No new migration
- No new tables
- No new columns
- No data backfill
- No account, task, attendance, DTR, Work Order, leave, overtime, payroll, or Quality Score records are rewritten

Current Alembic head: `20260803_0013`.
