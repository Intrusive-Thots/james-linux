import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { SettingsPage } from "./Settings";

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
}));

const baseProps = {
  state: { adapter: null },
  setAdapter: vi.fn(),
  send: vi.fn(),
  connected: false,
};

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("Settings live status", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows tool presence from the API and hides canned versions", async () => {
    vi.mocked(fetch).mockResolvedValue(jsonResponse({ nmap: true, hashcat: false }));

    render(<SettingsPage {...baseProps} activePanel="dependencies" />);

    expect(screen.queryByText("6.2.6")).toBeNull();
    expect(await screen.findByText("nmap")).toBeTruthy();
    expect(screen.getByText("hashcat")).toBeTruthy();
    expect(screen.getByText("1 missing")).toBeTruthy();
    expect(screen.queryByText("1.7")).toBeNull();
  });

  it("does not invent a passing diagnostic when the API is down", async () => {
    vi.mocked(fetch).mockRejectedValue(new Error("offline"));

    render(<SettingsPage {...baseProps} activePanel="diagnostics" />);

    expect(screen.queryByText("Packet injection capable")).toBeNull();
    expect(await screen.findByText("Unreachable")).toBeTruthy();
    expect(screen.getByText("Disconnected")).toBeTruthy();
    expect(screen.queryByText(/GPU acceleration/)).toBeNull();
  });

  it("lists wordlists returned by the backend", async () => {
    vi.mocked(fetch).mockResolvedValue(
      jsonResponse([
        { path: "/tmp/names.txt", name: "Names", category: "password", size_mb: 0.1 },
      ])
    );

    render(<SettingsPage {...baseProps} activePanel="advanced" />);

    expect(screen.queryByText("best64.rule")).toBeNull();
    expect(screen.queryByText("30 min")).toBeNull();
    expect(await screen.findByText("Names")).toBeTruthy();
    expect(screen.getByText("/tmp/names.txt")).toBeTruthy();
  });

  it("does not claim NetworkGuard is active before the backend answers", () => {
    render(<SettingsPage {...baseProps} activePanel="interfaces" />);

    expect(screen.getByText(/UNKNOWN/)).toBeTruthy();
    expect(screen.queryByText(/ACTIVE/)).toBeNull();
  });
});
