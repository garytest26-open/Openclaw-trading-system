import { useAppState } from '../../store/appStore'
import { Cpu, CheckCircle2, AlertTriangle, XCircle, ShieldAlert, Activity } from 'lucide-react'

export default function Recommendations() {
    const { aiRecommendations } = useAppState()

    const levelStyles = {
        alta_probabilidad: 'bg-brand-accent-green/10 border-brand-accent-green/30 text-brand-accent-green',
        moderada: 'bg-brand-accent-yellow/10 border-brand-accent-yellow/30 text-brand-accent-yellow',
        edge_insuficiente: 'bg-brand-accent-red/10 border-brand-accent-red/30 text-brand-accent-red'
    }

    const icons = {
        alta_probabilidad: <CheckCircle2 size={16} />,
        moderada: <AlertTriangle size={16} />,
        edge_insuficiente: <XCircle size={16} />
    }

    return (
        <div className="bg-[var(--color-brand-secondary)] border border-[var(--color-brand-border)] p-3 shadow-sm rounded-sm flex flex-col h-full">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-[var(--color-brand-border)]">
                <div className="flex items-center gap-2 text-[var(--color-brand-text)]">
                    <Cpu size={16} className="text-brand-accent-blue" />
                    <span className="text-sm font-bold uppercase tracking-wide">AI Recommendation</span>
                </div>
            </div>

            <div className={`flex items-start gap-2 p-2.5 border mb-3 ${levelStyles[aiRecommendations.level]}`}>
                <div className="mt-0.5 shrink-0">{icons[aiRecommendations.level]}</div>
                <div className="text-xs uppercase font-bold leading-relaxed tracking-wide">
                    {aiRecommendations.message}
                </div>
            </div>

            <div className="bg-[var(--color-brand-primary)] p-2.5 border border-[var(--color-brand-border)] mb-3 relative overflow-hidden">
                {/* Decorative background lines */}
                <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 1px, var(--color-brand-text) 1px, var(--color-brand-text) 2px)', backgroundSize: '100% 4px' }}></div>

                <div className="text-[11px] uppercase font-bold text-brand-accent-blue mb-2 flex items-center gap-1.5 relative z-10 border-b border-[var(--color-brand-border)] pb-1">
                    <Activity size={10} className="text-brand-accent-blue" /> Confluence Factors
                </div>
                <ul className="text-xs text-[var(--color-brand-text)] space-y-1 relative z-10 font-mono">
                    {aiRecommendations.confluence.map((factor, index) => (
                        <li key={index} className="flex items-start gap-1.5">
                            <span className="text-[var(--color-brand-text-muted)]">-</span>
                            <span>{factor}</span>
                        </li>
                    ))}
                </ul>
            </div>

            <div className="mt-auto bg-brand-accent-yellow/5 p-2.5 border border-brand-accent-yellow/20">
                <div className="text-[11px] uppercase font-bold text-brand-accent-yellow mb-2 flex items-center gap-1.5 border-b border-brand-accent-yellow/10 pb-1">
                    <ShieldAlert size={10} className="text-brand-accent-yellow" /> Dynamic Risk Protocol
                </div>
                <ul className="text-xs text-[var(--color-brand-text-muted)] space-y-1 font-mono">
                    <li className="flex items-start gap-1.5">
                        <span className="text-brand-accent-yellow/50">-</span>
                        <span>Risk Capped: 2% max per trade</span>
                    </li>
                    <li className="flex items-start gap-1.5">
                        <span className="text-brand-accent-yellow/50">-</span>
                        <span>Auto-Breakeven at +1R</span>
                    </li>
                    <li className="flex items-start gap-1.5">
                        <span className="text-brand-accent-yellow/50">-</span>
                        <span>Take Profit: 50% size at TP1</span>
                    </li>
                    <li className="flex items-start gap-1.5">
                        <span className="text-brand-accent-yellow/50">-</span>
                        <span>Trailing Stop activated towards TP2</span>
                    </li>
                </ul>
            </div>
        </div>
    )
}
