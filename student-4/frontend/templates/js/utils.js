/* =====================================================
   UTILS
   Small, dependency-free helper functions used across
   every page. Nothing in here touches page-specific
   DOM structure or app state.
===================================================== */

/*
 * Your Flask backend already has CORS(app) from flask-cors,
 * which sends Access-Control-Allow-Origin on every response.
 * So there's no CORS problem calling it directly — no nginx
 * proxy needed. Point straight at the backend container's
 * published port.
 */

const API_BASE_URL = "http://localhost:8204";

function escapeHtml(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}
