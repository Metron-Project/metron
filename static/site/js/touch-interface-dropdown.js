document.addEventListener('DOMContentLoaded', function () {
    // check if touch device, return if not
    const isTouchDevice = matchMedia('(hover: none)').matches;

    if (!isTouchDevice) return;

    // Find all hoverable dropdowns and disable hover for them
    const dropdowns = document.querySelectorAll('.navbar-item.has-dropdown.is-hoverable');

    dropdowns.forEach(dropdown => {
        dropdown.classList.remove('is-hoverable');

        const link = dropdown.querySelector('.navbar-link');

        // Toggle dropdown on touch and close all other dropdowns
        link.addEventListener('click', function (event) {
            event.preventDefault();

            dropdowns.forEach(d => {
                if (d !== dropdown) d.classList.remove('is-active');
            });

            dropdown.classList.toggle('is-active');
        });
    });

    // If touched anywhere else, close all dropdowns
    document.addEventListener('click', function (event) {
        if (!event.target.closest('.navbar-item.has-dropdown')) {
            dropdowns.forEach(d => d.classList.remove('is-active'));
        }
    });
});