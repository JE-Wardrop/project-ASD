/* =====================================================
   AUTH GUARD
   Include this at the top of every page that requires
   a logged-in session (dashboard.html, users.html).
   Runs immediately on load, before the rest of the
   page's scripts, and bounces to the login page if
   there is no active session.
===================================================== */

if (
    sessionStorage.getItem("loggedIn")
    !== "true"
) {

    window.location.href = "index.html";

}
