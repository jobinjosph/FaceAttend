const menuButton = document.querySelector(".menu-button");
const navLinks = document.querySelector(".nav-links");

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

const year = document.getElementById("current-year");
if (year) {
    year.textContent = new Date().getFullYear();
}

const courseSelect = document.getElementById("course_id");
const semesterSelect = document.getElementById("semester_id");

const courseCombobox = document.querySelector("[data-course-combobox]");

if (courseCombobox && courseSelect) {
    const trigger = courseCombobox.querySelector(".course-combobox-button");
    const selectedLabel = courseCombobox.querySelector("#course_selected_label");
    const menu = courseCombobox.querySelector(".course-combobox-menu");
    const search = courseCombobox.querySelector(".course-search");
    const options = Array.from(courseCombobox.querySelectorAll(".course-option"));
    const noResults = courseCombobox.querySelector(".course-no-results");

    const closeMenu = () => {
        menu.hidden = true;
        trigger.setAttribute("aria-expanded", "false");
        search.value = "";
        options.forEach((option) => {
            option.hidden = false;
        });
        noResults.hidden = true;
    };

    const openMenu = () => {
        menu.hidden = false;
        trigger.setAttribute("aria-expanded", "true");
        search.focus();
    };

    trigger.addEventListener("click", () => {
        if (menu.hidden) openMenu();
        else closeMenu();
    });

    search.addEventListener("input", () => {
        const query = search.value.trim().toLowerCase();
        let visibleCount = 0;

        options.forEach((option) => {
            const visible = option.dataset.label.toLowerCase().includes(query);
            option.hidden = !visible;
            if (visible) visibleCount += 1;
        });

        noResults.hidden = visibleCount !== 0;
    });

    search.addEventListener("keydown", (event) => {
        const visibleOptions = options.filter((option) => !option.hidden);

        if (event.key === "Enter" && visibleOptions.length > 0) {
            event.preventDefault();
            visibleOptions[0].click();
        }

        if (event.key === "ArrowDown" && visibleOptions.length > 0) {
            event.preventDefault();
            visibleOptions[0].focus();
        }
    });

    options.forEach((option) => {
        option.addEventListener("click", () => {
            courseSelect.value = option.dataset.value;
            selectedLabel.textContent = option.dataset.label;
            options.forEach((item) => {
                item.setAttribute("aria-selected", String(item === option));
            });
            courseSelect.dispatchEvent(new Event("change", { bubbles: true }));
            closeMenu();
            trigger.focus();
        });

        option.addEventListener("keydown", (event) => {
            const visibleOptions = options.filter((item) => !item.hidden);
            const currentIndex = visibleOptions.indexOf(option);

            if (event.key === "ArrowDown") {
                event.preventDefault();
                visibleOptions[Math.min(currentIndex + 1, visibleOptions.length - 1)].focus();
            }

            if (event.key === "ArrowUp") {
                event.preventDefault();
                if (currentIndex === 0) search.focus();
                else visibleOptions[currentIndex - 1].focus();
            }
        });
    });

    document.addEventListener("click", (event) => {
        if (!courseCombobox.contains(event.target)) closeMenu();
    });

    courseCombobox.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeMenu();
            trigger.focus();
        }
    });
}

if (courseSelect && semesterSelect) {
    const placeholderOption = semesterSelect.options[0].cloneNode(true);
    const semesterOptions = Array.from(semesterSelect.options)
        .filter((option) => option.value)
        .map((option) => option.cloneNode(true));

    const filterSemesters = (resetSelection = false) => {
        const selectedCourse = courseSelect.value;
        const selectedSemester = resetSelection ? "" : semesterSelect.value;

        semesterSelect.replaceChildren(placeholderOption.cloneNode(true));

        semesterOptions
            .filter((option) => option.dataset.courseId === selectedCourse)
            .forEach((option) => {
                const visibleOption = option.cloneNode(true);
                visibleOption.selected = visibleOption.value === selectedSemester;
                semesterSelect.appendChild(visibleOption);
            });
    };

    courseSelect.addEventListener("change", () => filterSemesters(true));
    filterSemesters();
}
