import { useAppState } from '../../store/appStore'
import { Crosshair, TrendingDown, TrendingUp, AlertTriangle } from 'lucide-react'

export default function TradeSetup() {
    const { symbol, setup } = useAppState()
    const baseAsset = symbol.split('/')[0]

    return (
        <div className="bg-[var(--color-brand-secondary)] border border-[var(--color-brand-border)] p-3 shadow-sm rounded-sm">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-[var(--color-brand-border)]">
                <div className="flex items-center gap-2 text-[var(--color-brand-text)]">
                    <Crosshair size={16} className="text-brand-accent-blue" />
                    <span className="text-sm font-bold uppercase tracking-wide">Execution Setup</span>
                </div>
                <span className="px-1.5 py-0.5 bg-brand-accent-green/10 text-brand-accent-green border border-brand-accent-green/20 text-[11px] font-bold rounded-sm uppercase tracking-wider">
                    LONG
                </span>
            </div>

            <div className="grid grid-cols-2 gap-2 mb-3">
                <div className="bg-[var(--color-brand-primary)] border border-[var(--color-brand-border)] p-2">
                    <div className="text-xs text-[var(--color-brand-text-muted)] uppercase font-bold mb-1 flex items-center gap-1">
                        <TrendingUp size={10} className="text-brand-accent-blue" /> Entry
                    </div>
                    <div className="data-value text-sm font-bold text-brand-accent-blue">
                        ${setup.entry.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                    </div>
                </div>
                <div className="bg-[var(--color-brand-primary)] border border-brand-accent-red/30 border-l-2 border-l-brand-accent-red p-2">
                    <div className="text-xs text-[var(--color-brand-text-muted)] uppercase font-bold mb-1 flex items-center gap-1">
                        <TrendingDown size={10} className="text-brand-accent-red" /> Stop Loss
                    </div>
                    <div className="data-value text-sm font-bold text-brand-accent-red">
                        ${setup.stopLoss.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                    </div>
                </div>
                <div className="bg-[var(--color-brand-primary)] border border-[var(--color-brand-border)] p-2">
                    <div className="text-xs text-[var(--color-brand-text-muted)] uppercase font-bold mb-1 flex items-center gap-1">
                        <Target size={10} className="text-brand-accent-green" /> Target 1
                    </div>
                    <div className="data-value text-sm font-bold text-brand-accent-green">
                        ${setup.tp1.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                    </div>
                </div>
                <div className="bg-[var(--color-brand-primary)] border border-[var(--color-brand-border)] p-2">
                    <div className="text-xs text-[var(--color-brand-text-muted)] uppercase font-bold mb-1 flex items-center gap-1">
                        <Target size={10} className="text-brand-accent-green" /> Target 2
                    </div>
                    <div className="data-value text-sm font-bold text-brand-accent-green">
                        ${setup.tp2.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                    </div>
                </div>
            </div>

            <div className="flex items-center justify-between p-2 mb-3 bg-[var(--color-brand-elevated)] border border-[var(--color-brand-border)]">
                <div className="text-xs text-[var(--color-brand-text-muted)] uppercase tracking-wider font-bold">R/R Ratio</div>
                <div className="data-value text-base font-bold text-brand-accent-green">1:{setup.rrRatio}</div>
            </div>

            <div className="space-y-0 text-xs">
                <div className="flex justify-between py-1.5 border-b border-[var(--color-brand-border)]">
                    <span className="text-xs uppercase font-bold text-[var(--color-brand-text-muted)]">Position Size</span>
                    <span className="data-value font-bold text-[var(--color-brand-text)]">{setup.positionSize.toFixed(3)} {baseAsset}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[var(--color-brand-border)]">
                    <span className="text-xs uppercase font-bold text-[var(--color-brand-text-muted)] flex items-center gap-1">
                        <AlertTriangle size={10} className="text-brand-accent-yellow" /> Total Risk
                    </span>
                    <span className="data-value font-bold text-brand-accent-yellow">${setup.riskAmount.toFixed(2)}</span>
                </div>
                <div className="flex justify-between py-1.5">
                    <span className="text-xs uppercase font-bold text-[var(--color-brand-text-muted)]">Pot. Profit</span>
                    <span className="data-value font-bold text-brand-accent-green">${setup.potentialProfit.toFixed(2)}</span>
                </div>
            </div>
        </div>
    )
}

function Target(props) {
    return (
        <svg
            {...props}
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <circle cx="12" cy="12" r="10" />
            <circle cx="12" cy="12" r="6" />
            <circle cx="12" cy="12" r="2" />
        </svg>
    )
}
