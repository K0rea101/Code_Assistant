import { EditorView, basicSetup } from 'codemirror';
import { EditorState, Compartment, StateEffect, StateField } from '@codemirror/state';
import { keymap, Decoration } from '@codemirror/view';
import { javascript } from '@codemirror/lang-javascript';
import { html } from '@codemirror/lang-html';
import { css } from '@codemirror/lang-css';
import { json } from '@codemirror/lang-json';
import { markdown } from '@codemirror/lang-markdown';
import { python } from '@codemirror/lang-python';
import { oneDark } from '@codemirror/theme-one-dark';

// Compartments for dynamic configuration
const languageConf = new Compartment();
const themeConf = new Compartment();

// ----- Inline AI completion support -----

const completionEffect = StateEffect.define();

const completionField = StateField.define({
  create() {
    return null;
  },
  update(value, tr) {
    for (const e of tr.effects) {
      if (e.is(completionEffect)) return e.value;
    }
    // Clear completion only on actual document changes
    if (tr.docChanged) return null;
    return value;
  },
  provide: (field) =>
    EditorView.decorations.from(field, (completion) => {
      if (!completion || !completion.text) return Decoration.none;
      return completion.decorations;
    })
});

let currentCompletion = null;
let completionTimer = null;
let abortController = null;
const COMPLETION_DELAY_MS = 300;
const COMPLETION_MIN_CONFIDENCE = 0.2;
const MIN_CHARS_FOR_COMPLETION = 2;

async function fetchAICompletion(view, lastChar) {
  try {
    const content = view.state.doc.toString();
    const cursor = view.state.selection.main.head;

    // Don't fetch if content is too short
    if (content.length < MIN_CHARS_FOR_COMPLETION) {
      currentCompletion = null;
      view.dispatch({ effects: completionEffect.of(null) });
      return;
    }

    // Cancel any pending request
    if (abortController) {
      abortController.abort();
    }
    abortController = new AbortController();

    const response = await fetch('http://localhost:8000/api/complete', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        content,
        cursor_position: cursor,
        language: currentLanguage || 'python',
        last_char: lastChar || ''
      }),
      signal: abortController.signal
    });

    if (!response.ok) {
      currentCompletion = null;
      view.dispatch({ effects: completionEffect.of(null) });
      return;
    }

    const data = await response.json();
    if (!data.triggered || !data.completion || data.confidence < COMPLETION_MIN_CONFIDENCE) {
      currentCompletion = null;
      view.dispatch({ effects: completionEffect.of(null) });
      return;
    }

    const pos = view.state.selection.main.head;
    const widget = Decoration.widget({
      widget: {
        toDOM() {
          const container = document.createElement('span');
          container.style.display = 'inline-flex';
          container.style.alignItems = 'center';
          container.style.gap = '6px';

          const ghost = document.createElement('span');
          ghost.textContent = data.completion;
          ghost.style.opacity = '0.5';
          ghost.style.color = '#999';
          ghost.style.fontStyle = 'italic';
          ghost.style.whiteSpace = 'pre';

          const btn = document.createElement('button');
          btn.textContent = '📋 Clipboard';
          btn.style.padding = '2px 6px';
          btn.style.fontSize = '11px';
          btn.style.borderRadius = '3px';
          btn.style.border = '1px solid #555';
          btn.style.background = '#333';
          btn.style.color = '#aaa';
          btn.style.cursor = 'pointer';
          btn.style.whiteSpace = 'nowrap';
          btn.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (window.CodeMirrorEditor && window.CodeMirrorEditor.acceptCompletion) {
              window.CodeMirrorEditor.acceptCompletion();
            }
          };

          container.appendChild(ghost);
          container.appendChild(btn);
          return container;
        },
        ignoreEvent() { return false; }
      },
      side: 1
    }).range(pos);

    currentCompletion = {
      text: data.completion,
      decorations: Decoration.set([widget])
    };
    view.dispatch({ effects: completionEffect.of(currentCompletion) });
  } catch (e) {
    if (e.name !== 'AbortError') {
      currentCompletion = null;
      view.dispatch({ effects: completionEffect.of(null) });
    }
  }
}

// Language configurations
const languages = {
  javascript: javascript(),
  html: html(),
  css: css(),
  json: json(),
  markdown: markdown(),
  python: python(),
  plaintext: []
};

// Theme configurations
const themes = {
  light: [],
  dark: oneDark
};

let currentTheme = 'light';
let currentLanguage = 'javascript';

// Create initial state
const initialDoc = `// Welcome to the CodeMirror Text Editor!
// Start typing your code here...

function greet(name) {
  return \`Hello, \${name}!\`;
}

console.log(greet("World"));
`;

// Create editor state
const startState = EditorState.create({
  doc: initialDoc,
  extensions: [
    basicSetup,
    languageConf.of(languages[currentLanguage]),
    themeConf.of(themes[currentTheme]),
    completionField,
    keymap.of([
      // Custom keybindings
      {
        key: 'Mod-s',
        run: (view) => {
          saveDocument(view);
          return true;
        }
      },

    ]),
    EditorView.updateListener.of((update) => {
      if (update.docChanged) {
        updateStatus(view);
        
        // Clear existing completion and timer
        if (currentCompletion) {
          view.dispatch({ effects: completionEffect.of(null) });
          currentCompletion = null;
        }
        if (completionTimer) {
          clearTimeout(completionTimer);
        }
        if (abortController) {
          abortController.abort();
        }
        
        const tr = update.transactions[0];
        const lastChar = tr && tr.newDoc
          ? tr.newDoc.sliceString(Math.max(0, tr.newDoc.length - 1))
          : '';
        completionTimer = setTimeout(() => {
          fetchAICompletion(update.view, lastChar);
        }, COMPLETION_DELAY_MS);
      }
    })
  ]
});

// Create editor view
const editorElement = document.getElementById('editor');
const view = new EditorView({
  state: startState,
  parent: editorElement
});

// Export functions for UI controls
window.CodeMirrorEditor = {
  // Change language
  setLanguage: function(lang) {
    if (languages[lang]) {
      currentLanguage = lang;
      view.dispatch({
        effects: languageConf.reconfigure(languages[lang])
      });
      updateStatus(view);
    }
  },

  // Toggle theme
  toggleTheme: function() {
    currentTheme = currentTheme === 'light' ? 'dark' : 'light';
    view.dispatch({
      effects: themeConf.reconfigure(themes[currentTheme])
    });
    document.body.classList.toggle('dark-mode', currentTheme === 'dark');
    updateThemeButton();
  },

  // Get document content
  getContent: function() {
    return view.state.doc.toString();
  },

  // Set document content
  setContent: function(content) {
    view.dispatch({
      changes: {
        from: 0,
        to: view.state.doc.length,
        insert: content
      }
    });
  },

  // Clear document
  clearDocument: function() {
    this.setContent('');
    view.focus();
  },

  // Save document
  saveDocument: function() {
    saveDocument(view);
  },

  // Load document from file
  loadDocument: function() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.js,.html,.css,.json,.md,.py,.txt';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (file) {
        const content = await file.text();
        this.setContent(content);
        
        // Auto-detect language from file extension
        const ext = file.name.split('.').pop().toLowerCase();
        const langMap = {
          'js': 'javascript',
          'html': 'html',
          'css': 'css',
          'json': 'json',
          'md': 'markdown',
          'py': 'python',
          'txt': 'plaintext'
        };
        if (langMap[ext]) {
          this.setLanguage(langMap[ext]);
          document.getElementById('language-select').value = langMap[ext];
        }
        
        updateStatus(view);
      }
    };
    input.click();
  },

  // Get editor view
  getView: function() {
    return view;
  },

  // Accept AI completion (called by Accept button)
    acceptCompletion: function() {
      if (!currentCompletion || !currentCompletion.text) {
        return;
      }
      
      const text = currentCompletion.text;

      // Copy to clipboard
      navigator.clipboard.writeText(text).then(() => {
        console.log('Completion copied to clipboard:', text);
      }).catch(err => {
        console.error('Failed to copy to clipboard:', err);
      });

      // Clear the completion and ghost text
      currentCompletion = null;
      if (completionTimer) {
        clearTimeout(completionTimer);
        completionTimer = null;
      }
      if (abortController) {
        abortController.abort();
        abortController = null;
      }

      view.dispatch({
        effects: completionEffect.of(null)
      });
    }
};

// Save document to file
function saveDocument(view) {
  const content = view.state.doc.toString();
  const extMap = {
    'javascript': 'js',
    'html': 'html',
    'css': 'css',
    'json': 'json',
    'markdown': 'md',
    'python': 'py',
    'plaintext': 'txt'
  };
  const ext = extMap[currentLanguage] || 'txt';
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `document.${ext}`;
  a.click();
  URL.revokeObjectURL(url);
}

// Update status bar
function updateStatus(view) {
  const doc = view.state.doc;
  const selection = view.state.selection.main;
  const line = doc.lineAt(selection.head);
  
  document.getElementById('line-count').textContent = doc.lines;
  document.getElementById('char-count').textContent = doc.length;
  document.getElementById('cursor-position').textContent = 
    `Ln ${line.number}, Col ${selection.head - line.from + 1}`;
  document.getElementById('current-language').textContent = 
    currentLanguage.charAt(0).toUpperCase() + currentLanguage.slice(1);
}

// Update theme button text
function updateThemeButton() {
  const btn = document.getElementById('theme-toggle');
  if (btn) {
    btn.textContent = currentTheme === 'light' ? '🌙 Dark' : '☀️ Light';
  }
}

// Initialize status bar
updateStatus(view);
updateThemeButton();

// Focus editor on load
view.focus();
