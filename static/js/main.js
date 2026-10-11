const menuButton = document.querySelector(".menu-button");
const subjectStatusFilter = document.querySelector("[data-subject-status-filter]");
if (subjectStatusFilter) {
    subjectStatusFilter.addEventListener("change", () => {
        subjectStatusFilter.form.requestSubmit();
    });
}

const sessionDateFilter = document.querySelector("[data-session-date-filter]");
if (sessionDateFilter) {
    sessionDateFilter.addEventListener("change", () => {
        if (sessionDateFilter.value && sessionDateFilter.checkValidity()) {
            sessionDateFilter.form.requestSubmit();
        }
    });
}

const navLinks = document.querySelector(".nav-links");
const accountMenu = document.querySelector(".account-menu");

if (accountMenu && window.matchMedia("(hover: hover)").matches) {
    let closeTimer;
    accountMenu.addEventListener("mouseenter", () => window.clearTimeout(closeTimer));
    accountMenu.addEventListener("mouseleave", () => {
        closeTimer = window.setTimeout(() => {
            accountMenu.open = false;
        }, 250);
    });
}

if (menuButton && navLinks) {
    menuButton.addEventListener("click", () => {
        const isOpen = navLinks.classList.toggle("open");
        menuButton.setAttribute("aria-expanded", String(isOpen));
    });

    navLinks.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => {
            navLinks.classList.remove("open");
            menuButton.setAttribute("aria-expanded", "false");
        });
    });
}

const courseSelect = document.getElementById("course_id");
const semesterSelect = document.getElementById("semester_id");
const academicYearSelect = document.getElementById("student_academic_year");
const semesterNumberSelect = document.getElementById("student_semester_number");

if (courseSelect && academicYearSelect && semesterNumberSelect && semesterSelect) {
    const contexts = Array.from(semesterSelect.options)
        .filter((option) => option.value)
        .map((option) => ({
            id: option.value,
            courseId: option.dataset.courseId,
            academicYear: option.dataset.academicYear,
            semesterNumber: option.dataset.semesterNumber,
            sectionLabel: option.textContent.trim(),
        }));
    const initial = {
        academicYear: academicYearSelect.value,
        semesterNumber: semesterNumberSelect.value,
        semesterId: semesterSelect.value,
    };

    const replaceOptions = (select, placeholder, items, selectedValue) => {
        const uniqueItems = items.filter(
            (item, index, allItems) => allItems.findIndex((candidate) => candidate.value === item.value) === index
        );
        select.replaceChildren(new Option(placeholder, ""));
        uniqueItems.forEach((item) => select.add(new Option(item.label, item.value)));
        select.value = uniqueItems.some((item) => item.value === selectedValue)
            ? selectedValue
            : (uniqueItems[0]?.value || "");
    };

    const refreshSections = (preserveSelection = true) => {
        const matching = contexts.filter(
            (item) => item.courseId === courseSelect.value
                && item.academicYear === academicYearSelect.value
                && item.semesterNumber === semesterNumberSelect.value
        );
        replaceOptions(
            semesterSelect,
            "Select section",
            matching.map((item) => ({ value: item.id, label: item.sectionLabel })),
            preserveSelection ? initial.semesterId : ""
        );
    };

    const refreshSemesters = (preserveSelection = true) => {
        const matching = contexts.filter(
            (item) => item.courseId === courseSelect.value && item.academicYear === academicYearSelect.value
        );
        replaceOptions(
            semesterNumberSelect,
            "Select semester",
            matching.map((item) => ({ value: item.semesterNumber, label: `Semester ${item.semesterNumber}` })),
            preserveSelection ? initial.semesterNumber : ""
        );
        refreshSections(preserveSelection);
    };

    const refreshAcademicYears = (preserveSelection = true) => {
        const matching = contexts.filter((item) => item.courseId === courseSelect.value);
        replaceOptions(
            academicYearSelect,
            "Select academic year",
            matching.map((item) => ({ value: item.academicYear, label: item.academicYear })),
            preserveSelection ? initial.academicYear : ""
        );
        refreshSemesters(preserveSelection);
    };

    courseSelect.addEventListener("change", () => refreshAcademicYears(false));
    academicYearSelect.addEventListener("change", () => refreshSemesters(false));
    semesterNumberSelect.addEventListener("change", () => refreshSections(false));
    refreshAcademicYears(true);
}

const selectAllStudents = document.querySelector("[data-select-all-students]");
if (selectAllStudents) {
    const studentCheckboxes = Array.from(document.querySelectorAll('input[name="student_id"]'));
    selectAllStudents.addEventListener("change", () => {
        studentCheckboxes.forEach((checkbox) => {
            checkbox.checked = selectAllStudents.checked;
        });
    });
    studentCheckboxes.forEach((checkbox) => {
        checkbox.addEventListener("change", () => {
            selectAllStudents.checked = studentCheckboxes.every((item) => item.checked);
            selectAllStudents.indeterminate = studentCheckboxes.some((item) => item.checked)
                && !selectAllStudents.checked;
        });
    });
}

document.querySelectorAll("form[data-confirm-message], form[data-confirm-edit]").forEach((form) => {
    form.addEventListener("submit", (event) => {
        const message = form.dataset.confirmMessage || form.dataset.confirmEdit;
        if (message && !window.confirm(message)) event.preventDefault();
    });
});

const deleteDialog = document.getElementById("delayed-delete-dialog");
if (deleteDialog) {
    const deleteForm = document.getElementById("delayed-delete-form");
    const message = document.getElementById("delayed-delete-message");
    const phraseLabel = document.getElementById("delayed-delete-phrase");
    const confirmation = document.getElementById("delayed-delete-confirmation");
    const submit = document.getElementById("delayed-delete-submit");
    let countdownTimer;
    let delayComplete = false;
    let requiredPhrase = "";

    const updateDeleteState = () => {
        submit.disabled = !delayComplete || confirmation.value.trim().toUpperCase() !== requiredPhrase;
    };

    document.querySelectorAll("[data-delayed-delete]").forEach((button) => {
        button.addEventListener("click", () => {
            clearInterval(countdownTimer);
            requiredPhrase = button.dataset.phrase.toUpperCase();
            delayComplete = false;
            confirmation.value = "";
            deleteForm.action = button.dataset.url;
            message.textContent = button.dataset.message;
            phraseLabel.textContent = requiredPhrase;
            let seconds = 10;
            submit.textContent = `Delete in ${seconds} seconds`;
            updateDeleteState();
            deleteDialog.showModal();
            countdownTimer = setInterval(() => {
                seconds -= 1;
                if (seconds <= 0) {
                    clearInterval(countdownTimer);
                    delayComplete = true;
                    submit.textContent = "Permanently delete";
                    updateDeleteState();
                } else {
                    submit.textContent = `Delete in ${seconds} seconds`;
                }
            }, 1000);
        });
    });

    confirmation.addEventListener("input", updateDeleteState);
    deleteDialog.querySelector("[data-close-dialog]").addEventListener("click", () => {
        clearInterval(countdownTimer);
        deleteDialog.close();
    });
    deleteDialog.addEventListener("close", () => clearInterval(countdownTimer));
}
