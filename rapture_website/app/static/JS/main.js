// main.js
function toggleProfileMenu() {
    var menu = document.getElementById("profile-menu");
    if (menu.style.display === "block") {
        menu.style.display = "none";
    } else {
        menu.style.display = "block";
    }
}

// Optional: Close the menu if clicking outside of it
window.onclick = function(event) {
    if (!event.target.matches('.profile-icon')) {
        var menu = document.getElementById("profile-menu");
        if (menu.style.display === "block") {
            menu.style.display = "none";
        }
    }
}
