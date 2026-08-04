# BIMFM Portal Release 21.13
## Dashboard Member Visibility and Freelancer Attendance Card Hotfix

Release 21.13 is a cumulative hotfix built from Release 21.12.

## Purpose

This release corrects two presentation issues:

1. A freelancer using an active Work Order could disappear from the upper Live Team Availability board after the standalone Working Now group was removed in Release 21.09.
2. The freelancer Today's Attendance card used inconsistent corner treatments between its outer card, information blocks, buttons, and completion notice.

## Dashboard member visibility fix

The upper availability board remains limited to three responsibility sections:

- Available now
- Assigned members
- Overdue responsibility

There is still no separate Working Now member column in this upper board. Instead:

- Members with active assigned tasks remain visible under Assigned members.
- A member with an active Work Order keeps a blue Working Now card and badge inside that section.
- A member with overdue work remains under Overdue responsibility, even while a timer is active.
- The separate Live Work Orders panel continues to show real-time timer details.

This prevents members such as Gab from disappearing after one assigned task is completed while another assigned task remains active.

## Correct task-state behavior

Completing one task does not remove the freelancer when another assigned task is still open. The dashboard continues to count and display all task statuses except:

- COMPLETED
- CANCELLED

The summary counters remain separate:

- Working Now counts active Work Order users.
- Assigned counts members with active tasks but no active timer.
- The Assigned members display section contains both categories so every responsible member stays visible.

## Freelancer Today's Attendance styling

The freelancer attendance screen now uses consistent rounded styling for:

- The main attendance card
- Official date and server-time blocks
- Time In and Time Out blocks
- Attendance calculation blocks
- Time In and Time Out buttons
- Completion message

The update is visual only. Attendance calculations, server timestamps, Time In, Time Out, and Work Order safeguards are unchanged.

## Database impact

- New migration: None
- New tables: None
- New columns: None
- Existing records rewritten: No

The Alembic head remains `20260803_0013`.

## Version

`3.0.13-release21.13-dashboard-member-visibility-attendance-card`
