import { NextResponse } from "next/server";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}));

    // The deployed URL of your FastAPI backend (e.g. Render.com or Railway.app)
    // Default to localhost for local testing
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

    console.log(`Forwarding pipeline request to backend: ${backendUrl}/api/run-pipeline`);

    const response = await fetch(`${backendUrl}/api/run-pipeline`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        {
          status: "error",
          message: data.detail?.message || "Backend pipeline failed",
          stdout: data.detail?.stdout || "",
          stderr: data.detail?.stderr || "",
        },
        { status: response.status }
      );
    }

    return NextResponse.json(data);

  } catch (error: any) {
    console.error("Pipeline forwarding failed:", error);
    return NextResponse.json(
      {
        status: "error",
        message: "Failed to connect to the Python backend server.",
        stderr: error.message,
      },
      { status: 500 }
    );
  }
}
