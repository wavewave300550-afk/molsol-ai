const MOCK = new URL("./server.mjs", import.meta.url).href;

export async function resolve(specifier, context, nextResolve) {
  if (specifier === "@minecraft/server") return { url: MOCK, shortCircuit: true };
  return nextResolve(specifier, context);
}
