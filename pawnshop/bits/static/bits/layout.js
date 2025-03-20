// Toggle dropdown menu for profile
document.querySelector('.profile-pic').addEventListener('click', function(e) {
    e.stopPropagation(); // Prevent event from bubbling up
    document.querySelector('.dropdown-menu').classList.toggle('active');
});

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    if (!event.target.closest('.profile-container')) {
        document.querySelector('.dropdown-menu').classList.remove('active');
    }
});

// Animated search functionality
const searchContainer = document.getElementById('searchContainer');
const searchIcon = document.getElementById('searchIcon');
const searchInput = document.getElementById('searchInput');
const cancelSearch = document.getElementById('cancelSearch');
const logo = document.querySelector('.logo');

searchIcon.addEventListener('click', function() {
    searchContainer.classList.add('expanded');
    setTimeout(() => {
        searchInput.focus();
    }, 100);
});

cancelSearch.addEventListener('click', function(e) {
    e.preventDefault();
    searchContainer.classList.remove('expanded');
    searchInput.value = '';
});

// Close search when clicking outside
document.addEventListener('click', function(event) {
    if (!searchContainer.contains(event.target) && searchContainer.classList.contains('expanded')) {
        searchContainer.classList.remove('expanded');
    }
});

// Message notification system
document.addEventListener('DOMContentLoaded', function() {
    // Message close functionality
    const messages = document.querySelectorAll('.message');
    
    messages.forEach(message => {
        // Auto-dismiss after 2 seconds
        setTimeout(() => {
            if (message && message.parentNode) {
                message.classList.add('fade-out');
                setTimeout(() => {
                    if (message && message.parentNode) {
                        message.parentNode.removeChild(message);
                    }
                }, 300);
            }
        }, 2000);
        
        // Close button functionality
        const closeBtn = message.querySelector('.message-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function(e) {
                e.stopPropagation(); // Prevent event from bubbling
                message.classList.add('fade-out');
                setTimeout(() => {
                    if (message && message.parentNode) {
                        message.parentNode.removeChild(message);
                    }
                }, 300);
            });
        }
    });
});

// Category dropdown functionality
const desktopCategoryBtn = document.getElementById('desktopCategoryBtn');
const mobileCategoryBtn = document.getElementById('mobileCategoryBtn');
const desktopCategoryDropdown = document.getElementById('desktopCategoryDropdown');
const mobileCategoryDropdown = document.getElementById('mobileCategoryDropdown');

function toggleDropdown(dropdown) {
    dropdown.classList.toggle('show');
}

desktopCategoryBtn.addEventListener('click', function(e) {
    e.preventDefault();
    toggleDropdown(desktopCategoryDropdown);
});

mobileCategoryBtn.addEventListener('click', function(e) {
    e.preventDefault();
    toggleDropdown(mobileCategoryDropdown);
});

// Close dropdowns when clicking outside
document.addEventListener('click', function(event) {
    if (!event.target.matches('.category-btn') && !event.target.closest('.category-dropdown')) {
        const dropdowns = document.getElementsByClassName('category-dropdown');
        for (let i = 0; i < dropdowns.length; i++) {
            if (dropdowns[i].classList.contains('show')) {
                dropdowns[i].classList.remove('show');
            }
        }
    }
});
