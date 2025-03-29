document.addEventListener('DOMContentLoaded', () => {
    let allTransactions = [];

    // Обработка формы отправки транзакции
    const form = document.getElementById('transaction-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(form);
        try {
            const response = await fetch('/send_transaction', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            if (result.status === 'success') {
                alert(result.message);
                form.reset();
            } else {
                alert(`Error: ${result.message}`);
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    });

    // Обработка кнопки управления продюсером
    const toggleButton = document.getElementById('toggle-producer');
    toggleButton.addEventListener('click', async () => {
        try {
            const response = await fetch('/toggle_producer', {
                method: 'POST'
            });
            const result = await response.json();
            toggleButton.textContent = result.message === 'Producer started' ? 'Stop Producer' : 'Start Producer';
            toggleButton.classList.toggle('btn-success', result.message === 'Producer started');
            toggleButton.classList.toggle('btn-danger', result.message === 'Producer stopped');
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    });

    // Функция для отображения транзакций с учётом фильтра
    const tableBody = document.getElementById('transactions-table');
    const filterSelect = document.getElementById('filter-status');
    const renderTransactions = () => {
        const filter = filterSelect.value;
        tableBody.innerHTML = '';
        allTransactions.forEach(transaction => {
            if (filter === 'all' ||
                (filter === 'normal' && transaction.status === 'Normal') ||
                (filter === 'attack' && transaction.status === 'Attack')) {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${transaction.transaction_id}</td>
                    <td>${transaction.user_id}</td>
                    <td>${transaction.amount}</td>
                    <td>${new Date(transaction.timestamp * 1000).toLocaleString()}</td>
                    <td class="${transaction.status.toLowerCase()}">
                        ${transaction.status}
                    </td>
                `;
                tableBody.prepend(row);
            }
        });
    };

    // Обработка фильтра
    filterSelect.addEventListener('change', renderTransactions);

    // Обработка кнопки очистки таблицы
    const clearButton = document.getElementById('clear-table');
    clearButton.addEventListener('click', () => {
        allTransactions = [];
        renderTransactions();
    });

    // Подключение к SSE для получения транзакций в реальном времени
    const source = new EventSource('/stream');
    source.onmessage = (event) => {
        const transaction = JSON.parse(event.data);
        allTransactions.unshift(transaction);
        renderTransactions();
    };

    source.onerror = (error) => {
        console.error('SSE error:', error);
    };
});