// ZOE Outage Widget для Scriptable
// Віджет відображення графіків відключення електроенергії
// Автор: ZOE API Project
// Версія: 1.0.0

// ========================================
// НАЛАШТУВАННЯ
// ========================================

const CONFIG = {
  // URL вашого API (змініть на свій після deployment)
  API_BASE_URL: "http://localhost:8000",

  // Черга за замовчуванням (можна змінити через widget parameter)
  DEFAULT_QUEUE: "1.1",

  // Таймаут запиту (секунди)
  REQUEST_TIMEOUT: 10,

  // Час життя кешу (хвилини)
  CACHE_DURATION: 30,

  // Кольори
  COLORS: {
    powerOn: new Color("#4CAF50"),      // Зелений - є світло
    powerOff: new Color("#F44336"),     // Червоний - немає світла
    background: new Color("#1E1E1E"),   // Темний фон
    textPrimary: new Color("#FFFFFF"),  // Білий текст
    textSecondary: new Color("#B0B0B0"),// Сірий текст
    cardBackground: new Color("#2D2D2D") // Фон карток
  }
};

// ========================================
// ГОЛОВНА ФУНКЦІЯ
// ========================================

// Отримати параметр віджету (номер черги)
const widgetParam = args.widgetParameter || CONFIG.DEFAULT_QUEUE;
const selectedQueue = widgetParam.trim();

// Створити віджет
const widget = await createWidget(selectedQueue);

// Відобразити віджет
if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  // Показати preview в додатку
  widget.presentMedium();
}

Script.complete();

// ========================================
// СТВОРЕННЯ ВІДЖЕТУ
// ========================================

async function createWidget(queue) {
  const widget = new ListWidget();

  // Встановити фон
  widget.backgroundColor = CONFIG.COLORS.background;

  try {
    // Завантажити дані з API
    const scheduleData = await fetchSchedule(queue);

    if (!scheduleData || !scheduleData.success) {
      return createErrorWidget(widget, "Помилка завантаження даних");
    }

    const queueData = scheduleData.queue_data;

    // Визначити розмір віджету та побудувати відповідний UI
    const family = config.widgetFamily || "medium";

    if (family === "small") {
      buildSmallWidget(widget, queueData);
    } else if (family === "medium") {
      buildMediumWidget(widget, queueData);
    } else {
      buildLargeWidget(widget, queueData);
    }

  } catch (error) {
    console.error("Widget error: " + error.message);

    // Спробувати завантажити з кешу
    const cachedData = loadFromCache(queue);
    if (cachedData) {
      buildMediumWidget(widget, cachedData);

      // Додати індикатор кешу
      widget.addSpacer(4);
      const cacheText = widget.addText("📦 Кешовані дані");
      cacheText.font = Font.systemFont(8);
      cacheText.textColor = CONFIG.COLORS.textSecondary;
      cacheText.textOpacity = 0.6;
    } else {
      return createErrorWidget(widget, error.message);
    }
  }

  return widget;
}

// ========================================
// UI ДЛЯ МАЛОГО ВІДЖЕТУ
// ========================================

function buildSmallWidget(widget, queueData) {
  const isOff = isCurrentlyOff(queueData.outages);
  const statusColor = isOff ? CONFIG.COLORS.powerOff : CONFIG.COLORS.powerOn;

  // Заголовок з номером черги
  const header = widget.addText(`⚡️ ${queueData.queue}`);
  header.font = Font.boldSystemFont(16);
  header.textColor = CONFIG.COLORS.textPrimary;

  widget.addSpacer(8);

  // Статус
  const statusStack = widget.addStack();
  statusStack.layoutHorizontally();
  statusStack.centerAlignContent();

  const statusDot = statusStack.addText("●");
  statusDot.font = Font.systemFont(20);
  statusDot.textColor = statusColor;

  statusStack.addSpacer(6);

  const statusText = statusStack.addText(isOff ? "Немає світла" : "Є світло");
  statusText.font = Font.semiboldSystemFont(14);
  statusText.textColor = statusColor;

  widget.addSpacer(8);

  // Наступна подія
  const nextEvent = getNextEvent(queueData.outages);
  if (nextEvent) {
    const eventText = widget.addText(nextEvent.isOutage ? `🔌 ${nextEvent.time}` : `💡 ${nextEvent.time}`);
    eventText.font = Font.systemFont(12);
    eventText.textColor = CONFIG.COLORS.textSecondary;
  }

  widget.addSpacer();

  // Час оновлення
  const updateTime = widget.addText(getUpdateTime());
  updateTime.font = Font.systemFont(8);
  updateTime.textColor = CONFIG.COLORS.textSecondary;
  updateTime.textOpacity = 0.6;
}

// ========================================
// UI ДЛЯ СЕРЕДНЬОГО ВІДЖЕТУ
// ========================================

function buildMediumWidget(widget, queueData) {
  const isOff = isCurrentlyOff(queueData.outages);
  const statusColor = isOff ? CONFIG.COLORS.powerOff : CONFIG.COLORS.powerOn;

  // Заголовок
  const headerStack = widget.addStack();
  headerStack.layoutHorizontally();
  headerStack.centerAlignContent();

  const title = headerStack.addText(`⚡️ Черга ${queueData.queue}`);
  title.font = Font.boldSystemFont(16);
  title.textColor = CONFIG.COLORS.textPrimary;

  headerStack.addSpacer();

  const statusDot = headerStack.addText("●");
  statusDot.font = Font.systemFont(16);
  statusDot.textColor = statusColor;

  widget.addSpacer(12);

  // Статус великими літерами
  const statusText = widget.addText(isOff ? "НЕМАЄ СВІТЛА" : "Є СВІТЛО");
  statusText.font = Font.boldSystemFont(18);
  statusText.textColor = statusColor;

  widget.addSpacer(12);

  // Графік відключень
  const scheduleTitle = widget.addText("📅 Графік на сьогодні:");
  scheduleTitle.font = Font.semiboldSystemFont(12);
  scheduleTitle.textColor = CONFIG.COLORS.textSecondary;

  widget.addSpacer(6);

  // Відобразити всі відключення
  for (let i = 0; i < Math.min(queueData.outages.length, 3); i++) {
    const outage = queueData.outages[i];
    const outageStack = widget.addStack();
    outageStack.layoutHorizontally();

    const timeText = outageStack.addText(`🔌 ${outage.start} - ${outage.end}`);
    timeText.font = Font.systemFont(12);
    timeText.textColor = CONFIG.COLORS.textPrimary;

    if (i < queueData.outages.length - 1) {
      widget.addSpacer(4);
    }
  }

  widget.addSpacer();

  // Час оновлення
  const updateTime = widget.addText(getUpdateTime());
  updateTime.font = Font.systemFont(8);
  updateTime.textColor = CONFIG.COLORS.textSecondary;
  updateTime.textOpacity = 0.6;
}

// ========================================
// UI ДЛЯ ВЕЛИКОГО ВІДЖЕТУ
// ========================================

function buildLargeWidget(widget, queueData) {
  const isOff = isCurrentlyOff(queueData.outages);
  const statusColor = isOff ? CONFIG.COLORS.powerOff : CONFIG.COLORS.powerOn;

  // Заголовок
  const headerStack = widget.addStack();
  headerStack.layoutHorizontally();
  headerStack.centerAlignContent();

  const title = headerStack.addText(`⚡️ Графік відключень`);
  title.font = Font.boldSystemFont(18);
  title.textColor = CONFIG.COLORS.textPrimary;

  headerStack.addSpacer();

  const queueBadge = headerStack.addText(queueData.queue);
  queueBadge.font = Font.boldSystemFont(14);
  queueBadge.textColor = CONFIG.COLORS.background;
  queueBadge.backgroundColor = statusColor;
  queueBadge.cornerRadius = 6;
  queueBadge.setPadding(4, 8, 4, 8);

  widget.addSpacer(12);

  // Поточний статус - велика картка
  const statusCard = widget.addStack();
  statusCard.layoutVertically();
  statusCard.backgroundColor = CONFIG.COLORS.cardBackground;
  statusCard.cornerRadius = 12;
  statusCard.setPadding(12, 16, 12, 16);

  const statusLabel = statusCard.addText("ПОТОЧНИЙ СТАТУС");
  statusLabel.font = Font.semiboldSystemFont(10);
  statusLabel.textColor = CONFIG.COLORS.textSecondary;

  statusCard.addSpacer(4);

  const mainStatus = statusCard.addText(isOff ? "НЕМАЄ СВІТЛА" : "Є СВІТЛО");
  mainStatus.font = Font.boldSystemFont(24);
  mainStatus.textColor = statusColor;

  widget.addSpacer(12);

  // Наступна подія
  const nextEvent = getNextEvent(queueData.outages);
  if (nextEvent) {
    const nextLabel = widget.addText(nextEvent.isOutage ? "⏰ Наступне відключення:" : "⏰ Відновлення світла:");
    nextLabel.font = Font.semiboldSystemFont(12);
    nextLabel.textColor = CONFIG.COLORS.textSecondary;

    widget.addSpacer(4);

    const nextTime = widget.addText(nextEvent.time);
    nextTime.font = Font.boldSystemFont(20);
    nextTime.textColor = CONFIG.COLORS.textPrimary;

    widget.addSpacer(12);
  }

  // Повний графік
  const scheduleTitle = widget.addText("📅 Повний графік:");
  scheduleTitle.font = Font.semiboldSystemFont(12);
  scheduleTitle.textColor = CONFIG.COLORS.textSecondary;

  widget.addSpacer(6);

  for (const outage of queueData.outages) {
    const outageStack = widget.addStack();
    outageStack.layoutHorizontally();

    const timeText = outageStack.addText(`🔌 ${outage.start} - ${outage.end}`);
    timeText.font = Font.systemFont(13);
    timeText.textColor = CONFIG.COLORS.textPrimary;

    widget.addSpacer(3);
  }

  widget.addSpacer();

  // Час оновлення
  const updateTime = widget.addText(getUpdateTime());
  updateTime.font = Font.systemFont(9);
  updateTime.textColor = CONFIG.COLORS.textSecondary;
  updateTime.textOpacity = 0.6;
}

// ========================================
// ВІДЖЕТ ПОМИЛКИ
// ========================================

function createErrorWidget(widget, errorMessage) {
  widget.backgroundColor = CONFIG.COLORS.background;

  const errorIcon = widget.addText("⚠️");
  errorIcon.font = Font.systemFont(32);

  widget.addSpacer(8);

  const errorTitle = widget.addText("Помилка");
  errorTitle.font = Font.boldSystemFont(16);
  errorTitle.textColor = CONFIG.COLORS.powerOff;

  widget.addSpacer(4);

  const errorText = widget.addText(errorMessage);
  errorText.font = Font.systemFont(12);
  errorText.textColor = CONFIG.COLORS.textSecondary;

  widget.addSpacer();

  const helpText = widget.addText("Перевірте підключення\nдо API");
  helpText.font = Font.systemFont(10);
  helpText.textColor = CONFIG.COLORS.textSecondary;
  helpText.textOpacity = 0.6;

  return widget;
}

// ========================================
// API ФУНКЦІЇ
// ========================================

async function fetchSchedule(queue) {
  const url = `${CONFIG.API_BASE_URL}/api/schedules/queue/${queue}`;

  console.log(`Fetching schedule from: ${url}`);

  const request = new Request(url);
  request.timeoutInterval = CONFIG.REQUEST_TIMEOUT;

  try {
    const response = await request.loadJSON();

    // Зберегти в кеш
    if (response.success && response.queue_data) {
      saveToCache(queue, response.queue_data);
    }

    return response;
  } catch (error) {
    console.error(`API request failed: ${error.message}`);
    throw new Error("Не вдалось з'єднатися з API");
  }
}

// ========================================
// ЛОГІКА ВИЗНАЧЕННЯ СТАТУСУ
// ========================================

function isCurrentlyOff(outages) {
  const now = new Date();
  const currentMinutes = now.getHours() * 60 + now.getMinutes();

  for (const outage of outages) {
    const { start, end } = parseOutageMinutes(outage);

    if (start === null || end === null) continue;

    // Обробка випадку коли відключення через північ (21:00 - 24:00)
    if (end < start) {
      if (currentMinutes >= start || currentMinutes <= end) {
        return true;
      }
    } else {
      if (currentMinutes >= start && currentMinutes <= end) {
        return true;
      }
    }
  }

  return false;
}

function getNextEvent(outages) {
  const now = new Date();
  const currentMinutes = now.getHours() * 60 + now.getMinutes();

  let events = [];

  // Зібрати всі події (початок та кінець відключень)
  for (const outage of outages) {
    const { start, end } = parseOutageMinutes(outage);
    if (start !== null && end !== null) {
      events.push({ time: outage.start, minutes: start, isOutage: true });
      events.push({ time: outage.end, minutes: end, isOutage: false });
    }
  }

  // Сортувати за часом
  events.sort((a, b) => a.minutes - b.minutes);

  // Знайти наступну подію
  for (const event of events) {
    if (event.minutes > currentMinutes) {
      return event;
    }
  }

  // Якщо нічого не знайдено сьогодні, повернути першу подію (завтра)
  if (events.length > 0) {
    return events[0];
  }

  return null;
}

function parseOutageMinutes(outage) {
  const startParts = outage.start.split(":");
  const endParts = outage.end.split(":");

  if (startParts.length !== 2 || endParts.length !== 2) {
    return { start: null, end: null };
  }

  const startMinutes = parseInt(startParts[0]) * 60 + parseInt(startParts[1]);
  const endMinutes = parseInt(endParts[0]) * 60 + parseInt(endParts[1]);

  return { start: startMinutes, end: endMinutes };
}

// ========================================
// КЕШУВАННЯ
// ========================================

function saveToCache(queue, data) {
  try {
    const fm = FileManager.local();
    const cachePath = fm.joinPath(fm.documentsDirectory(), `zoe_cache_${queue}.json`);

    const cacheData = {
      data: data,
      timestamp: Date.now()
    };

    fm.writeString(cachePath, JSON.stringify(cacheData));
    console.log(`Saved to cache: ${queue}`);
  } catch (error) {
    console.error(`Cache save error: ${error.message}`);
  }
}

function loadFromCache(queue) {
  try {
    const fm = FileManager.local();
    const cachePath = fm.joinPath(fm.documentsDirectory(), `zoe_cache_${queue}.json`);

    if (!fm.fileExists(cachePath)) {
      return null;
    }

    const cacheContent = fm.readString(cachePath);
    const cacheData = JSON.parse(cacheContent);

    // Перевірити чи не застарів кеш
    const cacheAge = (Date.now() - cacheData.timestamp) / 1000 / 60; // в хвилинах

    if (cacheAge > CONFIG.CACHE_DURATION) {
      console.log(`Cache expired for ${queue} (${Math.round(cacheAge)} minutes old)`);
      return null;
    }

    console.log(`Loaded from cache: ${queue}`);
    return cacheData.data;
  } catch (error) {
    console.error(`Cache load error: ${error.message}`);
    return null;
  }
}

// ========================================
// ДОПОМІЖНІ ФУНКЦІЇ
// ========================================

function getUpdateTime() {
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  return `Оновлено: ${hours}:${minutes}`;
}
