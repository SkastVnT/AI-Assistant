This folder should contain icon files for the browser extension.

Since we can't generate PNG files directly, you have two options:

1. **Use any 16x16, 48x48, and 128x128 PNG icons** and place them here as:
   - icon16.png
   - icon48.png  
   - icon128.png

2. **Generate them from SVG** — Create an SVG with a robot/AI icon and convert to PNG:
   ```
   <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
     <rect width="128" height="128" rx="24" fill="#667eea"/>
     <text x="64" y="88" font-size="72" text-anchor="middle" fill="white">🤖</text>
   </svg>
   ```

3. **Quick workaround**: The extension will work without icons — Chrome will show default icons.
