// Talks to the Treeline API. The token lives in localStorage when the browser allows it.
const BASE = (window.TREELINE_API_BASE || "").replace(/\/$/, "");
const KEY = "treeline.token";
let memoryToken = null;

export const token = {
  get() { try { return localStorage.getItem(KEY) || memoryToken; } catch { return memoryToken; } },
  set(v) { memoryToken = v; try { localStorage.setItem(KEY, v); } catch { /* private window */ } },
  clear() { memoryToken = null; try { localStorage.removeItem(KEY); } catch { /* ignore */ } },
};

export class ApiError extends Error {
  constructor(message, status, code) { super(message); this.status = status; this.code = code; }
}

export async function api(method, path, body, { auth = "bearer", basic = null } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (basic) headers.Authorization = "Basic " + btoa(basic);
  else if (auth === "bearer" && token.get()) headers.Authorization = "Bearer " + token.get();
  let res;
  try {
    res = await fetch(BASE + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new ApiError("Can't reach Treeline right now. Check your connection and try again.", 0, "offline");
  }
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { /* not JSON */ }
  if (!res.ok) {
    const err = new ApiError((data && data.error) || "Something went wrong. Try again in a moment.", res.status, data && data.code);
    if (res.status === 401 && err.code === "signed_out") {
      token.clear();
      window.dispatchEvent(new CustomEvent("tl-signed-out"));
    }
    throw err;
  }
  return data;
}

export const get = (p, o) => api("GET", p, undefined, o);
export const post = (p, b, o) => api("POST", p, b === undefined ? {} : b, o);
export const put = (p, b, o) => api("PUT", p, b, o);
export const patch = (p, b, o) => api("PATCH", p, b, o);
export const del = (p, b, o) => api("DELETE", p, b === undefined ? {} : b, o);
export const apiUrl = (p) => BASE + p;
