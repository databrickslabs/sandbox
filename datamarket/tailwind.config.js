/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ["class"],
    content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./public/**/*.html",
    "./components/**/*.{js,jsx}",
    "./lib/**/*.{js,jsx}"
  ],
  theme: {
  	extend: {
  		colors: {
  			// Professional Databricks Palette
  			'databricks-navy': '#1e293b',      // Primary dark blue
  			'databricks-slate': '#334155',     // Secondary blue-gray  
  			'databricks-blue': '#3b82f6',      // Primary blue
  			'databricks-cyan': '#06b6d4',      // Accent cyan
  			'databricks-emerald': '#10b981',   // Success green
  			'databricks-amber': '#f59e0b',     // Warning amber
  			'databricks-purple': '#8b5cf6',    // Analytics purple
  			'databricks-gray': '#6b7280',      // Neutral gray
  			
  			// Chart Colors - Professional palette
  			'chart-1': '#3b82f6',  // Blue
  			'chart-2': '#10b981',  // Emerald
  			'chart-3': '#8b5cf6',  // Purple
  			'chart-4': '#f59e0b',  // Amber
  			'chart-5': '#06b6d4',  // Cyan
  			'chart-6': '#ec4899',  // Pink
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		fontFamily: {
  			sans: [
  				'Inter',
  				'system-ui',
  				'sans-serif'
  			]
  		},
  		fontSize: {
  			'display-1': [
  				'3.5rem',
  				{
  					lineHeight: '1.2',
  					fontWeight: '700'
  				}
  			],
  			'display-2': [
  				'3rem',
  				{
  					lineHeight: '1.2',
  					fontWeight: '700'
  				}
  			],
  			h1: [
  				'2.5rem',
  				{
  					lineHeight: '1.3',
  					fontWeight: '600'
  				}
  			],
  			h2: [
  				'2rem',
  				{
  					lineHeight: '1.3',
  					fontWeight: '600'
  				}
  			],
  			h3: [
  				'1.5rem',
  				{
  					lineHeight: '1.4',
  					fontWeight: '600'
  				}
  			],
  			'body-lg': [
  				'1.125rem',
  				{
  					lineHeight: '1.6',
  					fontWeight: '400'
  				}
  			],
  			body: [
  				'1rem',
  				{
  					lineHeight: '1.6',
  					fontWeight: '400'
  				}
  			],
  			'body-sm': [
  				'0.875rem',
  				{
  					lineHeight: '1.5',
  					fontWeight: '400'
  				}
  			],
  			caption: [
  				'0.75rem',
  				{
  					lineHeight: '1.4',
  					fontWeight: '500'
  				}
  			]
  		},
  		spacing: {
  			'18': '4.5rem',
  			'88': '22rem'
  		},
  		borderRadius: {
  			databricks: '8px',
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
}