// Mock of @minecraft/server-ui 2.3.0: forms record their content and resolve with
// answers queued by the test (or "UserClosed" when nothing is queued).
export const FormCancelationReason = { UserBusy: "UserBusy", UserClosed: "UserClosed" };
export const ui = { answers: [], shown: [] };

function next(kind) {
  const a = ui.answers.shift();
  if (!a) return { canceled: true, cancelationReason: FormCancelationReason.UserClosed };
  if (a.busy) return { canceled: true, cancelationReason: FormCancelationReason.UserBusy };
  if (a.kind !== kind) throw new Error(`test expected a ${a.kind} form but the script showed a ${kind}`);
  return a.response;
}

class Base {
  constructor(kind) {
    this.kind = kind;
    this.data = { title: "", body: "", buttons: [], controls: [] };
  }
  title(t) {
    this.data.title = String(t);
    return this;
  }
  body(t) {
    this.data.body = String(t);
    return this;
  }
  header(t) {
    this.data.controls.push({ header: t });
    return this;
  }
  label(t) {
    this.data.controls.push({ label: t });
    return this;
  }
  divider() {
    return this;
  }
  show(player) {
    ui.shown.push({ kind: this.kind, player: player.id, ...this.data });
    return Promise.resolve(next(this.kind));
  }
}

export class ActionFormData extends Base {
  constructor() {
    super("action");
  }
  button(text, icon) {
    this.data.buttons.push({ text: String(text), icon });
    return this;
  }
}
export class MessageFormData extends Base {
  constructor() {
    super("message");
  }
  button1(t) {
    this.data.buttons[0] = { text: String(t) };
    return this;
  }
  button2(t) {
    this.data.buttons[1] = { text: String(t) };
    return this;
  }
}
export class ModalFormData extends Base {
  constructor() {
    super("modal");
  }
  toggle(l, o) {
    this.data.controls.push({ toggle: l, o });
    return this;
  }
  slider(l, a, b, o) {
    this.data.controls.push({ slider: l, a, b, o });
    return this;
  }
  dropdown(l, items, o) {
    this.data.controls.push({ dropdown: l, items, o });
    return this;
  }
  textField(l, p, o) {
    this.data.controls.push({ text: l, p, o });
    return this;
  }
  submitButton(t) {
    this.data.submit = t;
    return this;
  }
}

/** Queue helpers for tests. */
export const answer = {
  action: (selection) => ui.answers.push({ kind: "action", response: { canceled: false, selection } }),
  message: (selection) => ui.answers.push({ kind: "message", response: { canceled: false, selection } }),
  modal: (formValues) => ui.answers.push({ kind: "modal", response: { canceled: false, formValues } }),
  busy: () => ui.answers.push({ busy: true }),
};
