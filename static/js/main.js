document.addEventListener('DOMContentLoaded', () => {
    // Hamburger menu toggle
    const hamburger = document.getElementById('hamburger');
    const navLinks = document.getElementById('nav-links');

    if (hamburger && navLinks) {
        hamburger.addEventListener('click', () => {
            navLinks.classList.toggle('active');
        });
    }

    // Predict Form Handling
    const predictForm = document.getElementById('predict-form');
    if (predictForm) {
        predictForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = document.getElementById('predict-btn');
            const loader = submitBtn.querySelector('.loader');
            const btnText = submitBtn.querySelector('.btn-text');
            const resultBox = document.getElementById('result-box');
            
            // Collect data
            const data = {
                gender: document.getElementById('gender').value,
                age: document.getElementById('age').value,
                income: document.getElementById('income').value,
                spending: document.getElementById('spending').value
            };

            // Loading state
            loader.classList.add('active');
            btnText.textContent = "Predicting...";
            submitBtn.disabled = true;
            resultBox.classList.remove('active');

            try {
                const response = await fetch('/api/predict', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    document.getElementById('res-cluster').textContent = `Cluster ${result.cluster}`;
                    document.getElementById('res-label').textContent = result.label;
                    document.getElementById('res-rec').textContent = result.recommendation;
                    
                    const stickerIcon = document.getElementById('gender-icon');
                    const stickerContainer = document.getElementById('gender-sticker-container');
                    if (data.gender === 'Male') {
                        stickerIcon.className = 'fas fa-person';
                        stickerContainer.className = 'gender-sticker male';
                    } else if (data.gender === 'Female') {
                        stickerIcon.className = 'fas fa-person-dress';
                        stickerContainer.className = 'gender-sticker female';
                    }
                    
                    const visualSection = document.querySelector('.result-visual-section');
                    if (visualSection) {
                        visualSection.style.animation = 'none';
                        void visualSection.offsetWidth; // trigger reflow
                        visualSection.style.animation = null; 
                    }

                    renderPredictionChart(data.age, data.income, data.spending);

                    resultBox.classList.add('active');
                } else {
                    alert('Error: ' + result.message);
                }
            } catch (error) {
                alert('Connection Error!');
                console.error(error);
            } finally {
                // Reset state
                loader.classList.remove('active');
                btnText.textContent = "Predict Cluster";
                submitBtn.disabled = false;
            }
        });
    }

    // Chatbot functionality
    const chatToggle = document.getElementById('chatbot-toggle');
    const chatWidget = document.getElementById('chatbot-widget');
    const chatClose = document.getElementById('chatbot-close');
    const chatInput = document.getElementById('chatbot-input-field');
    const chatSendBtn = document.getElementById('chatbot-send-btn');
    const chatMessages = document.getElementById('chatbot-messages');

    if (chatToggle && chatWidget) {
        chatToggle.addEventListener('click', () => {
            chatWidget.classList.add('active');
            chatInput.focus();
        });

        chatClose.addEventListener('click', () => {
            chatWidget.classList.remove('active');
        });

        const sendChatMessage = async () => {
            const message = chatInput.value.trim();
            if (!message) return;

            // Append user message
            appendMessage(message, 'user');
            chatInput.value = '';

            // Show typing indicator
            const typingId = 'typing-' + Date.now();
            appendTypingIndicator(typingId);

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                });

                const result = await response.json();
                
                // Remove typing indicator
                const typingEl = document.getElementById(typingId);
                if (typingEl) typingEl.remove();

                if (result.status === 'success') {
                    appendMessage(result.reply, 'bot', true);
                } else {
                    appendMessage(`Error: ${result.message}`, 'bot');
                }
            } catch (error) {
                const typingEl = document.getElementById(typingId);
                if (typingEl) typingEl.remove();
                appendMessage('Sorry, I am having trouble connecting right now.', 'bot');
                console.error(error);
            }
        };

        chatSendBtn.addEventListener('click', sendChatMessage);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendChatMessage();
            }
        });

        function appendMessage(text, sender, isHtml = false) {
            const msgDiv = document.createElement('div');
            msgDiv.className = `chat-message ${sender}`;
            if (isHtml) {
                msgDiv.innerHTML = text;
            } else {
                msgDiv.textContent = text;
            }
            chatMessages.appendChild(msgDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function appendTypingIndicator(id) {
            const msgDiv = document.createElement('div');
            msgDiv.className = `chat-message bot`;
            msgDiv.id = id;
            msgDiv.innerHTML = `
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            `;
            chatMessages.appendChild(msgDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    // Password Generator
    const genBtn = document.getElementById('generate-pw-btn');
    const pwInput = document.getElementById('password');
    const pwSuggestion = document.getElementById('password-suggestion');

    if (genBtn && pwInput && pwSuggestion) {
        genBtn.addEventListener('click', () => {
            const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+";
            let pw = "";
            for (let i = 0; i < 16; i++) {
                const arr = new Uint32Array(1);
                window.crypto.getRandomValues(arr);
                pw += chars[arr[0] % chars.length];
            }
            pwInput.value = pw;
            pwInput.type = "text"; 
            pwSuggestion.textContent = "Strong password generated and applied!";
            pwSuggestion.style.display = "block";
            
            setTimeout(() => {
                pwInput.type = "password";
            }, 3000);
        });
    }
});

let predictionChartInstance = null;

function renderPredictionChart(age, income, spending) {
    const ctx = document.getElementById('predictionChart');
    if (!ctx) return;

    if (predictionChartInstance) {
        predictionChartInstance.destroy();
    }

    predictionChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Age', 'Income (k$)', 'Spending Score'],
            datasets: [{
                label: 'Customer Profile',
                data: [age, income, spending],
                backgroundColor: [
                    'rgba(79, 140, 255, 0.7)',
                    'rgba(34, 197, 94, 0.7)',
                    'rgba(245, 158, 11, 0.7)'
                ],
                borderColor: [
                    'rgb(79, 140, 255)',
                    'rgb(34, 197, 94)',
                    'rgb(245, 158, 11)'
                ],
                borderWidth: 1,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 1500,
                easing: 'easeInOutQuart'
            },
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    suggestedMax: 100,
                    grid: { color: 'rgba(0, 0, 0, 0.05)' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}
