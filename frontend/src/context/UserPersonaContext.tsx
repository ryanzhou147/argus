import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

export type UserRole = 'general_user' | 'academic' | 'investor' | 'industry_leader'

export type UserIndustry =
  | 'energy_resources'
  | 'technology'
  | 'financial_services'
  | 'agriculture_food'
  | 'mining_minerals'
  | 'manufacturing'
  | 'healthcare_life_sciences'
  | 'transportation_logistics'

interface UserPersonaContextValue {
  role: UserRole
  industry: UserIndustry | null
  setRole: (role: UserRole) => void
  setIndustry: (industry: UserIndustry | null) => void
}

const UserPersonaContext = createContext<UserPersonaContextValue | null>(null)

export function UserPersonaProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<UserRole>('general_user')
  const [industry, setIndustry] = useState<UserIndustry | null>(null)

  const setRole = useCallback((newRole: UserRole) => {
    setRoleState(newRole)
    if (newRole !== 'industry_leader') {
      setIndustry(null)
    }
  }, [])

  return (
    <UserPersonaContext.Provider value={{ role, industry, setRole, setIndustry }}>
      {children}
    </UserPersonaContext.Provider>
  )
}

export function useUserPersona(): UserPersonaContextValue {
  const ctx = useContext(UserPersonaContext)
  if (!ctx) throw new Error('useUserPersona must be used inside UserPersonaProvider')
  return ctx
}
