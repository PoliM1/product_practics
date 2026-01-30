// Общие функции приложения

// Показ уведомлений
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Копирование текста в буфер обмена
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showNotification('Скопировано в буфер обмена!');
        return true;
    } catch (err) {
        console.error('Failed to copy:', err);
        showNotification('Ошибка копирования', 'error');
        return false;
    }
}

// Форматирование времени
function formatTime(date) {
    return new Date(date).toLocaleTimeString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Генерация ID
function generateId() {
    return Math.random().toString(36).substr(2, 9);
}

// Валидация формы
function validateForm(formElement) {
    const inputs = formElement.querySelectorAll('input[required], select[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('error');
        } else {
            input.classList.remove('error');
        }
    });
    
    return isValid;
}

// Экспорт функций для использования в других скриптах
window.gameUtils = {
    showNotification,
    copyToClipboard,
    formatTime,
    generateId,
    validateForm
};
