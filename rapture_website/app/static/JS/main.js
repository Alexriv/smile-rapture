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


function toggleMenu() {
    const navLinks = document.querySelector('.nav-links');
    navLinks.classList.toggle('active');
}

function toggleProfileMenu() {
    const profileMenu = document.getElementById('profile-menu');
    profileMenu.classList.toggle('active');
}
