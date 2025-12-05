# CodeMirror Text Editor

A basic web-based text editor built with [CodeMirror 6](https://codemirror.net/).

## Features

- 🎨 **Syntax Highlighting** - Support for JavaScript, HTML, CSS, JSON, Markdown, and Python
- 🌓 **Dark/Light Theme** - Toggle between light and dark themes
- 📂 **File Operations** - Open and save files
- 📊 **Status Bar** - Shows line count, character count, and cursor position
- ⌨️ **Keyboard Shortcuts** - `Ctrl+S` to save
- 📱 **Responsive Design** - Works on desktop and mobile devices

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) (version 16 or higher)
- npm (comes with Node.js)

### Installation

1. Navigate to the project directory:
   ```bash
   cd test_project
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Build the editor:
   ```bash
   npm run build
   ```

4. Start a local server:
   ```bash
   npm start
   ```

5. Open your browser and go to `http://localhost:3000`

### Development

For development with auto-rebuild on changes:

```bash
npm run dev
```

Then in another terminal, start the server:

```bash
npm start
```

## Project Structure

```
test_project/
├── dist/                  # Built files (generated)
│   └── editor.bundle.js   # Bundled JavaScript
├── src/
│   └── editor.js          # Main editor code
├── index.html             # HTML page
├── styles.css             # Styles
├── package.json           # Dependencies and scripts
├── rollup.config.js       # Rollup bundler configuration
└── README.md              # This file
```

## Supported Languages

- JavaScript
- HTML
- CSS
- JSON
- Markdown
- Python
- Plain Text

## Keyboard Shortcuts

- `Ctrl+S` / `Cmd+S` - Save document
- `Ctrl+Z` / `Cmd+Z` - Undo
- `Ctrl+Shift+Z` / `Cmd+Shift+Z` - Redo
- `Ctrl+F` / `Cmd+F` - Find
- `Ctrl+H` / `Cmd+H` - Find and Replace
- `Ctrl+/` / `Cmd+/` - Toggle comment

## License

MIT
