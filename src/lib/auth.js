// Auth state now lives in an httpOnly cookie set by the backend on login,
// so it's never readable from JS (this mitigates token theft via XSS).
// The browser attaches it automatically to same-site fetches that pass
// `credentials: "include"` (see lib/api.js) -- there's nothing for the
// frontend to store or read directly.
//
// To check whether a session is active, call fetchCurrentUser() from
// lib/api.js and see whether it resolves or throws.
