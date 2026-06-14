
/**
 * Centralized API client for the FastAPI backend.
 *
 * Uses the native `fetch` API with async/await and returns typed promises.
 * All HTTP errors throw an `Error` containing the status code and response text.
 * The helper `apiRequest` centralises request construction, response handling,
 * and error handling to avoid duplication.
 */

const API_BASE_URL = "http://localhost:8000";

type HttpMethod = "GET" | "POST" | "PUT" | "DELETE";

/**
 * Core request helper.
 *
 * @param endpoint   Path relative to the API base URL (e.g. "/api/tracks")
 * @param method     HTTP method
 * @param body       Optional request payload (will be JSON‑stringified)
 * @returns          Parsed JSON response
 * @throws         Error on non‑2xx responses
 */
async function apiRequest<T>(
  endpoint: string,
  method: HttpMethod = "GET",
  body?: unknown
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const options: RequestInit = {
    method,
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "same-origin",
  };

  if (body !== undefined) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errText}`);
  }

  // 204 No Content returns an empty body – treat as `null`.
  if (response.status === 204) {
    return null as unknown as T;
  }

  const data = (await response.json()) as T;
  return data;
}

/* ------------------------------------------------------------
/* Tracks                                                                     */
/* ------------------------------------------------------------
export async function getTracks() {
  return apiRequest<any[]>("/api/tracks");
}

export async function getTrack(trackId: number) {
  return apiRequest<any>(`/api/tracks/${trackId}`);
}

export async function searchTracks(query: string) {
  // Backend search endpoint expects query parameters; encode s
  const params = new URLSearchParams({ q: query });
  return apiRequest<any[]>(`/api/tracks/search?${params}`);
}

/* -------------------------------------------------------------------------- */
/* Playlists
/* -------------------------------------------------------------------------- */
export async function getPlaylists() {
  return apiRequest<any[]>("/api/playlists");
}

export async function getPlaylist(playlistId: number) {
  return apiRequest<any>(`/api/playlists/${playlistId}`);
}

export async function createPlaylist(name: string) {
  return apiRequest<any>("/api/playlists", "POST", { name });
}

export async function deletePlaylist(playlistId: number) {
  return apiRequest<void>(`/api/playlists/${playlistId}`, "DELETE");
}

/* ------------------------------------------------------------
/* Favorites                                                                  */
/* ------------------------------------------------------------
export async function getFavorites() {
  return apiRequest<any[]>("/api/favorites");
}

export async function addFavorite(trackId: number) {
  return apiRequest<any>(`/api/favorites/${trackId}`, "POST");
}

export async function removeFavorite(trackId: number) {
  return apiRequest<void>(`/api/favorites/${trackId}`, "DELETE"
}

/* -------------------------------------------------------------------------- */
/* History (Recently Played)
/* -------------------------------------------------------------------------- */
export async function getRecentlyPlayed() {
  return apiRequest<any[]>("/api/history");
}

/* ------------------------------------------------------------
/* Settings                                                                   */
/* ------------------------------------------------------------
export async function getSettings() {
  return apiRequest<any>("/api/settings");
}

export async function updateSettings(settings: object) {
  return apiRequest<any>("/api/settings", "PUT", settings);
}

/* -------------------------------------------------------------------------- */
/* Library
/* -------------------------------------------------------------------------- */
export async function importDirectory(directoryPath: string) {
  return apiRequest<any>("/api/library/import", "POST", { directory_path: directoryPath });
}

export async function rescanLibrary() {
  return apiRequest<any>("/api/library/rescan", "POST");
}