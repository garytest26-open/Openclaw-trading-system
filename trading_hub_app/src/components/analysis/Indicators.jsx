import { useAppState } from '../../store/appStore'
import { BarChart2, Search } from 'lucide-react'

export default function Indicators() {
    const { indicators, strategy } = useAppState()

    const patterns = {
        trend: 'Bull Flag H4 conf. Soporte EMA 50.',
        breakout: 'Compresión BBs + Triángulo. Breakout inminente altos vols.',
        range: 'Rango $62K-$68K. Rebote soporte, RSI oversold.',
        scalping: 'Micro-estructura UP M15. HH/HL series conf. Momentum++.',
        swing: 'Fib 0.618 respetado. Confluencia supps. Acumulación detectada.'
    };

    return (
        <div className="bg-[var(--color-brand-secondary)] border border-[var(--color-brand-border)] p-3 shadow-sm rounded-sm">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-[var(--color-brand-border)]">
                <div className="flex items-center gap-2 text-[var(--color-brand-text)]">
                    <BarChart2 size={16} className="text-brand-accent-blue" />
                    <span className="text-sm font-bold uppercase tracking-wide">Technical Indicators</span>
                </div>
            </div>

            <div className="space-y-0.5 text-xs">
                <div className="flex justify-between py-1 border-b border-[var(--color-brand-border)] hover:bg-[var(--color-brand-elevated)] transition-colors px-1">
                    <span className="text-xs uppercase font-bold text-[var(--color-brand-text-muted)]">EMA 50</span>
                    <span className="data-value font-bold text-brand-accent-blue">${indicators.ema50.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[var(--color-brand-border)] hover:bg-[var(--color-brand-elevated)] transition-colors px-1">
                    <span className="text-xs uppercase font-bold text-[var(--color-brand-text-muted)]">EMA 200</span>
                    <span className="data-value font-bold text-brand-accent-yellow">${indicators.ema200.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[var(--color-brand-border)] hover:bg-[var(--color-brand-elevated)] transition-colors px-1">
                    <span className="text-xs uppercase font-bold text-[var(--color-brand-text-muted)]">RSI (14)</span>
                    <span className={`data-value font-bold ${indicators.rsi > 70 ? 'text-brand-accent-red' : indicators.rsi < 30 ? 'text-brand-accent-green' : 'text-[var(--color-brand-text)]'}`}>
                        {indicators.rsi.toFixed(1)}
                    </span>
                </div>
                <div className="flex justify-between py-1 border-b border-[var(--color-brand-border)] hover:bg-[var(--color-brand-elevated)] transition-colors px-1">
                    <span className="text-xs uppercase font-bold text-[var(--color-brand-text-muted)]">MACD</span>
                    <span className={`data-value font-bold ${indicators.macd.includes('Bullish') ? 'text-brand-accent-green' : 'text-[var(--color-brand-text)]'}`}>
                        {indicators.macd.toUpperCase()}
                    </span>
                </div>
                <div className="flex justify-between py-1 border-b border-[var(--color-brand-border)] hover:bg-[var(--color-brand-elevated)] transition-colors px-1">
                    <span className="text-xs uppercase font-bold text-[var(--color-brand-text-muted)]">Vol Ratio</span>
                    <span className="data-value font-bold text-[var(--color-brand-text)]">{indicators.volumeRatio.toFixed(2)}x</span>
                </div>
                <div className="flex justify-between py-1 hover:bg-[var(--color-brand-elevated)] transition-colors px-1">
                    <span className="text-xs uppercase font-bold text-[var(--color-brand-text-muted)]">ATR (14)</span>
                    <span className="data-value font-bold text-[var(--color-brand-text)]">${indicators.atr.toFixed(0)}</span>
                </div>
            </div>

            <div className="mt-3 bg-[var(--color-brand-primary)] p-2 border border-[var(--color-brand-border)]">
                <div className="text-[11px] uppercase font-bold text-[var(--color-brand-text)] mb-1 flex items-center gap-1.5 border-b border-[var(--color-brand-border)] pb-1">
                    <Search size={10} className="text-brand-accent-yellow" /> Pattern Detected
                </div>
                <div className="text-xs text-[var(--color-brand-text-muted)] leading-relaxed font-mono">
                    {'>'} {patterns[strategy]}
                </div>
            </div>
        </div>
    )
}
