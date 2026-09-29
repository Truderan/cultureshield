const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const parseResponseBody = async (response) => {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return { detail: text.slice(0, 300) };
  }
};

export const fetchWithRetry = async (url, options = {}, retryCount = 1) => {
  let lastError;

  for (let attempt = 0; attempt <= retryCount; attempt += 1) {
    try {
      const response = await fetch(url, options);
      const data = await parseResponseBody(response.clone());
      return { response, data };
    } catch (error) {
      lastError = error;
      if (attempt < retryCount) {
        await wait(500);
      }
    }
  }

  throw lastError;
};