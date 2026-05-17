import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Trigger a browser download of `content` as a file with `filename`. */
export function downloadFile(filename: string, content: string, mime = "text/csv") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Convert an array of objects to a CSV string. */
export function toCSV<T extends Record<string, any>>(rows: T[], columns: (keyof T)[]): string {
  const header = columns.join(",");
  const body = rows.map((row) =>
    columns.map((col) => {
      const val = String(row[col] ?? "");
      return val.includes(",") || val.includes('"') ? `"${val.replace(/"/g, '""')}"` : val;
    }).join(",")
  ).join("\n");
  return `${header}\n${body}`;
}
