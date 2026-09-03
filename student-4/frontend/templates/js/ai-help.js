/* =====================================================
   AI HELP
   The "🤖 AI Help" modal: opening/closing it and
   sending questions to the backend AI endpoint. Lives
   on users.html only. Depends on utils.js (escapeHtml).

   Frontend
       ↓
   Backend/API
       ↓
   Ollama
       ↓
   Qwen/Llama
       ↓
   Backend/API
       ↓
   Frontend
===================================================== */

function openAIHelp() {

    document
        .getElementById("aiQuestion")
        .value = "";

    document
        .getElementById("aiResponse")
        .textContent = "";

    document
        .getElementById("aiModal")
        .classList.remove("hidden");

}

function closeAIHelp() {

    document
        .getElementById("aiModal")
        .classList.add("hidden");

}

async function askAI() {

    const question =
        document
            .getElementById("aiQuestion")
            .value
            .trim();

    if (!question) {

        document
            .getElementById("aiResponse")
            .textContent =
                "Please enter a question.";

        return;

    }

    document
        .getElementById("aiResponse")
        .textContent =
            "🤖 AI is generating an explanation...";

    try {

        /*
         * Change this endpoint to match
         * your backend implementation.
         */

        const response =
            await fetch(
                `${API_BASE_URL}/users/help`,
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        question: question,

                        context:
                            "The user is currently using the User Management feature. Explain the requested user-management information clearly and simply."

                    })

                }
            );

        if (!response.ok) {

            throw new Error(
                "AI request failed"
            );

        }

        const data =
            await response.json();

        document
            .getElementById("aiResponse")
            .innerHTML = `
                <h4>AI Response</h4>
                <p>${escapeHtml(data.response || data.answer || "The AI did not return a response.")}</p>
            `;

    }
    catch (error) {

        document
            .getElementById("aiResponse")
            .innerHTML = `
                <h4>AI Response</h4>
                <p>Unable to connect to the AI service.</p>
            `;

        console.error(error);

    }

}

function userAIHelp(id) {

    openAIHelp();

    document
        .getElementById("aiQuestion")
        .value =
            `Please explain the information associated with user ID ${id}.`;

}
