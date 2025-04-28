// Enhanced layout.js with better mobile support and smoother animations

document.addEventListener('DOMContentLoaded', function() {
    // Profile dropdown functionality
    const profilePic = document.querySelector('.profile-pic');
    const dropdownMenu = document.querySelector('.dropdown-menu');
    
    if (profilePic && dropdownMenu) {
        profilePic.addEventListener('click', function(e) {
            e.stopPropagation();
            dropdownMenu.classList.toggle('active');
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(event) {
            if (!event.target.closest('.profile-container') && dropdownMenu.classList.contains('active')) {
                dropdownMenu.classList.remove('active');
            }
        });
    }
    
    // Enhanced mobile search functionality
    const searchContainer = document.getElementById('searchContainer');
    const searchIcon = document.getElementById('searchIcon');
    const searchInput = document.getElementById('searchInput');
    const searchForm = document.getElementById('searchForm');
    const cancelSearch = document.getElementById('cancelSearch');
    
    if (searchIcon && searchContainer) {
        searchIcon.addEventListener('click', function() {
            searchContainer.classList.add('expanded');
            // Delay focus to allow animation to complete
            setTimeout(() => {
                if (searchInput) searchInput.focus();
            }, 100);
        });
    }
    
    if (cancelSearch && searchContainer) {
        cancelSearch.addEventListener('click', function(e) {
            e.preventDefault();
            searchContainer.classList.remove('expanded');
            if (searchInput) searchInput.value = '';
        });
    }
    
    // Close search when clicking outside
    document.addEventListener('click', function(event) {
        if (searchContainer && 
            !searchContainer.contains(event.target) && 
            searchContainer.classList.contains('expanded')) {
            searchContainer.classList.remove('expanded');
        }
    });
    
    // Add form submit event for search (mobile)
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            if (searchInput && searchInput.value.trim() === '') {
                e.preventDefault();
                searchInput.focus();
            }
        });
    }
    
    // Message notification system
    const messages = document.querySelectorAll('.message');
    
    messages.forEach(message => {
        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            if (message && message.parentNode) {
                message.classList.add('fade-out');
                setTimeout(() => {
                    if (message && message.parentNode) {
                        message.parentNode.removeChild(message);
                    }
                }, 300);
            }
        }, 3000);
        
        // Close button functionality
        const closeBtn = message.querySelector('.message-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                message.classList.add('fade-out');
                setTimeout(() => {
                    if (message && message.parentNode) {
                        message.parentNode.removeChild(message);
                    }
                }, 300);
            });
        }
    });
    
    // Campus dropdown functionalities
    // Desktop campus dropdown
    const desktopCampusBtn = document.querySelector('.campus-filter-container .campus-btn');
    if (desktopCampusBtn) {
        desktopCampusBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            const menu = this.nextElementSibling;
            menu.classList.toggle('show');
        });
    }
    
    // Mobile campus dropdown
    const mobileCampusBtn = document.querySelector('.mobile-campus-btn');
    if (mobileCampusBtn) {
        mobileCampusBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            const menu = this.nextElementSibling;
            menu.classList.toggle('show');
        });
    }
    
    // Close campus menus when clicking outside
    document.addEventListener('click', function(e) {
        const campusMenus = document.querySelectorAll('.campus-menu');
        campusMenus.forEach(menu => {
            if (menu.classList.contains('show') && !menu.parentNode.contains(e.target)) {
                menu.classList.remove('show');
            }
        });
    });
    
    // Mobile navigation active state
    const currentPath = window.location.pathname;
    const mobileNavLinks = document.querySelectorAll('.mobile-nav a');
    
    mobileNavLinks.forEach(link => {
        const linkPath = link.getAttribute('href');
        if (linkPath === currentPath || (currentPath.includes('/home') && linkPath === '/')) {
            link.classList.add('active');
        }
    });
    
    // Add smooth scrolling to the top for page navigation
    document.querySelectorAll('.pagination a').forEach(link => {
        link.addEventListener('click', function(e) {
            // Don't use smooth scroll if user prefers reduced motion
            if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                e.preventDefault();
                const href = this.getAttribute('href');
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
                
                // Navigate to the page after scroll animation
                setTimeout(() => {
                    window.location.href = href;
                }, 500);
            }
        });
    });
    
    // Add touch feedback to clickable elements on mobile
    if ('ontouchstart' in window) {
        const touchElements = document.querySelectorAll('button, .mobile-nav a, .item-card, .page-item a');
        
        touchElements.forEach(el => {
            el.addEventListener('touchstart', function() {
                this.classList.add('touch-active');
            }, {passive: true});
            
            el.addEventListener('touchend', function() {
                this.classList.remove('touch-active');
            }, {passive: true});
            
            el.addEventListener('touchcancel', function() {
                this.classList.remove('touch-active');
            }, {passive: true});
        });
    }
});