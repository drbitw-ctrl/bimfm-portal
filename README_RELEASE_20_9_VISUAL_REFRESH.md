# BIMFM Portal Release 20.9 — Visual Refresh

**Application version:** `2.3.4-release20.9-visual-refresh`  
**Release date:** 2026-08-01  
**Functional base:** Release 20.8 project-member mapping

## Purpose

Release 20.9 improves the portal’s visual hierarchy, readability, navigation,
responsive behavior, and presentation consistency without changing the
PostgreSQL data model or business calculations.

## Main visual improvements

### Application shell

- New BIMFM-branded sidebar with the BIMFM logo.
- Clearer navigation groups for Projects, HR, Supervision, Finance, and Administration.
- Stronger active-page indicator.
- Sticky translucent top bar.
- User avatar and clearer account context.
- System-status indicator and visible application build number.
- Improved mobile navigation with overlay and close control.

### Dashboard presentation

- Refined executive-style hero panel.
- Improved KPI card spacing, contrast, and hover behavior.
- Cleaner workforce, approval, assignment, activity, and quick-launch panels.
- Consistent card radius, shadows, typography, and spacing.

### Tables and project-member mapping

- Sticky table headers.
- Improved row hover states and readability.
- Better member avatars, status chips, task counts, and action controls.
- New project-member search field.
- New **Show unmapped only** filter.
- Live visible-record count.
- Mapping rows remain connected to the existing Release 20.8 PostgreSQL data.

### Forms and workflow controls

- Clearer labels, focus states, input fields, select menus, and text areas.
- More consistent primary, secondary, warning, and danger actions.
- Improved flash messages and empty states.
- Submit-button locking on login forms to reduce accidental duplicate submissions.

### Login and public pages

- New branded login background and login card.
- BIMFM logo and favicon.
- Cleaner staff and freelancer login presentation.
- Responsive mobile login layout.

### Theme and accessibility

- Light and dark themes with browser-local preference storage.
- System theme is used on the first visit.
- Improved focus-visible indicators.
- Reduced-motion support.
- Better contrast and bilingual typography.
- New interface terms added to English and Traditional Chinese catalogs.

## Database safety

Release 20.9 contains **no Alembic migration** and does not alter:

- Project members or member mappings
- Projects or task assignments
- Freelancer profiles or accounts
- Attendance and corrections
- Leave and overtime
- Compensatory credits
- DTR and Finance records
- Administrator accounts

The repaired PostgreSQL member directory from Release 20.8 remains the source of
truth. Do not rerun the SQLite-to-PostgreSQL migration or the repair utility for
this visual release.

## Deployment compatibility

- PostgreSQL on Render remains supported.
- Existing `DATABASE_URL` must be retained.
- Existing `BIMFM_SESSION_SECRET` must be retained.
- Build command remains:

```text
pip install -r requirements.txt && alembic upgrade head
```

- Start command remains:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Validation

Release 20.9 passed:

```text
80 tests
0 failures
0 errors
```

Validation covered application startup, authentication, permissions, project
member mapping, PostgreSQL-native projects, Finance clarity, localization,
production hardening, and the new visual assets and table controls.
