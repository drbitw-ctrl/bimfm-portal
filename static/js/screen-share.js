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
    let stream = null;
    let socket = null;
    let heartbeatTimer = null;
    let stopping = false;
    const peers = new Map();

    const updateViewers = () => setText(viewers, String(peers.size));

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

    async function stopSharing() {
      if (stopping) return;
      stopping = true;
      if (heartbeatTimer) window.clearInterval(heartbeatTimer);
      heartbeatTimer = null;
      if (stream) stream.getTracks().forEach((track) => track.stop());
      stream = null;
      for (const viewerId of [...peers.keys()]) await closePeer(viewerId);
      if (socket) socket.close(1000, 'User stopped sharing');
      socket = null;
      root.classList.remove('is-live');
      root.classList.remove('is-source-paused');
      setText(state, 'Not sharing');
      setText(detail, 'Your screen is not being transmitted.');
      shareButton.disabled = false;
      stopButton.hidden = true;
      updateViewers();
      stopping = false;
    }

    async function startSharing() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
        setText(state, 'Screen capture unavailable');
        setText(detail, 'Use a current Chrome or Edge browser on localhost/HTTPS.');
        return;
      }
      shareButton.disabled = true;
      setText(state, 'Select a work screen or window…');
      try {
        stream = await navigator.mediaDevices.getDisplayMedia({
          video: { frameRate: { ideal: 10, max: 15 } },
          audio: false,
        });
        const track = stream.getVideoTracks()[0];
        if (!track) throw new Error('No display video track was selected.');
        track.addEventListener('ended', stopSharing, { once: true });
        track.addEventListener('mute', () => {
          root.classList.add('is-source-paused');
          setText(state, 'LIVE — source temporarily unavailable');
          setText(detail, 'The shared window may be minimized. Restore it, or share a dedicated work monitor for a more stable stream.');
        });
        track.addEventListener('unmute', () => {
          root.classList.remove('is-source-paused');
          setText(state, 'LIVE — screen visible to authorized viewers');
          setText(detail, track.label || 'Selected work screen');
        });

        socket = new WebSocket(wsUrl('/ws/screen-share/publish'));
        socket.addEventListener('open', () => {
          root.classList.add('is-live');
          setText(state, 'LIVE — screen visible to authorized viewers');
          setText(detail, track.label || 'Selected work screen');
          stopButton.hidden = false;
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
            setText(state, 'Work Order ended — live screen stopped');
            setText(detail, 'Screen sharing closes automatically when the active Work Order ends.');
            await stopSharing();
          }
        });
        socket.addEventListener('error', () => {
          setText(state, 'Signaling connection failed');
          setText(detail, 'Unable to connect to the live screen service. Refresh the page and try again.');
        });
        socket.addEventListener('close', (event) => {
          if (stream) {
            setText(state, 'Signaling disconnected');
            const reason = event.code === 4401
              ? 'Your freelancer session was not recognized. Sign in again.'
              : (event.code === 4409 || event.code === 4003)
                ? 'An active Work Order is required for live screen sharing.'
                : 'The live connection was interrupted. Stop sharing and try again.';
            setText(detail, reason);
          }
        });
      } catch (error) {
        shareButton.disabled = false;
        setText(state, 'Not sharing');
        setText(detail, error?.name === 'NotAllowedError' ? 'Screen sharing was cancelled.' : (error?.message || 'Unable to start screen sharing.'));
      }
    }

    shareButton.addEventListener('click', startSharing);
    stopButton.addEventListener('click', stopSharing);
    const stopWorkOrderForm = document.querySelector('.stop-work-order-form');
    if (stopWorkOrderForm) {
      stopWorkOrderForm.addEventListener('submit', () => {
        if (stream) stopSharing();
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
    const thumbnailPeers = new Map();
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

    function disconnectThumbnail(freelancerId) {
      const entry = thumbnailPeers.get(String(freelancerId));
      if (!entry) return;
      try { if (entry.ws) entry.ws.close(1000, 'Thumbnail closed'); } catch (_) {}
      try { if (entry.pc) entry.pc.close(); } catch (_) {}
      if (entry.video) entry.video.srcObject = null;
      thumbnailPeers.delete(String(freelancerId));
    }

    function stopExpandedViewer() {
      if (expanded) {
        try { if (expanded.ws) expanded.ws.close(1000, 'Viewer closed'); } catch (_) {}
        try { if (expanded.pc) expanded.pc.close(); } catch (_) {}
        expanded = null;
      }
      if (video) video.srcObject = null;
      viewer.hidden = true;
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
          ws.send(JSON.stringify({ type: 'answer', sdp: pc.localDescription }));
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
        if (event.code === 4403) onEnded('This account is not authorized to view live screens');
      });
      return { pc, ws };
    }

    function connectThumbnail(freelancerId, videoNode, badgeNode, noteNode) {
      const key = String(freelancerId);
      if (!videoNode || thumbnailPeers.has(key) || expanded?.freelancerId === key) return;
      const peer = connectPeer(
        freelancerId,
        (stream) => {
          videoNode.srcObject = stream;
          if (badgeNode) badgeNode.textContent = '● LIVE GLIMPSE';
          if (noteNode) noteNode.textContent = 'Live thumbnail — not recorded or stored';
        },
        (connectionState) => {
          if (connectionState === 'connected') {
            if (badgeNode) badgeNode.textContent = '● LIVE GLIMPSE';
          } else if (connectionState === 'failed') {
            if (badgeNode) badgeNode.textContent = 'Preview failed';
          } else if (connectionState === 'disconnected') {
            if (badgeNode) badgeNode.textContent = 'Preview interrupted';
          }
        },
        (message) => {
          if (badgeNode) badgeNode.textContent = message;
          if (noteNode) noteNode.textContent = 'Preview unavailable';
          videoNode.srcObject = null;
          disconnectThumbnail(key);
        },
      );
      thumbnailPeers.set(key, { ...peer, video: videoNode });
    }

    function openExpandedViewer(freelancerId, freelancerName) {
      const key = String(freelancerId);
      disconnectThumbnail(key);
      stopExpandedViewer();
      viewer.hidden = false;
      setText(title, `${freelancerName} — live screen`);
      setText(state, 'Connecting…');
      const peer = connectPeer(
        freelancerId,
        (stream) => {
          video.srcObject = stream;
          setText(state, 'LIVE — direct WebRTC');
        },
        (connectionState) => {
          if (connectionState === 'connected') setText(state, 'LIVE — direct WebRTC');
          else if (connectionState === 'failed') setText(state, 'Direct connection failed');
          else if (connectionState === 'disconnected') setText(state, 'Connection interrupted');
        },
        (message) => {
          setText(state, message);
          if (video) video.srcObject = null;
        },
      );
      expanded = { freelancerId: key, ...peer };
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
      const previousExpanded = expanded ? String(expanded.freelancerId) : null;
      for (const key of [...thumbnailPeers.keys()]) disconnectThumbnail(key);
      list.innerHTML = '';
      empty.hidden = rooms.length > 0;
      updatePresenceMeta(rooms);

      rooms.forEach((room) => {
        const key = String(room.freelancer_id);
        const card = document.createElement('article');
        card.className = `live-work-order-card${room.screen_live ? ' has-live-screen' : ''}`;
        card.dataset.fid = key;

        const preview = document.createElement('div');
        preview.className = 'live-work-order-preview';
        if (room.screen_live) {
          preview.innerHTML = `
            <video class="live-work-thumb" autoplay playsinline muted></video>
            <div class="live-thumb-overlay">
              <span class="live-thumb-badge">Connecting preview…</span>
              <small class="live-thumb-note">Live thumbnail — not recorded or stored</small>
            </div>`;
        } else {
          preview.innerHTML = '<div class="live-preview-placeholder is-offline"><span>○ NOT SHARING</span><strong>Work Order active</strong><small>No screen video is being transmitted</small></div>';
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
        card.append(preview, body);
        list.append(card);

        if (room.screen_live) {
          const videoNode = preview.querySelector('.live-work-thumb');
          const badgeNode = preview.querySelector('.live-thumb-badge');
          const noteNode = preview.querySelector('.live-thumb-note');
          if (previousExpanded === key) {
            if (badgeNode) badgeNode.textContent = 'Expanded live view open';
            if (noteNode) noteNode.textContent = 'Thumbnail paused while full viewer is open';
          } else {
            connectThumbnail(room.freelancer_id, videoNode, badgeNode, noteNode);
          }
        }
      });
      updatePresenceMeta(rooms);
    }

    close.addEventListener('click', () => {
      const key = expanded?.freelancerId || null;
      stopExpandedViewer();
      if (key) {
        const card = list.querySelector(`.live-work-order-card[data-fid="${key}"]`);
        const videoNode = card?.querySelector('.live-work-thumb');
        const badgeNode = card?.querySelector('.live-thumb-badge');
        const noteNode = card?.querySelector('.live-thumb-note');
        if (videoNode) connectThumbnail(key, videoNode, badgeNode, noteNode);
      }
    });

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
      for (const key of [...thumbnailPeers.keys()]) disconnectThumbnail(key);
    });
  }

  document.querySelectorAll('[data-screen-share-publisher]').forEach(publisherPrototype);
  document.querySelectorAll('[data-screen-share-viewer-page]').forEach(viewerPrototype);
})();
