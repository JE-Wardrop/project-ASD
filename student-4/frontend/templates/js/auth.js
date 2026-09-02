/* =====================================================
   AUTH
===================================================== */

const currentPage =
    window.location.pathname.split("/").pop();

/*
 * Only redirect an already-logged-in user when they
 * are actually on the login page.
 */
if (
    (currentPage === "index.html" || currentPage === "") &&
    sessionStorage.getItem("loggedIn") === "true"
) {
    window.location.href = "dashboard.html";
}


const loginForm =
    document.getElementById("loginForm");

if (loginForm) {

    loginForm.addEventListener("submit", async function(event) {

        event.preventDefault();

        const username =
            document.getElementById("loginUsername").value;

        const password =
            document.getElementById("loginPassword").value;

        try {

            const response =
                await fetch(`${API_BASE_URL}/users/login`, {

                    method: "POST",

                    body: new URLSearchParams({
                        username: username,
                        password: password
                    })

                });

            if (!response.ok) {
                throw new Error("Invalid login");
            }

            sessionStorage.setItem(
                "loggedIn",
                "true"
            );

            sessionStorage.setItem(
                "username",
                username
            );

            window.location.href = "dashboard.html";

        }
        catch (error) {

            document.getElementById("loginMessage")
                .innerHTML = `
                    <div class="alert alert-error">
                        Invalid username or password.
                    </div>
                `;

        }

    });

}


function logout() {

    sessionStorage.removeItem("loggedIn");
    sessionStorage.removeItem("username");

    window.location.href = "index.html";

}