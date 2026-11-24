// Scriptable @minecraft/server-ui mock: tests push the selections a player would click.
export const FormCancelationReason = { UserBusy: "UserBusy", UserClosed: "UserClosed" };
export const __ui = { queue: [], shown: [] };

class BaseForm {
  constructor(kind) {
    this.kind = kind;
    this.buttons = [];
    this.titleText = "";
    this.bodyText = "";
  }
  title(t) {
    this.titleText = t;
    return this;
  }
  body(t) {
    this.bodyText = t;
    return this;
  }
  async show() {
    __ui.shown.push({ kind: this.kind, title: this.titleText, body: this.bodyText, buttons: this.buttons.slice() });
    const next = __ui.queue.shift();
    if (next === undefined) return { canceled: true, cancelationReason: FormCancelationReason.UserClosed };
    if (next === "busy") return { canceled: true, cancelationReason: FormCancelationReason.UserBusy };
    if (typeof next === "string") {
      const idx = this.buttons.findIndex((b) => b.text.includes(next));
      if (idx < 0) throw new Error(`smoke: button containing "${next}" not found in form "${this.titleText}": ${this.buttons.map((b) => b.text).join(" / ")}`);
      return { canceled: false, selection: idx };
    }
    return { canceled: false, selection: next };
  }
}

export class ActionFormData extends BaseForm {
  constructor() {
    super("action");
  }
  button(text, icon) {
    this.buttons.push({ text, icon });
    return this;
  }
}

export class MessageFormData extends BaseForm {
  constructor() {
    super("message");
  }
  button1(text) {
    this.buttons[0] = { text };
    return this;
  }
  button2(text) {
    this.buttons[1] = { text };
    return this;
  }
}
