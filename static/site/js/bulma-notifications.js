window.addEventListener("DOMContentLoaded", function() {
    const notifications = document.querySelectorAll(".notification");
    for (let i = 0; i < notifications.length; i++) {
        let button = notifications[i].querySelector("button.delete");

        button.onclick = function() {
            notifications[i].style.display = 'none';
        }
    }
});
