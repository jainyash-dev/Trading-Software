import type { ConnectionState } from "../types/contracts";

export function connectionLabel(connection: ConnectionState): string {
  if (connection === "loading") return "Checking";
  if (connection === "connected") return "Connected";
  if (connection === "disconnected") return "Disconnected";
  if (connection === "unauthenticated") return "Authentication required";
  return "Unavailable";
}

export function sessionLabel(connection: ConnectionState): string {
  if (connection === "loading") return "Checking";
  if (connection === "connected") return "Authenticated";
  if (connection === "unauthenticated") return "Authentication required";
  return "Unknown";
}

export function apiStatusLabel(connection: ConnectionState): string {
  if (connection === "loading") return "Checking API";
  if (connection === "connected") return "API connected";
  if (connection === "disconnected") return "API disconnected";
  if (connection === "unauthenticated") return "Authentication required";
  return "API unavailable";
}
