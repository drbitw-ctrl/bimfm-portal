# Release 21.21 — Workspace and Profile Refresh

This cumulative release refreshes the two interface areas highlighted by the Administrator.

## Branding

- Keeps the application name as **BIM Portal**.
- Uses **Unified Workspace** as the application subtitle.
- Does not add the BIMFM company name or company logo.
- Adds a compact online indicator and premium application identity card in the upper-left sidebar.

## Signed-in user area

- Replaces the plain initial box with a circular gradient avatar and online-status dot.
- Adds a clearer signed-in identity, name, and role chip.
- Groups password and logout actions into compact icon controls.
- Retains the English / Traditional Chinese switch bar. It is not converted to a dropdown.
- Includes responsive behavior for smaller screens.

## Database impact

- No migration.
- No schema change.
- No data backfill.
- No production records are modified.

## Rollback

Because this is a template/CSS/configuration-only release, Render can safely roll the web service back to the previous successful deployment without a database rollback.
