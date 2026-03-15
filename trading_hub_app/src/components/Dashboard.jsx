import InputPanel from './parameters/InputPanel'
import MultiTimeframe from './analysis/MultiTimeframe'
import EdgeScore from './analysis/EdgeScore'
import TradeSetup from './analysis/TradeSetup'
import Indicators from './analysis/Indicators'
import Recommendations from './analysis/Recommendations'
import { Activity, ShieldAlert } from 'lucide-react'
import { useAppState } from '../store/appStore'

export default function Dashboard() {
    const { symbol, price } = useAppState()
    const baseAsset = symbol?.split('/')[0] || 'BTC'

    return (
        <div className="min-h-screen bg-[var(--color-brand-primary)] text-[var(--color-brand-text)] flex flex-col">
            {/* Top Bar - Bloomberg Terminal Style */}
            <header className="bg-[var(--color-brand-secondary)] border-b border-[var(--color-brand-border)] px-4 py-2 flex items-center justify-between sticky top-0 z-50">
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 text-brand-accent-blue font-bold tracking-tight">
                        <Activity size={18} strokeWidth={2.5} />
                        <span className="text-sm uppercase tracking-wider">NEXUS TRADING TERMINAL</span>
                    </div>
                    <div className="h-4 w-px bg-[var(--color-brand-border)]"></div>
                    <div className="flex items-center gap-3">
                        <span className="text-xs font-mono font-bold px-2 py-0.5 bg-[var(--color-brand-elevated)] rounded border border-[var(--color-brand-border)] text-[var(--color-brand-text)]">
                            {symbol}
                        </span>
                        <span className="data-value text-sm font-bold text-brand-accent-green">
                            ${price?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                    </div>
                </div>

                <div className="flex items-center gap-3 text-xs font-mono text-[var(--color-brand-text-muted)]">
                    <div className="flex items-center gap-1">
                        <div className="w-2 h-2 rounded-full bg-brand-accent-green animate-pulse"></div>
                        LIVE FEED
                    </div>
                    <span>|</span>
                    <span>SYS: OK</span>
                </div>
            </header>

            {/* Main Grid Workspace */}
            <div className="flex-1 p-2 md:p-4 overflow-hidden">
                <div className="grid grid-cols-12 gap-2 md:gap-4 h-full max-w-[2000px] mx-auto">

                    {/* Left Column: Controls & Micro-trends */}
                    <div className="col-span-12 xl:col-span-3 space-y-2 md:space-y-4 flex flex-col">
                        <InputPanel />
                        <MultiTimeframe />
                    </div>

                    {/* Center Column: Core Execution Data */}
                    <div className="col-span-12 md:col-span-6 xl:col-span-5 space-y-2 md:space-y-4 flex flex-col">
                        <EdgeScore />
                        <div className="bg-[var(--color-brand-secondary)] border-l-2 border-brand-accent-blue p-3 flex items-start gap-3 shadow-sm">
                            <ShieldAlert size={16} className="text-brand-accent-blue shrink-0 mt-0.5" />
                            <div className="text-xs leading-relaxed text-[var(--color-brand-text-muted)]">
                                <span className="text-[var(--color-brand-text)] font-semibold">RISK NOTICE:</span> Posición ajustada a volatilidad dinámica. El trailing stop recomendado se activará al alcanzar el 50% de recorrido hacia TP1.
                            </div>
                        </div>
                        <TradeSetup />
                    </div>

                    {/* Right Column: Quantitative Data */}
                    <div className="col-span-12 md:col-span-6 xl:col-span-4 space-y-2 md:space-y-4 flex flex-col">
                        <Indicators />
                        <Recommendations />
                    </div>

                </div>
            </div>
        </div>
    )
}
