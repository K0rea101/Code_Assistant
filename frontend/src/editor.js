import { EditorView, basicSetup } from 'codemirror';
import { EditorState, Compartment, StateEffect, StateField } from '@codemirror/state';
import { keymap, Decoration } from '@codemirror/view';
import { javascript } from '@codemirror/lang-javascript';
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
    // Clear completion on any document change or selection change
    if (tr.docChanged || tr.selection) return null;
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
const COMPLETION_DELAY_MS = 500;
const COMPLETION_MIN_CONFIDENCE = 0.2;
const MIN_CHARS_FOR_COMPLETION = 3;

// Clear completion state and UI
function clearCompletion(view) {
  if (currentCompletion) {
    currentCompletion = null;
  }
  if (completionTimer) {
    clearTimeout(completionTimer);
    completionTimer = null;
  }
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
  view.dispatch({ effects: completionEffect.of(null) });
}

// Accept and insert the current completion
function acceptCurrentCompletion(view) {
  if (!currentCompletion || !currentCompletion.text) {
    return false;
  }
  
  const fullCompletion = currentCompletion.text;
  const pos = currentCompletion.position;
  const lineStart = currentCompletion.lineStart;
  
  // Validate position is still valid
  if (pos < 0 || pos > view.state.doc.length) {
    clearCompletion(view);
    return false;
  }
  
  // Get what the user has already typed on this line (from line start to cursor)
  const existingText = view.state.doc.sliceString(lineStart, pos);
  
  // Calculate what to insert: only the continuation part
  // If completion starts with what user already typed, strip that prefix
  let textToInsert = fullCompletion;
  if (fullCompletion.startsWith(existingText)) {
    textToInsert = fullCompletion.slice(existingText.length);
  }
  
  // Clear completion first to prevent re-triggering
  currentCompletion = null;
  if (completionTimer) {
    clearTimeout(completionTimer);
    completionTimer = null;
  }
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
  
  // Insert only the continuation at the cursor position
  view.dispatch({
    changes: { from: pos, to: pos, insert: textToInsert },
    selection: { anchor: pos + textToInsert.length },
    effects: completionEffect.of(null)
  });
  
  view.focus();
  return true;
}

async function fetchAICompletion(view, lastChar) {
  try {
    const content = view.state.doc.toString();
    const cursor = view.state.selection.main.head;

    // Don't fetch if content is too short
    if (content.length < MIN_CHARS_FOR_COMPLETION) {
      clearCompletion(view);
      return;
    }

    // Don't fetch if cursor is not at end of a word/line (user might be in middle of text)
    const lineAtCursor = view.state.doc.lineAt(cursor);
    const textAfterCursor = lineAtCursor.text.slice(cursor - lineAtCursor.from);
    if (textAfterCursor.trim().length > 0) {
      // There's non-whitespace text after cursor, don't show completion
      clearCompletion(view);
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
      clearCompletion(view);
      return;
    }

    const data = await response.json();
    if (!data.triggered || !data.completion || data.confidence < COMPLETION_MIN_CONFIDENCE) {
      clearCompletion(view);
      return;
    }

    // Check if cursor position is still valid and hasn't changed
    const currentCursor = view.state.selection.main.head;
    if (currentCursor !== cursor) {
      // Cursor moved, don't show stale completion
      return;
    }

    const pos = currentCursor;
    const completionText = data.completion;
    
    const widget = Decoration.widget({
      widget: {
        toDOM() {
          const container = document.createElement('span');
          container.className = 'ai-completion-widget';
          container.style.display = 'inline-flex';
          container.style.alignItems = 'center';
          container.style.gap = '8px';
          container.style.pointerEvents = 'none';

          const ghost = document.createElement('span');
          ghost.className = 'ai-completion-ghost';
          ghost.textContent = completionText;
          ghost.style.opacity = '0.5';
          ghost.style.color = '#888';
          ghost.style.fontStyle = 'italic';
          ghost.style.whiteSpace = 'pre';
          ghost.style.pointerEvents = 'none';

          const hint = document.createElement('span');
          hint.className = 'ai-completion-hint';
          hint.textContent = 'Tab to accept';
          hint.style.fontSize = '10px';
          hint.style.color = '#666';
          hint.style.background = 'rgba(100, 100, 100, 0.2)';
          hint.style.padding = '1px 4px';
          hint.style.borderRadius = '3px';
          hint.style.marginLeft = '4px';
          hint.style.pointerEvents = 'none';

          container.appendChild(ghost);
          container.appendChild(hint);
          return container;
        },
        ignoreEvent() { return true; }
      },
      side: 1
    }).range(pos);

    // Store line start for prefix detection when accepting
    const lineAtPos = view.state.doc.lineAt(pos);
    
    currentCompletion = {
      text: completionText,
      position: pos,
      lineStart: lineAtPos.from,
      decorations: Decoration.set([widget])
    };
    view.dispatch({ effects: completionEffect.of(currentCompletion) });
  } catch (e) {
    if (e.name !== 'AbortError') {
      clearCompletion(view);
    }
  }
}

// Language configurations (Python and JavaScript only)
const languages = {
  javascript: javascript(),
  python: python()
};

// Theme configurations
const themes = {
  light: [],
  dark: oneDark
};

let currentTheme = 'dark';
let currentLanguage = 'python';

// Create initial state
const initialDoc = `# Welcome to the Code Editor!
# Start typing your Python code here...

def greet(name):
    return f"Hello, {name}!"

print(greet("World"))
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
      // Tab to accept AI completion
      {
        key: 'Tab',
        run: (view) => {
          if (currentCompletion && currentCompletion.text) {
            return acceptCurrentCompletion(view);
          }
          // Return false to let default Tab behavior happen (indent)
          return false;
        }
      },
      // Escape to dismiss AI completion
      {
        key: 'Escape',
        run: (view) => {
          if (currentCompletion) {
            clearCompletion(view);
            return true;
          }
          return false;
        }
      },
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
        
        // Clear existing completion and timer on any document change
        clearCompletion(update.view);
        
        // Get the last character typed
        const tr = update.transactions[0];
        let lastChar = '';
        if (tr) {
          tr.changes.iterChanges((fromA, toA, fromB, toB, inserted) => {
            if (inserted.length > 0) {
              lastChar = inserted.sliceString(inserted.length - 1);
            }
          });
        }
        
        // Only trigger completion for insertions, not deletions
        const isInsertion = update.transactions.some(tr => {
          let hasInsertion = false;
          tr.changes.iterChanges((fromA, toA, fromB, toB, inserted) => {
            if (inserted.length > 0) hasInsertion = true;
          });
          return hasInsertion;
        });
        
        if (isInsertion && lastChar) {
          completionTimer = setTimeout(() => {
            fetchAICompletion(update.view, lastChar);
          }, COMPLETION_DELAY_MS);
        }
      } else if (update.selectionSet) {
        // Clear completion when selection/cursor changes without doc change
        clearCompletion(update.view);
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
    input.accept = '.js,.py';
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (file) {
        const content = await file.text();
        this.setContent(content);
        
        // Auto-detect language from file extension
        const ext = file.name.split('.').pop().toLowerCase();
        const langMap = {
          'js': 'javascript',
          'py': 'python'
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

  // Accept AI completion - inserts the text into the editor
  acceptCompletion: function() {
    return acceptCurrentCompletion(view);
  },
  
  // Dismiss/clear the current AI completion
  dismissCompletion: function() {
    clearCompletion(view);
  },
  
  // Run code (Python and JavaScript only)
  runCode: async function() {
    const code = view.state.doc.toString();
    const lang = currentLanguage;
    
    if (lang !== 'python' && lang !== 'javascript') {
      alert('Run is only supported for Python and JavaScript.');
      return;
    }
    
    // Show output panel
    showOutputPanel();
    setOutputContent('⏳ Running ' + lang + ' code...');
    
    try {
      const response = await fetch('http://localhost:8000/api/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          code: code,
          language: lang
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        setOutputContent('❌ Error: ' + (errorData.error || errorData.detail || response.statusText));
        return;
      }
      
      const data = await response.json();
      let output = '';
      
      // Show error message first if present
      if (data.error) {
        output += data.error + '\n\n';
      }
      
      // Show stdout
      if (data.stdout) {
        output += data.stdout;
      }
      
      // Show stderr if present
      if (data.stderr) {
        if (output) output += '\n';
        output += '─── stderr ───\n' + data.stderr;
      }
      
      // Show exit code if non-zero
      if (data.exit_code !== 0 && data.exit_code !== null) {
        output += '\n\n[Exit code: ' + data.exit_code + ']';
      }
      
      if (!output.trim()) {
        output = '✓ Code executed successfully (no output)';
      }
      
      setOutputContent(output);
    } catch (error) {
      setOutputContent('❌ Failed to run code: ' + error.message + '\n\nMake sure the backend server is running on http://localhost:8000');
    }
  }
};

// Save document to file
function saveDocument(view) {
  const content = view.state.doc.toString();
  const extMap = {
    'javascript': 'js',
    'python': 'py'
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

// Output panel functions
function showOutputPanel() {
  let panel = document.getElementById('output-panel');
  if (!panel) {
    // Create output panel if it doesn't exist
    panel = document.createElement('div');
    panel.id = 'output-panel';
    panel.className = 'output-panel';
    panel.innerHTML = `
      <div class="output-header">
        <span>📤 Output</span>
        <button onclick="CodeMirrorEditor.hideOutput()" title="Close">✕</button>
      </div>
      <pre class="output-content" id="output-content"></pre>
    `;
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
      mainContent.appendChild(panel);
    }
  }
  panel.style.display = 'flex';
}

function hideOutputPanel() {
  const panel = document.getElementById('output-panel');
  if (panel) {
    panel.style.display = 'none';
  }
}

function setOutputContent(content) {
  const outputEl = document.getElementById('output-content');
  if (outputEl) {
    outputEl.textContent = content;
  }
}

// Export output functions
window.CodeMirrorEditor.hideOutput = hideOutputPanel;

// Initialize status bar and theme
updateStatus(view);
updateThemeButton();

// Apply initial theme class to body (dark mode by default)
document.body.classList.toggle('dark-mode', currentTheme === 'dark');

// Focus editor on load
view.focus();
