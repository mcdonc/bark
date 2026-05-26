import { Type } from "@sinclair/typebox";
import { spawn, ChildProcess } from "child_process";

const SUBAGENT_TIMEOUT_S = parseInt(
  process.env.PARALLEL_TASK_TIMEOUT || "120",
  10,
); // default 2 minutes per task

export default function (pi: any) {
  pi.registerTool({
    name: "parallel_tasks",
    description:
      "Execute multiple independent tasks in parallel using subagents. " +
      "Each task gets its own Pi coding agent that can read files, " +
      "write files, and run commands in /work. Use this when you have " +
      "several independent tasks that don't depend on each other " +
      "(e.g., refactoring multiple files, researching separate topics, " +
      "creating multiple independent files). Do NOT use for tasks that " +
      "must run sequentially or that depend on each other's output.",
    parameters: Type.Object({
      tasks: Type.Array(
        Type.Object({
          description: Type.String({
            description: "What this subagent should do",
          }),
        }),
        {
          description:
            "List of independent task descriptions to execute in parallel",
        },
      ),
    }),
    async execute(
      _toolCallId: string,
      params: { tasks: Array<{ description: string }> },
      signal: AbortSignal | undefined,
      onUpdate: any,
      _ctx: any,
    ) {
      const { tasks } = params;
      if (!tasks || tasks.length === 0) {
        return {
          content: [{ type: "text", text: "No tasks provided." }],
          details: {},
        };
      }

      if (onUpdate) {
        onUpdate(`Running ${tasks.length} tasks in parallel...`);
      }

      // Track child processes so we can kill them on abort
      const children: ChildProcess[] = [];

      // Kill all children if the parent is aborted
      const onAbort = () => {
        for (const child of children) {
          child.kill("SIGTERM");
        }
      };
      if (signal) {
        signal.addEventListener("abort", onAbort, { once: true });
      }

      const results: string[] = new Array(tasks.length);
      const promises = tasks.map(async (task, index) => {
        const label = `[${index + 1}/${tasks.length}]`;
        try {
          if (signal?.aborted) {
            results[index] = `${label} ${task.description}\n\nAborted.`;
            return;
          }
          if (onUpdate) {
            onUpdate(`${label} Starting: ${task.description}`);
          }
          const result = await runSubagent(task.description, children);
          results[index] = `${label} ${task.description}\n\n${result}`;
          if (onUpdate) {
            onUpdate(`${label} Done: ${task.description}`);
          }
        } catch (e) {
          results[index] = `${label} ${task.description}\n\nError: ${e}`;
          if (onUpdate) {
            onUpdate(`${label} Failed: ${task.description}`);
          }
        }
      });

      await Promise.all(promises);

      if (signal) {
        signal.removeEventListener("abort", onAbort);
      }

      const output = results.join("\n\n---\n\n");
      return {
        content: [{ type: "text", text: output }],
        details: {},
      };
    },
  });
}

// Resolve the pi binary path once at load time
const { execSync } = require("child_process");
let piBinary = "pi";
try {
  piBinary = execSync("which pi", { encoding: "utf-8" }).trim();
} catch {
  // fall back to "pi" and hope it's on PATH
}

function runSubagent(
  taskDescription: string,
  children: ChildProcess[],
): Promise<string> {
  return new Promise((resolve) => {
    const cwd = process.env.BARK_WORKSPACE_DIR || process.cwd();
    const proc = spawn(
      piBinary,
      ["-p", "--no-context-files", taskDescription],
      {
        cwd,
        stdio: ["pipe", "pipe", "pipe"],
      },
    );

    children.push(proc);

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data: Buffer) => {
      stdout += data.toString();
    });
    proc.stderr.on("data", (data: Buffer) => {
      stderr += data.toString();
    });

    proc.stdin.end();

    const timer = setTimeout(() => {
      proc.kill("SIGTERM");
      resolve(`Subagent timed out after ${SUBAGENT_TIMEOUT_S} seconds.`);
    }, SUBAGENT_TIMEOUT_S * 1000);

    proc.on("close", (code: number | null) => {
      clearTimeout(timer);

      // Remove from tracked children
      const idx = children.indexOf(proc);
      if (idx !== -1) children.splice(idx, 1);

      if (code !== 0 && code !== null) {
        resolve(
          `Subagent exited with code ${code}: ${stderr || "(no stderr)"}`,
        );
        return;
      }

      // -p mode outputs plain text (the assistant's final response)
      const text = stdout.trim();
      resolve(text || "Task completed (no text output).");
    });
  });
}
