import { useUserPersona, type UserRole, type UserIndustry } from '../../context/UserPersonaContext'

const ROLE_OPTIONS: { value: UserRole; label: string }[] = [
  { value: 'general_user', label: 'General User' },
  { value: 'academic', label: 'Academic' },
  { value: 'investor', label: 'Investor' },
  { value: 'industry_leader', label: 'Industry Leader' },
]

const INDUSTRY_OPTIONS: { value: UserIndustry; label: string }[] = [
  { value: 'energy_resources', label: 'Energy & Resources' },
  { value: 'technology', label: 'Technology' },
  { value: 'financial_services', label: 'Financial Services' },
  { value: 'agriculture_food', label: 'Agriculture & Food' },
  { value: 'mining_minerals', label: 'Mining & Minerals' },
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'healthcare_life_sciences', label: 'Healthcare & Life Sciences' },
  { value: 'transportation_logistics', label: 'Transportation & Logistics' },
]

const selectStyle: React.CSSProperties = {
  background: 'var(--bg-raised)',
  border: '1px solid var(--border-strong)',
  color: 'var(--text-secondary)',
  fontSize: '11px',
  padding: '4px 6px',
  width: '100%',
  outline: 'none',
  cursor: 'pointer',
}

export default function PersonaSelector() {
  const { role, industry, setRole, setIndustry } = useUserPersona()

  return (
    <div className="px-4 py-2 flex flex-col gap-1.5" style={{ borderBottom: '1px solid var(--border)' }}>
      <div className="text-xs uppercase tracking-widest mb-0.5" style={{ color: 'var(--text-muted)' }}>Perspective</div>
      <select
        value={role}
        onChange={e => setRole(e.target.value as UserRole)}
        style={selectStyle}
      >
        {ROLE_OPTIONS.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      {role === 'industry_leader' && (
        <select
          value={industry ?? ''}
          onChange={e => setIndustry((e.target.value as UserIndustry) || null)}
          style={selectStyle}
        >
          <option value="">Select industry…</option>
          {INDUSTRY_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      )}
    </div>
  )
}
