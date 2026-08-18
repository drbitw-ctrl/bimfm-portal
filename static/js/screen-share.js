(() => {
  'use strict';

  const wsUrl = (path) => `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}${path}`;
  const iceServers = [{ urls: ['stun:stun.l.google.com:19302'] }];

  function setText(node, value) {
    if (node) node.textContent = value;
  }

  function publisherPrototype(root) {
    const shareButton = root.querySelector('[data-share-start]');
    const stopButton = root.querySelector('[data-share-stop]');
    const state = root.querySelector('[data-share-state]');
    const detail = root.querySelector('[data-share-detail]');
    const viewers = root.querySelector('[data-share-viewers]');
    const preview = root.querySelector('[data-share-preview]');
    const previewPlaceholder = root.querySelector('[data-share-preview-placeholder]');
    const notification = root.querySelector('[data-share-notification]');
    const notificationTitle = root.querySelector('[data-share-notification-title]');
    const notificationMessage = root.querySelector('[data-share-notification-message]');
    const notificationIcon = root.querySelector('[data-share-notification-icon]');
    let stream = null;
    let socket = null;
    let heartbeatTimer = null;
    let stopping = false;
    const peers = new Map();

    const updateViewers = () => setText(viewers, String(peers.size));

    function setButtons(isSharing, isTransitioning = false) {
      if (shareButton) shareButton.disabled = isSharing || isTransitioning;
      if (stopButton) stopButton.disabled = !isSharing || isTransitioning;
    }

    function setNotification(kind, titleText, messageText, iconText = '●') {
      if (!notification) return;
      notification.dataset.state = kind;
      setText(notificationTitle, titleText);
      setText(notificationMessage, messageText);
      setText(notificationIcon, iconText);
    }

    function setLocalPreview(mediaStream) {
      if (!preview) return;
      preview.srcObject = mediaStream || null;
      if (previewPlaceholder) previewPlaceholder.hidden = Boolean(mediaStream);
      if (mediaStream) {
        const playPromise = preview.play();
        if (playPromise && typeof playPromise.catch === 'function') playPromise.catch(() => {});
      }
    }

    async function closePeer(viewerId) {
      const pc = peers.get(viewerId);
      if (pc) pc.close();
      peers.delete(viewerId);
      updateViewers();
    }

    async function createPublisherPeer(viewerId) {
      if (!stream || !socket || socket.readyState !== WebSocket.OPEN) return;
      await closePeer(viewerId);
      const pc = new RTCPeerConnection({ iceServers });
      pc._pendingRemoteIce = [];
      peers.set(viewerId, pc);
      stream.getTracks().forEach((track) => pc.addTrack(track, stream));
      pc.onicecandidate = (event) => {
        if (event.candidate && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'ice', viewer_id: viewerId, candidate: event.candidate }));
        }
      };
      pc.onconnectionstatechange = () => {
        if (['failed', 'closed', 'disconnected'].includes(pc.connectionState)) {
          if (pc.connectionState !== 'disconnected') closePeer(viewerId);
        }
      };
      const offer = await pc.createOffer({ offerToReceiveAudio: false, offerToReceiveVideo: false });
      await pc.setLocalDescription(offer);
      socket.send(JSON.stringify({ type: 'offer', viewer_id: viewerId, sdp: pc.localDescription }));
      updateViewers();
    }

    async function stopSharing(options = {}) {
      if (stopping) return;
      stopping = true;
      const reason = options.reason || 'user';
      setButtons(true, true);
      if (heartbeatTimer) window.clearInterval(heartbeatTimer);
      heartbeatTimer = null;
      const activeStream = stream;
      stream = null;
      if (activeStream) activeStream.getTracks().forEach((track) => track.stop());
      setLocalPreview(null);
      for (const viewerId of [...peers.keys()]) await closePeer(viewerId);
      if (socket) {
        try { socket.close(1000, 'Screen sharing stopped'); } catch (_) {}
      }
      socket = null;
      root.classList.remove('is-live');
      root.classList.remove('is-source-paused');
      setText(state, 'Not sharing');
      setText(detail, 'Your Revit window is not being transmitted.');
      setButtons(false, false);
      updateViewers();

      if (reason === 'work-order-ended') {
        setNotification('stopped', 'Live screen sharing stopped automatically', 'Your Work Order ended, so BIM Portal closed the live screen session.', '■');
      } else if (reason === 'browser') {
        setNotification('stopped', 'Live screen sharing stopped', 'Screen sharing was stopped from the browser. Your Work Order continues to run.', '■');
      } else {
        setNotification('stopped', 'Live screen sharing stopped', 'Your Revit window is no longer visible to management. Your Work Order continues to run.', '■');
      }
      stopping = false;
    }

    async function startSharing() {
      if (stream || stopping) return;
      if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
        setText(state, 'Screen capture unavailable');
        setText(detail, 'Use a current Chrome or Edge browser over HTTPS.');
        setNotification('error', 'Live screen sharing is unavailable', 'Use a current Chrome or Edge browser and reload this page.', '!');
        return;
      }

      setButtons(false, true);
      setText(state, 'Select your Revit window…');
      setText(detail, 'In the browser sharing dialog, choose the Revit application window rather than your entire desktop.');
      setNotification('preparing', 'Select the Revit window to share', 'Choose the active Autodesk Revit window in the browser sharing dialog.', '…');

      try {
        stream = await navigator.mediaDevices.getDisplayMedia({
          video: {
            displaySurface: 'window',
            frameRate: { ideal: 10, max: 15 },
          },
          audio: false,
        });
        const track = stream.getVideoTracks()[0];
        if (!track) throw new Error('No display video track was selected.');
        setLocalPreview(stream);
        setText(state, 'Connecting live screen…');
        setText(detail, track.label || 'Selected Revit window');
        setNotification('preparing', 'Connecting your live Revit view', 'Your selected window is ready. BIM Portal is connecting authorized viewers.', '…');

        track.addEventListener('ended', () => stopSharing({ reason: 'browser' }), { once: true });
        track.addEventListener('mute', () => {
          root.classList.add('is-source-paused');
          setText(state, 'LIVE — shared window temporarily unavailable');
          setText(detail, 'The Revit window may be minimized or temporarily unavailable. Restore it to continue the live view.');
          setNotification('paused', 'Live view temporarily interrupted', 'Restore the shared Revit window if it was minimized. Your Work Order continues normally.', '!');
        });
        track.addEventListener('unmute', () => {
          root.classList.remove('is-source-paused');
          setText(state, 'LIVE — Revit window visible to authorized viewers');
          setText(detail, track.label || 'Selected Revit window');
          setNotification('live', 'Live screen sharing is active', 'Authorized management viewers can currently view your selected Revit window.', '●');
        });

        socket = new WebSocket(wsUrl('/ws/screen-share/publish'));
        socket.addEventListener('open', () => {
          root.classList.add('is-live');
          setText(state, 'LIVE — Revit window visible to authorized viewers');
          setText(detail, track.label || 'Selected Revit window');
          setButtons(true, false);
          setNotification('live', 'Live screen sharing is active', 'Authorized management viewers can currently view your selected Revit window.', '●');
          if (heartbeatTimer) window.clearInterval(heartbeatTimer);
          heartbeatTimer = window.setInterval(() => {
            if (socket?.readyState === WebSocket.OPEN) {
              socket.send(JSON.stringify({ type: 'ping' }));
            }
          }, 25000);
        });
        socket.addEventListener('message', async (event) => {
          const message = JSON.parse(event.data);
          if (message.type === 'viewer_joined') {
            await createPublisherPeer(message.viewer_id);
          } else if (message.type === 'answer') {
            const pc = peers.get(message.viewer_id);
            if (pc && message.sdp) {
              await pc.setRemoteDescription(message.sdp);
              const queued = Array.isArray(pc._pendingRemoteIce) ? pc._pendingRemoteIce.splice(0) : [];
              for (const candidate of queued) {
                try { await pc.addIceCandidate(candidate); } catch (_) {}
              }
            }
          } else if (message.type === 'ice') {
            const pc = peers.get(message.viewer_id);
            if (pc && message.candidate) {
              if (pc.remoteDescription?.type) {
                try { await pc.addIceCandidate(message.candidate); } catch (_) {}
              } else {
                pc._pendingRemoteIce = pc._pendingRemoteIce || [];
                pc._pendingRemoteIce.push(message.candidate);
              }
            }
          } else if (message.type === 'viewer_left') {
            await closePeer(message.viewer_id);
          } else if (message.type === 'work_order_ended') {
            await stopSharing({ reason: 'work-order-ended' });
          }
        });
        socket.addEventListener('error', () => {
          if (!stream) return;
          setText(state, 'Live connection unavailable');
          setText(detail, 'Unable to connect to the live screen service. Stop sharing and try again.');
          setNotification('error', 'Live connection could not be established', 'Stop the current share and try again. Your Work Order remains active.', '!');
          setButtons(true, false);
        });
        socket.addEventListener('close', (event) => {
          if (!stream || stopping) return;
          setText(state, 'Live connection interrupted');
          const reason = event.code === 4401
            ? 'Your freelancer session was not recognized. Sign in again.'
            : (event.code === 4409 || event.code === 4003)
              ? 'An active Work Order is required for live screen sharing.'
              : 'The live connection was interrupted. Stop sharing and try again.';
          setText(detail, reason);
          setNotification('error', 'Live screen connection interrupted', `${reason} Your Work Order timer is not affected.`, '!');
          setButtons(true, false);
        });
      } catch (error) {
        const activeStream = stream;
        stream = null;
        if (activeStream) activeStream.getTracks().forEach((track) => track.stop());
        setLocalPreview(null);
        setButtons(false, false);
        setText(state, 'Not sharing');
        const cancelled = error?.name === 'NotAllowedError';
        const message = cancelled ? 'Screen sharing was cancelled.' : (error?.message || 'Unable to start screen sharing.');
        setText(detail, message);
        setNotification(cancelled ? 'idle' : 'error', cancelled ? 'Screen sharing was not started' : 'Unable to start live screen sharing', `${message} Your Work Order continues normally.`, cancelled ? '○' : '!');
      }
    }

    setButtons(false, false);
    setLocalPreview(null);
    shareButton?.addEventListener('click', startSharing);
    stopButton?.addEventListener('click', () => stopSharing({ reason: 'user' }));
    const stopWorkOrderForm = document.querySelector('.stop-work-order-form');
    if (stopWorkOrderForm) {
      stopWorkOrderForm.addEventListener('submit', () => {
        if (stream) stopSharing({ reason: 'work-order-ended' });
      });
    }
    window.addEventListener('beforeunload', () => {
      if (stream) stream.getTracks().forEach((track) => track.stop());
    });
  }

  function viewerPrototype(root) {
    const list = root.querySelector('[data-live-share-list]');
    const empty = root.querySelector('[data-live-share-empty]');
    const viewer = root.querySelector('[data-screen-viewer]');
    const video = root.querySelector('[data-screen-video]');
    const title = root.querySelector('[data-screen-viewer-title]');
    const state = root.querySelector('[data-screen-viewer-state]');
    const close = root.querySelector('[data-screen-viewer-close]');
    const viewerPeers = new Map();
    let expanded = null;

    function formatElapsed(startedAt) {
      if (!startedAt) return '—';
      const started = new Date(startedAt);
      if (Number.isNaN(started.getTime())) return '—';
      const seconds = Math.max(0, Math.floor((Date.now() - started.getTime()) / 1000));
      const h = String(Math.floor(seconds / 3600)).padStart(2, '0');
      const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
      const sec = String(seconds % 60).padStart(2, '0');
      return `${h}:${m}:${sec}`;
    }

    function disconnectViewerPeer(freelancerId) {
      const key = String(freelancerId);
      const entry = viewerPeers.get(key);
      if (!entry) return;
      viewerPeers.delete(key);
      entry.closing = true;
      try { if (entry.ws) entry.ws.close(1000, 'Live viewer closed'); } catch (_) {}
      try { if (entry.pc) entry.pc.close(); } catch (_) {}
      if (entry.thumbnailVideo) entry.thumbnailVideo.srcObject = null;
      if (expanded?.freelancerId === key && video) video.srcObject = null;
    }

    function stopExpandedViewer() {
      if (video) video.srcObject = null;
      expanded = null;
      if (viewer) viewer.hidden = true;
    }

    function connectPeer(freelancerId, onTrack, onState, onEnded) {
      const pc = new RTCPeerConnection({ iceServers });
      const pendingRemoteIce = [];
      const ws = new WebSocket(wsUrl(`/ws/screen-share/view/${encodeURIComponent(freelancerId)}`));
      pc.ontrack = (event) => onTrack(event.streams[0]);
      pc.onicecandidate = (event) => {
        if (event.candidate && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ice', candidate: event.candidate }));
        }
      };
      pc.onconnectionstatechange = () => onState(pc.connectionState || 'closed');
      ws.addEventListener('message', async (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'offer' && message.sdp) {
          await pc.setRemoteDescription(message.sdp);
          while (pendingRemoteIce.length) {
            const candidate = pendingRemoteIce.shift();
            try { await pc.addIceCandidate(candidate); } catch (_) {}
          }
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'answer', sdp: pc.localDescription }));
          }
        } else if (message.type === 'ice' && message.candidate) {
          if (pc.remoteDescription?.type) {
            try { await pc.addIceCandidate(message.candidate); } catch (_) {}
          } else {
            pendingRemoteIce.push(message.candidate);
          }
        } else if (message.type === 'publisher_left') {
          onEnded('Sharing ended');
        }
      });
      ws.addEventListener('close', (event) => {
        if (event.code === 4404) onEnded('This sharing session is no longer available');
        else if (event.code === 4403) onEnded('This account is not authorized to view live screens');
        else if (event.code !== 1000) onEnded('Live viewer connection closed');
      });
      return { pc, ws };
    }

    function setThumbnailStatus(entry, badgeText, noteText) {
      if (entry.badgeNode) entry.badgeNode.textContent = badgeText;
      if (entry.noteNode && noteText) entry.noteNode.textContent = noteText;
    }

    function ensureViewerPeer(freelancerId, videoNode, badgeNode, noteNode) {
      const key = String(freelancerId);
      let entry = viewerPeers.get(key);
      if (entry) {
        entry.thumbnailVideo = videoNode || entry.thumbnailVideo;
        entry.badgeNode = badgeNode || entry.badgeNode;
        entry.noteNode = noteNode || entry.noteNode;
        if (entry.stream && entry.thumbnailVideo) entry.thumbnailVideo.srcObject = entry.stream;
        if (entry.stream && expanded?.freelancerId === key && video) {
          video.srcObject = entry.stream;
          setText(state, 'LIVE — direct WebRTC');
        }
        return entry;
      }

      entry = {
        freelancerId: key,
        thumbnailVideo: videoNode || null,
        badgeNode: badgeNode || null,
        noteNode: noteNode || null,
        stream: null,
        pc: null,
        ws: null,
        closing: false,
      };
      viewerPeers.set(key, entry);

      const peer = connectPeer(
        freelancerId,
        (remoteStream) => {
          if (viewerPeers.get(key) !== entry) return;
          entry.stream = remoteStream;
          if (entry.thumbnailVideo) {
            entry.thumbnailVideo.srcObject = remoteStream;
            const playPromise = entry.thumbnailVideo.play();
            if (playPromise && typeof playPromise.catch === 'function') playPromise.catch(() => {});
          }
          setThumbnailStatus(entry, '● LIVE GLIMPSE', 'Live thumbnail — not recorded or stored');
          if (expanded?.freelancerId === key && video) {
            video.srcObject = remoteStream;
            const playPromise = video.play();
            if (playPromise && typeof playPromise.catch === 'function') playPromise.catch(() => {});
            setText(state, 'LIVE — direct WebRTC');
          }
        },
        (connectionState) => {
          if (viewerPeers.get(key) !== entry) return;
          if (connectionState === 'connected') {
            setThumbnailStatus(entry, '● LIVE GLIMPSE', 'Live thumbnail — not recorded or stored');
            if (expanded?.freelancerId === key) setText(state, 'LIVE — direct WebRTC');
          } else if (connectionState === 'failed') {
            setThumbnailStatus(entry, 'Preview failed', 'Live connection could not be established');
            if (expanded?.freelancerId === key) setText(state, 'Direct connection failed');
          } else if (connectionState === 'disconnected') {
            setThumbnailStatus(entry, 'Preview interrupted', 'Attempting to retain the live connection');
            if (expanded?.freelancerId === key) setText(state, 'Connection interrupted');
          }
        },
        (message) => {
          if (viewerPeers.get(key) !== entry || entry.closing) return;
          setThumbnailStatus(entry, message, 'Preview unavailable');
          if (entry.thumbnailVideo) entry.thumbnailVideo.srcObject = null;
          if (expanded?.freelancerId === key) {
            if (video) video.srcObject = null;
            setText(state, message);
          }
          disconnectViewerPeer(key);
        },
      );
      entry.pc = peer.pc;
      entry.ws = peer.ws;
      return entry;
    }

    function openExpandedViewer(freelancerId, freelancerName) {
      const key = String(freelancerId);
      const sameViewerAlreadyOpen = expanded?.freelancerId === key && viewer && !viewer.hidden;
      if (sameViewerAlreadyOpen) {
        viewer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        return;
      }

      expanded = { freelancerId: key };
      if (viewer) viewer.hidden = false;
      setText(title, `${freelancerName} — live screen`);
      setText(state, 'Connecting…');

      const card = list.querySelector(`.live-work-order-card[data-fid="${key}"]`);
      const videoNode = card?.querySelector('.live-work-thumb');
      const badgeNode = card?.querySelector('.live-thumb-badge');
      const noteNode = card?.querySelector('.live-thumb-note');
      const entry = ensureViewerPeer(freelancerId, videoNode, badgeNode, noteNode);

      if (entry.stream && video) {
        video.srcObject = entry.stream;
        const playPromise = video.play();
        if (playPromise && typeof playPromise.catch === 'function') playPromise.catch(() => {});
        setText(state, 'LIVE — direct WebRTC');
      }
      viewer?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    let lastRoomStructure = '';

    function roomStructureSignature(rooms) {
      return JSON.stringify(rooms.map((room) => ({
        freelancer_id: String(room.freelancer_id),
        freelancer_name: room.freelancer_name || '',
        screen_live: Boolean(room.screen_live),
        project_name: room.project_name || '',
        task_title: room.task_title || '',
        started_at: room.started_at || '',
      })));
    }

    function updatePresenceMeta(rooms) {
      const workCount = root.querySelector('[data-live-work-count]');
      const screenCount = root.querySelector('[data-live-screen-count]');
      setText(workCount, String(rooms.length));
      setText(screenCount, String(rooms.filter((room) => room.screen_live).length));
      rooms.forEach((room) => {
        const card = list.querySelector(`.live-work-order-card[data-fid="${String(room.freelancer_id)}"]`);
        const viewerNode = card?.querySelector('[data-room-viewers]');
        setText(viewerNode, String(room.viewer_count || 0));
      });
    }

    function renderRooms(rooms) {
      const structure = roomStructureSignature(rooms);
      if (structure === lastRoomStructure) {
        updatePresenceMeta(rooms);
        return;
      }
      lastRoomStructure = structure;

      const liveKeys = new Set(rooms.filter((room) => room.screen_live).map((room) => String(room.freelancer_id)));
      for (const key of [...viewerPeers.keys()]) {
        if (!liveKeys.has(key)) disconnectViewerPeer(key);
      }
      if (expanded && !liveKeys.has(String(expanded.freelancerId))) stopExpandedViewer();

      list.innerHTML = '';
      empty.hidden = rooms.length > 0;
      updatePresenceMeta(rooms);

      rooms.forEach((room) => {
        const key = String(room.freelancer_id);
        const card = document.createElement('article');
        card.className = `live-work-order-card${room.screen_live ? ' has-live-screen' : ''}`;
        card.dataset.fid = key;

        const previewNode = document.createElement('div');
        previewNode.className = 'live-work-order-preview';
        if (room.screen_live) {
          previewNode.innerHTML = `
            <video class="live-work-thumb" autoplay playsinline muted></video>
            <div class="live-thumb-overlay">
              <span class="live-thumb-badge">Connecting preview…</span>
              <small class="live-thumb-note">Live thumbnail — not recorded or stored</small>
            </div>`;
        } else {
          previewNode.innerHTML = '<div class="live-preview-placeholder is-offline"><span>○ NOT SHARING</span><strong>Work Order active</strong><small>No screen video is being transmitted</small></div>';
        }

        const body = document.createElement('div');
        body.className = 'live-work-order-body';

        const head = document.createElement('div');
        head.className = 'live-work-order-head';
        const identity = document.createElement('div');
        const name = document.createElement('strong');
        name.className = 'privacy-member-name';
        name.dataset.hiddenLabel = 'Hidden member';
        name.textContent = room.freelancer_name;
        const stateChip = document.createElement('span');
        stateChip.className = `status-chip ${room.screen_live ? 'status-available' : 'status-neutral'}`;
        stateChip.textContent = room.screen_live ? 'SCREEN LIVE' : 'NOT SHARING';
        identity.append(name);
        head.append(identity, stateChip);

        const task = document.createElement('h3');
        task.textContent = room.task_title || 'Active Work Order';
        const project = document.createElement('p');
        project.textContent = room.project_name || '—';

        const meta = document.createElement('div');
        meta.className = 'live-work-order-meta';
        const elapsed = document.createElement('div');
        elapsed.innerHTML = '<span>Work Order</span>';
        const elapsedStrong = document.createElement('strong');
        elapsedStrong.dataset.startedAt = room.started_at || '';
        elapsedStrong.textContent = formatElapsed(room.started_at);
        elapsed.append(elapsedStrong);
        const viewersMeta = document.createElement('div');
        viewersMeta.innerHTML = `<span>Viewers</span><strong data-room-viewers>${room.viewer_count || 0}</strong>`;
        meta.append(elapsed, viewersMeta);

        const actions = document.createElement('div');
        actions.className = 'live-work-order-actions';
        if (room.screen_live) {
          const button = document.createElement('button');
          button.className = 'button primary';
          button.type = 'button';
          button.textContent = 'View Live';
          button.addEventListener('click', () => openExpandedViewer(room.freelancer_id, room.freelancer_name));
          actions.append(button);
        } else {
          const note = document.createElement('small');
          note.textContent = 'Freelancer has not shared a screen.';
          actions.append(note);
        }

        body.append(head, task, project, meta, actions);
        card.append(previewNode, body);
        list.append(card);

        if (room.screen_live) {
          const videoNode = previewNode.querySelector('.live-work-thumb');
          const badgeNode = previewNode.querySelector('.live-thumb-badge');
          const noteNode = previewNode.querySelector('.live-thumb-note');
          ensureViewerPeer(room.freelancer_id, videoNode, badgeNode, noteNode);
        }
      });
      updatePresenceMeta(rooms);
    }

    close?.addEventListener('click', stopExpandedViewer);

    const watch = new WebSocket(wsUrl('/ws/screen-share/watch'));
    watch.addEventListener('message', (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === 'presence') renderRooms(payload.rooms || []);
    });
    watch.addEventListener('close', (event) => {
      empty.hidden = false;
      empty.textContent = event.code === 4403
        ? 'This account is not authorized to view live screens.'
        : 'Live presence connection closed. Refresh this page to reconnect.';
    });
    setInterval(() => {
      if (watch.readyState === WebSocket.OPEN) watch.send(JSON.stringify({ type: 'ping' }));
    }, 15000);
    setInterval(() => {
      list.querySelectorAll('[data-started-at]').forEach((node) => {
        node.textContent = formatElapsed(node.dataset.startedAt);
      });
    }, 1000);

    window.addEventListener('beforeunload', () => {
      stopExpandedViewer();
      for (const key of [...viewerPeers.keys()]) disconnectViewerPeer(key);
    });
  }

  document.querySelectorAll('[data-screen-share-publisher]').forEach(publisherPrototype);
  document.querySelectorAll('[data-screen-share-viewer-page]').forEach(viewerPrototype);
})();
