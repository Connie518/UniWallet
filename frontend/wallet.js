let myPieChart = null;
let rawRecords = [];
let rawCategories = [];
let rawItems = [];
let rawCurrencies = [];

window.addEventListener('DOMContentLoaded', async () => {
    await initWallet();
    setupEventListeners();
});

function setupEventListeners() {
    document.getElementById('logoutBtn').addEventListener('click', async (e) => {
        e.preventDefault();
        const response = await fetch(`${CONFIG.API_HOST}/api/logout`, { method: 'POST', credentials: 'include' });
        if (response.ok) window.location.href = 'index.html';
    });

    document.getElementById('filterStartDate').addEventListener('change', applyFilters);
    document.getElementById('filterEndDate').addEventListener('change', applyFilters);
    document.getElementById('filterCategory').addEventListener('change', applyFilters);
    document.getElementById('filterItem').addEventListener('change', applyFilters);
    document.getElementById('filterCurrency').addEventListener('change', applyFilters);

    document.getElementById('resetFilterBtn').addEventListener('click', resetFilters);
    
    document.getElementById('categorySelect').addEventListener('change', syncItemSelectOptions);

    document.getElementById('addRecordForm').addEventListener('submit', handleAddRecord);

    document.getElementById('cameraBtn').addEventListener('click', () => alert("正在開發中，拍照辨識功能尚未完成，請稍後再試。"));
    document.getElementById('voiceBtn').addEventListener('click', () => alert("正在開發中，語音輸入功能尚未完成，請稍後再試。"));
}

async function initWallet() {
    try {
        const response = await fetch(`${CONFIG.API_HOST}/api/wallet/data`, { credentials: 'include' });
        if (!response.ok) {
            window.location.href = 'index.html';
            return;
        }
        const data = await response.json();
        if (data.status === 'success') {
            document.getElementById('usernameDisplay').innerText = data.username;

            rawRecords = data.records;
            rawCategories = data.categories;
            rawItems = data.items;
            rawCurrencies = data.currencies;

            populateFilterSelectors();
            populateFormSelectors();
            renderRecordsTable(rawRecords);
            applyFilters();
        }
    } catch (error) {
        console.error('錢包初始化失敗   :', error);
        window.location.href = '/';
    }
}

function populateFilterSelectors() {
    const catFilter =document.getElementById('filterCategory');
    const itemFilter = document.getElementById('filterItem');
    const currencyFilter = document.getElementById('filterCurrency');

    catFilter.innerHTML = '<option value="all">所有類別</option>' + rawCategories.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
    itemFilter.innerHTML = '<option value="all">所有品項</option>' + rawItems.map(i => {
        const parentCat = rawCategories.find(c => c.id === i.category_id)?.name || '';
        return `<option value="${i.name}" data-category="${parentCat}">${i.name}</option>`;
    }).join('');
    currencyFilter.innerHTML = '<option value="all">所有貨幣</option>' + rawCurrencies.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
}

function populateFormSelectors() {
    document.getElementById('categorySelect').innerHTML = rawCategories.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
    document.getElementById('currencySelect').innerHTML = rawCurrencies.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
    syncItemSelectOptions();
}

function syncItemSelectOptions() {
    const selectCatName = document.getElementById('categorySelect').value;
    const targetCatId = rawCategories.find(c => c.name === selectCatName)?.id;
    const itemSelect = document.getElementById('itemSelect');

    const filtered = rawItems.filter(i => i.category_id === targetCatId);
    itemSelect.innerHTML = filtered.map(i => `<option value="${i.name}">${i.name}</option>`).join('');
}

function renderRecordsTable(records) {
    const tbody = document.getElementById('recordsTbody');
    if (records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: #888; padding: 20px;">目前尚無消費紀錄。</td></tr>`;
        return;
    }

    tbody.innerHTML = records.map(r => `
        <tr class="record-row" data-date="${r.date}" data-category="${r.category}" data-item="${r.item}" data-currency="${r.currency}" style="border-bottom: 1px solid #333;">
            <td>${r.date}</td>
            <td>${r.category}</td>
            <td>${r.item}</td>
            <td>${r.currency}</td>
            <td>${r.price}</td>
            <td class="twd-price">${r.twd}</td>
            <td>
                <span onclick="deleteRecord(${r.id})" style="color: #ff6b6b; cursor: pointer;">刪除</span>
            </td>
        </tr>
    `).join('') + `<tr id="noMatchedRow" style="display: none;"><td colspan="7" style="text-align: center; color: #888; padding: 20px;">沒有符合篩選條件的消費紀錄。</td></tr>`;
}

async function handleAddRecord(e) {
    e.preventDefault();
    const category = document.getElementById('categorySelect').value;
    const item = document.getElementById('itemSelect').value;
    const currency_name = document.getElementById('currencySelect').value;
    const price = document.getElementById('priceInput').value;

    if (!item) return alert('請確認是否已在編輯選單建立品項！');

    try {
        const response = await fetch(`${CONFIG.API_HOST}/api/record`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, item, currency_name, price}),
            credentials: 'include'
        });
        if (response.ok) {
            document.getElementById('priceInput').value = '';
            await initWallet();
        } else {
            const err = await response.json();
            alert(err.message);
        }
    } catch (e) {
        alert('新增消費紀錄失敗，請檢查網路連線。');
    }
}

window.deleteRecord = async function(id) {
    if (!confirm('確定刪除這筆紀錄嗎？')) return;
    try {
        const response = await fetch(`${CONFIG.API_HOST}/api/record/${id}`,  {
            method: 'DELETE',
            credentials: 'include'
        });
        if (response.ok) {
            await initWallet();
        }
    } catch (e) {
        alert('刪除失敗');
    }
}

function generateHslColors(count) {
    return Array.from({ length: count }, (_, i) => {
        const hue = (i * (360 / Math.max(count, 1))) % 360;
        return `hsl(${hue}, 50%, 50%)`;
    });
}

function applyFilters() {
    const startDate = document.getElementById('filterStartDate').value;
    const endDate = document.getElementById('filterEndDate').value;
    const fCategory = document.getElementById('filterCategory').value;
    const fItem = document.getElementById('filterItem').value;
    const fCurrency = document.getElementById('filterCurrency').value;

    const itemSelect = document.getElementById('filterItem');
    const itemOptions = itemSelect.querySelectorAll('option');

    // 如果這次是因為「切換類別」導致的，且目前選的品項不屬於新類別，就把品項歸零到 'all'
    let currentSelectedOption = itemSelect.options[itemSelect.selectedIndex];
    let currentItemCategory = currentSelectedOption.getAttribute('data-category');
    if (fCategory !== 'all' && currentItemCategory && currentItemCategory !== fCategory) {
        itemSelect.value = 'all';
    }

    // 根據選中的類別，顯示/隱藏品項選單裡的 option
    itemOptions.forEach(opt => {
        if (opt.value === 'all') return;
        const optCategory = opt.getAttribute('data-category');

        if (fCategory === 'all' || optCategory === fCategory) {
            opt.style.display = '';
        } else {
            opt.style.display = 'none';
        }
    });

    // 重新抓取最新（可能已經被重置為 all）的品項值
    const finalItem = itemSelect.value;
    const rows = document.querySelectorAll('.record-row');
    let visibleCount = 0;
    const currentFilteredTotals = {};

    rows.forEach(row => {
        const rowDate = row.getAttribute('data-date');
        const rowCategory = row.getAttribute('data-category');
        const rowItem = row.getAttribute('data-item');
        const rowCurrency = row.getAttribute('data-currency');

        let matchDate = true;
        if (startDate && rowDate < startDate) matchDate = false;
        if (endDate && rowDate > endDate) matchDate = false;

        const matchCategory = (fCategory === 'all' || rowCategory === fCategory);
        const matchItem = (fItem === 'all' || rowItem === finalItem);
        const matchCurrency = (fCurrency === 'all' || rowCurrency === fCurrency);

        if (matchDate && matchCategory && matchItem && matchCurrency) {
            row.style.display = '';
            visibleCount++;

            const twdCell = row.querySelector('.twd-price');
            if (twdCell) {
                const twdPrice = parseFloat(twdCell.innerText) || 0;
                currentFilteredTotals[rowCategory] = (currentFilteredTotals[rowCategory] || 0) + twdPrice;
            }
        } else {
            row.style.display = 'none';
        }
    });

    const noMatchesRow = document.getElementById('noMatchesRow');
    if (noMatchesRow) {
        if (visibleCount === 0) {
            noMatchesRow.style.display = '';
        } else {
            noMatchesRow.style.display = 'none';
        }
    }

    const labels = Object.keys(currentFilteredTotals);
    const dataValues = Object.values(currentFilteredTotals).map(val => parseFloat(val.toFixed(2)));

    const chartContainer = document.getElementById('chartContainer');
    const noDataHint = document.getElementById('noChartDataHint');

    if (labels.length === 0) {
        if (chartContainer) chartContainer.style.display = 'none';
        if (noDataHint) noDataHint.style.display = 'flex';

        if (myPieChart) {
            myPieChart.destroy();
            myPieChart = null;
        }
    } else {
        if (chartContainer) chartContainer.style.display = 'block';
        if (noDataHint) noDataHint.style.display = 'none';

        if (myPieChart) {
            myPieChart.data.labels = labels;
            myPieChart.data.datasets[0].data = dataValues;
            myPieChart.data.datasets[0].backgroundColor = generateHslColors(labels.length);
            myPieChart.update();
        } else {
            const ctx = document.getElementById('categoryPieChart').getContext('2d');
            myPieChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: dataValues,
                        backgroundColor: generateHslColors(labels.length),
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                color: '#fff',
                                font: { size: 16 }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `${context.label}: $${context.raw} TWD`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }
}

function resetFilters() {
    document.getElementById('filterStartDate').value = '';
    document.getElementById('filterEndDate').value = '';
    document.getElementById('filterCategory').value = 'all';
    document.getElementById('filterItem').value = 'all';
    document.getElementById('filterCurrency').value = 'all';
    applyFilters();
}

function triggerCamera() {
    alert("正在開發中，拍照辨識功能尚未完成，請稍後再試。");
    // const fileInput = document.createElement('input');
    // fileInput.type = 'file';
    // fileInput.accept = 'image/*';
    // fileInput.capture = 'environment';

    // fileInput.onchange = (e) => {
    //     const file = e.target.files[0];
    //     if (file) {

    //     }
    // };

    // fileInput.click();
}

function triggerVoice() {
    alert("正在開發中，語音辨識功能尚未完成，請稍後再試。");
    // // 檢查瀏覽器有沒有支援語音辨識
    // const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    // if (!SpeechRecognition) {
    //     alert("很抱歉，您的瀏覽器不支援語音辨識功能，建議使用 Chrome 或 Safari！");
    //     return;
    // }

    // const recognition = new SpeechRecognition();
    // recognition.lang = 'zh-TW'; // 設定語音為繁體中文
    // recognition.interimResults = false; // 只拿最終結果

    // // 提示使用者正在錄音
    // const voiceBtn = document.querySelector('button[onclick="triggerVoice()"]');
    // const originalText = voiceBtn.innerText;
    // voiceBtn.innerText = "🎙️ 聆聽中...";
    // voiceBtn.style.background = "#ff6b6b";

    // recognition.start();

    // // 辨識成功
    // recognition.onresult = (event) => {
    //     const resultText = event.results[0][0].transcript;
    //     alert(`聽到你說：「${resultText}」\n（之後可將這串文字送給 AI 拆解成類別、品項與金額）`);
        
    //     // 【預留功能：自動填入輸入框範例】
    //     // 假設使用者大喊數字，我們可以試著幫他填入金額欄位
    //     const numbers = resultText.match(/\d+/);
    //     if (numbers) {
    //         const priceInput = document.querySelector('input[name="price"]');
    //         if (priceInput) priceInput.value = numbers[0];
    //     }
    // };

    // // 辨識結束（不論成功或失敗）
    // recognition.onend = () => {
    //     voiceBtn.innerText = originalText;
    //     voiceBtn.style.background = "#444";
    // };

    // // 發生錯誤
    // recognition.onerror = (event) => {
    //     alert("語音辨識發生錯誤: " + event.error);
    // };
}