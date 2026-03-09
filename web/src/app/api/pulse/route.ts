import { NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

export async function GET() {
    try {
        const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

        // Fetch the latest pulse from the Python backend server
        const response = await fetch(`${backendUrl}/api/pulse`, {
            method: "GET",
            // Add no-store to prevent Next.js from aggressively caching this response
            cache: "no-store",
        });

        if (!response.ok) {
            console.error(`Backend returned ${response.status} for /api/pulse`);
            return NextResponse.json({ pulse: null, message: "Backend error fetching pulse." });
        }

        const data = await response.json();

        return NextResponse.json(data);

    } catch (error: any) {
        console.error("Failed to fetch pulse from backend:", error);
        return NextResponse.json(
            { pulse: null, error: "Internal server error connecting to backend" },
            { status: 500 }
        );
    }
}
