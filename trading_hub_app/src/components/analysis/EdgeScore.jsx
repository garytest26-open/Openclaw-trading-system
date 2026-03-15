import { useAppState } from '../../store/appStore'
import { Target, Activity, TrendingUp, Zap } from 'lucide-react'

export default function EdgeScore() {
    const { edgeScore, winProb, confidence, volatility, momentum } = useAppState()

    // Status colors based on value
    const getScoreColor = (score) => {
        if (score >= 75) return 'text-brand-accent-green'
        if (score >= 50) return 'text-brand-accent-yellow'
        return 'text-brand-accent-red'
    }

    return (
        <div className="bg-[var(--color-brand-secondary)] border border-[var(--color-brand-border)] p-3 shadow-sm rounded-sm">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-[var(--color-brand-border)]">
                <div className="flex items-center gap-2 text-[var(--color-brand-text)]">
                    <Target size={16} className="text-brand-accent-blue" />
                    <span className="text-sm font-bold uppercase tracking-wide">AI Edge Score</span>
                </div>
                <div className="flex items-center gap-1">
                    <div className={`w-1.5 h-1.5 rounded-full ${edgeScore >= 50 ? 'bg-brand-accent-green animate-pulse' : 'bg-brand-accent-red'}`}></div>
                    <span className="text-xs text-[var(--color-brand-text-muted)] uppercase tracking-wider">Sync</span>
                </div>
            </div>

            <div className="flex items-center gap-4">
                {/* Main Score - Left */}
                <div className="flex-shrink-0 flex flex-col items-center justify-center p-3 border border-[var(--color-brand-border)] bg-[var(--color-brand-primary)]">
                    <span className={`data-value text-4xl font-bold tracking-tighter ${getScoreColor(edgeScore)} leading-none`}>
                        {edgeScore}
                    </span>
                    <span className="text-xs text-[var(--color-brand-text-muted)] font-bold mt-1 tracking-widest uppercase">/100</span>
                </div>

                {/* Metrics - Right */}
                <div className="flex-1 grid grid-cols-2 gap-x-4 gap-y-2">
                    <div className="flex justify-between items-center border-b border-[var(--color-brand-border)] pb-1">
                        <span className="text-xs text-[var(--color-brand-text-muted)] uppercase font-bold flex items-center gap-1">
                            <TrendingUp size={10} /> Win Prob
                        </span>
                        <span className="data-value text-xs font-bold text-[var(--color-brand-text)]">{winProb}%</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-[var(--color-brand-border)] pb-1">
                        <span className="text-xs text-[var(--color-brand-text-muted)] uppercase font-bold flex items-center gap-1">
                            <Target size={10} /> Conf
                        </span>
                        <span className="data-value text-xs font-bold text-[var(--color-brand-text)]">{confidence}%</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-[var(--color-brand-border)] pb-1">
                        <span className="text-xs text-[var(--color-brand-text-muted)] uppercase font-bold flex items-center gap-1">
                            <Activity size={10} /> Volat
                        </span>
                        <span className="text-xs font-bold text-brand-accent-yellow uppercase">{volatility}</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-[var(--color-brand-border)] pb-1">
                        <span className="text-xs text-[var(--color-brand-text-muted)] uppercase font-bold flex items-center gap-1">
                            <Zap size={10} /> Moment
                        </span>
                        <span className={`data-value text-xs font-bold ${momentum.startsWith('+') ? 'text-brand-accent-green' : 'text-brand-accent-red'}`}>
                            {momentum}
                        </span>
                    </div>
                </div>
            </div>

            {/* Tags Strip */}
            <div className="flex flex-wrap gap-1.5 mt-3 pt-2 border-t border-[var(--color-brand-border)]">
                <span className="px-1.5 py-0.5 bg-[var(--color-brand-primary)] border border-brand-accent-blue/30 text-brand-accent-blue text-[11px] uppercase font-bold">Trend Confrm</span>
                <span className="px-1.5 py-0.5 bg-[var(--color-brand-primary)] border border-brand-accent-blue/30 text-brand-accent-blue text-[11px] uppercase font-bold">High Vol</span>
                <span className="px-1.5 py-0.5 bg-[var(--color-brand-primary)] border border-brand-accent-blue/30 text-brand-accent-blue text-[11px] uppercase font-bold">Breakout Ready</span>
            </div>
        </div>
    )
}
