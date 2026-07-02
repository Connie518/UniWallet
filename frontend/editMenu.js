let allItems = [];
let currentManageCategory = "";

window.addEventListener('DOMContentLoaded', async () => {
    await fetchMenuData();

    const addCatBtn = document.getElementById('addCategoryBtn');
    if (addCatBtn) addCatBtn.addEventListener('click', addNewCategory);

    const addItemBtn = document.getElementById('addItemBtn');
    if (addItemBtn) addItemBtn.addEventListener('click', addNewItem);

    const addCurBtn = document.getElementById('addCurrencyBtn');
    if (addCurBtn) addCurBtn.addEventListener('click', addNewCurrency);

    document.getElementById('logoutBtn').addEventListener('click', async (e) => {
        e.preventDefault();
        const response = await fetch(`${CONFIG.API_HOST}/api/logout`, { method: 'POST', credentials: 'include'});
        if (response.ok) window.location.href = 'index.html';
    });
});

async function apiFetch(url, option = {}) {
    option.credentials = 'include';
    if (option.body && typeof option.body === 'object') {
        option.headers = { ...option.headers, 'Content-Type': 'application/json' };
        option.body = JSON.stringify(option.body);
    }
    const response = await fetch(`${CONFIG.API_HOST}${url}`, option);
    if (response.status === 401) {
        window.location.href = 'index.html';
        return;
    }
    return response;
}

async function fetchMenuData() {
    const response = await apiFetch('/api/wallet/data');
    if (!response) return;
    const data = await response.json();

    if (data.status === 'success') {
        const userDisplay = document.getElementById('usernameDisplay');
        if (userDisplay) userDisplay.innerHTML = data.username;
        allItems = data.items;

        renderCategories(data.categories);
        renderCurrencies(data.currencies);
        resetItemSection();
    }
}

function renderCategories(categories) {
    const tbody = document.getElementById('categoriesTbody');
    if (categories.length === 0) {
        tbody.innerHTML = `<tr id="noCategoriesRow"><td colspan="2" style="text-align: center; color: #888; padding: 20px;">目前尚無類別。</td></tr>`;
        return;
    }

    tbody.innerHTML = categories.map(cat => `
        <tr id="cat-row-${cat.id}" class="category-manage-row" onclick="selectCategoryForManage('${cat.name}', this)" style="border-bottom: 1px solid #333; cursor: pointer;">
            <td style="padding: 8px; text-align: left; padding-left: 15px; width: 70px;">
                <button type="button" style="color: #fff; border: none; padding: 2px 10px; font-size: 1em; border-radius: 4px; cursor: pointer; margin: 0;">選擇</button>
            </td>
            <td style="padding: 8px; text-align: left; padding-left: 30px;">${cat.name}</td>
            <td style="padding: 8px; text-align: right; padding-right: 15px;">
                <span onclick="event.stopPropagation(); deleteCategory(${cat.id}, '${cat.name}')" style="color: #ff6b6b; cursor: pointer;">刪除</span>
            </td>
        </tr>
    `).join('');
}

async function addNewCategory() {
    const input = document.getElementById('newCategoryInput');
    const name = input.value.trim();
    if (!name) return alert('請輸入類別名稱');

    const response = await apiFetch('/api/category', { method: 'POST', body: { name } });
    const data = await response.json();
    if (response.ok) {
        input.value = '';
        await fetchMenuData();
    } else {
        alert(data.message);
    }
}

async function deleteCategory(id, name) {
    if (!confirm(`確定要刪除「${name}」嗎？該類別底下的所有品項也會一併被刪除！`)) return;
    const response = await apiFetch(`/api/category/${id}`, { method: 'DELETE' });
    if (response.ok) await fetchMenuData();
}

function resetItemSection() {
    document.getElementById('selectedCategoryTitle').innerText = '';
    document.getElementById('addItemSection').style.display = 'none';
    document.getElementById('itemsTbody').innerHTML = `
        <tr id="pleaseSelectHint"><td colspan="2" style="text-align: center; color: #888; padding: 40px 0;">請先點擊類別來管理項目。</td></tr>
    `;
    currentManageCategory = '';
}

function selectCategoryForManage(categoryName, element) {
    currentManageCategory = categoryName;
    
    document.querySelectorAll('.category-manage-row').forEach(row => {
        row.style.backgroundColor = '';
        const btn = row.querySelector('button[type="button"]');
        if (btn) {
            btn.innerText = '選擇';
            btn.style.backgroundColor = '';
        }
    });
    
    element.style.backgroundColor = '#333'; 
    const currentBtn = element.querySelector('button[type="button"]');
    if (currentBtn) {
        currentBtn.style.backgroundColor = '#4dadf7';
        currentBtn.innerText = '已選';
    }
    
    document.getElementById('selectedCategoryTitle').innerText = ` - 正在編輯「${categoryName}」`;
    document.getElementById('addItemSection').style.display = 'flex';

    // 篩選品項
    const catRow = element.innerText;
    const filteredItems = allItems.filter(item => {
        return true;
    });

    renderItems(categoryName);
}

function renderItems(categoryName) {
    const tbody = document.getElementById('itemsTbody');
    const resRows = allItems.filter(i => {
        return true;
    })

    let hasItems = 0;
    tbody.innerHTML = allItems.map(item => {
        return `
            <tr class="item-manage-row" data-item-cat="${categoryName}" style="border-bottom: 1px solid #333;">
                <td style="padding: 8px; padding-left: 15px;">${item.name}</td>
                <td style="padding: 8px; text-align: right; padding-right: 15px;">
                    <span onclick="deleteItem(${item.id}, '${item.name}')" style="color: #ff6b6b; cursor: pointer;">刪除</span>
                </td>
        `;
    }).join('');

    const rows = tbody.querySelectorAll('.item-manage-row');
    refreshItemsView(categoryName);
}

function refreshItemsView(categoryName) {
    const tbody = document.getElementById('itemsTbody');
    tbody.innerHTML = '';

    const activeCatRow = document.querySelector('.category-manage-row[style*="background-color: rgb(51, 51, 51)"]');
    if (!activeCatRow) return;
    const catId = activeCatRow.id.replace('cat-row-', '');

    const targetItems = allItems.filter(i => String(i.category_id) === String(catId));

    if (targetItems.length === 0) {
        tbody.innerHTML = `<tr id="noItemsHint"><td colspan="2" style="text-align: center; color: #888; padding: 40px 0;">該類別目前尚無項目。</td></tr>`;
        return;
    }

    tbody.innerHTML = targetItems.map(item => `
        <tr class="item-manage-row" style="border-bottom: 1px solid #333;"> 
            <td style="padding: 8px; padding-left: 15px;">${item.name}</td>
            <td style="padding: 8px; text-align: right; padding-right: 15px;">
                <span onclick="deleteItem(${item.id}, '${item.name}')" style="color: #ff6b6b; cursor: pointer;">刪除</span>
            </td>
        </tr>
    `).join('');
}

async function addNewItem() {
    const input = document.getElementById('newItemInput');
    const name = input.value.trim();
    if (!name) return alert('請輸入品項');

    const response = await apiFetch('/api/item', {
        method: 'POST',
        body: { name, category_name: currentManageCategory }
    });
    if (response.ok) {
        input.value = '';
        const dataRes = await apiFetch('/api/wallet/data');
        const data = await dataRes.json();
        allItems = data.items;
        refreshItemsView(currentManageCategory);
    }
}

async function deleteItem(id, name) {
    if (!confirm(`確定要刪除「${name}」嗎？`)) return;
    const response = await apiFetch(`/api/item/${id}`, { method: 'DELETE' });
    if (response.ok) {
        const dataRes = await apiFetch('/api/wallet/data');
        const data = await dataRes.json();
        allItems = data.items;
        refreshItemsView(currentManageCategory);
    }
}

function renderCurrencies(currencies) {
    const tbody = document.getElementById('currenciesTbody');
    if (currencies.length === 0) {
        tbody.innerHTML = `<tr id="noCurrenciesRow"><td colspan="3" style="text-align: center; color: #888; padding: 40px 0;">目前尚無幣別。</td></tr>`;
        return;
    }

    tbody.innerHTML = currencies.map(cur => `
        <tr id="cur-row-${cur.id}" class="currency-manage-row" style="border-bottom: 1px solid #333;">
            <td style="padding: 8px; text-align: left; padding-left: 15px; color: #fff; font-weight: bold;">${cur.name}</td>
            <td style="padding: 8px; text-align: left; padding-left: 15px; color: #fff;">${cur.rate}</td>
            <td style="padding: 8px; text-align: right; padding-right: 15px;">
                <span onclick="deleteCurrency(${cur.id}, '${cur.name}')" style="color: #ff6b6b; cursor: pointer;">刪除</span>
            </td>
        </tr>
    `).join('');
}

async function addNewCurrency() {
    const inputCurrency = document.getElementById('newCurrencyInput');
    const inputRate = document.getElementById('newRateInput');
    const name = inputCurrency.value.trim().toUpperCase();
    const rate = inputRate.value.trim();

    if (!name) return alert('請輸入幣別');

    const response = await apiFetch('/api/currency', { method: 'POST', body: { name, rate } });
    const data = await response.json();
    if (response.ok) {
        inputCurrency.value = '';
        inputRate.value = '';
        await fetchMenuData();
    } else {
        alert(data.message);
    }
}

async function deleteCurrency(id, name) {
    if (!confirm(`確定要刪除「${name}」嗎？`)) return;
    const response = await apiFetch(`/api/currency/${id}`, { method: 'DELETE' });
    if (response.ok) await fetchMenuData();
}