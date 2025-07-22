// Clean navigation and minimal UI interactions

(function () {
  const hamburger = document.getElementById('hamburger');
  const drawer = document.getElementById('drawer');
  const overlay = document.getElementById('drawer-overlay');

  // Toggle navigation drawer
  function toggleDrawer() {
    const isOpen = drawer.classList.contains('open');
    
    drawer.classList.toggle('open');
    overlay.classList.toggle('open');
    hamburger.classList.toggle('open');
    
    // Prevent body scroll when drawer is open
    document.body.style.overflow = isOpen ? '' : 'hidden';
  }

  // Close drawer
  function closeDrawer() {
    drawer.classList.remove('open');
    overlay.classList.remove('open');
    hamburger.classList.remove('open');
    document.body.style.overflow = '';
  }

  if (hamburger && drawer && overlay) {
    hamburger.addEventListener('click', toggleDrawer);
    overlay.addEventListener('click', closeDrawer);
    
    // Close drawer on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && drawer.classList.contains('open')) {
        closeDrawer();
      }
    });
    
    // Close drawer when clicking nav links
    drawer.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', closeDrawer);
    });
  }

  // Simple page fade-in without anime.js dependency
  window.addEventListener('load', () => {
    document.querySelectorAll('.fade-in').forEach((el, i) => {
      // Small staggered delay for multiple elements
      setTimeout(() => {
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
      }, i * 50);
    });
  });

  // Enhanced accessibility
  document.addEventListener('DOMContentLoaded', () => {
    // Add focus trap for drawer when open
    const focusableElements = drawer.querySelectorAll(
      'a[href], button, textarea, input, select'
    );
    
    if (focusableElements.length > 0) {
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      
      drawer.addEventListener('keydown', (e) => {
        if (e.key === 'Tab' && drawer.classList.contains('open')) {
          if (e.shiftKey) {
            if (document.activeElement === firstElement) {
              lastElement.focus();
              e.preventDefault();
            }
          } else {
            if (document.activeElement === lastElement) {
              firstElement.focus();
              e.preventDefault();
            }
          }
        }
      });
    }
  });
})();
