/**
 * revit-claude-mcp — Production MCP Server
 * Author: Prasanna Chaurasia — Urban Matrix
 *
 * Architecture:
 *   Claude → MCP tools → writes command.json → Revit Idling event picks up
 *   → ExternalEventHandler executes → writes result.json → MCP reads → Claude
 *
 * Bridge files:
 *   C:\tools\revit-bridge\command.json  (MCP writes, Revit reads & clears)
 *   C:\tools\revit-bridge\result.json   (Revit writes, MCP reads)
 */

const { Server }               = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} = require("@modelcontextprotocol/sdk/types.js");

const fs   = require("fs");
const path = require("path");

// ── Bridge paths ────────────────────────────────────────────────
const BRIDGE_DIR = process.env.BRIDGE_DIR || "C:\\tools\\revit-bridge";
const CMD_FILE   = path.join(BRIDGE_DIR, "command.json");
const RESULT_FILE= path.join(BRIDGE_DIR, "result.json");
const TIMEOUT_MS = parseInt(process.env.REVIT_TIMEOUT || "15000");
const POLL_MS    = 200;

// ── Bridge helpers ───────────────────────────────────────────────
function writeCommand(data) {
  fs.writeFileSync(CMD_FILE, JSON.stringify(data, null, 2), "utf8");
}

async function waitForResult(timeoutMs = TIMEOUT_MS) {
  // Clear any old result first
  fs.writeFileSync(RESULT_FILE, "{}", "utf8");

  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const poll = setInterval(() => {
      try {
        const raw = fs.readFileSync(RESULT_FILE, "utf8").trim();
        if (raw && raw !== "{}") {
          const data = JSON.parse(raw);
          if (data.status) {
            clearInterval(poll);
            fs.writeFileSync(RESULT_FILE, "{}", "utf8");
            resolve(data);
          }
        }
      } catch (e) { /* file locked, retry */ }

      if (Date.now() > deadline) {
        clearInterval(poll);
        reject(new Error(
          "Revit did not respond within " + (timeoutMs / 1000) + "s.\n" +
          "Make sure:\n" +
          "1. Revit is open\n" +
          "2. You clicked 'Start Listener' in the ClaudeRevit tab\n" +
          "3. A Revit model is open (not just the start screen)"
        ));
      }
    }, POLL_MS);
  });
}

async function sendToRevit(data) {
  writeCommand(data);
  return await waitForResult();
}

function resultToText(result) {
  if (result.status === "error") {
    return "Revit error: " + result.message;
  }
  return JSON.stringify(result, null, 2);
}

// ── Tool definitions ─────────────────────────────────────────────
const TOOLS = [
  {
    name: "revit_get_model_info",
    description: "Get current Revit model name, wall/floor/sheet/room/level counts. Use this first to understand the model.",
    inputSchema: { type: "object", properties: {}, required: [] }
  },
  {
    name: "revit_get_levels",
    description: "Get all levels in the model with their names and elevations in mm.",
    inputSchema: { type: "object", properties: {}, required: [] }
  },
  {
    name: "revit_get_sheets",
    description: "Get all sheets in the model with sheet numbers and names.",
    inputSchema: { type: "object", properties: {}, required: [] }
  },
  {
    name: "revit_get_rooms",
    description: "Get all rooms with name, number, area, and level.",
    inputSchema: { type: "object", properties: {}, required: [] }
  },
  {
    name: "revit_get_elements",
    description: "Get element count by category. Categories: Walls, Floors, Doors, Windows, Rooms, Furniture.",
    inputSchema: {
      type: "object",
      properties: {
        category: { type: "string", description: "Category name: Walls, Floors, Doors, Windows, Rooms, Furniture" }
      },
      required: ["category"]
    }
  },
  {
    name: "revit_create_levels",
    description: "Create one or more levels in the Revit model.",
    inputSchema: {
      type: "object",
      properties: {
        levels: {
          type: "array",
          description: "Array of levels to create",
          items: {
            type: "object",
            properties: {
              name: { type: "string", description: "Level name e.g. 'Ground Floor'" },
              elevation_mm: { type: "number", description: "Elevation in millimetres from project base point" }
            },
            required: ["name", "elevation_mm"]
          }
        }
      },
      required: ["levels"]
    }
  },
  {
    name: "revit_create_walls",
    description: "Create walls in the model. All coordinates in millimetres from origin. Walls are straight lines between two XY points.",
    inputSchema: {
      type: "object",
      properties: {
        level: { type: "string", description: "Level name to place walls on e.g. 'Level 0'" },
        wall_type: { type: "string", description: "Partial wall type name e.g. '200mm' or 'Generic'" },
        height_mm: { type: "number", description: "Wall height in mm e.g. 3000" },
        walls: {
          type: "array",
          description: "Array of wall lines",
          items: {
            type: "object",
            properties: {
              x1: { type: "number" }, y1: { type: "number" },
              x2: { type: "number" }, y2: { type: "number" }
            },
            required: ["x1","y1","x2","y2"]
          }
        }
      },
      required: ["walls"]
    }
  },
  {
    name: "revit_create_room",
    description: "Place and name a room on a level at a given position.",
    inputSchema: {
      type: "object",
      properties: {
        level:   { type: "string", description: "Level name" },
        name:    { type: "string", description: "Room name e.g. 'Living Room'" },
        number:  { type: "string", description: "Room number e.g. 'GF-01'" },
        x_mm:    { type: "number", description: "X position in mm" },
        y_mm:    { type: "number", description: "Y position in mm" }
      },
      required: ["name", "number"]
    }
  },
  {
    name: "revit_create_sheets",
    description: "Create one or more drawing sheets in the model.",
    inputSchema: {
      type: "object",
      properties: {
        sheets: {
          type: "array",
          items: {
            type: "object",
            properties: {
              number: { type: "string", description: "Sheet number e.g. 'A100'" },
              name:   { type: "string", description: "Sheet name e.g. 'Ground Floor Plan'" }
            },
            required: ["number", "name"]
          }
        }
      },
      required: ["sheets"]
    }
  },
  {
    name: "revit_create_views",
    description: "Create floor plan, ceiling plan, or 3D views.",
    inputSchema: {
      type: "object",
      properties: {
        views: {
          type: "array",
          items: {
            type: "object",
            properties: {
              type:  { type: "string", description: "FloorPlan, CeilingPlan, or ThreeD" },
              level: { type: "string", description: "Level name (not needed for ThreeD)" },
              name:  { type: "string", description: "View name" }
            },
            required: ["type", "name"]
          }
        }
      },
      required: ["views"]
    }
  },
  {
    name: "revit_create_schedule",
    description: "Create a Revit schedule/quantity takeoff for a category.",
    inputSchema: {
      type: "object",
      properties: {
        category: { type: "string", description: "Walls, Rooms, Doors, Windows, Floors, Sheets" },
        name:     { type: "string", description: "Schedule name" },
        fields:   {
          type: "array",
          items: { type: "string" },
          description: "Field names to include e.g. ['Type Name', 'Length', 'Area']"
        }
      },
      required: ["category", "name", "fields"]
    }
  },
  {
    name: "revit_set_parameter",
    description: "Set a parameter value on a specific Revit element by ID.",
    inputSchema: {
      type: "object",
      properties: {
        element_id: { type: "number", description: "Revit element integer ID" },
        parameter:  { type: "string", description: "Parameter name e.g. 'Mark'" },
        value:      { description: "Value to set (string, number)" }
      },
      required: ["element_id", "parameter", "value"]
    }
  },
  {
    name: "revit_delete_elements",
    description: "Delete elements from the model by their integer element IDs.",
    inputSchema: {
      type: "object",
      properties: {
        element_ids: {
          type: "array",
          items: { type: "number" },
          description: "Array of integer element IDs to delete"
        }
      },
      required: ["element_ids"]
    }
  },
  {
    name: "revit_exec_python",
    description: "Execute arbitrary Python code inside Revit API context. Full Revit API access. Use for complex operations not covered by other tools. Wrap model changes in Transaction.",
    inputSchema: {
      type: "object",
      properties: {
        code:        { type: "string", description: "IronPython 2.7 code. doc and all DB classes available." },
        description: { type: "string", description: "What this code does (becomes transaction name)" }
      },
      required: ["code", "description"]
    }
  }
];

// ── Server ───────────────────────────────────────────────────────
const server = new Server(
  { name: "revit-claude-mcp", version: "2.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  // Map tool name → action name
  const actionMap = {
    "revit_get_model_info":  "get_model_info",
    "revit_get_levels":      "get_levels",
    "revit_get_sheets":      "get_sheets",
    "revit_get_rooms":       "get_rooms",
    "revit_get_elements":    "get_elements",
    "revit_create_levels":   "create_levels",
    "revit_create_walls":    "create_walls",
    "revit_create_room":     "create_room",
    "revit_create_sheets":   "create_sheets",
    "revit_create_views":    "create_views",
    "revit_create_schedule": "create_schedule",
    "revit_set_parameter":   "set_parameter",
    "revit_delete_elements": "delete_elements",
    "revit_exec_python":     "exec_python",
  };

  const action = actionMap[name];
  if (!action) {
    return { content: [{ type: "text", text: "Unknown tool: " + name }], isError: true };
  }

  try {
    const result = await sendToRevit({ action, ...args });
    return {
      content: [{ type: "text", text: resultToText(result) }],
      isError: result.status === "error"
    };
  } catch (err) {
    return {
      content: [{ type: "text", text: err.message }],
      isError: true
    };
  }
});

async function main() {
  // Ensure bridge files exist
  if (!fs.existsSync(BRIDGE_DIR)) fs.mkdirSync(BRIDGE_DIR, { recursive: true });
  if (!fs.existsSync(CMD_FILE))   fs.writeFileSync(CMD_FILE, "{}", "utf8");
  if (!fs.existsSync(RESULT_FILE))fs.writeFileSync(RESULT_FILE, "{}", "utf8");

  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Revit Claude MCP v2.0 running — bridge: " + BRIDGE_DIR);
}

main().catch(console.error);
