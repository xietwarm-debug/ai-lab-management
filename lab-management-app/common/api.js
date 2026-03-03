const envBaseUrl =
  (typeof process !== "undefined" && process.env && process.env.UNI_APP_BASE_URL) || "";

export const BASE_URL = envBaseUrl || "http://127.0.0.1:5000";
