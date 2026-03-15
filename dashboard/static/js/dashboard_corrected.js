/**
 * Dashboard JavaScript CORREGIDO
 * Soluciona error "illegal invocation" en Socket.IO
 */

// ==================== GLOBAL STATE ====================
let socket = null;
let appState = {
    theme: 'dark',
    connected: false,
    currentTab: 'dashboard',
    signals: [],
    agents: {},
    prices: {}
};

// ==================== SOCKET.IO INITIALIZATION ====================
function initializeSocketIO() {
    console.log('🔌 Inicializando Socket.IO...');
    
    try {
        // Inicializar Socket.IO con configuración robusta
        socket = io({
            reconnection: true,
            reconnectionAttempts: 10,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 20000,
            transports: ['websocket', 'polling']
        });
        
        // Event handlers
        socket.on('connect', handleSocketConnect);
        socket.on('disconnect', handleSocketDisconnect);
        socket.on('price_update', handlePriceUpdate);
        socket.on('signal_update', handleSignalUpdate);
        socket.on('agent_update', handleAgentUpdate);
        socket.on('trade_executed', handleTradeExecuted);
        socket.on('signal_generated', handleSignalGenerated);
        socket.on('auto_signal_generated', handleAutoSignalGenerated);
        socket.on('execution_result', handleExecutionResult);
        socket.on('strategies_list', handleStrategiesList);
        socket.on('configuration_data', handleConfigurationData);
        socket.on('error', handleSocketError);
        
        console.log('✅ Socket.IO inicializado correctamente');
        
    } catch (error) {
        console.error('❌ Error inicializando Socket.IO:', error);
        showError('Error de conexión WebSocket. Recarga la página.');
    }
}

// ==================== SOCKET EVENT HANDLERS ====================
function handleSocketConnect() {
    console.log('✅ Conectado al servidor WebSocket');
    appState.connected = true;
    updateConnectionStatus(true);
    
    // Solicitar datos iniciales
    if (socket && socket.connected) {
        socket.emit('get_strategies');
        socket.emit('get_configuration');
    }
}

function handleSocketDisconnect() {
    console.log('⚠️ Desconectado del servidor WebSocket');
    appState.connected = false;
    updateConnectionStatus(false);
}

function handlePriceUpdate(data) {
    console.log('📊 Actualización de precios:', data);
    updatePrices(data);
}

function handleSignalUpdate(data) {
    console.log('🚨 Nueva señal:', data);
    addNewSignal(data);
}

function handleAgentUpdate(data) {
    console.log('🤖 Actualización de agente:', data);
    updateAgentStatus(data);
}

function handleTradeExecuted(data) {
    console.log('💰 Trade ejecutado:', data);
    showNotification(`Trade ${data.trade.type} ${data.trade.symbol} ejecutado`, 'success');
    updateTradeHistory(data.trade);
}

function handleSignalGenerated(data) {
    console.log('🎯 Señal generada:', data);
    showNotification(data.message, 'info');
}

function handleAutoSignalGenerated(data) {
    console.log('🤖 Señal automática:', data);
    showNotification(`Señal automática: ${data.message}`, 'warning');
}

function handleExecutionResult(data) {
    console.log('📋 Resultado de ejecución:', data);
    if (data.success) {
        showNotification(data.message, 'success');
    } else {
        showNotification(`Error: ${data.message}`, 'error');
    }
}

function handleStrategiesList(data) {
    console.log('📋 Lista de estrategias:', data);
    updateStrategiesList(data.strategies);
}

function handleConfigurationData(data) {
    console.log('⚙️ Datos de configuración:', data);
    updateConfigurationForm(data);
}

function handleSocketError(data) {
    console.error('❌ Error de Socket.IO:', data);
    showError(data.message || 'Error de conexión');
}

// ==================== UI FUNCTIONS ====================
function updateConnectionStatus(connected) {
    const statusEl = document.querySelector('.connection-status');
    if (!statusEl) return;
    
    if (connected) {
        statusEl.className = 'px-3 py-1 bg-green-900/30 text-green-400 rounded-full flex items-center connection-status';
        statusEl.innerHTML = '<span class="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse-glow"></span>CONECTADO';
    } else {
        statusEl.className = 'px-3 py-1 bg-red-900/30 text-red-400 rounded-full flex items-center connection-status';
        statusEl.innerHTML = '<span class="w-2 h-2 bg-red-500 rounded-full mr-2"></span>DESCONECTADO';
    }
}

function updatePrices(data) {
    // Actualizar precios en la UI
    if (data.prices) {
        appState.prices = data.prices;
        
        for (const [symbol, priceData] of Object.entries(data.prices)) {
            const priceEl = document.getElementById(`price-${symbol}`);
            const changeEl = document.getElementById(`change-${symbol}`);
            
            if (priceEl) {
                priceEl.textContent = `$${priceData.price.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
            }
            
            if (changeEl) {
                const change = priceData.change || 0;
                changeEl.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
                changeEl.className = change >= 0 ? 'text-green-400' : 'text-red-400';
            }
        }
    }
    
    // Actualizar gráficos si hay historial
    if (data.priceHistory) {
        updatePriceCharts(data.priceHistory);
    }
}

function updatePriceCharts(priceHistory) {
    // Implementar actualización de gráficos Plotly
    // (simplificado por ahora)
    console.log('📈 Actualizando gráficos con historial:', Object.keys(priceHistory));
}

function addNewSignal(signal) {
    // Añadir señal a la lista
    appState.signals.push(signal);
    
    // Actualizar UI
    const signalsList = document.getElementById('signals-list');
    if (signalsList) {
        const signalElement = createSignalElement(signal);
        signalsList.insertBefore(signalElement, signalsList.firstChild);
        
        // Limitar a 10 señales
        if (signalsList.children.length > 10) {
            signalsList.removeChild(signalsList.lastChild);
        }
    }
    
    // Actualizar contador
    updateSignalsCount();
}

function createSignalElement(signal) {
    const typeClass = signal.type === 'BUY' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400';
    const typeIcon = signal.type === 'BUY' ? 'fa-arrow-up' : 'fa-arrow-down';
    
    return `
        <div class="signal-item p-4 bg-gray-800/50 rounded-lg border border-gray-700/50 mb-3 animate-slide-in">
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
                    <div class="font-semibold">$${signal.price.toFixed(2)}</div>
                </div>
                <div>
                    <div class="text-gray-500">Entrada</div>
                    <div class="font-semibold">$${signal.entry.toFixed(2)}</div>
                </div>
                <div>
                    <div class="text-gray-500">Confianza</div>
                    <div class="font-semibold">
                        <span class="px-2 py-1 ${signal.confidence >= 70 ? 'bg-green-900/30 text-green-400' : 'bg-yellow-900/30 text-yellow-400'} rounded">
                            ${signal.confidence}%
                        </span>
                    </div>
                </div>
                <div>
                    <div class="text-gray-500">Estrategia</div>
                    <div class="font-semibold">${signal.strategy}</div>
                </div>
            </div>
            <div class="mt-3 flex justify-end">
                <button class="execute-btn px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white transition-colors"
                        data-signal-id="${signal.id}">
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
    if (data.agents) {
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
                            <span class="w-3 h-3 rounded-full mr-2 ${statusClass.replace('text-', 'bg-').split(' ')[0]}"></span>
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
}

function updateTradeHistory(trade) {
    const historyList = document.getElementById('trade-history');
    if (historyList) {
        const tradeElement = createTradeElement(trade);
        historyList.insertBefore(tradeElement, historyList.firstChild);
        
        // Limitar a 10 trades
        if (historyList.children.length > 10) {
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
                    <span class="font-medium">${trade.symbol}</span>
                    <span class="mx-2 text-gray-500">•</span>
                    <span class="text-sm text-gray-400">${trade.type}</span>
                </div>
                <span class="text-sm text-gray-400">${formatTime(trade.timestamp)}</span>
            </div>
            <div class="mt-1 text-sm">
                <span class="text-gray-500">Entrada: </span>
                <span class="font-semibold">$${trade.entry_price.toFixed(2)}</span>
                <span class="mx-2 text-gray-500">•</span>
                <span class="text-gray-500">Cantidad: </span>
                <span class="font-semibold">${trade.quantity}</span>
            </div>
        </div>
    `;
}

// ==================== UTILITY FUNCTIONS ====================
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

function showNotification(message, type = 'info') {
    // Crear notificación
    const notification = document.createElement('div');
    const typeClass = type === 'success' ? 'bg-green-900/80 border-green-700' :
                     type === 'error' ? 'bg-red-900/80 border-red-700' :
                     type === 'warning' ? 'bg-yellow-900/80 border-yellow-700' :
                     'bg-blue-900/80 border-blue-700';
    
    notification.className = `fixed top-4 right-4 z-50 px-4 py-3 rounded-lg border ${typeClass} text-white shadow-lg animate-slide-in`;
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

// ==================== EVENT LISTENERS ====================
function setupEventListeners() {
    console.log('🔧 Configurando event listeners...');
    
    // Botón de nueva señal
    const newSignalBtn = document.getElementById('new-signal-btn');
    if (newSignalBtn) {
        newSignalBtn.addEventListener('click', handleNewSignalClick);
    }
    
    // Botones de ejecución (delegación de eventos)
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('execute-btn') || e.target.closest('.execute-btn')) {
            const button = e.target.classList.contains('execute-btn') ? e.target : e.target.closest('.execute-btn');
            const signalId = button.getAttribute('data-signal-id');
            if (signalId) {
                handleExecuteSignal(signalId);
            }
        }
    });
    
    // Botón de configuración
    const configBtn = document.getElementById('config-btn');
    if (configBtn) {
        configBtn.addEventListener('click', handleConfigClick);
    }
    
    // Formulario de configuración
    const configForm = document.getElementById('config-form');
    if (configForm) {
        configForm.addEventListener('submit', handleConfigSubmit);
    }
    
    // Botones de estrategias
    const strategyButtons = document.querySelectorAll('.strategy-btn');
    strategyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const strategy = this.getAttribute('data-strategy');
            handleStrategySelect(strategy);
        });
    });
    
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
    
    // Confirmar ejecución
    if (confirm('¿Estás seguro de ejecutar esta señal?')) {
        socket.emit('execute_signal', { signalId: signalId });
        showNotification('Ejecutando señal...', 'info');
    }
}

function handleConfigClick() {
    console.log('⚙️ Abriendo configuración...');
    // Cambiar a pestaña de configuración si existe
    switchTab('config');
}

function handleConfigSubmit(e) {
    e.preventDefault();
    console.log('📝 Enviando configuración...');
    
    if (!socket || !socket.