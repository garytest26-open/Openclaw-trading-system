import { create } from 'zustand'

export const useAppState = create((set) => ({
    symbol: 'BTC/USDT',
    price: 65000,
    strategy: 'trend',
    riskPercent: 1.5,
    capital: 10000,
    edgeScore: 78,
    winProb: 68,
    confidence: 85,
    volatility: 'Medium',
    momentum: '+72',
    timeframes: [1, 1, 1, -1, 1, 1], // M15, H1, H4, D1, W1, MN (1=Bull, -1=Bear, 0=Neutral)
    setup: {
        entry: 64800,
        stopLoss: 63500,
        tp1: 67200,
        tp2: 69500,
        positionSize: 0.15,
        riskAmount: 150,
        potentialProfit: 420,
        rrRatio: 2.8
    },
    indicators: {
        ema50: 63200,
        ema200: 61800,
        rsi: 58.3,
        macd: 'Bullish Cross',
        volumeRatio: 1.32,
        atr: 1240
    },
    aiRecommendations: {
        level: 'alta_probabilidad', // 'alta_probabilidad', 'moderada', 'edge_insuficiente'
        message: 'Configuración de alta probabilidad. Edge positivo detectado con alineación multi-timeframe favorable.',
        pattern: 'Bull Flag confirmado en H4 + Golden Cross en H1. Retroceso Fibonacci 0.618 respetado. Confluencia de soportes en zona de entrada.',
        confluence: [
            '5/6 timeframes alcistas',
            'Precio sobre EMA 50 y EMA 200',
            'RSI en zona neutral-alcista',
            'MACD con cruce bullish',
            'Volumen 32% superior a media',
            'Patrón trend confirmado'
        ]
    },
    updateConfig: (param, value) => set((state) => ({ [param]: value })),
    updateAnalysisData: (data) => set((state) => {
        // Extraemos 'price' para que no sobreescriba el valor introducido por el usuario
        const { price, ...restData } = data;
        return { ...state, ...restData };
    }),
}))
