// Minimal @minecraft/server-ui mock: forms resolve as cancelled unless a test queues answers.
export const answers = [];
class Form {
  constructor() {
    this.buttons = [];
    this.bodyText = "";
  }
  title(t) {
    this.titleText = t;
    return this;
  }
  body(b) {
    this.bodyText = b;
    return this;
  }
  button(b) {
    this.buttons.push(b);
    return this;
  }
  button1(b) {
    this.buttons[0] = b;
    return this;
  }
  button2(b) {
    this.buttons[1] = b;
    return this;
  }
  show() {
    globalThis.__SIM_LAST_FORM = this;
    const a = answers.shift();
    if (a === undefined) return Promise.resolve({ canceled: true, cancelationReason: "UserClosed" });
    return Promise.resolve({ canceled: false, selection: a });
  }
}
export class ActionFormData extends Form {}
export class MessageFormData extends Form {}
export class ModalFormData extends Form {}
