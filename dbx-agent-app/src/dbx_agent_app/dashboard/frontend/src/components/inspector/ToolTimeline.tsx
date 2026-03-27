import type { ToolCallEntry } from "../../types";
import { ToolCallCard } from "./ToolCallCard";

interface Props {
  entries: ToolCallEntry[];
}

export function ToolTimeline({ entries }: Props) {
  if (entries.length === 0) return null;

  return (
    <div className="tool-timeline">
      {entries.map((entry) => (
        <ToolCallCard key={entry.id} entry={entry} />
      ))}
    </div>
  );
}
