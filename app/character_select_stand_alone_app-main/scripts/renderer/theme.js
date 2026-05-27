export function setupThemeToggle() {
    const themeToggleButton = document.getElementById('global-settings-theme-toggle');
    if (!themeToggleButton) {
        console.error(CAT, '[applyTheme] Theme button or icon not found');
        return null;
    }

    const baseTheme = 'html/index.css'; 
    loadCSS(baseTheme, 'base-theme');    

    const savedTheme = globalThis.globalSettings.css_style || 'dark';
    applyTheme(savedTheme);

    themeToggleButton.addEventListener('click', () => {
        const currentTheme = globalThis.globalSettings.css_style;
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        applyTheme(newTheme);
        globalThis.globalSettings.css_style = newTheme;
    });

    return themeToggleButton;
}

export function applyTheme(theme) {
    const themeIcon = document.getElementById('global-settings-theme-icon');
    if (!themeIcon) {
        console.error(CAT, '[applyTheme] Theme button or icon not found');
        return null;
    }
    const baseTheme = 'html/index.css'; 
    loadCSS(baseTheme, 'base-theme');   
    
    const galleryDarkTheme = 'html/gallery_dark.css'; 
    const galleryLightTheme = 'html/gallery_light.css';     
    const lightTheme = 'html/index_light.css'; 
    const darkTheme = 'html/index_dark.css'; 

    if (theme === 'dark') {
        loadCSS(darkTheme, 'theme-style');
        loadCSS(galleryDarkTheme, 'gallery-theme');
        themeIcon.src = 'scripts/svg/sun.svg';
    } else {
        loadCSS(lightTheme, 'theme-style');
        loadCSS(galleryLightTheme, 'gallery-theme');
        themeIcon.src = 'scripts/svg/moon.svg';
    }
}

function loadCSS(href, id) {
    let link = document.getElementById(id);
    if (!link) {
        link = document.createElement('link');
        link.rel = 'stylesheet';
        link.id = id;
        document.head.appendChild(link);
    }
    link.href = href;
}
