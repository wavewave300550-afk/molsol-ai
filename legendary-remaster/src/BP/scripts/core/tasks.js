const tasks = [];
export function addTask(name, step) {
    tasks.push({ name, step, age: 0 });
}
export function runTasks() {
    for (let i = tasks.length - 1; i >= 0; i--) {
        const t = tasks[i];
        let keep = false;
        try {
            keep = t.step(t.age++);
        }
        catch (e) {
            console.warn(`[legends] task ${t.name} failed: ${e}`);
            keep = false;
        }
        if (!keep)
            tasks.splice(i, 1);
    }
}
export const taskCount = () => tasks.length;
export const clearTasks = () => {
    tasks.length = 0;
};
