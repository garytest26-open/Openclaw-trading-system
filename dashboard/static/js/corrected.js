/**
 * Dashboard JavaScript CORREGIDO
 * Soluciona error "illegal invocation" en Socket.IO
 */

// ==================== CONFIGURACIÓN GLOBAL ====================
let socket = null;
let appState = {
    theme: 'dark',
    connected: false,
    currentTab: 'dashboard',
    signals: [],
    agents: {},
    prices: {}
};

// ==================== INICIALIZACIÓN ====================
function initializeDashboard() {
    console.log('🚀 Inicializando dashboard...');
    
    // Inicializar Socket.IO
    initializeSocketIO();
    
    // Configurar event listeners
    setupEventListeners();
    
    // Iniciar actualizaciones de tiempo
    updateTime();
    setInterval(updateTime, 1000);
    
    // Mostrar notificación de inicio
    showNotification('Dashboard REAL inicializado correctamente', 'success');
}

// ==================== SOCKET.IO ====================
function initializeSocketIO() {
    console.log('🔌 Inicializando Socket.IO...');
    
    try {
        // Inicializar Socket.IO
        socket = io({
            reconnection: true,
            reconnectionAttempts: 10,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 20000,
            transports: ['websocket', 'polling']
        });
        
        // Configurar event handlers
        setupSocketHandlers();
        
        console.log('✅ Socket.IO inicializado');
    } catch (error) {
        console.error('❌ Error inicializando Socket.IO:', error);
        showError('Error de conexión WebSocket');
    }
}

function setupSocketHandlers() {
    if (!socket) return;
    
    socket.on('connect', () => {
        console.log('✅ Conectado al servidor');
        appState.connected = true;
        updateConnectionStatus(true);
        
        // Solicitar datos iniciales
        socket.emit('get_strategies');
        socket.emit('get_configuration');
    });
    
    socket.on('disconnect', () => {
        console.log('⚠️ Desconectado del servidor');
        appState.connected = false;
        updateConnectionStatus(false);
    });
    
    socket.on('price_update', (data) => {
        console.log('📊 Actualización de precios:', data);
        updatePrices(data);
    });
    
    socket.on('signal_update', (data) => {
        console.log('🚨 Nueva señal:', data);
        addNewSignal(data);
    });
    
    socket.on('agent_update', (data) => {
        console.log('🤖 Actualización de agente:', data);
        updateAgentStatus(data);
    });
    
    socket.on('trade_executed', (data) => {
        console.log('💰 Trade ejecutado:', data);
        showNotification(`Trade ${data.trade.type} ${data.trade.symbol} ejecutado`, 'success');
        updateTradeHistory(data.trade);
    });
    
    socket.on('signal_generated', (data) => {
        console.log('🎯 Señal generada:', data);
        showNotification(data.message, 'info');
    });
    
    socket.on('execution_result', (data) => {
        console.log('📋 Resultado de ejecución:', data);
        if (data.success) {
            showNotification(data.message, 'success');
        } else {
            showNotification(`Error: ${data.message}`, 'error');
        }
    });
    
    socket.on('error', (data) => {
        console.error('❌ Error de Socket.IO:', data);
        showError(data.message || 'Error de conexión');
    });
}

// ==================== UI FUNCTIONS ====================
function updateConnectionStatus(connected) {
    const statusEl = document.querySelector('.bg-green-900\\/30, .connection-status');
    if (!statusEl) return;
    
    if (connected) {
        statusEl.className = 'px-3 py-1 bg-green-900/30 text-green-400 rounded-full flex items-center';
        statusEl.innerHTML = '<span class="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse-glow"></span>CONECTADO';
    } else {
        statusEl.className = 'px-3 py-1 bg-red-900/30 text-red-400 rounded-full flex items-center';
        statusEl.innerHTML = '<span class="w-2 h-2 bg-red-500 rounded-full mr-2"></span>DESCONECTADO';
    }
}

function updateTime() {
    const now = new Date();
    const madridTime = new Date(now.toLocaleString('en-US', { timeZone: 'Europe/Madrid' }));
    const timeStr = madridTime.toLocaleTimeString('es-ES', { hour12: false });
    
    const timeEl = document.getElementById('current-time');
    if (timeEl) timeEl.textContent = timeStr;
    
    const updateEl = document.getElementById('last-update');
    if (updateEl) updateEl.textContent = timeStr;
}

function updatePrices(data) {
    if (!data || !data.prices) return;
    
    appState.prices = data.prices;
    
    // Actualizar precios en la UI
    for (const [symbol, priceData] of Object.entries(data.prices)) {
        const priceEl = document.getElementById(`price-${symbol}`);
        const changeEl = document.getElementById(`change-${symbol}`);
        
        if (priceEl && priceData.price) {
            priceEl.textContent = `$${priceData.price.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
        }
        
        if (changeEl && priceData.change !== undefined) {
            const change = priceData.change;
            changeEl.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
            changeEl.className = change >= 0 ? 'text-green-400' : 'text-red-400';
        }
    }
}

function addNewSignal(signal) {
    if (!signal) return;
    
    // Añadir a estado
    appState.signals.unshift(signal);
    if (appState.signals.length > 10) appState.signals = appState.signals.slice(0, 10);
    
    // Actualizar UI
    const signalsList = document.getElementById('signals-list');
    if (signalsList) {
        const signalElement = createSignalElement(signal);
        signalsList.insertAdjacentHTML('afterbegin', signalElement);
        
        // Limitar a 10 señales visibles
        while (signalsList.children.length > 10) {
            signalsList.removeChild(signalsList.lastChild);
        }
    }
    
    updateSignalsCount();
}

function createSignalElement(signal) {
    const typeClass = signal.type === 'BUY' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400';
    const typeIcon = signal.type === 'BUY' ? 'fa-arrow-up' : 'fa-arrow-down';
    
    return `
        <div class="signal-item p-4 bg-gray-800/50 rounded-lg border border-gray-700/50 mb-3">
            <div class="flex justify-between items-center mb-2">
                <div class="flex items-center">
                    <span class="px-3 py-1 ${typeClass} rounded-full mr-3">
                        <i class="fas ${typeIcon} mr-1"></i>${signal.type}
                    </span>
                    <span class="font-bold text-lg">${signal.symbol}</span>
                </div>
                <span class="text-gray-400">${formatTime(signal.timestamp)}</span>
            </div>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div>
                    <div class="text-gray-500">Precio</div>
                    <div class="font-semibold">$${signal.price?.toFixed(2) || '0.00'}</div>
                </div>
                <div>
                    <div class="text-gray-500">Entrada</div>
                    <div class="font-semibold">$${signal.entry?.toFixed(2) || '0.00'}</div>
                </div>
                <div>
                    <div class="text-gray-500">Confianza</div>
                    <div class="font-semibold">
                        <span class="px-2 py-1 ${(signal.confidence || 0) >= 70 ? 'bg-green-900/30 text-green-400' : 'bg-yellow-900/30 text-yellow-400'} rounded">
                            ${signal.confidence || 0}%
                        </span>
                    </div>
                </div>
                <div>
                    <div class="text-gray-500">Estrategia</div>
                    <div class="font-semibold">${signal.strategy || 'N/A'}</div>
                </div>
            </div>
            <div class="mt-3 flex justify-end">
                <button class="execute-btn px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition-colors"
                        data-signal-id="${signal.id || ''}">
                    <i class="fas fa-play mr-2"></i>Ejecutar
                </button>
            </div>
        </div>
    `;
}

function updateSignalsCount() {
    const countEl = document.getElementById('signals-count');
    if (countEl) {
        const buyCount = appState.signals.filter(s => s.type === 'BUY').length;
        const sellCount = appState.signals.filter(s => s.type === 'SELL').length;
        countEl.textContent = `${appState.signals.length} (${buyCount} BUY, ${sellCount} SELL)`;
    }
}

function updateAgentStatus(data) {
    if (!data || !data.agents) return;
    
    appState.agents = data.agents;
    
    for (const [agentName, agentData] of Object.entries(data.agents)) {
        const agentEl = document.getElementById(`agent-${agentName}`);
        if (agentEl) {
            const statusClass = agentData.status === 'active' ? 'bg-green-900/30 text-green-400' : 
                              agentData.status === 'training' ? 'bg-yellow-900/30 text-yellow-400' : 
                              'bg-red-900/30 text-red-400';
            
            agentEl.innerHTML = `
                <div class="flex items-center justify-between">
                    <div class="flex items-center">
                        <span class="w-3 h-3 rounded-full mr-2 ${agentData.status === 'active' ? 'bg-green-500' : 
                                                                    agentData.status === 'training' ? 'bg-yellow-500' : 
                                                                    'bg-red-500'}"></span>
                        <span class="font-medium">${agentName.charAt(0).toUpperCase() + agentName.slice(1)}</span>
                    </div>
                    <span class="px-2 py-1 ${statusClass} rounded text-xs">
                        ${agentData.status === 'active' ? 'ACTIVO' : 
                          agentData.status === 'training' ? 'ENTRENANDO' : 'INACTIVO'}
                    </span>
                </div>
                <div class="mt-2 text-sm text-gray-400">
                    Confianza: <span class="font-semibold">${agentData.confidence || 0}%</span>
                </div>
            `;
        }
    }
}

function updateTradeHistory(trade) {
    const historyList = document.getElementById('trade-history');
    if (historyList) {
        const tradeElement = createTradeElement(trade);
        historyList.insertAdjacentHTML('afterbegin', tradeElement);
        
        // Limitar a 10 trades
        while (historyList.children.length > 10) {
            historyList.removeChild(historyList.lastChild);
        }
    }
}

function createTradeElement(trade) {
    const typeClass = trade.type === 'BUY' ? 'text-green-400' : 'text-red-400';
    const typeIcon = trade.type === 'BUY' ? 'fa-arrow-up' : 'fa-arrow-down';
    
    return `
        <div class="trade-item p-3 bg-gray-800/30 rounded-lg border border-gray-700/30 mb-2">
            <div class="flex justify-between items-center">
                <div class="flex items-center">
                    <i class="fas ${typeIcon} ${typeClass} mr-2"></i>
                    <span class="font-medium">${trade.symbol || 'N/A'}</span>
                    <span class="mx-2 text-gray-500">•</span>
                    <span class="text-sm text-gray-400">${trade.type || 'N/A'}</span>
                </div>
                <span class="text-sm text-gray-400">${formatTime(trade.timestamp)}</span>
            </div>
            <div class="mt-1 text-sm">
                <span class="text-gray-500">Entrada: </span>
                <span class="font-semibold">$${(trade.entry_price || 0).toFixed(2)}</span>
                <span class="mx-2 text-gray-500">•</span>
                <span class="text-gray-500">Cantidad: </span>
                <span class="font-semibold">${trade.quantity || 0}</span>
            </div>
        </div>
    `;
}

function formatTime(timestamp) {
    try {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('es-ES', { 
            hour: '2-digit', 
            minute: '2-digit',
            second: '2-digit'
        });
    } catch (e) {
        return '--:--:--';
    }
}

// ==================== EVENT LISTENERS ====================
function setupEventListeners() {
    console.log('🔧 Configurando event listeners...');
    
    // Botón de nueva señal
    const newSignalBtn = document.getElementById('new-signal-btn');
    if (newSignalBtn) {
        newSignalBtn.addEventListener('click', handleNewSignalClick);
    }
    
    // Delegación de eventos para botones de ejecutar
    document.addEventListener('click', (e) => {
        const executeBtn = e.target.closest('.execute-btn');
        if (executeBtn) {
            const signalId = executeBtn.getAttribute('data-signal-id');
            if (signalId) {
                handleExecuteSignal(signalId);
            }
        }
    });
    
    // Botones de cambio de timeframe
    document.querySelectorAll('.timeframe-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            const timeframe = e.target.getAttribute('data-timeframe');
            handleTimeframeChange(timeframe);
        });
    });
    
    // Botón de tema
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', handleThemeToggle);
    }
    
    // Navegación por pestañas
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const tab = e.target.getAttribute('onclick')?.match(/'([^']+)'/)?.[1] || 
                       e.target.closest('.nav-item').getAttribute('onclick')?.match(/'([^']+)'/)?.[1];
            if (tab) {
                switchTab(tab);
            }
        });
    });
    
    // Event listeners para Sindicato Nexus
    setupSindicatoEventListeners();
    
    console.log('✅ Event listeners configurados');
}

// ==================== EVENT HANDLERS ====================
function handleNewSignalClick() {
    console.log('🎯 Generando nueva señal...');
    
    if (!socket || !socket.connected) {
        showError('No conectado al servidor');
        return;
    }
    
    // Obtener símbolo y estrategia seleccionados
    const symbolSelect = document.getElementById('signal-symbol');
    const strategySelect = document.getElementById('signal-strategy');
    
    const symbol = symbolSelect ? symbolSelect.value : 'BTC';
    const strategy = strategySelect ? strategySelect.value : 'Trend Following';
    
    // Emitir evento al servidor
    socket.emit('generate_signal', {
        symbol: symbol,
        strategy: strategy
    });
    
    showNotification(`Generando señal ${symbol} con estrategia ${strategy}...`, 'info');
}

function handleExecuteSignal(signalId) {
    console.log('🚀 Ejecutando señal:', signalId);
    
    if (!socket || !socket.connected) {
        showError('No conectado al servidor');
        return;
    }
    
    if (confirm('¿Estás seguro de ejecutar esta señal?')) {
        socket.emit('execute_signal', { signalId: signalId });
        showNotification('Ejecutando señal...', 'info');
    }
}

function handleTimeframeChange(timeframe) {
    console.log('⏰ Cambiando timeframe:', timeframe);
    
    // Actualizar botones activos
    document.querySelectorAll('.timeframe-btn').forEach(btn => {
        if (btn.getAttribute('data-timeframe') === timeframe) {
            btn.className = 'timeframe-btn px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm';
        } else {
            btn.className = 'timeframe-btn px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm';
        }
    });
    
    showNotification(`Timeframe cambiado a ${timeframe}`, 'info');
}

function handleThemeToggle() {
    appState.theme = appState.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.classList.toggle('light');
    
    const icon = document.querySelector('#theme-toggle i');
    if (icon) {
        icon.className = appState.theme === 'dark' ? 'fas fa-moon' : 'fas fa-sun';
    }
    
    showNotification(`Tema cambiado a ${appState.theme === 'dark' ? 'oscuro' : 'claro'}`, 'info');
}

// ==================== UTILITY FUNCTIONS ====================
function switchTab(tabName) {
    console.log('🔀 Cambiando a pestaña:', tabName);
    
    // Actualizar navegación
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    document.querySelectorAll('.nav-item').forEach(item => {
        if (item.getAttribute('onclick')?.includes(`'${tabName}'`)) {
            item.classList.add('active');
        }
    });
    
    // Mostrar pestaña seleccionada
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    const selectedTab = document.getElementById(`${tabName}-tab`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    appState.currentTab = tabName;
}

function showNotification(message, type = 'info') {
    // Crear notificación
    const notification = document.createElement('div');
    const typeClass = type === 'success' ? 'bg-green-900/80 border-green-700' :
                     type === 'error' ? 'bg-red-900/80 border-red-700' :
                     type === 'warning' ? 'bg-yellow-900/80 border-yellow-700' :
                     'bg-blue-900/80 border-blue-700';
    
    notification.className = `fixed top-4 right-4 z-50 px-4 py-3 rounded-lg border ${typeClass} text-white shadow-lg`;
    notification.innerHTML = `
        <div class="flex items-center">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 
                         type === 'error' ? 'fa-exclamation-circle' : 
                         type === 'warning' ? 'fa-exclamation-triangle' : 
                         'fa-info-circle'} mr-2"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remover después de 5 segundos
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

function showError(message) {
    showNotification(message, 'error');
}

// ==================== SINDICATO_NEXUS FUNCTIONS ====================

let sindicatoState = {
    initialized: false,
    modelsLoaded: 0,
    predictions: {},
    performance: {},
    configuration: {}
};

// Inicializar Sindicato Nexus
async function initializeSindicatoNexus() {
    try {
        showNotification('Inicializando Sindicato Nexus...', 'info');
        
        const response = await fetch('/api/sindicato/initialize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            sindicatoState.initialized = true;
            updateSindicatoUI(data.status);
            showNotification('✅ Sindicato Nexus inicializado correctamente', 'success');
            loadSindicatoPredictions();
            loadSindicatoPerformance();
        } else {
            showError('❌ Error al inicializar Sindicato Nexus');
        }
    } catch (error) {
        console.error('Error inicializando Sindicato Nexus:', error);
        showError('Error de conexión con Sindicato Nexus');
    }
}

// Cargar predicciones de Sindicato Nexus
async function loadSindicatoPredictions() {
    try {
        const response = await fetch('/api/sindicato/predictions');
        const data = await response.json();
        
        if (data.success) {
            sindicatoState.predictions = data.predictions;
            updateSindicatoPredictionsUI(data.predictions);
        }
    } catch (error) {
        console.error('Error cargando predicciones:', error);
    }
}

// Cargar performance de Sindicato Nexus
async function loadSindicatoPerformance() {
    try {
        const response = await fetch('/api/sindicato/performance');
        const data = await response.json();
        
        if (data.success) {
            sindicatoState.performance = data.performance;
            updateSindicatoPerformanceUI(data.performance);
        }
    } catch (error) {
        console.error('Error cargando performance:', error);
    }
}

// Actualizar UI de Sindicato Nexus
function updateSindicatoUI(status) {
    const statusElement = document.getElementById('sindicato-status');
    const modelsElement = document.getElementById('sindicato-models');
    const initButton = document.getElementById('init-sindicato');
    
    if (statusElement) {
        if (sindicatoState.initialized) {
            statusElement.textContent = 'ACTIVO';
            statusElement.className = 'text-2xl font-bold mt-1 text-green-400';
            
            if (initButton) {
                initButton.innerHTML = '<i class="fas fa-check mr-2"></i> Sindicato Nexus Activo';
                initButton.className = 'w-full py-3 bg-gradient-to-r from-green-600 to-green-700 rounded-lg font-medium transition-all duration-300 cursor-default';
                initButton.disabled = true;
            }
        } else {
            statusElement.textContent = 'INACTIVO';
            statusElement.className = 'text-2xl font-bold mt-1 text-yellow-400';
        }
    }
    
    if (modelsElement && status.models_loaded) {
        modelsElement.textContent = status.models_loaded;
        sindicatoState.modelsLoaded = status.models_loaded;
    }
}

// Actualizar UI de predicciones
function updateSindicatoPredictionsUI(predictions) {
    const container = document.getElementById('sindicato-predictions');
    if (!container) return;
    
    if (!predictions || Object.keys(predictions).length === 0) {
        container.innerHTML = `
            <div class="col-span-3 text-center py-8 text-gray-500">
                <i class="fas fa-exclamation-triangle text-2xl mb-3"></i>
                <p>No hay predicciones disponibles</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    Object.values(predictions).forEach(prediction => {
        const confidence = Math.round(prediction.confidence * 100);
        let badgeClass = 'bg-gray-800 text-gray-300';
        let icon = 'fa-question-circle';
        
        if (prediction.prediction === 'BUY') {
            badgeClass = 'bg-green-900/30 text-green-400';
            icon = 'fa-arrow-up';
        } else if (prediction.prediction === 'SELL') {
            badgeClass = 'bg-red-900/30 text-red-400';
            icon = 'fa-arrow-down';
        } else if (prediction.prediction === 'HOLD') {
            badgeClass = 'bg-yellow-900/30 text-yellow-400';
            icon = 'fa-pause';
        }
        
        html += `
            <div class="gradient-card rounded-lg p-4 border border-gray-800 hover-lift">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <div class="flex items-center mb-1">
                            <div class="w-10 h-10 ${prediction.asset === 'BTC' ? 'bg-orange-900/30' : prediction.asset === 'ETH' ? 'bg-blue-900/30' : 'bg-purple-900/30'} rounded-lg flex items-center justify-center mr-3">
                                <span class="font-bold">${prediction.asset.charAt(0)}</span>
                            </div>
                            <div>
                                <h4 class="font-bold text-lg">${prediction.asset}</h4>
                                <p class="text-sm text-gray-400">${prediction.timeframe}</p>
                            </div>
                        </div>
                    </div>
                    <span class="px-3 py-1 ${badgeClass} rounded-full font-medium">
                        <i class="fas ${icon} mr-1"></i> ${prediction.prediction}
                    </span>
                </div>
                
                <div class="space-y-2">
                    <div class="flex justify-between text-sm">
                        <span class="text-gray-400">Confianza:</span>
                        <span class="font-medium">${confidence}%</span>
                    </div>
                    <div class="flex justify-between text-sm">
                        <span class="text-gray-400">Entrada:</span>
                        <span class="font-mono">$${prediction.entry_price.toLocaleString()}</span>
                    </div>
                    <div class="flex justify-between text-sm">
                        <span class="text-gray-400">Stop Loss:</span>
                        <span class="font-mono text-red-400">$${prediction.stop_loss.toLocaleString()}</span>
                    </div>
                    <div class="flex justify-between text-sm">
                        <span class="text-gray-400">Take Profit:</span>
                        <span class="font-mono text-green-400">$${prediction.take_profit.toLocaleString()}</span>
                    </div>
                </div>
                
                <div class="mt-4 pt-3 border-t border-gray-800">
                    <p class="text-xs text-gray-400 italic">"${prediction.reasoning}"</p>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Actualizar UI de performance
function updateSindicatoPerformanceUI(performance) {
    const returnElement = document.getElementById('sindicato-return');
    const sharpeElement = document.getElementById('sindicato-sharpe');
    
    if (returnElement && performance.total_return) {
        returnElement.textContent = `+${performance.total_return}%`;
    }
    
    if (sharpeElement && performance.sharpe_ratio) {
        sharpeElement.textContent = performance.sharpe_ratio;
    }
}

// Configurar event listeners para Sindicato Nexus
function setupSindicatoEventListeners() {
    const initButton = document.getElementById('init-sindicato');
    const refreshButton = document.getElementById('refresh-predictions');
    
    if (initButton) {
        initButton.addEventListener('click', initializeSindicatoNexus);
    }
    
    if (refreshButton) {
        refreshButton.addEventListener('click', loadSindicatoPredictions);
    }
}

// ==================== INICIALIZACIÓN AL CARGAR ====================
document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 DOM cargado, inicializando dashboard...');
    initializeDashboard();
});

// Manejar errores globales
window.addEventListener('error', (e) => {
    console.error('🚨 Error global:', e.error);
    showError(`Error de JavaScript: ${e.message}`);
});