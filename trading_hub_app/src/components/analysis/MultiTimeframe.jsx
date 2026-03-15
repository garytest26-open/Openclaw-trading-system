import { useAppState } from '../../store/appStore'
import { Clock } from 'lucide-react'

const LABELS = ['M15', 'H1', 'H4', 'D1', 'W1', 'MN'];

export default function MultiTimeframe() {
    const { timeframes } = useAppState()
    const bullishCount = timeframes.filter(tf => tf === 1).length;

    // Calculate badge state
    let badgeState = 'neutral';
    let badgeText = 'NEUT';
    if (bullishCount >= 4) {
        badgeState = 'bullish';
        badgeText = 'BULL';
    } else if (bullishCount <= 2) {
        badgeState = 'bearish';
        badgeText = 'BEAR';
    }

    return (
        <div className="bg-[var(--color-brand-secondary)] border border-[var(--color-brand-border)] p-3 shadow-sm rounded-sm flex flex-col h-full">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-[var(--color-brand-border)]">
                <div className="flex items-center gap-2 text-[var(--color-brand-text)]">
                    <Clock size={16} className="text-brand-accent-blue" />
                    <span className="text-sm font-bold uppercase tracking-wide">Timeframe Sync</span>
                </div>
                <span className={`px-2 py-0.5 text-[11px] font-bold rounded-sm uppercase tracking-wider border
                    ${badgeState === 'bullish' ? 'bg-brand-accent-green/10 text-brand-accent-green border-brand-accent-green/20' : ''}
                    ${badgeState === 'bearish' ? 'bg-brand-accent-red/10 text-brand-accent-red border-brand-accent-red/20' : ''}
                    ${badgeState === 'neutral' ? 'bg-[var(--color-brand-elevated)] text-[var(--color-brand-text-muted)] border-[var(--color-brand-border)]' : ''}
                `}>
                    {badgeText} [{bullishCount}/6]
                </span>
            </div>

            <div className="grid grid-cols-3 gap-1 mb-3">
                {timeframes.map((tf, i) => (
                    <div
                        key={i}
                        className={`p-1 flex flex-col items-center justify-center border transition-all ${tf === 1 ? 'border-brand-accent-green/30 bg-brand-accent-green/5' :
                            tf === -1 ? 'border-brand-accent-red/30 bg-brand-accent-red/5' :
                                'border-[var(--color-brand-border)] bg-[var(--color-brand-primary)]'
                            }`}
                    >
                        <span className="text-xs text-[var(--color-brand-text-muted)] font-bold mb-0.5">{LABELS[i]}</span>
                        <span className={`text-xs font-bold tracking-wider uppercase ${tf === 1 ? 'text-brand-accent-green' : tf === -1 ? 'text-brand-accent-red' : 'text-[var(--color-brand-text)]'
                            }`}>
                            {tf === 1 ? 'UP' : tf === -1 ? 'DN' : '--'}
                        </span>
                    </div>
                ))}
            </div>

            <div className="mt-auto bg-[var(--color-brand-primary)] p-2 border border-brand-accent-blue/30 border-l-2 border-l-brand-accent-blue">
                <div className="text-[11px] uppercase font-bold text-brand-accent-blue mb-1">SYNERGY DETECTED</div>
                <div className="text-[13px] text-[var(--color-brand-text-muted)] leading-tight">
                    {bullishCount >= 5 ? 'Tendencia principal fuerte. Correcciones intradía recomendadas para entradas.' :
                        bullishCount === 4 ? 'Tendencia moderada con ligera divergencia en timeframes menores.' :
                            'Mercado sin dirección clara. Evitar exposición direccional alta.'}
                </div>
            </div>
        </div>
    )
}
