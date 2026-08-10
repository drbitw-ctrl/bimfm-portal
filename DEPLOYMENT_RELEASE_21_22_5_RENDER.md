# Release 21.22.5 Render Deployment

1. Extract `BIM_PORTAL_RELEASE_21_22_5_RENDER.zip` and open PowerShell inside `BIM_PORTAL_RELEASE_21_22_5_RENDER`.
2. Set repository/release paths and copy with robocopy (commands supplied in ChatGPT response).
3. Review `git status` and `git diff --stat`.
4. Commit and push to `main`.
5. Keep Render build/start/health commands unchanged.
6. After Live, hard refresh and verify version `v3.0.22.5-release21.22.5-review-work-queue`.
7. Test Admin > Review Queue: assign an IN_PROGRESS/FOR_REVIEW task to an Administrator/Supervisor, start review, stop review with a note, and verify freelancer task assignment/status/progress remain unchanged.
