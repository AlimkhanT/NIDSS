document.addEventListener('DOMContentLoaded', () => {
    let allAlerts = [];
    let normalCounter = 0; // Счётчик для нормальных логов

    // Функция для отображения логов с учётом фильтра
    const tableBody = document.getElementById('transactions-table');
    const filterSelect = document.getElementById('filter-status');
    const renderAlerts = () => {
        const filter = filterSelect.value;
        tableBody.innerHTML = '';
        normalCounter = 0; // Сбрасываем счётчик при каждом рендере

        allAlerts.forEach(alert => {
            const attackStatus = alert.attack_status.toLowerCase();
            let shouldDisplay = false;

            if (attackStatus === 'attack') {
                // Все атаки отображаются всегда
                shouldDisplay = true;
            } else if (attackStatus === 'normal') {
                // Для нормальных логов увеличиваем счётчик
                normalCounter++;
                // Отображаем только каждый десятый нормальный лог
                if (normalCounter % 10 === 0) {
                    shouldDisplay = true;
                }
            }

            // Применяем фильтр
            if (filter === 'all' && shouldDisplay) {
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
                tableBody.prepend(row); // Добавляем строку сверху
            } else if (filter === 'attack' && attackStatus === 'attack') {
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
                tableBody.prepend(row); // Добавляем строку сверху
            }
        });
    };

    // Обработка фильтра
    filterSelect.addEventListener('change', renderAlerts);

    // Обработка кнопки очистки таблицы
    const clearButton = document.getElementById('clear-table');
    clearButton.addEventListener('click', () => {
        allAlerts = [];
        normalCounter = 0; // Сбрасываем счётчик
        renderAlerts();
    });

    // Подключение к SSE для получения логов в реальном времени
    const source = new EventSource('/stream');
    source.onmessage = (event) => {
        const alert = JSON.parse(event.data);
        allAlerts.unshift(alert); // Добавляем новый лог в начало массива
        renderAlerts();
    };

    source.onerror = (error) => {
        console.error('SSE error:', error);
    };
});