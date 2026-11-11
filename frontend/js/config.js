// Frontend configuration.
// When the portal is served by the backend (http://localhost:8000/app/) the API is same-origin.
// If you open the HTML from another server/port, the API defaults to http://localhost:8000.
window.NBA_CONFIG = {
  API_BASE: location.port === "8000" ? "/api/v1" : "http://localhost:8000/api/v1",
  // Used only when the logged-in account has no faculty profile (e.g. ADMIN).
  DEFAULT_DEPARTMENT: "Artificial Intelligence and Machine Learning",
  CRITERION_CODE: "CRITERION_3",
};
