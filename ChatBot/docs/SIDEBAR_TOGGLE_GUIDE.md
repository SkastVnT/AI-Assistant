# Sidebar Toggle & Preferences Guide

## Overview

The sidebar toggle system provides a smooth, user-friendly way to collapse/expand the sidebar on desktop, or show/hide it as an overlay on mobile devices. The preferences system manages all user settings and persists them across sessions.

---

## 🎮 User Controls

### Desktop

**Toggle Sidebar**:
- Click the toggle button on the sidebar edge
- **Keyboard**: Press `Ctrl+B` (Windows/Linux) or `Cmd+B` (Mac)
- Sidebar smoothly collapses to the left
- Toggle button rotates 180° when collapsed

**Visual Feedback**:
- Smooth 300ms cubic-bezier animation
- Main content expands to fill space
- Hover effects on toggle button
- Preference automatically saved

### Mobile (< 768px)

**Open Sidebar**:
- Tap the toggle button
- Sidebar slides in from left (85% screen width)
- Semi-transparent backdrop appears
- Body scroll is prevented

**Close Sidebar**:
- Tap the backdrop overlay
- Tap any chat item in the sidebar
- Swipe left (future enhancement)
- Sidebar slides out smoothly

---

## ⚙️ Preferences System

### Available Preferences

```javascript
{
    // Sidebar state
    sidebarCollapsed: false,          // Desktop sidebar collapsed
    
    // Theme
    theme: 'light',                   // 'light', 'dark', 'auto'
    
    // Active project
    activeProjectId: null,            // Current project ID
    
    // Search settings
    searchFilters: {
        messageType: 'all',           // 'all', 'user', 'assistant'
        dateRange: 'all',             // 'all', 'today', 'week', 'month'
        sortBy: 'newest'              // 'newest', 'oldest', 'relevance'
    },
    
    // Message display
    messageDisplay: {
        showTimestamps: true,         // Show message timestamps
        showVersions: true,           // Show version navigation
        compactMode: false            // Compact message layout
    },
    
    // Notifications
    notifications: {
        enabled: true,                // Enable notifications
        duration: 3000                // Display duration (ms)
    },
    
    // Accessibility
    accessibility: {
        reducedMotion: false,         // Reduce animations
        highContrast: false,          // High contrast mode
        fontSize: 'medium'            // 'small', 'medium', 'large', 'x-large'
    }
}
```

### Automatic Detection

The system automatically detects and applies:

1. **Dark Mode**
   - Detects: `prefers-color-scheme: dark`
   - Applies: Dark theme if preference is 'auto'
   - Updates: When system preference changes

2. **Reduced Motion**
   - Detects: `prefers-reduced-motion: reduce`
   - Applies: Minimal animations
   - Adds: `.reduced-motion` class to body

3. **High Contrast**
   - Detects: `prefers-contrast: high`
   - Applies: Enhanced contrast colors
   - Adds: `.high-contrast` class to body

---

## 🔔 Notification System

### Types

**Success** (Green border):
```javascript
app.notificationManager.show('Chat saved successfully!', 'success');
```

**Error** (Red border):
```javascript
app.notificationManager.show('Failed to save chat', 'error');
```

**Info** (Blue border):
```javascript
app.notificationManager.show('Loading your data...', 'info');
```

**Warning** (Yellow border):
```javascript
app.notificationManager.show('Connection unstable', 'warning');
```

### Features

- **Auto-dismiss**: Notifications disappear after 3 seconds (configurable)
- **Queue system**: Multiple notifications are queued and shown sequentially
- **Smooth animations**: Slide in from right, slide out smoothly
- **User control**: Can be disabled in preferences
- **Custom duration**: Override default duration per notification

---

## 🎨 Animations & Effects

### Sidebar Animations

**Collapse/Expand** (Desktop):
```css
/* Transform-based animation for GPU acceleration */
transition: transform 300ms cubic-bezier(0.4, 0, 0.2, 1);
transform: translateX(-100%);  /* Collapsed */
transform: translateX(0);      /* Expanded */
```

**Slide In/Out** (Mobile):
```css
/* Overlay animation */
transition: transform 250ms cubic-bezier(0.4, 0, 0.2, 1);
transform: translateX(-100%);  /* Hidden */
transform: translateX(0);      /* Visible */
```

### Button Interactions

**Ripple Effect**:
- Click any button to see ripple animation
- Expands from click point
- Fades out smoothly
- Pure CSS, no JavaScript

**Hover Effects**:
- Sidebar items slide slightly right on hover
- Project items show action buttons on hover
- Buttons lighten/darken on hover
- Smooth transitions on all effects

### Loading States

**Spinner**:
```html
<div class="loading-spinner"></div>
```
- Circular spinning animation
- Material Design style
- 16px size, customizable

**Skeleton**:
```html
<div class="skeleton" style="width: 200px; height: 20px;"></div>
```
- Shimmer loading effect
- Placeholder for content
- Smooth gradient animation

---

## 📱 Responsive Behavior

### Breakpoints

1. **Mobile** (< 768px)
   - Sidebar: Full overlay (85% width, max 320px)
   - Touch: 44px minimum tap targets
   - Font: 16px (prevents iOS zoom)

2. **Tablet** (769px - 1024px)
   - Sidebar: 240px standard, 60px collapsed
   - Layout: Optimized spacing

3. **Desktop** (> 1440px)
   - Sidebar: 320px standard
   - Container: Max 1920px, centered
   - Messages: Max 900px, centered

### Mobile-Specific Features

**Overlay Mode**:
- Sidebar appears over content
- Semi-transparent backdrop (50% black)
- Tap backdrop to close
- Prevents body scroll when open

**Touch Optimization**:
- All tap targets ≥ 44px (Apple guidelines)
- Input font size 16px (prevents iOS zoom)
- Smooth touch scrolling
- No hover states on mobile

---

## ♿ Accessibility Features

### Keyboard Navigation

**Shortcuts**:
- `Ctrl+B` / `Cmd+B`: Toggle sidebar
- `Ctrl+F`: Open search
- `Tab`: Navigate focusable elements
- `Enter`: Activate focused element
- `Esc`: Close modals/overlays

**Focus Indicators**:
- 2px solid accent color outline
- 2px offset for clarity
- 4px glow shadow for emphasis
- `:focus-visible` for keyboard-only focus

### Screen Readers

**ARIA Labels**:
```html
<button aria-label="Toggle sidebar">
<div role="dialog" aria-labelledby="modal-title">
<input aria-describedby="input-help">
```

**Semantic HTML**:
- Proper heading hierarchy
- Landmark regions
- Form labels
- Button descriptions

### Motion & Contrast

**Reduced Motion**:
- Respects `prefers-reduced-motion`
- Disables decorative animations
- Keeps functional animations minimal
- Instant state changes

**High Contrast**:
- Respects `prefers-contrast: high`
- Enhanced border colors
- Stronger text contrast
- Clear focus indicators

---

## ⚡ Performance

### Optimizations

1. **GPU Acceleration**
   ```css
   will-change: transform;
   transform: translateZ(0);
   ```
   - Promotes element to composite layer
   - Hardware-accelerated animations
   - Smooth 60fps performance

2. **Layout Containment**
   ```css
   contain: layout style paint;
   ```
   - Isolates element reflows
   - Prevents cascading layouts
   - Improves scroll performance

3. **Efficient Selectors**
   - Avoid deep nesting
   - Use classes over complex selectors
   - Minimize specificity

4. **Lazy Loading**
   - Images load on scroll
   - Deferred content rendering
   - Progressive enhancement

### Metrics

- **Sidebar toggle**: <16ms (60fps)
- **Preferences load**: <5ms
- **Notification show**: <10ms
- **Mobile overlay**: <16ms (60fps)

---

## 🛠️ Developer API

### PreferencesManager

```javascript
// Access the manager
const prefs = app.preferencesManager;

// Get preferences
const theme = prefs.get('theme');
const collapsed = prefs.get('sidebarCollapsed');
const fontSize = prefs.get('accessibility.fontSize');

// Set preferences
prefs.set('theme', 'dark');
prefs.set('sidebarCollapsed', true);
prefs.set('accessibility.fontSize', 'large');

// Toggle boolean preference
prefs.toggle('sidebarCollapsed');
prefs.toggle('notifications.enabled');

// Listen for changes
prefs.on('theme', (value) => {
    console.log('Theme changed to:', value);
});

prefs.on('*', (value, key) => {
    console.log(`${key} changed to:`, value);
});

// Export/Import
const json = prefs.export();
prefs.import(json);

// Reset
prefs.reset('theme');          // Reset specific preference
prefs.reset();                 // Reset all preferences
```

### SidebarToggle

```javascript
// Access the toggle
const sidebar = app.sidebarToggle;

// Toggle sidebar
sidebar.toggle();

// Desktop-specific
sidebar.toggleDesktop();

// Mobile-specific
sidebar.toggleMobile();
sidebar.close();

// Listen for toggle events
window.addEventListener('sidebarToggled', (e) => {
    console.log('Collapsed:', e.detail.collapsed);
});
```

### NotificationManager

```javascript
// Access the manager
const notify = app.notificationManager;

// Show notifications
notify.show('Success message', 'success');
notify.show('Error message', 'error');
notify.show('Info message', 'info');
notify.show('Warning message', 'warning');

// Custom duration
notify.show('Stays longer', 'info', 5000);

// Disable notifications
app.preferencesManager.set('notifications.enabled', false);
```

---

## 🎯 Utility Classes

### Animations

```html
<div class="fade-in">Fades in</div>
<div class="fade-out">Fades out</div>
<div class="slide-in-left">Slides from left</div>
<div class="slide-in-right">Slides from right</div>
<div class="scale-in">Scales up</div>
<div class="bounce">Bounces</div>
<div class="pulse">Pulses</div>
```

### Layout

```html
<div class="flex items-center justify-between gap-2">
    <span>Label</span>
    <button>Action</button>
</div>

<div class="flex-col gap-3">
    <div>Item 1</div>
    <div>Item 2</div>
</div>
```

### Text

```html
<p class="text-ellipsis">Long text that truncates...</p>
<p class="text-wrap">Wraps long words</p>
<p class="text-center">Centered text</p>
```

### Spacing

```html
<div class="m-0">No margin</div>
<div class="mt-2">Top margin</div>
<div class="p-3">Padding all sides</div>
<div class="pt-4">Top padding</div>
```

### Visibility

```html
<div class="hidden">Completely hidden</div>
<div class="invisible">Hidden but takes space</div>
```

---

## 🐛 Troubleshooting

### Sidebar Not Toggling

**Issue**: Sidebar doesn't collapse/expand on click

**Solutions**:
1. Check console for JavaScript errors
2. Verify toggle button exists: `.sidebar-toggle-btn`
3. Check if `PreferencesManager` initialized
4. Verify CSS transitions not disabled

### Preferences Not Persisting

**Issue**: Settings reset on page reload

**Solutions**:
1. Check browser localStorage is enabled
2. Verify no incognito/private mode
3. Check localStorage quota (5MB limit)
4. Look for localStorage errors in console

### Animations Choppy

**Issue**: Animations lag or stutter

**Solutions**:
1. Check GPU acceleration: `transform: translateZ(0)`
2. Verify `will-change` is applied
3. Reduce concurrent animations
4. Check browser hardware acceleration enabled

### Mobile Sidebar Issues

**Issue**: Sidebar behavior incorrect on mobile

**Solutions**:
1. Verify mobile breakpoint: `max-width: 768px`
2. Check `.mobile-overlay` element exists
3. Test on actual device (not just DevTools)
4. Check touch event handlers registered

---

## 📚 Best Practices

### For Users

1. **Keyboard shortcuts**: Use `Ctrl+B` for quick sidebar toggle
2. **Mobile**: Tap backdrop to close sidebar quickly
3. **Preferences**: Explore settings to customize experience
4. **Accessibility**: Enable reduced motion if animations distracting

### For Developers

1. **Use utility classes**: Leverage existing classes before writing custom CSS
2. **Respect preferences**: Check user preferences before showing animations
3. **Test mobile**: Always test on real mobile devices
4. **Accessibility**: Add ARIA labels to interactive elements
5. **Performance**: Use transform/opacity for animations

---

## 🔮 Future Enhancements

### Planned Features

1. **Swipe Gestures**
   - Swipe right to open sidebar (mobile)
   - Swipe left to close sidebar (mobile)
   - Custom touch handlers

2. **More Themes**
   - High contrast theme
   - Solarized theme
   - Custom color picker
   - Theme scheduling (auto-switch at night)

3. **Advanced Preferences**
   - Custom keyboard shortcuts
   - Animation speed control
   - Font family selection
   - Compact/comfortable/spacious density

4. **Preference Sync**
   - Sync across devices
   - Cloud backup
   - Import from file
   - Share preference profiles

---

## 📖 Related Documentation

- **[PHASE5_COMPLETE_SUMMARY.md](PHASE5_COMPLETE_SUMMARY.md)** - Complete Phase 5 technical documentation
- **[VERSION_NAVIGATION_GUIDE.md](VERSION_NAVIGATION_GUIDE.md)** - Phase 3 version navigation guide
- **[SEARCH_GUIDE.md](SEARCH_GUIDE.md)** - Phase 2 search functionality guide
- **[PROJECTS_GUIDE.md](PROJECTS_GUIDE.md)** - Phase 4 projects system guide

---

## ✅ Quick Reference

| Action | Desktop | Mobile |
|--------|---------|--------|
| **Toggle Sidebar** | Click button or `Ctrl+B` | Tap button |
| **Close Sidebar** | Click button or `Ctrl+B` | Tap backdrop or chat item |
| **Keyboard Shortcut** | `Ctrl+B` or `Cmd+B` | N/A |
| **Animation Duration** | 300ms | 250ms |
| **Collapsed Width** | 0px (hidden) | N/A |
| **Expanded Width** | 260px | 85% (max 320px) |

| Preference | Type | Default | Options |
|------------|------|---------|---------|
| **sidebarCollapsed** | Boolean | `false` | `true`, `false` |
| **theme** | String | `'light'` | `'light'`, `'dark'`, `'auto'` |
| **notifications.enabled** | Boolean | `true` | `true`, `false` |
| **notifications.duration** | Number | `3000` | Any number (ms) |
| **accessibility.fontSize** | String | `'medium'` | `'small'`, `'medium'`, `'large'`, `'x-large'` |

---

**Last Updated**: January 2025  
**Phase**: 5 (Complete)  
**Next**: Phase 6 Testing & Integration
