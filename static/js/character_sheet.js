document.addEventListener("DOMContentLoaded", () => {
    const reactionCheckboxes = document.querySelectorAll("#reactions .checkbox-box");
    const maxReactions = 3;

    reactionCheckboxes.forEach(cb => {
        cb.addEventListener("change", () => {
            const checked = document.querySelectorAll("#reactions .checkbox-box:checked").length;

            if (checked >= maxReactions) {
                reactionCheckboxes.forEach(c => {
                    if (!c.checked) c.disabled = true;
                });
            } else {
                reactionCheckboxes.forEach(c => c.disabled = false);
            }
        });
    });
});