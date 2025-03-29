document.addEventListener('DOMContentLoaded', () => {
    let allAlerts = [];

    // Функция для отображения логов с учётом фильтра
    const tableBody = document.getElementById('transactions-table');
    const filterSelect = document.getElementById('filter-status');
    const renderAlerts = () => {
        const filter = filterSelect.value;
        tableBody.innerHTML = '';
        allAlerts.forEach(alert => {
            const attackStatus = alert.attack_status.toLowerCase();
            if (filter === 'all' ||
                (filter === 'normal' && attackStatus === 'normal') ||
                (filter === 'attack' && attackStatus === 'attack')) {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${new Date(alert.timestamp * 1000).toLocaleString()}</td>
                    <td class="${attackStatus}">
                        ${alert.attack_status}
                    </td>
                    <td>${alert.rf_prediction}</td>
                    <td>${alert.dt_prediction}</td>
                    <td>${alert.src_ip}</td>
                    <td>${alert.dst_ip}</td>
                    <td>${alert.src_port}</td>
                    <td>${alert.dst_port}</td>
                    <td>${alert.protocol}</td>
                `;
                tableBody.prepend(row);
            }
        });
    };

    // Обработка фильтра
    filterSelect.addEventListener('change', renderAlerts);

    // Обработка кнопки очистки таблицы
    const clearButton = document.getElementById('clear-table');
    clearButton.addEventListener('click', () => {
        allAlerts = [];
        renderAlerts();
    });

    // Подключение к SSE для получения логов в реальном времени
    const source = new EventSource('/stream');
    source.onmessage = (event) => {
        const alert = JSON.parse(event.data);
        allAlerts.unshift(alert);
        renderAlerts();
    };

    source.onerror = (error) => {
        console.error('SSE error:', error);
    };
});