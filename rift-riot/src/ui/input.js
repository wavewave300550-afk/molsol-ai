// Keyboard + multi-touch input → one shared control state.
// Touch: auto-accelerate, left thumb steers, right thumb drifts / fires the skill,
// a small separate brake. Keyboard: WASD / arrows, Space drift, E skill, Esc pause.
export class Input {
  constructor(root) {
    this.root = root;
    this.keys = new Set();
    this.steer = 0;
    this.touchSteer = 0;
    this.touchDrift = false;
    this.touchBrake = false;
    this.skillQueued = false;
    this.pauseQueued = false;
    this.touchMode = matchMedia('(pointer: coarse)').matches || 'ontouchstart' in window;
    this.autoGas = this.touchMode;
    this.enabled = false;
    this._off = [];
    this._bindKeys();
    this._bindTouch();
    this._guardPage();
  }

  _on(target, type, fn, opts) {
    target.addEventListener(type, fn, opts);
    this._off.push(() => target.removeEventListener(type, fn, opts));
  }

  _bindKeys() {
    const game = new Set(['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space', 'KeyE', 'Escape']);
    this._on(window, 'keydown', (e) => {
      if (!game.has(e.code)) return;
      if (this.enabled) e.preventDefault();
      if (e.repeat) return;
      this.keys.add(e.code);
      if (e.code === 'KeyE') this.skillQueued = true;
      if (e.code === 'Escape') this.pauseQueued = true;
      if (e.code !== 'Escape' && this.touchMode && !this._touchUsed) this.autoGas = false; // a keyboard is attached
    });
    this._on(window, 'keyup', (e) => this.keys.delete(e.code));
    this._on(window, 'blur', () => this.keys.clear());
  }

  _bindTouch() {
    const q = (id) => this.root.querySelector(id);
    const pad = q('#steerPad');
    const knob = q('#steerKnob');
    let padId = null;
    const setSteer = (e) => {
      const r = pad.getBoundingClientRect();
      const half = r.width / 2;
      let v = (e.clientX - (r.left + half)) / (half * 0.72);
      v = Math.max(-1, Math.min(1, v));
      if (Math.abs(v) < 0.08) v = 0;
      this.touchSteer = v;
      knob.style.transform = `translateX(${v * half * 0.72}px)`;
      pad.classList.toggle('left', v < -0.08);
      pad.classList.toggle('right', v > 0.08);
    };
    const endSteer = (e) => {
      if (e.pointerId !== padId) return;
      padId = null;
      this.touchSteer = 0;
      knob.style.transform = 'translateX(0)';
      pad.classList.remove('left', 'right');
    };
    this._on(pad, 'pointerdown', (e) => {
      e.preventDefault();
      this._touchUsed = true;
      this.autoGas = true;
      padId = e.pointerId;
      pad.setPointerCapture?.(e.pointerId);
      setSteer(e);
    });
    this._on(pad, 'pointermove', (e) => {
      if (e.pointerId === padId) setSteer(e);
    });
    this._on(pad, 'pointerup', endSteer);
    this._on(pad, 'pointercancel', endSteer);
    this._on(pad, 'lostpointercapture', endSteer);

    const hold = (el, set) => {
      let id = null;
      const up = (e) => {
        if (e.pointerId !== id) return;
        id = null;
        set(false);
        el.classList.remove('down');
      };
      this._on(el, 'pointerdown', (e) => {
        e.preventDefault();
        this._touchUsed = true;
        this.autoGas = true;
        id = e.pointerId;
        el.setPointerCapture?.(e.pointerId);
        set(true);
        el.classList.add('down');
      });
      this._on(el, 'pointerup', up);
      this._on(el, 'pointercancel', up);
      this._on(el, 'lostpointercapture', up);
    };
    hold(q('#btnDrift'), (v) => (this.touchDrift = v));
    hold(q('#btnBrake'), (v) => (this.touchBrake = v));
    const skill = q('#btnSkill');
    this._on(skill, 'pointerdown', (e) => {
      e.preventDefault();
      this._touchUsed = true;
      this.skillQueued = true;
      skill.classList.add('down');
    });
    const skillUp = () => skill.classList.remove('down');
    this._on(skill, 'pointerup', skillUp);
    this._on(skill, 'pointercancel', skillUp);
    this._on(skill, 'pointerleave', skillUp);
    this._on(q('#btnPause'), 'pointerdown', (e) => {
      e.preventDefault();
      this.pauseQueued = true;
    });
  }

  /** Stop the page from scrolling, zooming or selecting text while racing. */
  _guardPage() {
    const stop = (e) => {
      if (this.enabled && e.cancelable && !e.target.closest?.('.scrollable, input, a')) e.preventDefault();
    };
    this._on(document, 'touchmove', stop, { passive: false });
    this._on(document, 'gesturestart', (e) => e.preventDefault());
    this._on(document, 'gesturechange', (e) => e.preventDefault());
    this._on(document, 'dblclick', (e) => e.preventDefault());
    this._on(document, 'contextmenu', (e) => {
      if (this.enabled) e.preventDefault();
    });
    let lastTouchEnd = 0;
    this._on(
      document,
      'touchend',
      (e) => {
        const now = Date.now();
        if (now - lastTouchEnd < 320 && e.cancelable && !e.target.closest?.('button, input, .tap')) e.preventDefault(); // double-tap zoom
        lastTouchEnd = now;
      },
      { passive: false }
    );
  }

  reset() {
    this.keys.clear();
    this.touchSteer = 0;
    this.touchDrift = false;
    this.touchBrake = false;
    this.skillQueued = false;
    this.pauseQueued = false;
  }

  /** Write the current controls into a racer's input record. */
  apply(target) {
    const k = this.keys;
    let steer = 0;
    if (k.has('KeyA') || k.has('ArrowLeft')) steer -= 1;
    if (k.has('KeyD') || k.has('ArrowRight')) steer += 1;
    if (this.touchSteer !== 0) steer = this.touchSteer;
    const brake = k.has('KeyS') || k.has('ArrowDown') || this.touchBrake;
    const gas = k.has('KeyW') || k.has('ArrowUp') || this.autoGas;
    target.steer = steer;
    target.brake = brake ? 1 : 0;
    target.throttle = gas && !brake ? 1 : 0;
    target.drift = k.has('Space') || this.touchDrift;
    if (this.skillQueued) {
      target.skill = true;
      this.skillQueued = false;
    }
  }

  takePause() {
    const p = this.pauseQueued;
    this.pauseQueued = false;
    return p;
  }

  dispose() {
    for (const off of this._off) off();
    this._off.length = 0;
  }
}
