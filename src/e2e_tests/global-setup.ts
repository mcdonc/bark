import { spawn } from "child_process";
import { createWriteStream, mkdtempSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";

async function globalSetup() {
  const dataDir = mkdtempSync(join(tmpdir(), "bark-e2e-"));
  process.env.BARK_E2E_DATA_DIR = dataDir;

  const projectRoot = join(__dirname, "..", "..");
  const backendPort = process.env.BARK_E2E_PORT || "18997";

  // Warm up Ollama before starting the server to force model loading.
  // Cold model loads on first request can take 30+ seconds.
  const ollamaUrl = process.env.OLLAMA_BASE_URL;
  const ollamaModel = process.env.OLLAMA_MODEL;
  const ollamaKey = process.env.OLLAMA_API_KEY;
  if (ollamaUrl && ollamaModel) {
    console.log("Warming up Ollama...");
    const warmupStart = Date.now();
    try {
      const warmupResp = await fetch(`${ollamaUrl}/chat/completions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(ollamaKey ? { Authorization: `Bearer ${ollamaKey}` } : {}),
        },
        body: JSON.stringify({
          model: ollamaModel,
          messages: [{ role: "user", content: "hi" }],
          max_tokens: 1,
        }),
      });
      if (warmupResp.ok) {
        console.log(
          `Ollama warm (${((Date.now() - warmupStart) / 1000).toFixed(1)}s)`,
        );
      } else {
        console.warn(`Ollama warmup failed: ${warmupResp.status}`);
      }
    } catch (e) {
      console.warn(`Ollama warmup error: ${e}`);
    }
  }

  console.log(
    `Starting E2E server on port ${backendPort} ` +
      `with BARK_DATA_DIR=${dataDir}`,
  );

  // Start uvicorn directly with E2E overrides as env vars.
  // No devenv up or nginx needed — just the backend server.
  const backendProcess = spawn(
    "uvicorn",
    ["bark_backend.main:app", "--host", "0.0.0.0", "--port", backendPort],
    {
      cwd: join(projectRoot, "src", "backend"),
      detached: true,
      stdio: ["ignore", "pipe", "pipe"],
      env: {
        ...process.env,
        BARK_PORT: backendPort,
        BARK_DATA_DIR: dataDir,
        BARK_JWT_SECRET: "e2e-test-secret",
        BARK_DEFAULT_USER: "admin",
        BARK_DEFAULT_PASSWORD: "admin",
        BARK_TEST_MODE: "1",
      },
    },
  );

  process.env.BARK_E2E_PID = String(backendProcess.pid);

  // Write backend output to a per-run log file so logs aren't overwritten
  // when test-e2e runs each browser sequentially.
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const logPath = join(
    projectRoot,
    "src",
    "e2e_tests",
    `backend-${timestamp}.log`,
  );
  const logStream = createWriteStream(logPath);
  process.env.BARK_E2E_LOG = logPath;
  backendProcess.stdout?.pipe(logStream);
  backendProcess.stderr?.pipe(logStream);

  const baseUrl = `http://localhost:${backendPort}`;
  const maxWait = 600;
  for (let i = 0; i < maxWait; i++) {
    try {
      const resp = await fetch(`${baseUrl}/api/config`);
      if (resp.ok) {
        console.log(`E2E server ready after ${i} seconds`);
        return;
      }
    } catch {
      // Server not ready yet
    }
    await new Promise((r) => setTimeout(r, 1000));
  }

  throw new Error("E2E server failed to start within 10 minutes");
}

export default globalSetup;
