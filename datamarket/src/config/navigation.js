import { 
  BarChart3, 
  Database, 
  ShieldAlert, 
  DollarSign, 
  ArrowLeftRight, 
  Bot, 
  FileText,
  KeyRound,
  Settings
} from 'lucide-react'

export const primaryNavigation = [
  {
    id: 'overview',
    name: 'Overview',
    href: 'overview',
    icon: BarChart3,
    badge: null,
    description: 'DNA Portal dashboard with key metrics',
    disabled: false
  },
  {
    id: 'data-products',
    name: 'Data Products',
    href: 'data-products',
    icon: Database,
    badge: '10',
    description: 'Browse and discover enterprise data products',
    disabled: false
  },
  {
    id: 'vendor-analytics',
    name: 'Vendor Analytics',
    href: 'vendor-analytics',
    icon: ShieldAlert,
    badge: '5 flags',
    description: 'Vendor payments, risk scoring, and fraud detection',
    disabled: false
  },
  {
    id: 'budget-finance',
    name: 'Budget & Finance',
    href: 'budget-finance',
    icon: DollarSign,
    badge: null,
    description: 'Departmental budgets and variance analysis',
    disabled: false
  },
  {
    id: 'internal-billing',
    name: 'Internal Billing',
    href: 'internal-billing',
    icon: ArrowLeftRight,
    badge: '2',
    description: 'Inter-departmental charges and anomaly detection',
    disabled: false
  },
  {
    id: 'ai-explorer',
    name: 'AI Explorer',
    href: 'ai-explorer',
    icon: Bot,
    badge: 'AI',
    description: 'Natural language data exploration powered by Databricks Foundation Models',
    disabled: false
  },
  {
    id: 'documents',
    name: 'Documents',
    href: 'documents',
    icon: FileText,
    badge: null,
    description: 'Data dictionaries, training materials, and guides',
    disabled: false
  }
]

export const secondaryNavigation = [
  {
    id: 'access-requests',
    name: 'Access Requests',
    href: 'access-requests',
    icon: KeyRound,
    badge: null,
    description: 'Request access to data products',
    disabled: false
  },
  {
    id: 'admin',
    name: 'Admin',
    href: 'admin',
    icon: Settings,
    badge: null,
    description: 'Portal administration and access controls',
    disabled: false,
    permissions: ['admin']
  }
]

export const allNavigation = [...primaryNavigation, ...secondaryNavigation]

export const getNavigationItem = (id) => {
  return allNavigation.find(item => item.id === id)
}

export const isNavigationItemActive = (currentPage, itemHref) => {
  const normalizedCurrent = currentPage?.replace('#', '') || 'overview'
  const normalizedHref = itemHref?.replace('#', '') || 'overview'
  return normalizedCurrent === normalizedHref
}

export const filterNavigationByPermissions = (items, userPermissions = []) => {
  return items.filter(item => {
    if (!item.permissions || item.permissions.length === 0) return true
    return item.permissions.some(permission => userPermissions.includes(permission))
  })
}

export const getNavigationWithBadges = () => {
  return allNavigation.filter(item => item.badge !== null)
}

export const mobileNavConfig = {
  primaryNavigation,
  secondaryNavigation,
  showBadges: true,
  showDescriptions: false,
  minTouchTarget: '44px'
}

export const desktopSidebarConfig = {
  primaryNavigation,
  secondaryNavigation,
  showBadges: true,
  showDescriptions: true,
  collapsible: true
}
