// AI Chat Sidebar functionality

// Configuration - Your backend API endpoint
const API_CONFIG = {
  endpoint: 'http://localhost:8000/api/chat'
};

// Chat history for context
let chatHistory = [];

// Toggle chat sidebar visibility
function toggleChatSidebar() {
  const sidebar = document.getElementById('chat-sidebar');
  const mainContent = document.querySelector('.main-content');
  sidebar.classList.toggle('collapsed');
  mainContent.classList.toggle('chat-collapsed');
  
  // Update toggle button text based on new state
  updateChatToggleButton();
}

// Update toggle button text to match sidebar state
function updateChatToggleButton() {
  const sidebar = document.getElementById('chat-sidebar');
  const toggleBtn = document.getElementById('chat-sidebar-toggle');
  if (!toggleBtn) return;
  
  if (sidebar.classList.contains('collapsed')) {
    toggleBtn.innerHTML = '💬 AI Chat';
  } else {
    toggleBtn.innerHTML = '💬 Hide Chat';
  }
}

// Handle keyboard events in chat input
function handleChatKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

// Send message to AI
async function sendMessage() {
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  
  if (!message) return;
  
  // Add user message to chat
  addMessageToChat('user', message);
  input.value = '';
  input.focus();
  
  // Add to history
  chatHistory.push({ role: 'user', content: message });
  
  // Show typing indicator
  const typingId = showTypingIndicator();
  
  try {
    // Send to AI API
    const response = await callAIAPI(message);
    
    // Remove typing indicator
    removeTypingIndicator(typingId);
    
    // Add AI response to chat
    addMessageToChat('assistant', response);
    chatHistory.push({ role: 'assistant', content: response });
    
  } catch (error) {
    removeTypingIndicator(typingId);
    addMessageToChat('assistant', `Error: ${error.message}. Please check your API connection.`);
  }
}

// Add message to chat UI
function addMessageToChat(role, content) {
  const messagesContainer = document.getElementById('chat-messages');
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;
  
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';
  
  // Render markdown for assistant messages
  if (role === 'assistant') {
    contentDiv.innerHTML = renderMarkdown(content);
  } else {
    contentDiv.textContent = content;
  }
  
  messageDiv.appendChild(contentDiv);
  messagesContainer.appendChild(messageDiv);
  
  // Scroll to bottom
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Configure marked with highlight.js
function initMarkdown() {
  if (typeof marked !== 'undefined') {
    // Configure marked with proper highlight.js integration
    marked.setOptions({
      breaks: true,
      gfm: true,
      highlight: function(code, lang) {
        if (typeof hljs !== 'undefined') {
          if (lang && hljs.getLanguage(lang)) {
            try {
              return hljs.highlight(code, { language: lang }).value;
            } catch (e) {
              console.error('Highlight error:', e);
            }
          }
          return hljs.highlightAuto(code).value;
        }
        return code;
      }
    });
  }
}

// Initialize when DOM is ready
function initChat() {
  initMarkdown();
  updateChatToggleButton();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initChat);
} else {
  initChat();
}

// Render markdown to HTML using marked library
function renderMarkdown(text) {
  // First, strip the outer ```markdown wrapper if present
  if (text.startsWith('```markdown')) {
    text = text.replace(/^```markdown\s*\n?/, '');
    text = text.replace(/\n?```\s*$/, '');
  }
  
  // Also handle nested ```markdown tags
  text = text.replace(/```markdown\s*\n/g, '');
  
  // Use marked library if available
  if (typeof marked !== 'undefined') {
    let html = marked.parse(text);
    
    // Find all code blocks and apply syntax highlighting
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    tempDiv.querySelectorAll('pre code').forEach((block) => {
      // Get language from class
      const langClass = Array.from(block.classList).find(c => c.startsWith('language-'));
      const lang = langClass ? langClass.replace('language-', '') : null;
      
      // Apply highlight.js
      if (typeof hljs !== 'undefined') {
        if (lang && hljs.getLanguage(lang)) {
          block.innerHTML = hljs.highlight(block.textContent, { language: lang }).value;
        } else {
          block.innerHTML = hljs.highlightAuto(block.textContent).value;
        }
        block.classList.add('hljs');
      }
      
      // Wrap with our custom wrapper
      const pre = block.parentElement;
      const wrapper = document.createElement('div');
      wrapper.className = 'code-block-wrapper';
      wrapper.innerHTML = `
        <div class="code-block-header">
          <span class="code-language">${lang || 'code'}</span>
          <button class="copy-code-btn" onclick="copyCode(this)" title="Copy code">📋 Copy</button>
        </div>
      `;
      pre.parentNode.insertBefore(wrapper, pre);
      wrapper.appendChild(pre);
    });
    
    return tempDiv.innerHTML;
  }
  
  // Fallback to basic rendering
  return text.replace(/\n/g, '<br>');
}

// Escape HTML entities
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Copy code to clipboard
function copyCode(button) {
  const codeBlock = button.closest('.code-block-wrapper').querySelector('code');
  const code = codeBlock.textContent;
  
  navigator.clipboard.writeText(code).then(() => {
    const originalText = button.innerHTML;
    button.innerHTML = '✅ Copied!';
    button.classList.add('copied');
    setTimeout(() => {
      button.innerHTML = originalText;
      button.classList.remove('copied');
    }, 2000);
  }).catch(err => {
    console.error('Failed to copy:', err);
  });
}

// Show typing indicator with unique ID
let typingIndicatorCounter = 0;

function showTypingIndicator() {
  const messagesContainer = document.getElementById('chat-messages');
  const typingDiv = document.createElement('div');
  const uniqueId = `typing-indicator-${++typingIndicatorCounter}`;
  typingDiv.className = 'message assistant typing';
  typingDiv.id = uniqueId;
  typingDiv.innerHTML = `
    <div class="message-content">
      <span class="typing-dots">
        <span></span><span></span><span></span>
      </span>
    </div>
  `;
  messagesContainer.appendChild(typingDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  return uniqueId;
}

// Remove typing indicator
function removeTypingIndicator(id) {
  const indicator = document.getElementById(id);
  if (indicator) {
    indicator.remove();
  }
}

// Get current code from editor for context
function getCodeContext() {
  if (window.CodeMirrorEditor && window.CodeMirrorEditor.getContent) {
    const code = window.CodeMirrorEditor.getContent();
    return code.substring(0, 2000);
  }
  return '';
}

// Call AI API
async function callAIAPI(userMessage) {
  // Get current code context from editor
  const codeContext = getCodeContext();
  
  const response = await fetch(API_CONFIG.endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      user_input: userMessage,
      code_context: codeContext || undefined
    })
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  const data = await response.json();
  
  // Extract the generated response from your API format
  return data.generated_response || data.message || 'No response received';
}

// Insert code from AI response into editor
function insertCodeToEditor(code) {
  if (window.CodeMirrorEditor && window.CodeMirrorEditor.getView) {
    const view = window.CodeMirrorEditor.getView();
    const selection = view.state.selection.main;
    view.dispatch({
      changes: { from: selection.from, to: selection.to, insert: code }
    });
    view.focus();
  }
}

// Clear chat history
function clearChat() {
  chatHistory = [];
  const messagesContainer = document.getElementById('chat-messages');
  messagesContainer.innerHTML = `
    <div class="message assistant">
      <div class="message-content">Chat cleared. How can I help you?</div>
    </div>
  `;
}

// Resize functionality for chat sidebar
let isResizing = false;
let lastX = 0;

function initResizer() {
  const resizer = document.getElementById('chat-resizer');
  if (!resizer) return;
  
  resizer.addEventListener('mousedown', (e) => {
    isResizing = true;
    lastX = e.clientX;
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  });
  
  document.addEventListener('mousemove', (e) => {
    if (!isResizing) return;
    
    const sidebar = document.getElementById('chat-sidebar');
    const dx = lastX - e.clientX;
    lastX = e.clientX;
    
    const newWidth = sidebar.offsetWidth + dx;
    if (newWidth >= 250 && newWidth <= 600) {
      sidebar.style.width = newWidth + 'px';
      sidebar.style.minWidth = newWidth + 'px';
    }
  });
  
  document.addEventListener('mouseup', () => {
    if (isResizing) {
      isResizing = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
  });
}

// Initialize resizer when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initResizer);
} else {
  initResizer();
}

// Make functions available globally
window.toggleChatSidebar = toggleChatSidebar;
window.handleChatKeydown = handleChatKeydown;
window.sendMessage = sendMessage;
window.clearChat = clearChat;
window.insertCodeToEditor = insertCodeToEditor;
window.copyCode = copyCode;
window.updateChatToggleButton = updateChatToggleButton;
