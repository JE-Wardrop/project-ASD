/* =====================================================
   USERS
   All user CRUD, table rendering, search/filter, and
   the create/edit modal. Lives on users.html only.
   Depends on utils.js (escapeHtml).
===================================================== */

/* -----------------------------------------------------
   LOAD + DISPLAY
----------------------------------------------------- */

async function loadUsers() {

    const table =
        document.getElementById("userTable");

    table.innerHTML = `
        <tr>
            <td colspan="6" style="text-align:center;">
                Loading users...
            </td>
        </tr>
    `;

    try {

        /*
         * GET = READ
         */

        const response =
            await fetch(`${API_BASE_URL}/users`);
            console.log (response)
        if (!response.ok) {

            throw new Error(
                "Unable to retrieve users"
            );

        }

        const users =
            await response.json();

        displayUsers(users);

    }
    catch (error) {

        table.innerHTML = `
            <tr>
                <td
                    colspan="6"
                    style="text-align:center;">

                    Unable to load users.

                </td>
            </tr>
        `;

        console.error(error);

    }

}

function displayUsers(users) {

    const table =
        document.getElementById("userTable");

    if (!users || users.length === 0) {

        table.innerHTML = `
            <tr>
                <td colspan="6" style="text-align:center;">
                    No users found.
                </td>
            </tr>
        `;

        return;
    }

    table.innerHTML =
        users.map(user => `

            <tr>

                <td>
                    ${escapeHtml(user.user_id)}
                </td>

                <td>
                    ${escapeHtml(user.username)}
                </td>

                <td>
                    ${escapeHtml(user.email)}
                </td>

                <td>
                    <span class="pill">
                        ${escapeHtml(user.role)}
                    </span>
                </td>

                <td>
                    ${escapeHtml(user.created_at || "-")}
                </td>

                <td>

                    <div class="action-buttons">

                        <button
                            class="icon-button"
                            onclick="editUser(${user.user_id})">

                            ✏️

                        </button>

                        <button
                            class="icon-button"
                            onclick="deleteUser(${user.user_id})">

                            🗑️

                        </button>

                        <button
                            class="icon-button"
                            onclick="userAIHelp(${user.user_id})">

                            🤖

                        </button>

                    </div>

                </td>

            </tr>

        `).join("");

}

/* -----------------------------------------------------
   CREATE
----------------------------------------------------- */

function openCreateUser() {

    document
        .getElementById("userModalTitle")
        .textContent = "Create User";

    document
        .getElementById("userForm")
        .reset();

    document
        .getElementById("editUserId")
        .value = "";

    document
        .getElementById("password")
        .required = true;

    document
        .getElementById("userModal")
        .classList.remove("hidden");

}

/* -----------------------------------------------------
   EDIT
----------------------------------------------------- */

async function editUser(id) {

    try {

        /*
         * GET one user
         */

        const response =
            await fetch(`${API_BASE_URL}/users/${id}`);

        if (!response.ok) {

            throw new Error(
                "Unable to retrieve user"
            );

        }

        const user =
            await response.json();

        document
            .getElementById("userModalTitle")
            .textContent = "Edit User";

        document
            .getElementById("editUserId")
            .value = user.user_id;

        document
            .getElementById("username")
            .value = user.username;

        document
            .getElementById("email")
            .value = user.email;

        document
            .getElementById("role")
            .value = user.role;

        /*
         * Password is optional during editing.
         */

        document
            .getElementById("password")
            .value = "";

        document
            .getElementById("password")
            .required = false;

        document
            .getElementById("userModal")
            .classList.remove("hidden");

    }
    catch (error) {

        showUserMessage(
            "Unable to retrieve user.",
            "error"
        );

    }

}

/* -----------------------------------------------------
   CREATE / UPDATE SUBMIT
----------------------------------------------------- */

document
    .getElementById("userForm")
    .addEventListener("submit", async function(event) {

        event.preventDefault();

        const id =
            document.getElementById("editUserId").value;

        const user = {

            username:
                document.getElementById("username").value,

            email:
                document.getElementById("email").value,

            password:
                document.getElementById("password").value,

            role:
                document.getElementById("role").value

        };

        const editing =
            id !== "";

        const url =
            editing
                ? `${API_BASE_URL}/users/${id}`
                : `${API_BASE_URL}/users`;

        const method =
            editing
                ? "PUT"
                : "POST";

        try {

            /*
             * POST = CREATE
             * PUT  = UPDATE
             */

            const response =
                await fetch(url, {

                    method: method,

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify(user)

                });

            if (!response.ok) {

                throw new Error(
                    "Unable to save user"
                );

            }

            closeUserModal();

            showUserMessage(

                editing
                    ? "User updated successfully."
                    : "User created successfully.",

                "success"

            );

            loadUsers();

        }
        catch (error) {

            showUserMessage(
                "Unable to save user.",
                "error"
            );

        }

    });

/* -----------------------------------------------------
   DELETE
----------------------------------------------------- */

async function deleteUser(id) {

    const confirmed =
        confirm(
            "Are you sure you want to delete this user?"
        );

    if (!confirmed) {
        return;
    }

    try {

        /*
         * DELETE = DELETE
         */

        const response =
            await fetch(
                `${API_BASE_URL}/users/${id}`,
                {
                    method: "DELETE"
                }
            );

        if (!response.ok) {

            throw new Error(
                "Unable to delete user"
            );

        }

        showUserMessage(
            "User deleted successfully.",
            "success"
        );

        loadUsers();

    }
    catch (error) {

        showUserMessage(
            "Unable to delete user.",
            "error"
        );

    }

}

/* -----------------------------------------------------
   SEARCH / FILTER
----------------------------------------------------- */

function filterUsers() {

    const search =
        document
            .getElementById("searchUsers")
            .value
            .toLowerCase();

    const rows =
        document.querySelectorAll(
            "#userTable tr"
        );

    rows.forEach(row => {

        const text =
            row.textContent.toLowerCase();

        row.style.display =
            text.includes(search)
                ? ""
                : "none";

    });

}

/* -----------------------------------------------------
   MODAL + MESSAGES
----------------------------------------------------- */

function closeUserModal() {

    document
        .getElementById("userModal")
        .classList.add("hidden");

}

function showUserMessage(message, type) {

    const element =
        document.getElementById("userMessage");

    const alertClass =
        type === "success" ? "alert-info" : "alert-error";

    element.innerHTML = `
        <div class="alert ${alertClass}">
            ${escapeHtml(message)}
        </div>
    `;

    setTimeout(() => {

        element.innerHTML = "";

    }, 3000);

}

/* -----------------------------------------------------
   INITIAL LOAD
   users.html is a standalone page now, so it loads its
   own data as soon as its scripts run (auth-guard.js
   has already confirmed the session by this point).
----------------------------------------------------- */

loadUsers();
