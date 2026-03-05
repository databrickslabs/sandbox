/**
 * Shared context for WiringCanvas visual state.
 * Separated to avoid circular imports between WiringCanvas and AgentNode.
 */
import { createContext } from "react";
import type { ColorMode } from "./WiringCanvas";

interface AgentMeta {
  description?: string;
  capabilities?: string;
  role?: string;
}

export interface WiringCanvasContextValue {
  hoveredNode: string | null;
  connectedToHovered: Set<string>;
  colorMode: ColorMode;
  agentMeta: Record<string, AgentMeta>;
  deployStatus: Record<string, string>;
}

const EMPTY_SET = new Set<string>();

export const WiringCanvasContext = createContext<WiringCanvasContextValue>({
  hoveredNode: null,
  connectedToHovered: EMPTY_SET,
  colorMode: "role",
  agentMeta: {},
  deployStatus: {},
});
