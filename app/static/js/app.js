// SoulService front-end: small, plain JavaScript (no frameworks).

document.addEventListener("DOMContentLoaded", () => {
    setupConfirmForms();
    setupDemoButtons();
    setupListingForm();
});

// 1. "Are you sure?" before risky actions. Any <form data-confirm="..."> asks first.
function setupConfirmForms() {
    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!window.confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });
}

// 2. Login page: the "Use" buttons fill in the demo email address.
function setupDemoButtons() {
    document.querySelectorAll("[data-fill-email]").forEach((button) => {
        button.addEventListener("click", () => {
            document.getElementById("email").value = button.dataset.fillEmail;
            document.getElementById("password").focus();
        });
    });
}

// 3. "Post food" page: build an XML document and send it to the API.
function setupListingForm() {
    const form = document.getElementById("listing-form");
    if (!form) return;

    const errorBox = document.getElementById("form-error");
    const submitButton = document.getElementById("submit-btn");

    // Helpful defaults: prepared now, pickup deadline in 3 hours.
    const now = new Date();
    const later = new Date(now.getTime() + 3 * 60 * 60 * 1000);
    form.prepared_at.value = toInputValue(now);
    form.pickup_deadline.value = toInputValue(later);
    form.pickup_deadline.min = toInputValue(now);

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        hideError();

        const problem = checkForm(form);
        if (problem) {
            showError(problem.message, problem.field);
            return;
        }

        submitButton.disabled = true;
        submitButton.textContent = "Posting…";

        try {
            const response = await fetch("/api/v1/listings", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/xml",
                    "X-CSRF-Token": form.dataset.csrf,
                },
                body: buildListingXml(form),
            });

            const reply = new DOMParser().parseFromString(await response.text(), "application/xml");
            const status = reply.querySelector("response > status")?.textContent;

            if (response.status === 201 && status === "success") {
                window.location.href = "/dashboard"; // the server already queued a success message
                return;
            }
            if (response.status === 401) {
                window.location.href = "/login?next=/food/new";
                return;
            }
            const details = reply.querySelector("error > details")?.textContent;
            showError(details || "Something went wrong. Please try again.");
        } catch (networkError) {
            showError("Could not reach the server. Check your connection and try again.");
        }

        submitButton.disabled = false;
        submitButton.textContent = "Post food";
    });

    function showError(message, field) {
        errorBox.textContent = message;
        errorBox.hidden = false;
        errorBox.focus();
        if (field) field.setAttribute("aria-invalid", "true");
    }

    function hideError() {
        errorBox.hidden = true;
        form.querySelectorAll("[aria-invalid]").forEach((el) => el.removeAttribute("aria-invalid"));
    }
}

// Checks the form before sending. Returns {message, field} for the first problem, else null.
function checkForm(form) {
    const required = [
        ["food_name", "Please enter the food name."],
        ["description", "Please add a short description."],
        ["quantity", "Please enter the quantity."],
        ["pickup_location", "Please enter the pickup location."],
        ["prepared_at", "Please enter when the food was prepared."],
        ["pickup_deadline", "Please enter the pickup deadline."],
    ];
    for (const [name, message] of required) {
        if (!form[name].value.trim()) return { message, field: form[name] };
    }
    if (!(Number(form.quantity.value) >= 1) || !Number.isInteger(Number(form.quantity.value))) {
        return { message: "Quantity must be a whole number of at least 1.", field: form.quantity };
    }
    if (new Date(form.pickup_deadline.value) <= new Date(form.prepared_at.value)) {
        return { message: "The pickup deadline must be later than the preparation time.", field: form.pickup_deadline };
    }
    if (new Date(form.pickup_deadline.value) <= new Date()) {
        return { message: "The pickup deadline must be in the future.", field: form.pickup_deadline };
    }
    return null;
}

// Builds the <create_listing> XML described in docs/api-contract.md.
// Using the DOM (rather than gluing strings together) escapes special characters like & and <.
function buildListingXml(form) {
    const doc = document.implementation.createDocument(null, "create_listing");
    const root = doc.documentElement;

    const add = (parent, name, text) => {
        const element = doc.createElement(name);
        element.textContent = text;
        parent.appendChild(element);
        return element;
    };

    add(root, "food_name", form.food_name.value.trim());
    add(root, "description", form.description.value.trim());
    add(root, "quantity", String(Number(form.quantity.value)));
    add(root, "unit", form.unit.value);
    add(root, "prepared_at", withSeconds(form.prepared_at.value));
    add(root, "pickup_deadline", withSeconds(form.pickup_deadline.value));
    add(root, "pickup_location", form.pickup_location.value.trim());

    const dietary = add(root, "dietary_infos", "");
    form.querySelectorAll("input[name=dietary]:checked").forEach((box) => add(dietary, "dietary_info", box.value));

    const allergens = add(root, "allergens", "");
    form.querySelectorAll("input[name=allergens]:checked").forEach((box) => add(allergens, "allergen", box.value));

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(doc);
}

// "2026-11-04T18:30" -> "2026-11-04T18:30:00" (what xs:dateTime expects)
function withSeconds(value) {
    return value.length === 16 ? value + ":00" : value;
}

// Date -> "YYYY-MM-DDTHH:MM" in the user's local time, for <input type="datetime-local">
function toInputValue(date) {
    const pad = (n) => String(n).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
        `T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
