import axios from "axios";

const baseURL =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_BACKEND_URL ?? ""
    : process.env.NEXT_PUBLIC_BACKEND_URL ?? "";

export const api = axios.create({
  baseURL: baseURL || undefined,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});
