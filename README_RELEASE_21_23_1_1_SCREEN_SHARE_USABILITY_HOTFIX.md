# BIM Portal Release 21.23.1.1

## Screen Sharing Usability and Expanded-View Hotfix

Release 21.23.1.1 is a code-only hotfix built on Release 21.23.1. It does not introduce a database migration, schema change, seed, or screen-media persistence.

### 1. Management `View Live` fix

The management Dashboard and full Live Work Room now reuse the already-connected live-thumbnail WebRTC peer when `View Live` is opened.

This means:

- opening the expanded view does not create a second WebRTC viewer connection;
- repeatedly pressing `View Live` for the same freelancer is idempotent;
- the expanded player receives the same remote `MediaStream` already proven to work in the thumbnail;
- viewer count no longer increases simply because the same management user expands the thumbnail;
- closing the expanded view returns to the thumbnail without disconnecting the underlying thumbnail viewer.

A separate browser/tab still counts as its own viewer, which is expected.

### 2. Freelancer local live preview

While an active Work Order is running, the Live Screen Sharing card now includes `Your Shared View / Live Preview` beneath the Start/Stop controls.

The preview uses the freelancer's local `getDisplayMedia()` stream directly. It does not create another network viewer and is not stored.

### 3. Revit-window recommendation

The Work Order page now recommends selecting the active Autodesk Revit application window rather than sharing the entire desktop. The browser capture request also uses `displaySurface: 'window'` as a preference hint while preserving the browser's required user selection/permission flow.

### 4. Screen-sharing notifications

The freelancer receives an on-page live notification for:

- selecting/preparing a Revit share;
- successfully active screen sharing;
- a temporarily unavailable/minimized capture;
- manual/browser stop;
- signaling interruption;
- automatic stop when the Work Order ends.

The notification also makes clear that the Work Order timer continues independently when screen sharing stops or is interrupted.

### 5. Start/Stop button states

Both buttons remain visible:

- Not sharing: `Start Live Screen` enabled, `Stop Live Screen` greyed out/disabled.
- Preparing: both controls disabled during the transition.
- Sharing: `Start Live Screen` greyed out/disabled, `Stop Live Screen` enabled.
- Stopped/cancelled: Start is enabled again and Stop is greyed out/disabled.

### Privacy boundary retained

- No MediaRecorder
- No screenshots stored
- No microphone or webcam capture
- No keyboard/mouse monitoring
- No screen-media database records
- Live screen video remains peer-to-peer WebRTC

### Runtime boundary retained

The signaling/presence registry remains in application memory. Keep the Render service on one running application instance and one Uvicorn worker until a shared signaling registry is implemented.
