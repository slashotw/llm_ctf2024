const chatContainer = document.getElementById('chat');
const promptForm = document.getElementById('prompt-form');
const promptInput = document.getElementById('prompt');
const loadingIndicator = document.getElementById('loading');

promptForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    addMessage('user', prompt);
    promptInput.value = '';

    loadingIndicator.style.display = 'block';

    try {
        const response = await axios.post('/api/chat', { prompt });
        addMessage('assistant', response.data.response);
    } catch (error) {
        console.error('Error:', error);
        addMessage('assistant', 'Sorry, an error occurred. Please try again.');
    }

    loadingIndicator.style.display = 'none';
});

function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `mb-4 ${role === 'user' ? 'text-right' : 'text-left'}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = `inline-block p-2 rounded-lg ${role === 'user' ? 'bg-blue-200' : 'bg-gray-200'}`;
    contentDiv.textContent = content;
    
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}