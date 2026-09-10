/**
 * src/api/client.js
 * Unified HTTP & Server-Sent Events (SSE) client.
 */

// Storage keys
const TOKEN_KEY = 'ai_study_assistant_auth_token';
const DEV_USER_ID_KEY = 'ai_study_assistant_dev_user';

let dynamicTokenProvider = null;

export const setTokenProvider = (provider) => {
  dynamicTokenProvider = provider;
};

export const isJwtExpired = (token) => {
  if (!token || typeof token !== 'string' || !token.startsWith('ey')) return false;
  try {
    const parts = token.split('.');
    if (parts.length < 2) return false;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    const decoded = JSON.parse(jsonPayload);
    if (!decoded.exp) return false;
    // Expired if current time is within 10 seconds of exp
    return Math.floor(Date.now() / 1000) >= (decoded.exp - 10);
  } catch {
    return false;
  }
};

export const getStoredToken = () => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token && isJwtExpired(token)) {
    // If stored JWT is expired, remove it to prevent sending bad credentials
    localStorage.removeItem(TOKEN_KEY);
    return 'dev_student_user';
  }
  return token || 'dev_student_user';
};

export const setStoredToken = (token) => {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
};

export const getStoredUserId = () => {
  return localStorage.getItem(DEV_USER_ID_KEY) || 'student_demo_user';
};

export const setStoredUserId = (userId) => {
  if (userId) {
    localStorage.setItem(DEV_USER_ID_KEY, userId);
  } else {
    localStorage.removeItem(DEV_USER_ID_KEY);
  }
};

/**
 * Retrieves the currently active and valid authentication token.
 * Calls the Clerk dynamic provider if available, or falls back to valid stored token.
 */
export async function getEffectiveToken(skipCache = false) {
  if (dynamicTokenProvider) {
    try {
      const freshToken = await dynamicTokenProvider(skipCache);
      if (freshToken) {
        setStoredToken(freshToken);
        return freshToken;
      }
    } catch (err) {
      console.warn('[client] Token provider error:', err);
    }
  }
  return getStoredToken();
}

/**
 * Standard fetch request with Authorization headers and auto-retry on expired tokens.
 */
export async function apiRequest(endpoint, options = {}, isRetry = false) {
  const token = await getEffectiveToken(isRetry);
  const headers = {
    ...(!options.isFormData && { 'Content-Type': 'application/json' }),
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorJson.error || JSON.stringify(errorJson);
    } catch {
      const errorText = await response.text();
      if (errorText) errorDetail = errorText;
    }

    // Automatically refresh token and retry ONCE if token expired
    if (
      response.status === 401 &&
      !isRetry &&
      (errorDetail.toLowerCase().includes('expired') || errorDetail.toLowerCase().includes('signature'))
    ) {
      console.warn('[client] Auth token expired. Refreshing token and retrying request...');
      if (dynamicTokenProvider) {
        try {
          const freshToken = await dynamicTokenProvider(true);
          if (freshToken) {
            setStoredToken(freshToken);
            return await apiRequest(endpoint, options, true);
          }
        } catch (retryErr) {
          console.error('[client] Failed to refresh expired token:', retryErr);
        }
      }
      // If refresh not possible, clear stale token
      localStorage.removeItem(TOKEN_KEY);
    }

    const err = new Error(errorDetail);
    err.status = response.status;
    throw err;
  }

  // Handle empty or audio/blob responses
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return await response.json();
  } else if (contentType.includes('audio/') || contentType.includes('application/octet-stream')) {
    return await response.blob();
  }
  return await response.text();
}

/**
 * Real-time SSE streaming for `/api/chat/stream`.
 */
export async function streamChatResponse({
  prompt,
  conversationHistory = [],
  onToken,
  onError,
  onDone,
  signal,
}) {
  const token = await getEffectiveToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        user_prompt: prompt,
        conversation_history: conversationHistory,
      }),
      signal,
    });

    if (!response.ok) {
      let msg = `HTTP error ${response.status}`;
      try {
        const errJson = await response.json();
        msg = errJson.detail || errJson.error || msg;
      } catch {}
      throw new Error(msg);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // keep last incomplete line

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data:')) continue;

        const dataStr = trimmed.replace(/^data:\s*/, '');
        if (dataStr === '[DONE]') {
          if (onDone) onDone();
          return;
        }

        try {
          const parsed = JSON.parse(dataStr);
          if (parsed.error) {
            if (onError) onError(new Error(parsed.error));
          } else if (parsed.text) {
            if (onToken) onToken(parsed.text);
          }
        } catch {
          // If plain text chunk was passed
          if (onToken) onToken(dataStr);
        }
      }
    }

    if (onDone) onDone();
  } catch (err) {
    if (err.name === 'AbortError') {
      if (onDone) onDone();
      return;
    }
    if (onError) onError(err);
    else throw err;
  }
}
