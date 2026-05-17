import { useMemo } from "react";
import type { TraceTurn } from "../../types";
import type {
  LineageGraph,
  LineageNode,
  LineageEdge,
} from "../../types/lineage";
import { LineageGraphView } from "../lineage/LineageGraph";

interface Props {
  traces: TraceTurn[];
  agentName: string;
}

/**
 * Build a lineage graph from accumulated chat traces.
 * Each trace may contain routing info with tables_accessed, sub_agent, sql_queries, etc.
 */
/**
 * Collect columns observed per table from sql_queries traces.
 * Matches queries to tables by checking if the table name appears in the SQL statement.
 */
function collectTableColumns(
  traces: TraceTurn[],
): Map<string, Array<{ name: string; type: string }>> {
  const tableColumns = new Map<string, Map<string, string>>();

  for (const trace of traces) {
    const routing = trace.routing;
    if (!routing?.sql_queries || !routing.tables_accessed) continue;

    for (const query of routing.sql_queries) {
      if (!query.columns?.length) continue;
      const sql = query.statement.toLowerCase();

      for (const table of routing.tables_accessed) {
        const shortName = table.split(".").pop() ?? table;
        if (sql.includes(shortName.toLowerCase()) || sql.includes(table.toLowerCase())) {
          if (!tableColumns.has(table)) tableColumns.set(table, new Map());
          const colMap = tableColumns.get(table)!;
          for (const col of query.columns) {
            colMap.set(col.name, col.type);
          }
        }
      }
    }
  }

  const result = new Map<string, Array<{ name: string; type: string }>>();
  for (const [table, colMap] of tableColumns) {
    result.set(
      table,
      Array.from(colMap.entries())
        .map(([name, type]) => ({ name, type }))
        .sort((a, b) => a.name.localeCompare(b.name)),
    );
  }
  return result;
}

function buildSessionLineage(
  traces: TraceTurn[],
  agentName: string,
): LineageGraph {
  const nodesMap = new Map<string, LineageNode>();
  const edgesSet = new Set<string>();
  const edges: LineageEdge[] = [];
  const tableColumnsMap = collectTableColumns(traces);

  const rootId = `agent:${agentName}`;

  // Root agent node
  nodesMap.set(rootId, {
    id: rootId,
    node_type: "agent",
    name: agentName,
    full_name: agentName,
    metadata: {},
  });

  const addTableNode = (table: string) => {
    const shortName = table.split(".").pop() ?? table;
    const tableId = `table:${table}`;
    if (!nodesMap.has(tableId)) {
      const columns = tableColumnsMap.get(table) ?? [];
      nodesMap.set(tableId, {
        id: tableId,
        node_type: "table",
        name: shortName,
        full_name: table,
        metadata: columns.length > 0 ? { columns } : {},
      });
    }
    return `table:${table}`;
  };

  for (const trace of traces) {
    const routing = trace.routing;
    if (!routing) continue;

    // Sub-agent
    if (routing.sub_agent) {
      const agentId = `agent:${routing.sub_agent}`;
      if (!nodesMap.has(agentId)) {
        nodesMap.set(agentId, {
          id: agentId,
          node_type: "agent",
          name: routing.sub_agent,
          full_name: routing.sub_agent,
          metadata: {},
        });
      }
      const edgeKey = `${rootId}->${agentId}:observed_calls_agent`;
      if (!edgesSet.has(edgeKey)) {
        edgesSet.add(edgeKey);
        edges.push({
          source: rootId,
          target: agentId,
          relationship: "observed_calls_agent",
        });
      }

      // Tables accessed by sub-agent
      if (routing.tables_accessed) {
        for (const table of routing.tables_accessed) {
          const tableId = addTableNode(table);
          const tEdgeKey = `${agentId}->${tableId}:observed_reads_table`;
          if (!edgesSet.has(tEdgeKey)) {
            edgesSet.add(tEdgeKey);
            edges.push({
              source: agentId,
              target: tableId,
              relationship: "observed_reads_table",
            });
          }
        }
      }
    } else {
      // Direct table access (no sub-agent)
      if (routing.tables_accessed) {
        for (const table of routing.tables_accessed) {
          const tableId = addTableNode(table);
          const tEdgeKey = `${rootId}->${tableId}:observed_reads_table`;
          if (!edgesSet.has(tEdgeKey)) {
            edgesSet.add(tEdgeKey);
            edges.push({
              source: rootId,
              target: tableId,
              relationship: "observed_reads_table",
            });
          }
        }
      }
    }

    // Tools from routing decision
    if (routing.routing_decision?.tool_selected) {
      const toolName = routing.routing_decision.tool_selected;
      const toolId = `tool:${toolName}`;
      if (!nodesMap.has(toolId)) {
        nodesMap.set(toolId, {
          id: toolId,
          node_type: "tool",
          name: toolName,
          full_name: toolName,
          metadata: {},
        });
      }
      const source = routing.sub_agent ? `agent:${routing.sub_agent}` : rootId;
      const tEdgeKey = `${source}->${toolId}:observed_uses_tool`;
      if (!edgesSet.has(tEdgeKey)) {
        edgesSet.add(tEdgeKey);
        edges.push({
          source,
          target: toolId,
          relationship: "observed_uses_tool",
        });
      }
    }
  }

  return {
    nodes: Array.from(nodesMap.values()),
    edges,
    root_id: rootId,
  };
}

export function LineagePanel({ traces, agentName }: Props) {
  const graph = useMemo(
    () => buildSessionLineage(traces, agentName),
    [traces, agentName],
  );

  if (graph.nodes.length <= 1) {
    return (
      <div className="trace-empty">
        <p style={{ color: "var(--muted)", fontSize: "0.85rem" }}>
          Lineage graph builds here as the agent accesses tables, calls
          sub-agents, and uses tools during your chat session.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div
        style={{
          fontSize: "0.75rem",
          color: "var(--muted)",
          marginBottom: "0.5rem",
        }}
      >
        {graph.nodes.length} nodes, {graph.edges.length} edges
      </div>
      <LineageGraphView graph={graph} />
    </div>
  );
}
