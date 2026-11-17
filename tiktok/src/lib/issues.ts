export type Issue = {
  level: "error" | "warning";
  code: string;
  message: string;
  /** Scene or source the issue belongs to. */
  where?: string;
};

export const hasErrors = (issues: Issue[]): boolean => issues.some((i) => i.level === "error");

export function formatIssues(issues: Issue[]): string {
  if (issues.length === 0) return "  (none)";
  return issues
    .map((i) => `  ${i.level === "error" ? "✖ error  " : "⚠ warning"} ${i.where ? `[${i.where}] ` : ""}${i.message} (${i.code})`)
    .join("\n");
}
