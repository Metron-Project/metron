window.addEventListener("DOMContentLoaded", function() {
    const upload_fields = document.querySelectorAll("div.file.has-name");
    for (let i = 0; i < upload_fields.length; i++) {
        let input = upload_fields[i].querySelector("input.file-input");
        let filename = upload_fields[i].querySelector("span.file-name");

        input.onchange = function() {
            filename.textContent = input.files[0].name;
        }
    }
});
