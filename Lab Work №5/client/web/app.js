const API_BASE = "/api/v1";

const STATUS_TITLE = {
  placed: "Принят",
  in_preparation: "Готовится",
  ready_for_pickup: "Готов к выдаче",
  out_for_delivery: "Передан курьеру",
  delivered: "Завершен",
  cancelled: "Отменен",
};

const FULFILLMENT_TITLE = {
  pickup: "Самовывоз",
  delivery: "Доставка",
};

const CHANNEL_TITLE = {
  push: "Push",
  email: "Email",
};

const state = {
  selectedOrderId: null,
  selectedCustomerId: null,
  orders: [],
  customers: [],
};

const refs = {
  healthBadge: document.getElementById("healthBadge"),
  ordersBody: document.getElementById("ordersBody"),
  customersBody: document.getElementById("customersBody"),
  detailsContent: document.getElementById("detailsContent"),
  selectedOrderId: document.getElementById("selectedOrderId"),
  orderTimeline: document.getElementById("orderTimeline"),
  notificationsBox: document.getElementById("notificationsBox"),
  logBox: document.getElementById("logBox"),
  orderHint: document.getElementById("orderHint"),
};

function logLine(message, level = "INFO") {
  const now = new Date().toISOString().replace("T", " ").slice(0, 19);
  refs.logBox.textContent = `[${now}] ${level} ${message}\n${refs.logBox.textContent}`.slice(0, 9000);
}

function normalizeStatus(value) {
  return STATUS_TITLE[value] || value;
}

function normalizeFulfillment(value) {
  return FULFILLMENT_TITLE[value] || value;
}

function yesNo(value) {
  return value ? "Да" : "Нет";
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { raw: text };
    }
  }
  if (!response.ok) {
    const error = payload?.error || `HTTP ${response.status}`;
    throw new Error(error);
  }
  return payload;
}

function setHealth(ok, details = "") {
  if (ok) {
    refs.healthBadge.textContent = `API: доступен ${details}`.trim();
    refs.healthBadge.className = "health health-ok";
  } else {
    refs.healthBadge.textContent = `API: ошибка ${details}`.trim();
    refs.healthBadge.className = "health health-fail";
  }
}

async function checkHealth() {
  try {
    const result = await api("/health", { method: "GET" });
    setHealth(true, `(status=${result.status || "ok"})`);
    logLine("Проверка API выполнена.");
  } catch (error) {
    setHealth(false, `(${error.message})`);
    logLine(`Ошибка проверки API: ${error.message}`, "ERROR");
  }
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ru-RU");
}

function renderCustomers() {
  refs.customersBody.innerHTML = "";
  const filter = document.getElementById("customerSearchFilter").value.trim().toLowerCase();
  const items = state.customers.filter((item) => {
    if (!filter) {
      return true;
    }
    return item.customer_id.toLowerCase().includes(filter) || item.name.toLowerCase().includes(filter);
  });

  for (const item of items) {
    const tr = document.createElement("tr");
    if (item.customer_id === state.selectedCustomerId) {
      tr.classList.add("active");
    }
    tr.innerHTML = `
      <td>${item.customer_id}</td>
      <td>${item.name}</td>
      <td>${item.email || "-"}</td>
      <td>${yesNo(item.push_enabled)}</td>
      <td>${yesNo(item.email_enabled)}</td>
    `;
    tr.addEventListener("click", () => {
      state.selectedCustomerId = item.customer_id;
      document.querySelector("#orderForm input[name='customer_id']").value = item.customer_id;
      renderCustomers();
      logLine(`Выбран клиент ${item.customer_id} для создания заказа.`);
    });
    refs.customersBody.appendChild(tr);
  }
}

async function loadCustomers() {
  try {
    const result = await api("/customers", { method: "GET" });
    state.customers = result.items || [];
    renderCustomers();
    logLine(`Загружено клиентов: ${state.customers.length}.`);
  } catch (error) {
    logLine(`Ошибка загрузки клиентов: ${error.message}`, "ERROR");
  }
}

function renderOrders() {
  refs.ordersBody.innerHTML = "";
  for (const item of state.orders) {
    const tr = document.createElement("tr");
    if (item.order_id === state.selectedOrderId) {
      tr.classList.add("active");
    }
    tr.innerHTML = `
      <td>${item.order_id}</td>
      <td>${item.customer_id}</td>
      <td>${item.store_id}</td>
      <td><span class="status-badge">${normalizeStatus(item.status)}</span></td>
      <td>${normalizeFulfillment(item.fulfillment)}</td>
      <td>${item.total_amount}</td>
      <td>${formatDate(item.updated_at)}</td>
    `;
    tr.addEventListener("click", () => {
      state.selectedOrderId = item.order_id;
      showDetails(item);
      renderOrders();
    });
    refs.ordersBody.appendChild(tr);
  }
}

async function loadOrders() {
  try {
    const status = document.getElementById("statusFilter").value.trim();
    const customerId = document.getElementById("customerFilter").value.trim();
    const query = new URLSearchParams();
    if (status) {
      query.set("status", status);
    }
    if (customerId) {
      query.set("customer_id", customerId);
    }
    const suffix = query.toString() ? `?${query.toString()}` : "";
    const result = await api(`/orders${suffix}`, { method: "GET" });
    state.orders = result.items || [];
    renderOrders();
    logLine(`Загружено заказов: ${state.orders.length}.`);
    if (state.selectedOrderId) {
      const selected = state.orders.find((item) => item.order_id === state.selectedOrderId);
      if (selected) {
        showDetails(selected);
      }
    }
  } catch (error) {
    logLine(`Ошибка загрузки заказов: ${error.message}`, "ERROR");
  }
}

function showDetails(order) {
  refs.orderHint.classList.add("hidden");
  refs.detailsContent.classList.remove("hidden");
  refs.selectedOrderId.textContent = order.order_id;
  refs.orderTimeline.innerHTML = "";
  for (const stateName of order.history || []) {
    const step = document.createElement("div");
    step.className = "timeline-step";
    step.textContent = normalizeStatus(stateName);
    refs.orderTimeline.appendChild(step);
  }
}

async function loadOrderById(orderId) {
  const order = await api(`/orders/${orderId}`, { method: "GET" });
  const index = state.orders.findIndex((item) => item.order_id === orderId);
  if (index >= 0) {
    state.orders[index] = order;
  } else {
    state.orders.unshift(order);
  }
  showDetails(order);
  renderOrders();
}

async function createCustomer(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = {
    customer_id: form.customer_id.value.trim(),
    name: form.name.value.trim(),
    email: form.email.value.trim() || null,
    push_token: form.push_token.value.trim() || null,
    push_enabled: form.push_enabled.checked,
    email_enabled: form.email_enabled.checked,
  };
  try {
    const created = await api("/customers", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    logLine(`Клиент ${created.customer_id} создан.`);
    form.reset();
    form.push_enabled.checked = true;
    form.email_enabled.checked = true;
    await loadCustomers();
  } catch (error) {
    logLine(`Не удалось создать клиента: ${error.message}`, "ERROR");
  }
}

async function createOrder(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = {
    order_id: form.order_id.value.trim(),
    customer_id: form.customer_id.value.trim(),
    store_id: form.store_id.value.trim(),
    fulfillment: form.fulfillment.value,
    total_amount: Number(form.total_amount.value),
  };
  try {
    const created = await api("/orders", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.selectedOrderId = created.order_id;
    await loadOrders();
    await loadOrderById(created.order_id);
    logLine(`Заказ ${created.order_id} создан.`);
    form.reset();
    form.fulfillment.value = "pickup";
    form.total_amount.value = "350";
    if (state.selectedCustomerId) {
      form.customer_id.value = state.selectedCustomerId;
    }
  } catch (error) {
    logLine(`Не удалось создать заказ: ${error.message}`, "ERROR");
  }
}

async function updateOrder(event) {
  event.preventDefault();
  if (!state.selectedOrderId) {
    logLine("Сначала выбери заказ в таблице.", "ERROR");
    return;
  }
  const form = event.currentTarget;
  const payload = {};
  if (form.store_id.value.trim()) {
    payload.store_id = form.store_id.value.trim();
  }
  if (form.fulfillment.value) {
    payload.fulfillment = form.fulfillment.value;
  }
  if (form.total_amount.value.trim()) {
    payload.total_amount = Number(form.total_amount.value);
  }
  if (Object.keys(payload).length === 0) {
    logLine("Нет данных для обновления.", "ERROR");
    return;
  }
  try {
    await api(`/orders/${state.selectedOrderId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    await loadOrderById(state.selectedOrderId);
    logLine(`Заказ ${state.selectedOrderId} обновлен.`);
    form.reset();
  } catch (error) {
    logLine(`Ошибка обновления заказа: ${error.message}`, "ERROR");
  }
}

async function changeStatus(event) {
  event.preventDefault();
  if (!state.selectedOrderId) {
    logLine("Сначала выбери заказ в таблице.", "ERROR");
    return;
  }
  const status = event.currentTarget.status.value;
  try {
    await api(`/orders/${state.selectedOrderId}/status`, {
      method: "POST",
      body: JSON.stringify({ status }),
    });
    await loadOrderById(state.selectedOrderId);
    logLine(`Статус заказа ${state.selectedOrderId} изменен на ${normalizeStatus(status)}.`);
  } catch (error) {
    logLine(`Ошибка смены статуса: ${error.message}`, "ERROR");
  }
}

async function loadNotifications() {
  if (!state.selectedOrderId) {
    logLine("Сначала выбери заказ в таблице.", "ERROR");
    return;
  }
  try {
    const result = await api(`/orders/${state.selectedOrderId}/notifications`, { method: "GET" });
    const items = result.items || [];
    refs.notificationsBox.innerHTML = "";
    if (items.length === 0) {
      refs.notificationsBox.textContent = "Уведомления не найдены.";
      return;
    }
    for (const item of items) {
      const card = document.createElement("article");
      card.className = "notif";
      card.innerHTML = `
        <p><strong>${CHANNEL_TITLE[item.channel] || item.channel}</strong> -> ${item.recipient}</p>
        <p>${item.message}</p>
        <small>${formatDate(item.created_at)}</small>
      `;
      refs.notificationsBox.appendChild(card);
    }
    logLine(`Загружено уведомлений: ${items.length}.`);
  } catch (error) {
    logLine(`Ошибка загрузки уведомлений: ${error.message}`, "ERROR");
  }
}

async function deleteOrder() {
  if (!state.selectedOrderId) {
    logLine("Сначала выбери заказ в таблице.", "ERROR");
    return;
  }
  const orderId = state.selectedOrderId;
  try {
    await api(`/orders/${orderId}`, { method: "DELETE" });
    state.selectedOrderId = null;
    refs.detailsContent.classList.add("hidden");
    refs.orderHint.classList.remove("hidden");
    refs.notificationsBox.innerHTML = "";
    await loadOrders();
    logLine(`Заказ ${orderId} удален.`);
  } catch (error) {
    logLine(`Ошибка удаления заказа: ${error.message}`, "ERROR");
  }
}

function bindEvents() {
  document.getElementById("checkHealthBtn").addEventListener("click", checkHealth);
  document.getElementById("refreshCustomersBtn").addEventListener("click", loadCustomers);
  document.getElementById("refreshOrdersBtn").addEventListener("click", loadOrders);
  document.getElementById("applyCustomerFilterBtn").addEventListener("click", renderCustomers);
  document.getElementById("applyFilterBtn").addEventListener("click", loadOrders);
  document.getElementById("customerForm").addEventListener("submit", createCustomer);
  document.getElementById("orderForm").addEventListener("submit", createOrder);
  document.getElementById("updateOrderForm").addEventListener("submit", updateOrder);
  document.getElementById("statusForm").addEventListener("submit", changeStatus);
  document.getElementById("loadNotificationsBtn").addEventListener("click", loadNotifications);
  document.getElementById("deleteOrderBtn").addEventListener("click", deleteOrder);
}

async function bootstrap() {
  bindEvents();
  await checkHealth();
  await loadCustomers();
  await loadOrders();
}

bootstrap();
