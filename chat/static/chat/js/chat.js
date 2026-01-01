document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const chatForm = document.getElementById('chat-form');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const chatToggle = document.getElementById('chat-toggle');
    const chatContainer = document.getElementById('chat-container');
    const closeChat = document.getElementById('close-chat');
    const expandChat = document.getElementById('expand-chat');
    const sendButton = document.getElementById('send-button');
    const typingIndicator = document.getElementById('typing-indicator');
    
    // Check if all required elements exist
    if (!chatToggle || !chatContainer) {
        console.error('Chat widget elements not found');
        return;
    }
    
    // State
    let isExpanded = false;
    
    // Initialize chat
    function initChat() {
        // Start with chat closed (no auto-show)
        if (chatContainer) {
            chatContainer.style.display = 'none';
            chatContainer.style.opacity = '0';
            chatContainer.style.transform = 'translateY(20px)';
            chatContainer.style.pointerEvents = 'none';
        }
    }
    
    // Toggle chat visibility
    function toggleChat(e) {
        if (e) {
            e.stopPropagation(); // Prevent event from bubbling up
            e.preventDefault();
        }
        
        if (!chatContainer) {
            console.error('Chat container not found');
            return;
        }
        
        const currentDisplay = window.getComputedStyle(chatContainer).display;
        const isHidden = currentDisplay === 'none' || chatContainer.style.display === 'none';
        
        if (isHidden) {
            // Open chat
            chatContainer.style.display = 'flex';
            chatContainer.style.pointerEvents = 'auto';
            
            // Force reflow to ensure the transition works
            void chatContainer.offsetWidth;
            
            // Trigger transition
            setTimeout(() => {
                chatContainer.style.opacity = '1';
                chatContainer.style.transform = 'translateY(0)';
                // Scroll to bottom when chat opens
                scrollToBottom();
            }, 10);
            
            if (userInput) {
                setTimeout(() => userInput.focus(), 300);
            }
            console.log('Chat opened');
        } else {
            // Close chat
            chatContainer.style.opacity = '0';
            chatContainer.style.transform = 'translateY(20px)';
            chatContainer.style.pointerEvents = 'none';
            
            // Hide after animation completes
            setTimeout(() => {
                if (chatContainer) {
                    chatContainer.style.display = 'none';
                }
            }, 300);
            console.log('Chat closed');
        }
    }
    
    // Toggle chat between expanded and normal size
    function toggleExpand() {
        isExpanded = !isExpanded;
        if (isExpanded) {
            // For expanded view, set a max height based on viewport height
            chatContainer.style.maxHeight = '90vh';
            chatContainer.style.top = '5vh';
            chatContainer.style.bottom = 'auto';
            chatContainer.classList.add('w-[95vw]', 'max-w-[1200px]', 'right-1/2', 'translate-x-1/2');
            chatContainer.classList.remove('w-96', 'right-8');
            expandChat.innerHTML = '<i class="fas fa-compress text-sm"></i>';
        } else {
            // For normal view, reset to default positioning
            chatContainer.style.maxHeight = '80vh';
            chatContainer.style.top = '';
            chatContainer.style.bottom = '7rem';
            chatContainer.classList.remove('w-[95vw]', 'max-w-[1200px]', 'right-1/2', 'translate-x-1/2');
            chatContainer.classList.add('w-96', 'right-8');
            expandChat.innerHTML = '<i class="fas fa-expand text-sm"></i>';
        }
        // Ensure messages scroll to bottom after resize
        scrollToBottom();
    }
    
    // Set up event listeners
    function setupEventListeners() {
        // Toggle chat window
        if (chatToggle) {
            chatToggle.addEventListener('click', toggleChat);
        }
        
        // Close chat window
        if (closeChat) {
            closeChat.addEventListener('click', toggleChat);
        }
        
        // Toggle expand/collapse
        if (expandChat) {
            expandChat.addEventListener('click', function(e) {
                e.stopPropagation();
                toggleExpand();
            });
        }
        
        // Close chat when clicking outside (only if chat is open)
        document.addEventListener('click', function(e) {
            if (!chatContainer || !chatToggle) return;
            
            // Check if chat is currently open by checking display and opacity
            const currentDisplay = window.getComputedStyle(chatContainer).display;
            const currentOpacity = window.getComputedStyle(chatContainer).opacity;
            const isChatOpen = currentDisplay !== 'none' && currentOpacity !== '0';
            
            // Only handle clicks if chat is open
            if (isChatOpen) {
                // Don't close if clicking on chat container, toggle button, or any child elements
                const clickedInsideChat = chatContainer.contains(e.target);
                const clickedOnToggle = e.target === chatToggle || chatToggle.contains(e.target);
                
                // Also check if clicking on navbar or other important elements
                const clickedOnNavbar = e.target.closest('nav') !== null;
                
                if (!clickedInsideChat && !clickedOnToggle && !clickedOnNavbar) {
                    // Only close if clicking outside chat and not on navbar
                    toggleChat(e);
                }
            }
        });
        
        // Handle form submission
        if (chatForm) {
            chatForm.addEventListener('submit', function(e) {
                e.preventDefault();
                sendMessage();
            });
        }
        
        // Send message on button click
        if (sendButton) {
            sendButton.addEventListener('click', function() {
                sendMessage();
            });
        }
        
        // Send message on Enter key (but allow Shift+Enter for new line)
        if (userInput) {
            userInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            });
        }
        
        // Handle window resize
        window.addEventListener('resize', function() {
            if (!chatContainer) return;
            
            if (window.innerWidth < 768) { // Mobile view
                chatContainer.classList.remove('w-96', 'w-[95vw]', 'max-w-[1200px]', 'right-1/2', 'translate-x-1/2');
                chatContainer.classList.add('w-[calc(100%-2rem)]', 'right-4');
            } else if (isExpanded) {
                chatContainer.classList.remove('w-96', 'w-[calc(100%-2rem)]', 'right-4');
                chatContainer.classList.add('w-[95vw]', 'max-w-[1200px]', 'right-1/2', 'translate-x-1/2');
            } else {
                chatContainer.classList.remove('w-[95vw]', 'max-w-[1200px]', 'right-1/2', 'translate-x-1/2', 'w-[calc(100%-2rem)]', 'right-4');
                chatContainer.classList.add('w-96', 'right-8');
            }
        });
    }
    
    // Load chat history
    function loadChatHistory() {
        fetch('/chat/send/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.chats && data.chats.length > 0) {
                // API returns chats in reverse chronological order (newest first)
                // We want oldest at top, newest at bottom, so reverse the array
                const chatsInOrder = [...data.chats].reverse();
                chatsInOrder.forEach(chat => {
                    addMessage(chat.user_message, 'user');
                    addMessage(chat.ai_message, 'ai');
                });
                // Scroll to bottom after loading history
                setTimeout(() => {
                    scrollToBottom();
                }, 100);
            }
        })
        .catch(error => {
            console.error('Error loading chat history:', error);
        });
    }
    
    // Function to send a message
    function sendMessage() {
        const message = userInput.value.trim();
        
        if (!message) return;
        
        // Add user message to chat
        addMessage(message, 'user');
        userInput.value = '';
        
        // Show typing indicator immediately
        showTypingIndicator();
        
        // Scroll to bottom
        scrollToBottom();
        
        // Show loading state (disables input/button)
        setLoadingState(true);
        
        // Send message to server
        fetch('/chat/send/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                message: message
            }),
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                addMessage(data.ai_message, 'ai');
            } else {
                addMessage('Sorry, there was an error processing your request.', 'ai');
                console.error('Error:', data.error);
            }
            setLoadingState(false);
            scrollToBottom();
        })
        .catch(error => {
            console.error('Error:', error);
            addMessage('Sorry, there was an error connecting to the server.', 'ai');
            setLoadingState(false);
            scrollToBottom();
        });
    }
    
    // Function to format message with links and basic markdown
    function formatMessage(message) {
        // Check if message already contains HTML tags (from server)
        const hasHTML = /<[a-z][\s\S]*>/i.test(message);
        
        if (hasHTML) {
            // Message already has HTML from server, use it as-is
            // The server has already converted WhatsApp formatting to HTML
            return message;
        }
        
        // For plain text messages, escape HTML and format
        let formatted = message
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        
        // Convert markdown-style links [text](url) to HTML links
        formatted = formatted.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function(match, text, url) {
            return '<a href="' + url + '" target="_blank" style="color: #60a5fa; text-decoration: underline;">' + text + '</a>';
        });
        
        // Convert newlines to <br>
        formatted = formatted.replace(/\n/g, '<br>');
        
        // Convert emoji arrows 👉 to styled spans
        formatted = formatted.replace(/👉/g, '<span class="mr-1">👉</span>');
        
        return formatted;
    }
    
    // Function to add a message to the chat
    function addMessage(message, sender) {
        const messageContainer = document.createElement('div');
        messageContainer.className = `message ${sender === 'user' ? 'user-message' : 'ai-message'}`;
        
        // Avatar
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        const avatarIcon = document.createElement('i');
        avatarIcon.className = sender === 'user' ? 'fas fa-user' : 'fas fa-robot';
        avatar.appendChild(avatarIcon);
        
        // Message content wrapper
        const messageContentWrapper = document.createElement('div');
        messageContentWrapper.className = 'message-content';
        
        // Message bubble
        const messageBubble = document.createElement('div');
        messageBubble.className = 'message-bubble';
        
        const messageText = document.createElement('p');
        if (sender === 'user') {
            // User messages are plain text
            messageText.textContent = message;
        } else {
            // AI messages may contain HTML - render as HTML
            const formattedMessage = formatMessage(message);
            messageText.innerHTML = formattedMessage;
        }
        messageBubble.appendChild(messageText);
        
        // Message time
        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        const now = new Date();
        messageTime.textContent = sender === 'user' ? 'You • Just now' : 'TSC Assistant • Just now';
        
        messageContentWrapper.appendChild(messageBubble);
        messageContentWrapper.appendChild(messageTime);
        
        messageContainer.appendChild(avatar);
        messageContainer.appendChild(messageContentWrapper);
        
        chatMessages.appendChild(messageContainer);
        scrollToBottom();
    }
    
    // Show typing indicator
    function showTypingIndicator() {
        if (typingIndicator) {
            typingIndicator.classList.remove('hidden');
            typingIndicator.style.display = 'flex';
            // Ensure it's visible
            typingIndicator.style.visibility = 'visible';
            typingIndicator.style.opacity = '1';
            // Scroll to bottom to show typing indicator
            setTimeout(() => {
                scrollToBottom();
            }, 50);
            console.log('Typing indicator shown');
        } else {
            console.error('Typing indicator element not found');
        }
    }
    
    // Hide typing indicator
    function hideTypingIndicator() {
        if (typingIndicator) {
            typingIndicator.classList.add('hidden');
            typingIndicator.style.display = 'none';
            console.log('Typing indicator hidden');
        }
    }
    
    // Set loading state
    function setLoadingState(loading) {
        if (loading) {
            if (sendButton) sendButton.disabled = true;
            if (userInput) userInput.disabled = true;
            if (sendButton) sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        } else {
            if (sendButton) sendButton.disabled = false;
            if (userInput) userInput.disabled = false;
            if (sendButton) sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
            hideTypingIndicator();
            if (userInput) userInput.focus();
        }
    }
    
    // Scroll to bottom of chat
    function scrollToBottom() {
        if (chatMessages) {
            // Use requestAnimationFrame to ensure DOM is updated
            requestAnimationFrame(() => {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            });
        }
    }
    
    // Helper function to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Initialize the chat
    if (chatToggle && chatContainer) {
        initChat();
        setupEventListeners();
        loadChatHistory();
        
        // Debug: Log that chat is initialized
        console.log('Chat widget initialized');
    } else {
        console.error('Chat widget elements missing:', {
            chatToggle: !!chatToggle,
            chatContainer: !!chatContainer
        });
    }
});
