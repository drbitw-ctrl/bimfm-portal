# BIMFM Portal Release 21.02

**Application version:** `3.0.2-release21.02-finance-dtr-password-branding`  
**Release type:** Finance permission, account security, and official branding update

## Purpose

Release 21.02 prepares the portal for production use by giving Finance a narrow
and auditable DTR-generation capability, completing password self-service and
first-login enforcement for every account type, and replacing the temporary
portal branding with the official BIMFM Technology company logo supplied by
management.

## Finance DTR access

Finance accounts can now:

- Open Monthly DTR pages.
- Generate or refresh draft Monthly DTR records.
- Generate one freelancer's DTR or all active freelancers' DTRs.
- Open DTR details.
- Export DTR workbooks.

Finance remains unable to:

- Review or finalize a DTR.
- Edit attendance.
- Approve leave or overtime.
- Manage accounts, policies, or work schedules.
- Edit projects or portal tasks.

The new permission is `dtr.generate`. The authorization middleware permits only
the exact `POST /admin/dtr/generate` operation for Finance; other Finance writes
remain blocked.

## Password security

### First login

New freelancer accounts already required a password change. Release 21.02
extends the same rule to newly created Administrator, Supervisor, and Finance
accounts.

- New staff accounts are created with `must_change_password = true`.
- New freelancer accounts continue to be created with the same requirement.
- A temporary password issued by an Administrator forces another password change.
- Existing production staff accounts migrate with the flag set to `false`, so
  deployment does not unexpectedly lock current users out.

### Self-service password changes

Every signed-in user can change only their own password:

- Staff: `/admin/change-password`
- Freelancers: `/change-password`

The option is available in the sidebar and account area after the initial
password change is completed.

### Administrator-only resets

Only Administrators can reset another account's password.

- Freelancer reset remains under Freelancer Accounts.
- Staff reset is now available under Staff Access.
- Reset passwords are temporary.
- Failed-login counters and lockout are cleared.
- The account must choose a personal password at the next login.
- Every reset is written to the audit log.

## Official company branding

The supplied official BIMFM Technology assets are applied as follows:

- Official square company mark in the application sidebar.
- Official company mark as the browser favicon and touch icon.
- Full `繽紛科技 / BIMFM TECHNOLOGY` logo on staff login, freelancer login,
  first-time setup, and password-security pages.
- Full company lockup in the public header.

The uploaded JPEG logo was converted into a transparent, web-optimized PNG
without changing the logo artwork. The uploaded ICO is preserved as the browser
favicon and converted to PNG for the portal's square brand mark.

## Sidebar redesign

The old large Workspace box is replaced by a smaller context strip with:

- Compact workspace label.
- Management Console or Freelancer Workspace title.
- Small online indicator.
- Reduced decoration and height.

This prevents the workspace area from competing with the official logo and
creates more room for navigation.

## Database compatibility

Release 21.02 adds Alembic revision `20260802_0009`.

New column:

```text
hr_admin_accounts.must_change_password BOOLEAN NOT NULL DEFAULT false
```

No existing password hash, account status, task, project, attendance, DTR,
finance, payroll, work-order, reminder, or quality record is rewritten.

## Validation

Release 21.02 passed:

- Python compilation.
- Application import.
- 44 Jinja templates.
- 1,704 English localization keys.
- 1,704 Traditional Chinese localization keys.
- Explicit translation-key coverage.
- JavaScript syntax checks.
- Fresh Alembic migration through revision `20260802_0009`.
- Upgrade simulation from revision `20260802_0008`.
- Preservation of existing staff accounts with password-change flag disabled.
- Finance first-login password replacement.
- Finance Monthly DTR generation.
- Finance DTR export visibility.
- Finance review/finalization rejection.
- Supervisor first-login password replacement.
- Freelancer first-login and later self-service password changes.
- Administrator staff-account creation and password reset.
- Official company-logo rendering.
- Compact sidebar context rendering.

All validation completed with zero failures and zero errors.
