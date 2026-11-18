/** Stand-in for @minecraft/server-ui: forms resolve with scripted answers (uiSim.answers). */
export const uiSim = { answers: [], shown: [] };

function respond(kind, form) {
  uiSim.shown.push({ kind, title: form._title, buttons: form._buttons?.length ?? 0, controls: form._controls?.length ?? 0 });
  const a = uiSim.answers.shift();
  return Promise.resolve(a ?? { canceled: true });
}

export class ActionFormData {
  constructor() {
    this._buttons = [];
  }
  title(t) { this._title = t; return this; }
  body(b) { this._body = b; return this; }
  button(t) { this._buttons.push(t); return this; }
  divider() { return this; }
  header() { return this; }
  label() { return this; }
  show() { return respond("action", this); }
}

export class MessageFormData {
  title(t) { this._title = t; return this; }
  body(b) { this._body = b; return this; }
  button1(t) { this._b1 = t; return this; }
  button2(t) { this._b2 = t; return this; }
  show() { return respond("message", this); }
}

export class ModalFormData {
  constructor() {
    this._controls = [];
  }
  title(t) { this._title = t; return this; }
  dropdown(label, items, opts) {
    if (!Array.isArray(items) || (opts && typeof opts !== "object")) throw new Error("ModalFormData.dropdown: bad arguments");
    this._controls.push("dropdown");
    return this;
  }
  toggle(label, opts) {
    if (opts && typeof opts !== "object") throw new Error("ModalFormData.toggle: options must be an object");
    this._controls.push("toggle");
    return this;
  }
  slider() { this._controls.push("slider"); return this; }
  textField() { this._controls.push("text"); return this; }
  submitButton() { return this; }
  divider() { return this; }
  header() { return this; }
  label() { return this; }
  show() { return respond("modal", this); }
}
