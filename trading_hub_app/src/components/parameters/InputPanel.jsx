import { useState, useEffect } from 'react'
import { useAppState } from '../../store/appStore'

export default function InputPanel() {
    const { symbol, price, strategy, riskPercent, capital, updateConfig } = useAppState()

    // Estado local para evitar spam de WebSockets en cada pulsación de tecla
    const [localSymbol, setLocalSymbol] = useState(symbol)
    const [localPrice, setLocalPrice] = useState(price)
    const [localStrategy, setLocalStrategy] = useState(strategy)
    const [localRisk, setLocalRisk] = useState(riskPercent)
    const [localCapital, setLocalCapital] = useState(capital)

    // Sincronizar desde la app si hay cambios globales (e.g., precio en vivo realimenta el input)
    useEffect(() => {
        setLocalPrice(price);
    }, [price]);

    const handleAnalyze = () => {
        // Normalizamos si el usuario pone 'sol' en vez de 'SOL/USDT'
        let finalSymbol = localSymbol.toUpperCase().trim();
        if (!finalSymbol.includes('/')) {
            // Si no hay slash, asume USDT para crypto (BTC -> BTC/USDT)
            finalSymbol = finalSymbol + '/USDT';
            setLocalSymbol(finalSymbol);
        }

        updateConfig('symbol', finalSymbol);
        updateConfig('price', parseFloat(localPrice) || 0);
        updateConfig('strategy', localStrategy);
        updateConfig('riskPercent', parseFloat(localRisk) || 1.5);
        updateConfig('capital', parseFloat(localCapital) || 1000);

        console.log("Analyze triggered! Target:", finalSymbol);
    }

    return (
        <div className="bg-slate-800 rounded-xl p-5 border border-slate-700/50 shadow-lg mb-5">
            <div className="flex items-center justify-between mb-4 pb-2 text-slate-200 border-b border-slate-700/50">
                <div className="text-lg font-semibold flex items-center gap-2">
                    <span>📊</span> Parámetros de Análisis
                </div>
            </div>

            <div className="space-y-4">
                <div>
                    <label className="block mb-1.5 text-slate-300 text-sm font-medium">Símbolo / Par</label>
                    <input
                        type="text"
                        value={localSymbol}
                        onChange={(e) => setLocalSymbol(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                        className="w-full p-2.5 bg-slate-700 border border-slate-600 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all font-mono"
                        placeholder="Ej: BTC/USDT o SOL"
                    />
                </div>

                <div>
                    <label className="block mb-1.5 text-slate-300 text-sm font-medium">Precio Actual (Manual/Vivo)</label>
                    <input
                        type="number"
                        step="0.01"
                        value={localPrice}
                        onChange={(e) => setLocalPrice(e.target.value)}
                        className="w-full p-2.5 bg-slate-700 border border-slate-600 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all font-mono"
                    />
                </div>

                <div>
                    <label className="block mb-1.5 text-slate-300 text-sm font-medium">Estrategia Principal</label>
                    <select
                        value={localStrategy}
                        onChange={(e) => setLocalStrategy(e.target.value)}
                        className="w-full p-2.5 bg-slate-700 border border-slate-600 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                    >
                        <option value="trend">Trend Following (EMA Cloud)</option>
                        <option value="breakout">Breakout Trading</option>
                        <option value="range">Range Trading</option>
                        <option value="scalping">Scalping Multi-TF</option>
                        <option value="swing">Swing Trading</option>
                    </select>
                </div>

                <div>
                    <label className="block mb-1.5 text-slate-300 text-sm font-medium">Gestión de Riesgo (%)</label>
                    <input
                        type="number"
                        step="0.1" min="0.5" max="5"
                        value={localRisk}
                        onChange={(e) => setLocalRisk(e.target.value)}
                        className="w-full p-2.5 bg-slate-700 border border-slate-600 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all font-mono"
                    />
                </div>

                <div>
                    <label className="block mb-1.5 text-slate-300 text-sm font-medium">Capital de Trading</label>
                    <input
                        type="number"
                        step="100"
                        value={localCapital}
                        onChange={(e) => setLocalCapital(e.target.value)}
                        className="w-full p-2.5 bg-slate-700 border border-slate-600 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all font-mono"
                    />
                </div>

                <button
                    onClick={handleAnalyze}
                    className="w-full mt-4 p-3 bg-gradient-to-br from-blue-500 to-emerald-500 text-white rounded-lg font-semibold text-base shadow-md hover:-translate-y-0.5 hover:shadow-lg hover:shadow-blue-500/30 transition-all active:translate-y-0"
                >
                    🚀 Analizar Edge Trading
                </button>
            </div>
        </div>
    )
}
