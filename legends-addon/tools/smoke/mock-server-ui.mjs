// Minimal @minecraft/server-ui mock: forms resolve as "closed" immediately.
export const __ui = { shown: [] };

export class ActionFormData {
  constructor() {
    this._title = "";
    this._buttons = [];
  }
  title(t) {
    this._title = t;
    return this;
  }
  body(b) {
    this._body = b;
    return this;
  }
  button(b) {
    this._buttons.push(b);
    return this;
  }
  async show(player) {
    __ui.shown.push({ player: player.name, title: this._title, buttons: this._buttons.length });
    return { canceled: true, selection: undefined };
  }
}
