
export class CallWebRTC {
  constructor(onSignal, callbacks = {}) {
    this.onSignal = onSignal;
    this.callbacks = callbacks;

    this.peer = null;
    this.localStream = null;
    this.remoteStream = null;
    this.pendingCandidates = [];
    this.audio = null;
  }

  emit(event, data) {
    this.callbacks[event]?.(data);
  }

  async prepare() {
    if (this.peer) {
      throw new Error("WebRTC já inicializado.");
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: false
    });

    this.localStream = stream;

    try {
      this.peer = new RTCPeerConnection({
        iceServers: [
          { urls: "stun:stun.l.google.com:19302" }
        ]
      });

      this.remoteStream = new MediaStream();
      this.audio = new Audio();
      this.audio.autoplay = true;
      this.audio.srcObject = this.remoteStream;

      for (const track of stream.getAudioTracks()) {
        this.peer.addTrack(track, stream);
      }

      this.peer.ontrack = (event) => {
        this.remoteStream.addTrack(event.track);

        this.audio.play().catch((error) => {
          this.emit("error", error);
        });

        this.emit("remote-track", event.track);
      };

      this.peer.onicecandidate = (event) => {
        if (event.candidate) {
          this.onSignal({
            type: "ice-candidate",
            candidate: event.candidate.toJSON()
          });
        }
      };

      this.peer.onconnectionstatechange = () => {
        this.emit("connection-state", this.peer.connectionState);
      };
    } catch (error) {
      this.close();
      throw error;
    }
  }

  async createOffer() {
    const offer = await this.peer.createOffer();

    await this.peer.setLocalDescription(offer);

    this.onSignal({
      type: "offer",
      sdp: this.peer.localDescription.toJSON()
    });
  }

  async handleSignal(data) {
    if (!this.peer) {
      throw new Error("WebRTC não inicializado.");
    }

    switch (data.type) {
      case "offer": {
        await this.peer.setRemoteDescription(data.sdp);
        await this.flushCandidates();

        const answer = await this.peer.createAnswer();
        await this.peer.setLocalDescription(answer);

        this.onSignal({
          type: "answer",
          sdp: this.peer.localDescription.toJSON()
        });
        break;
      }

      case "answer":
        await this.peer.setRemoteDescription(data.sdp);
        await this.flushCandidates();
        break;

      case "ice-candidate":
        if (!data.candidate) return;

        if (this.peer.remoteDescription) {
          await this.peer.addIceCandidate(data.candidate);
        } else {
          this.pendingCandidates.push(data.candidate);
        }
        break;
    }
  }

  async flushCandidates() {
    const candidates = this.pendingCandidates.splice(0);

    for (const candidate of candidates) {
      await this.peer.addIceCandidate(candidate);
    }
  }

  close() {
    this.peer?.close();
    this.localStream?.getTracks().forEach(track => track.stop());
    this.remoteStream?.getTracks().forEach(track => track.stop());

    if (this.audio) {
      this.audio.pause();
      this.audio.srcObject = null;
    }

    this.peer = null;
    this.localStream = null;
    this.remoteStream = null;
    this.pendingCandidates = [];
    this.audio = null;
  }
}
