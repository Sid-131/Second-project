import { POST } from "../route";
import * as child_process from "child_process";
import { NextRequest } from "next/server";

// Mock child_process
jest.mock("child_process", () => ({
    execFile: jest.fn(),
}));

// Mock util.promisify to just return our mocked execFile
jest.mock("util", () => ({
    ...jest.requireActual("util"),
    promisify: (fn: any) => fn,
}));

describe("POST /api/run-pipeline", () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it("should return ok and stdout when python script succeeds", async () => {
        // Arrange
        const mockExecFileAsync = child_process.execFile as unknown as jest.Mock;
        mockExecFileAsync.mockResolvedValue({ stdout: "success log", stderr: "" });

        const req = {
            json: async () => ({ send: false, weeks: 12 }),
        } as unknown as Request;

        // Act
        const res = await POST(req);
        const data = await res.json();

        // Assert
        expect(res.status).toBe(200);
        expect(data.status).toBe("ok");
        expect(mockExecFileAsync).toHaveBeenCalledTimes(1);

        // Check args
        const calledArgs = mockExecFileAsync.mock.calls[0][1];
        expect(calledArgs).toEqual(["main.py", "--phase", "all", "--weeks", "12"]);
    });

    it("should append --send argument and override email when requested", async () => {
        // Arrange
        const mockExecFileAsync = child_process.execFile as unknown as jest.Mock;
        mockExecFileAsync.mockResolvedValue({ stdout: "", stderr: "" });

        const req = {
            json: async () => ({ send: true, weeks: 8, email: "test@example.com" }),
        } as unknown as Request;

        // Act
        await POST(req);

        // Assert
        const mockCall = mockExecFileAsync.mock.calls[0];
        const calledArgs = mockCall[1];
        const calledEnv = mockCall[2].env;

        expect(calledArgs).toEqual(["main.py", "--phase", "all", "--weeks", "8", "--send"]);
        expect(calledEnv.EMAIL_TO).toBe("test@example.com");
    });

    it("should return error when script fails", async () => {
        // Arrange
        const mockExecFileAsync = child_process.execFile as unknown as jest.Mock;
        const mockError = new Error("Command failed");
        (mockError as any).stdout = "";
        (mockError as any).stderr = "Exception occurred";
        mockExecFileAsync.mockRejectedValue(mockError);

        const req = {
            json: async () => ({}),
        } as unknown as Request;

        // Act
        const res = await POST(req);
        const data = await res.json();

        // Assert
        expect(res.status).toBe(500);
        expect(data.status).toBe("error");
        expect(data.message).toBe("Command failed");
        expect(data.stderr).toBe("Exception occurred");
    });
});
